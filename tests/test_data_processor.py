import unittest
import pandas as pd
import os
from src.data_processor import load_and_process_data

class TestDataProcessor(unittest.TestCase):

    def setUp(self):
        """Set up for the test cases."""
        self.test_data_dir = 'tests/test_data'
        self.good_csv_path = os.path.join(self.test_data_dir, 'sample_data.csv')
        self.empty_csv_path = os.path.join(self.test_data_dir, 'empty_data.csv')
        self.malformed_csv_path = os.path.join(self.test_data_dir, 'malformed_data.csv')
        self.non_existent_csv_path = os.path.join(self.test_data_dir, 'no_such_file.csv')
        self.missing_column_csv_path = os.path.join(self.test_data_dir, 'missing_column.csv')

        # Create an empty file for testing
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

    def tearDown(self):
        """Clean up after tests."""
        if os.path.exists(self.empty_csv_path):
            os.remove(self.empty_csv_path)
        if os.path.exists(self.malformed_csv_path):
            os.remove(self.malformed_csv_path)
        if os.path.exists(self.missing_column_csv_path):
            os.remove(self.missing_column_csv_path)

    def test_load_and_process_data_success(self):
        """Test successful loading and processing of data."""
        grouped_data = load_and_process_data(self.good_csv_path)
        self.assertIsNotNone(grouped_data)
        self.assertIsInstance(grouped_data, pd.core.groupby.generic.DataFrameGroupBy)
        # Expecting 4 unique patient groups from the sample data
        self.assertEqual(len(grouped_data), 4)

    def test_file_not_found(self):
        """Test that a nonexistent file returns None."""
        grouped_data = load_and_process_data(self.non_existent_csv_path)
        self.assertIsNone(grouped_data)

    def test_empty_csv(self):
        """Test that an empty CSV file is handled gracefully."""
        grouped_data = load_and_process_data(self.empty_csv_path)
        self.assertIsNone(grouped_data)

    def test_malformed_csv(self):
        """Test a malformed CSV file."""
        grouped_data = load_and_process_data(self.malformed_csv_path)
        self.assertIsNone(grouped_data)

    def test_filtering_of_patient_data(self):
        """Test that only 'Patient' type rows are included."""
        grouped_data = load_and_process_data(self.good_csv_path)
        for _, group in grouped_data:
            self.assertTrue((group['Type'] == 'Patient').all())

    def test_grouping_of_data(self):
        """Test that data is grouped correctly by MR# and Date collected."""
        grouped_data = load_and_process_data(self.good_csv_path)
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
        grouped_data = load_and_process_data(self.missing_column_csv_path)
        self.assertIsNone(grouped_data)

if __name__ == '__main__':
    unittest.main()