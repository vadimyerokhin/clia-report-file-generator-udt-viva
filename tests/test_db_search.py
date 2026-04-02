"""Tests for the db_search module."""
import csv
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.db_search import (
    db_exists,
    find_billing_files,
    find_report_pdf,
    get_db_path,
    get_distinct_test_names,
    get_specimen_details,
    open_file,
    search_patients,
)


def _create_test_db(db_path: Path):
    """Create a minimal lab_results database for testing."""
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()

    c.execute("""
        CREATE TABLE patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mrn TEXT NOT NULL UNIQUE,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            date_of_birth TEXT,
            sex TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    c.execute("""
        CREATE TABLE import_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_folder TEXT NOT NULL,
            export_file TEXT,
            billing_file TEXT,
            imported_at TEXT NOT NULL,
            export_rows INTEGER DEFAULT 0,
            billing_rows INTEGER DEFAULT 0,
            UNIQUE(run_folder, export_file)
        )
    """)

    c.execute("""
        CREATE TABLE specimens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL REFERENCES patients(id),
            import_run_id INTEGER NOT NULL REFERENCES import_runs(id),
            specimen_id_in_run INTEGER,
            specimen_type TEXT NOT NULL DEFAULT 'Urine',
            collection_date TEXT,
            collected_by TEXT,
            request_type TEXT,
            physician TEXT,
            tested_by TEXT,
            comment TEXT,
            is_retest INTEGER NOT NULL DEFAULT 0,
            retest_comment TEXT,
            UNIQUE(patient_id, collection_date, specimen_id_in_run, import_run_id)
        )
    """)

    c.execute("""
        CREATE TABLE test_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            specimen_id INTEGER NOT NULL REFERENCES specimens(id),
            test_name TEXT NOT NULL,
            test_abbreviation TEXT NOT NULL,
            test_code INTEGER,
            test_revision INTEGER,
            result TEXT,
            calculated_result TEXT,
            units TEXT,
            flags TEXT,
            test_completed_at TEXT,
            is_positive INTEGER NOT NULL DEFAULT 0,
            is_pending INTEGER NOT NULL DEFAULT 0,
            UNIQUE(specimen_id, test_code)
        )
    """)

    # Insert test data
    c.execute("""
        INSERT INTO import_runs (run_folder, export_file, imported_at)
        VALUES ('20260301', 'export_test.csv', '2026-03-01T12:00:00')
    """)

    c.execute("""
        INSERT INTO patients (mrn, first_name, last_name, date_of_birth, sex, created_at, updated_at)
        VALUES ('MRN001', 'John', 'Doe', '1990-05-15', 'M', '2026-03-01T12:00:00', '2026-03-01T12:00:00')
    """)
    c.execute("""
        INSERT INTO patients (mrn, first_name, last_name, date_of_birth, sex, created_at, updated_at)
        VALUES ('MRN002', 'Jane', 'Smith', '1985-11-22', 'F', '2026-03-01T12:00:00', '2026-03-01T12:00:00')
    """)

    c.execute("""
        INSERT INTO specimens (patient_id, import_run_id, specimen_id_in_run, collection_date, collected_by)
        VALUES (1, 1, 100, '2026-03-01', 'Dr. Test')
    """)
    c.execute("""
        INSERT INTO specimens (patient_id, import_run_id, specimen_id_in_run, collection_date, collected_by)
        VALUES (2, 1, 101, '2026-03-02', 'Dr. Other')
    """)

    # John Doe: 2 tests (1 positive THC, 1 negative AMP)
    c.execute("""
        INSERT INTO test_results (specimen_id, test_name, test_abbreviation, test_code,
                                  result, units, flags, test_completed_at, is_positive, is_pending)
        VALUES (1, 'THC (Marijuana)', 'THC', 1, 'Positive', 'ng/mL', '', '2026-03-01', 1, 0)
    """)
    c.execute("""
        INSERT INTO test_results (specimen_id, test_name, test_abbreviation, test_code,
                                  result, units, flags, test_completed_at, is_positive, is_pending)
        VALUES (1, 'Amphetamines', 'AMP', 2, 'Negative', 'ng/mL', '', '2026-03-01', 0, 0)
    """)

    # Jane Smith: 1 test (pending)
    c.execute("""
        INSERT INTO test_results (specimen_id, test_name, test_abbreviation, test_code,
                                  result, units, flags, test_completed_at, is_positive, is_pending)
        VALUES (2, 'Cocaine', 'COC', 3, '--', 'ng/mL', '', '', 0, 1)
    """)

    conn.commit()
    conn.close()


class TestDbPath(unittest.TestCase):
    def test_get_db_path_returns_path(self):
        path = get_db_path()
        self.assertIsInstance(path, Path)
        self.assertTrue(str(path).endswith("lab_results.db"))

    def test_db_exists_false_when_missing(self):
        with patch("src.db_search.DB_PATH", Path("/nonexistent/path/db.sqlite3")):
            self.assertFalse(db_exists())


class TestSearchPatients(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = Path(self.tmpdir) / "lab_results.db"
        _create_test_db(self.db_path)
        self._patcher = patch("src.db_search.DB_PATH", self.db_path)
        self._patcher.start()

    def tearDown(self):
        self._patcher.stop()
        os.unlink(self.db_path)
        os.rmdir(self.tmpdir)

    def test_search_by_name(self):
        results, total = search_patients(query="John")
        self.assertEqual(total, 1)
        self.assertEqual(results[0]["mrn"], "MRN001")
        self.assertEqual(results[0]["patient_name"], "John Doe")

    def test_search_by_mrn(self):
        results, total = search_patients(query="MRN002")
        self.assertEqual(total, 1)
        self.assertEqual(results[0]["last_name"], "Smith")

    def test_search_by_partial_name(self):
        results, total = search_patients(query="ohn")
        self.assertEqual(total, 1)

    def test_search_case_insensitive_name(self):
        """SQLite LIKE is case-insensitive for ASCII by default."""
        results, total = search_patients(query="john")
        self.assertEqual(total, 1)

    def test_search_empty_query_with_filter(self):
        results, total = search_patients(test_result="Positive")
        self.assertEqual(total, 1)
        self.assertEqual(results[0]["mrn"], "MRN001")

    def test_search_date_range(self):
        results, total = search_patients(
            query="", date_from="2026-03-01", date_to="2026-03-01"
        )
        self.assertEqual(total, 1)
        self.assertEqual(results[0]["mrn"], "MRN001")

    def test_search_date_to_inclusive(self):
        results, total = search_patients(
            query="", date_from="2026-03-01", date_to="2026-03-02"
        )
        self.assertEqual(total, 2)

    def test_search_by_dob(self):
        results, total = search_patients(dob="1990-05-15")
        self.assertEqual(total, 1)
        self.assertEqual(results[0]["mrn"], "MRN001")

    def test_search_by_collected_by(self):
        results, total = search_patients(collected_by="Dr. Test")
        self.assertEqual(total, 1)

    def test_search_by_test_name(self):
        results, total = search_patients(test_name="THC")
        self.assertEqual(total, 1)
        self.assertEqual(results[0]["mrn"], "MRN001")

    def test_search_pending_results(self):
        results, total = search_patients(test_result="Pending")
        self.assertEqual(total, 1)
        self.assertEqual(results[0]["mrn"], "MRN002")

    def test_search_negative_results(self):
        results, total = search_patients(test_result="Negative")
        self.assertEqual(total, 1)
        self.assertEqual(results[0]["mrn"], "MRN001")

    def test_search_no_results(self):
        results, total = search_patients(query="Nonexistent")
        self.assertEqual(total, 0)
        self.assertEqual(results, [])

    def test_search_pagination(self):
        results, total = search_patients(query="", date_from="2026-03-01",
                                         date_to="2026-03-31", limit=1, offset=0)
        self.assertEqual(total, 2)
        self.assertEqual(len(results), 1)

        results2, _ = search_patients(query="", date_from="2026-03-01",
                                      date_to="2026-03-31", limit=1, offset=1)
        self.assertEqual(len(results2), 1)
        self.assertNotEqual(results[0]["mrn"], results2[0]["mrn"])

    def test_result_fields(self):
        results, _ = search_patients(query="John")
        r = results[0]
        self.assertIn("first_name", r)
        self.assertIn("last_name", r)
        self.assertIn("patient_name", r)
        self.assertIn("mrn", r)
        self.assertIn("dob", r)
        self.assertIn("collection_date", r)
        self.assertIn("specimen_id", r)
        self.assertIn("num_tests", r)
        self.assertIn("num_positive", r)
        self.assertEqual(r["num_tests"], 2)
        self.assertEqual(r["num_positive"], 1)

    def test_sql_injection_safe(self):
        """Verify parameterised queries prevent injection."""
        results, total = search_patients(query="'; DROP TABLE patients; --")
        self.assertEqual(total, 0)
        # Verify table still exists
        results2, total2 = search_patients(query="John")
        self.assertEqual(total2, 1)


class TestSpecimenDetails(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = Path(self.tmpdir) / "lab_results.db"
        _create_test_db(self.db_path)
        self._patcher = patch("src.db_search.DB_PATH", self.db_path)
        self._patcher.start()

    def tearDown(self):
        self._patcher.stop()
        os.unlink(self.db_path)
        os.rmdir(self.tmpdir)

    def test_get_details(self):
        details = get_specimen_details(1)
        self.assertEqual(len(details), 2)
        test_names = [d["test_name"] for d in details]
        self.assertIn("THC (Marijuana)", test_names)
        self.assertIn("Amphetamines", test_names)

    def test_get_details_nonexistent_specimen(self):
        details = get_specimen_details(999)
        self.assertEqual(details, [])


class TestDistinctTestNames(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = Path(self.tmpdir) / "lab_results.db"
        _create_test_db(self.db_path)
        self._patcher = patch("src.db_search.DB_PATH", self.db_path)
        self._patcher.start()

    def tearDown(self):
        self._patcher.stop()
        os.unlink(self.db_path)
        os.rmdir(self.tmpdir)

    def test_distinct_names(self):
        names = get_distinct_test_names()
        self.assertEqual(len(names), 3)
        self.assertIn("THC (Marijuana)", names)
        self.assertIn("Amphetamines", names)
        self.assertIn("Cocaine", names)
        # Should be sorted
        self.assertEqual(names, sorted(names))


class TestFindReportPdf(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir)

    def test_find_exact_match(self):
        # Create a PDF with the expected naming convention
        pdf_name = "John-Doe_MRN001_2026-03-01.pdf"
        pdf_path = os.path.join(self.tmpdir, pdf_name)
        with open(pdf_path, 'w') as f:
            f.write("dummy")

        matches = find_report_pdf(self.tmpdir, "John", "Doe", "MRN001", "2026-03-01")
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0], pdf_path)

    def test_find_in_subdirectory(self):
        subdir = os.path.join(self.tmpdir, "2026-03-01")
        os.makedirs(subdir)
        pdf_name = "John-Doe_MRN001_2026-03-01.pdf"
        pdf_path = os.path.join(subdir, pdf_name)
        with open(pdf_path, 'w') as f:
            f.write("dummy")

        matches = find_report_pdf(self.tmpdir, "John", "Doe", "MRN001", "2026-03-01")
        self.assertEqual(len(matches), 1)

    def test_find_fallback_mrn_suffix(self):
        """Should find by MRN+date suffix if exact name doesn't match."""
        pdf_name = "Different-Name_MRN001_2026-03-01.pdf"
        pdf_path = os.path.join(self.tmpdir, pdf_name)
        with open(pdf_path, 'w') as f:
            f.write("dummy")

        matches = find_report_pdf(self.tmpdir, "John", "Doe", "MRN001", "2026-03-01")
        self.assertEqual(len(matches), 1)

    def test_no_match(self):
        matches = find_report_pdf(self.tmpdir, "John", "Doe", "MRN001", "2026-03-01")
        self.assertEqual(matches, [])

    def test_invalid_directory(self):
        matches = find_report_pdf("/nonexistent/path", "John", "Doe", "MRN001", "2026-03-01")
        self.assertEqual(matches, [])

    def test_empty_directory(self):
        matches = find_report_pdf("", "John", "Doe", "MRN001", "2026-03-01")
        self.assertEqual(matches, [])

    def test_multiple_matches(self):
        """When same file exists in multiple subdirectories."""
        pdf_name = "John-Doe_MRN001_2026-03-01.pdf"
        for subdir_name in ["2026-03-01", "backup"]:
            subdir = os.path.join(self.tmpdir, subdir_name)
            os.makedirs(subdir)
            with open(os.path.join(subdir, pdf_name), 'w') as f:
                f.write("dummy")

        matches = find_report_pdf(self.tmpdir, "John", "Doe", "MRN001", "2026-03-01")
        self.assertEqual(len(matches), 2)


class TestFindBillingFiles(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir)

    def _create_billing_csv(self, filename, rows):
        filepath = os.path.join(self.tmpdir, filename)
        with open(filepath, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                "Patient_Last_Name", "Patient_First_Name", "Patient_MRN",
                "Date_of_Birth", "Date_of_Service", "CPT_Code", "Units",
                "Specimen_ID", "Ordering_Provider", "Test_Completed_Date"
            ])
            writer.writeheader()
            writer.writerows(rows)
        return filepath

    def test_find_by_mrn(self):
        self._create_billing_csv("billing_80307_20260301_120000.csv", [
            {"Patient_Last_Name": "Doe", "Patient_First_Name": "John",
             "Patient_MRN": "MRN001", "Date_of_Birth": "05/15/1990",
             "Date_of_Service": "03/01/2026", "CPT_Code": "80307",
             "Units": "1", "Specimen_ID": "100", "Ordering_Provider": "Dr. Test",
             "Test_Completed_Date": "03/01/2026"}
        ])

        matches = find_billing_files(self.tmpdir, "MRN001")
        self.assertEqual(len(matches), 1)

    def test_find_by_mrn_and_date(self):
        self._create_billing_csv("billing_80307_20260301_120000.csv", [
            {"Patient_Last_Name": "Doe", "Patient_First_Name": "John",
             "Patient_MRN": "MRN001", "Date_of_Birth": "05/15/1990",
             "Date_of_Service": "03/01/2026", "CPT_Code": "80307",
             "Units": "1", "Specimen_ID": "100", "Ordering_Provider": "Dr. Test",
             "Test_Completed_Date": "03/01/2026"}
        ])

        matches = find_billing_files(self.tmpdir, "MRN001", "2026-03-01")
        self.assertEqual(len(matches), 1)

    def test_no_match_wrong_mrn(self):
        self._create_billing_csv("billing_80307_20260301_120000.csv", [
            {"Patient_Last_Name": "Doe", "Patient_First_Name": "John",
             "Patient_MRN": "MRN001", "Date_of_Birth": "05/15/1990",
             "Date_of_Service": "03/01/2026", "CPT_Code": "80307",
             "Units": "1", "Specimen_ID": "100", "Ordering_Provider": "Dr. Test",
             "Test_Completed_Date": "03/01/2026"}
        ])

        matches = find_billing_files(self.tmpdir, "MRN999")
        self.assertEqual(matches, [])

    def test_invalid_directory(self):
        matches = find_billing_files("/nonexistent/path", "MRN001")
        self.assertEqual(matches, [])

    def test_non_billing_csv_ignored(self):
        """Files not matching billing_80307_*.csv pattern are ignored."""
        filepath = os.path.join(self.tmpdir, "other_file.csv")
        with open(filepath, 'w') as f:
            f.write("Patient_MRN\nMRN001\n")

        matches = find_billing_files(self.tmpdir, "MRN001")
        self.assertEqual(matches, [])


class TestOpenFile(unittest.TestCase):
    @patch("subprocess.run")
    def test_open_file_success(self, mock_run):
        result = open_file("/tmp/test.pdf")
        self.assertIsNone(result)
        mock_run.assert_called_once()

    @patch("subprocess.run", side_effect=Exception("No app"))
    def test_open_file_failure(self, mock_run):
        result = open_file("/tmp/test.pdf")
        self.assertIsNotNone(result)
        self.assertIn("Could not open file", result)


if __name__ == '__main__':
    unittest.main()
