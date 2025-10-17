"""Unit tests for the billing_generator module.

This module tests all functionality related to medical billing file generation,
including name parsing, date formatting, and complete billing file creation.
"""
import unittest
import os
import csv
import tempfile
import shutil
import pandas as pd
from datetime import datetime
from src.billing_generator import parse_patient_name, format_date_for_billing, generate_billing_file
from src.run_summary import RunSummary


class TestParsePatientName(unittest.TestCase):
    """Test cases for the parse_patient_name function."""

    def test_standard_two_word_name(self):
        """Test parsing of standard 'FIRST LAST' format."""
        first, last = parse_patient_name("JOHN SMITH")
        self.assertEqual(first, "JOHN")
        self.assertEqual(last, "SMITH")

    def test_three_word_name(self):
        """Test parsing of three-word names (middle name or compound last name)."""
        first, last = parse_patient_name("MARY ANN SMITH")
        self.assertEqual(first, "MARY")
        self.assertEqual(last, "ANN SMITH")

    def test_single_word_name(self):
        """Test parsing of single-word names (like 'CHER')."""
        first, last = parse_patient_name("CHER")
        self.assertEqual(first, "")
        self.assertEqual(last, "CHER")

    def test_empty_string(self):
        """Test handling of empty string input."""
        first, last = parse_patient_name("")
        self.assertEqual(first, "")
        self.assertEqual(last, "UNKNOWN")

    def test_none_input(self):
        """Test handling of None input."""
        first, last = parse_patient_name(None)
        self.assertEqual(first, "")
        self.assertEqual(last, "UNKNOWN")

    def test_whitespace_only(self):
        """Test handling of whitespace-only input."""
        first, last = parse_patient_name("   ")
        self.assertEqual(first, "")
        self.assertEqual(last, "UNKNOWN")

    def test_multiple_spaces_between_words(self):
        """Test handling of multiple spaces between name parts."""
        first, last = parse_patient_name("JOHN    SMITH")
        self.assertEqual(first, "JOHN")
        self.assertEqual(last, "SMITH")

    def test_name_with_suffix(self):
        """Test parsing of names with suffixes."""
        first, last = parse_patient_name("JOHN SMITH JR")
        self.assertEqual(first, "JOHN")
        self.assertEqual(last, "SMITH JR")

    def test_four_word_name(self):
        """Test parsing of four-word names."""
        first, last = parse_patient_name("MARY ANN LOUISE SMITH")
        self.assertEqual(first, "MARY")
        self.assertEqual(last, "ANN LOUISE SMITH")


class TestFormatDateForBilling(unittest.TestCase):
    """Test cases for the format_date_for_billing function."""

    def test_slash_format_with_leading_zeros(self):
        """Test MM/DD/YYYY format with leading zeros."""
        result = format_date_for_billing("10/02/2025")
        self.assertEqual(result, "10/02/2025")

    def test_slash_format_without_leading_zeros(self):
        """Test M/D/YYYY format without leading zeros."""
        result = format_date_for_billing("10/2/2025")
        self.assertEqual(result, "10/02/2025")

    def test_dash_format_iso(self):
        """Test ISO format YYYY-MM-DD."""
        result = format_date_for_billing("2025-10-02")
        self.assertEqual(result, "10/02/2025")

    def test_datetime_object(self):
        """Test with datetime object input."""
        dt = datetime(2025, 10, 2)
        result = format_date_for_billing(dt)
        self.assertEqual(result, "10/02/2025")

    def test_pandas_timestamp(self):
        """Test with pandas Timestamp input."""
        ts = pd.Timestamp("2025-10-02")
        result = format_date_for_billing(ts)
        self.assertEqual(result, "10/02/2025")

    def test_none_input(self):
        """Test handling of None input."""
        result = format_date_for_billing(None)
        self.assertEqual(result, "UNKNOWN")

    def test_empty_string(self):
        """Test handling of empty string input."""
        result = format_date_for_billing("")
        self.assertEqual(result, "UNKNOWN")

    def test_invalid_date_string(self):
        """Test handling of invalid date string."""
        result = format_date_for_billing("not-a-date")
        self.assertEqual(result, "UNKNOWN")

    def test_custom_default_value(self):
        """Test custom default value for invalid dates."""
        result = format_date_for_billing(None, default="N/A")
        self.assertEqual(result, "N/A")

    def test_date_with_time(self):
        """Test date string with time component."""
        result = format_date_for_billing("10/2/2025 3:59:35 PM")
        self.assertEqual(result, "10/02/2025")


class TestGenerateBillingFile(unittest.TestCase):
    """Test cases for the generate_billing_file function."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.summary = RunSummary()

    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def create_sample_grouped_data(self):
        """Create sample grouped data for testing."""
        data = {
            'Type': ['Patient', 'Patient', 'Patient', 'Patient'],
            'ID': ['1', '1', '5', '5'],
            'Name': ['THOMAS ARNETT', 'THOMAS ARNETT', 'WILLIAM COX', 'WILLIAM COX'],
            'MR#': ['ARNETT-T-2002', 'ARNETT-T-2002', 'COX-W-1979', 'COX-W-1979'],
            'Date collected': ['10/2/2025', '10/2/2025', '10/3/2025', '10/3/2025'],
            'Date of Birth': ['9/23/2002', '9/23/2002', '7/6/1979', '7/6/1979'],
            'Collected by': ['TP', 'TP', 'JC', 'JC'],
            'Test completed': ['10/6/2025 3:59:35 PM', '10/6/2025 3:59:35 PM',
                             '10/6/2025 4:23:00 PM', '10/6/2025 4:23:00 PM'],
            'Test Name': ['Amphetamines 500', 'Barbiturates',
                         'Amphetamines 500', 'Buprenorphine 5'],
            'Test result': ['Negative', 'Negative', 'Negative', 'Positive']
        }
        df = pd.DataFrame(data)
        return df.groupby(['MR#', 'Date collected'])

    def test_generate_billing_file_creates_file(self):
        """Test that billing file is created successfully."""
        grouped_data = self.create_sample_grouped_data()
        billing_file = generate_billing_file(grouped_data, self.test_dir, self.summary)

        self.assertTrue(os.path.exists(billing_file))
        self.assertTrue(billing_file.endswith('.csv'))
        self.assertIn('billing_80307_', billing_file)

    def test_billing_file_has_correct_headers(self):
        """Test that billing file has all required column headers."""
        grouped_data = self.create_sample_grouped_data()
        billing_file = generate_billing_file(grouped_data, self.test_dir, self.summary)

        with open(billing_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            headers = next(reader)

        expected_headers = [
            'Patient_Last_Name',
            'Patient_First_Name',
            'Patient_MRN',
            'Date_of_Birth',
            'Date_of_Service',
            'CPT_Code',
            'Units',
            'Specimen_ID',
            'Ordering_Provider',
            'Test_Completed_Date'
        ]

        self.assertEqual(headers, expected_headers)

    def test_billing_file_correct_record_count(self):
        """Test that billing file has correct number of records."""
        grouped_data = self.create_sample_grouped_data()
        billing_file = generate_billing_file(grouped_data, self.test_dir, self.summary)

        df = pd.read_csv(billing_file)
        # Should have 2 unique patients (2 unique MR# + Date collected combinations)
        self.assertEqual(len(df), 2)

    def test_billing_records_have_correct_data(self):
        """Test that billing records contain correct patient data."""
        grouped_data = self.create_sample_grouped_data()
        billing_file = generate_billing_file(grouped_data, self.test_dir, self.summary)

        # Read with dtype to preserve string format for numeric columns
        df = pd.read_csv(billing_file, dtype=str)

        # Check first patient
        patient1 = df[df['Patient_MRN'] == 'ARNETT-T-2002'].iloc[0]
        self.assertEqual(patient1['Patient_First_Name'], 'THOMAS')
        self.assertEqual(patient1['Patient_Last_Name'], 'ARNETT')
        self.assertEqual(patient1['Date_of_Birth'], '09/23/2002')
        self.assertEqual(patient1['Date_of_Service'], '10/02/2025')
        self.assertEqual(patient1['CPT_Code'], '80307')
        self.assertEqual(patient1['Units'], '1')
        self.assertEqual(patient1['Specimen_ID'], '1')
        self.assertEqual(patient1['Ordering_Provider'], 'TP')

        # Check second patient
        patient2 = df[df['Patient_MRN'] == 'COX-W-1979'].iloc[0]
        self.assertEqual(patient2['Patient_First_Name'], 'WILLIAM')
        self.assertEqual(patient2['Patient_Last_Name'], 'COX')

    def test_cpt_code_always_80307(self):
        """Test that all records have CPT code 80307."""
        grouped_data = self.create_sample_grouped_data()
        billing_file = generate_billing_file(grouped_data, self.test_dir, self.summary)

        df = pd.read_csv(billing_file, dtype=str)
        self.assertTrue(all(df['CPT_Code'] == '80307'))

    def test_units_always_one(self):
        """Test that all records have units set to 1."""
        grouped_data = self.create_sample_grouped_data()
        billing_file = generate_billing_file(grouped_data, self.test_dir, self.summary)

        df = pd.read_csv(billing_file, dtype=str)
        self.assertTrue(all(df['Units'] == '1'))

    def test_summary_tracks_billing_entries(self):
        """Test that RunSummary correctly tracks billing entries."""
        grouped_data = self.create_sample_grouped_data()
        generate_billing_file(grouped_data, self.test_dir, self.summary)

        self.assertEqual(self.summary.get_billing_count(), 2)

    def test_summary_records_billing_file_path(self):
        """Test that RunSummary records the billing file path."""
        grouped_data = self.create_sample_grouped_data()
        billing_file = generate_billing_file(grouped_data, self.test_dir, self.summary)

        self.assertEqual(self.summary._billing_file_path, billing_file)

    def test_handles_missing_optional_fields(self):
        """Test handling of missing optional fields (DOB, provider)."""
        data = {
            'Type': ['Patient', 'Patient'],
            'ID': ['1', '1'],
            'Name': ['JOHN DOE', 'JOHN DOE'],
            'MR#': ['DOE-J-2000', 'DOE-J-2000'],
            'Date collected': ['10/1/2025', '10/1/2025'],
            'Date of Birth': [None, None],  # Missing DOB
            'Collected by': ['', ''],  # Missing provider
            'Test completed': ['10/5/2025', '10/5/2025'],
            'Test Name': ['Test1', 'Test2'],
            'Test result': ['Negative', 'Negative']
        }
        df = pd.DataFrame(data)
        grouped_data = df.groupby(['MR#', 'Date collected'])

        billing_file = generate_billing_file(grouped_data, self.test_dir, self.summary)
        df_billing = pd.read_csv(billing_file, keep_default_na=False)

        # Should still create record with empty optional fields
        self.assertEqual(len(df_billing), 1)
        self.assertEqual(df_billing.iloc[0]['Date_of_Birth'], '')
        self.assertEqual(df_billing.iloc[0]['Ordering_Provider'], '')

    def test_filename_includes_timestamp(self):
        """Test that billing file name includes timestamp."""
        grouped_data = self.create_sample_grouped_data()
        billing_file = generate_billing_file(grouped_data, self.test_dir, self.summary)

        filename = os.path.basename(billing_file)
        # Should match pattern: billing_80307_YYYYMMDD_HHMMSS.csv
        self.assertRegex(filename, r'billing_80307_\d{8}_\d{6}\.csv')

    def test_multiple_calls_create_unique_files(self):
        """Test that multiple calls create uniquely named files."""
        grouped_data = self.create_sample_grouped_data()

        billing_file1 = generate_billing_file(grouped_data, self.test_dir, self.summary)
        # Small delay to ensure different timestamp
        import time
        time.sleep(1)
        summary2 = RunSummary()
        billing_file2 = generate_billing_file(grouped_data, self.test_dir, summary2)

        self.assertNotEqual(billing_file1, billing_file2)
        self.assertTrue(os.path.exists(billing_file1))
        self.assertTrue(os.path.exists(billing_file2))


if __name__ == '__main__':
    unittest.main()
