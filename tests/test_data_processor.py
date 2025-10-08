import unittest
import pandas as pd
import os
from src.data_processor import load_and_process_data
from src.run_summary import RunSummary

class TestDataProcessor(unittest.TestCase):

    def setUp(self):
        """Set up for the test cases."""
        self.summary = RunSummary()
        self.test_data_dir = 'tests/test_data'
        self.good_csv_path = os.path.join(self.test_data_dir, 'sample_data.csv')
        self.empty_csv_path = os.path.join(self.test_data_dir, 'empty_data.csv')
        self.malformed_csv_path = os.path.join(self.test_data_dir, 'malformed_data.csv')
        self.non_existent_csv_path = os.path.join(self.test_data_dir, 'no_such_file.csv')
        self.missing_column_csv_path = os.path.join(self.test_data_dir, 'missing_column.csv')
        self.no_patient_data_csv_path = os.path.join(self.test_data_dir, 'no_patient_data.csv')
        self.inconsistent_columns_csv_path = os.path.join(self.test_data_dir, 'inconsistent_columns.csv')
        self.empty_lines_csv_path = os.path.join(self.test_data_dir, 'empty_lines.csv')
        self.same_date_diff_mrn_csv_path = os.path.join(self.test_data_dir, 'same_date_diff_mrn.csv')

        # Create an empty file for testing
        if not os.path.exists(self.test_data_dir):
            os.makedirs(self.test_data_dir)
        with open(self.empty_csv_path, 'w') as f:
            pass

        # Create a malformed file for testing
        with open(self.malformed_csv_path, 'w') as f:
            f.write("ID,Date collected,Name\\n")
            f.write("1,2023-01-15,John Doe,extra_column\\n")

        # Create a file with a missing required column for PDF generation
        with open(self.missing_column_csv_path, 'w') as f:
            f.write("Type,ID,Date collected,MR#\n")
            f.write("Patient,1,2023-01-15,MRN001\n")

        # Create a file with no 'Patient' data to test the warning
        with open(self.no_patient_data_csv_path, 'w') as f:
            f.write("Type,ID,Date collected,Name,MR#,Date of Birth,Collected by,Test completed,Test Name,Test result\n")
            f.write("Control,C1,2023-01-15,Control A,N/A,N/A,N/A,2023-01-15,QC,Passed\n")

        # Create a file with inconsistent column counts
        with open(self.inconsistent_columns_csv_path, 'w') as f:
            f.write("Col1,Col2,Col3\n")
            f.write("a,b,c\n")
            f.write("d,e\n")

        # Create a file with empty lines
        with open(self.empty_lines_csv_path, 'w') as f:
            f.write("Header1,Header2\n")
            f.write("\n")
            f.write("data1,data2\n")

        # Create a file with same date but different MRNs
        with open(self.same_date_diff_mrn_csv_path, 'w') as f:
            f.write("Type,ID,Date collected,Name,MR#,Date of Birth,Collected by,Test completed,Test Name,Test result\n")
            f.write("Patient,1,2023-01-15,John Doe,MRN001,01/01/1990,Collector,01/15/2023 12:00:00 PM,Test,Positive\n")
            f.write("Patient,2,2023-01-15,Jane Smith,MRN002,02/02/1991,Collector,01/15/2023 12:00:00 PM,Test,Negative\n")

    def tearDown(self):
        """Clean up after tests."""
        if os.path.exists(self.empty_csv_path):
            os.remove(self.empty_csv_path)
        if os.path.exists(self.malformed_csv_path):
            os.remove(self.malformed_csv_path)
        if os.path.exists(self.missing_column_csv_path):
            os.remove(self.missing_column_csv_path)
        if os.path.exists(self.no_patient_data_csv_path):
            os.remove(self.no_patient_data_csv_path)
        if os.path.exists(self.inconsistent_columns_csv_path):
            os.remove(self.inconsistent_columns_csv_path)
        if os.path.exists(self.empty_lines_csv_path):
            os.remove(self.empty_lines_csv_path)
        if os.path.exists(self.same_date_diff_mrn_csv_path):
            os.remove(self.same_date_diff_mrn_csv_path)

    def test_load_and_process_data_success(self):
        """Test successful loading and processing of data."""
        grouped_data = load_and_process_data(self.good_csv_path, self.summary)
        self.assertIsNotNone(grouped_data)
        self.assertIsInstance(grouped_data, pd.core.groupby.generic.DataFrameGroupBy)
        # Expecting 4 unique patient groups from the sample data
        self.assertEqual(len(grouped_data), 4)

    def test_file_not_found(self):
        """Test that a nonexistent file returns None."""
        grouped_data = load_and_process_data(self.non_existent_csv_path, self.summary)
        self.assertIsNone(grouped_data)

    def test_empty_csv(self):
        """Test that an empty CSV file is handled gracefully."""
        grouped_data = load_and_process_data(self.empty_csv_path, self.summary)
        self.assertIsNone(grouped_data)

    def test_malformed_csv(self):
        """Test a malformed CSV file."""
        grouped_data = load_and_process_data(self.malformed_csv_path, self.summary)
        self.assertIsNone(grouped_data)

    def test_filtering_of_patient_data(self):
        """Test that only 'Patient' type rows are included."""
        grouped_data = load_and_process_data(self.good_csv_path, self.summary)
        for _, group in grouped_data:
            self.assertTrue((group['Type'] == 'Patient').all())

    def test_grouping_of_data(self):
        """Test that data is grouped correctly by MR# and Date collected."""
        grouped_data = load_and_process_data(self.good_csv_path, self.summary)
        # Check the groups
        groups = list(grouped_data.groups.keys())
        self.assertIn(('MRN001', '2023-01-15'), groups)
        self.assertIn(('MRN002', '2023-01-16'), groups)
        self.assertIn(('MRN004', '2023-01-18'), groups)
        self.assertIn(('MRN005', '2023-01-19'), groups)

        # Check content of one group
        group1 = grouped_data.get_group(('MRN001', '2023-01-15'))
        self.assertEqual(len(group1), 3)
        self.assertEqual(group1['Name'].iloc[0], 'John Doe')

    def test_missing_required_column(self):
        """Test that a file with a missing required column returns None."""
        grouped_data = load_and_process_data(self.missing_column_csv_path, self.summary)
        self.assertIsNone(grouped_data)

    def test_no_patient_data_warning(self):
        """Test that a warning is printed when no 'Patient' data is found."""
        grouped_data = load_and_process_data(self.no_patient_data_csv_path, self.summary)
        self.assertIsNotNone(grouped_data)
        self.assertEqual(len(grouped_data), 0)

    def test_inconsistent_columns(self):
        """Test that a CSV with inconsistent column counts is handled gracefully."""
        grouped_data = load_and_process_data(self.inconsistent_columns_csv_path, self.summary)
        self.assertIsNone(grouped_data, "Should return None for inconsistent columns.")

    def test_empty_lines_in_csv(self):
        """Test that empty lines in a CSV are ignored."""
        # This test needs a valid file with empty lines. Let's adjust the setup.
        valid_file_with_empty_lines = os.path.join(self.test_data_dir, "valid_with_empty.csv")
        with open(valid_file_with_empty_lines, 'w') as f:
            f.write("Type,ID,Date collected,Name,MR#,Date of Birth,Collected by,Test completed,Test Name,Test result\n")
            f.write("\n")
            f.write("Patient,1,2023-01-15,John Doe,MRN001,01/01/1990,Collector,01/15/2023 12:00:00 PM,Test,Positive\n")
            f.write("\n")

        grouped_data = load_and_process_data(valid_file_with_empty_lines, self.summary)
        self.assertIsNotNone(grouped_data)
        self.assertEqual(len(grouped_data), 1)
        os.remove(valid_file_with_empty_lines)

    def test_same_date_different_mrn(self):
        """Test that records with the same date but different MRNs are in different groups."""
        grouped_data = load_and_process_data(self.same_date_diff_mrn_csv_path, self.summary)
        self.assertIsNotNone(grouped_data)
        self.assertEqual(len(grouped_data), 2, "Should create two separate groups for different MRNs on the same day.")
        groups = list(grouped_data.groups.keys())
        self.assertIn(('MRN001', '2023-01-15'), groups)
        self.assertIn(('MRN002', '2023-01-15'), groups)

if __name__ == '__main__':
    unittest.main()