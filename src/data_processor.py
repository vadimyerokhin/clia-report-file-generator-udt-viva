import pandas as pd

def load_and_process_data(file_path):
    """
    Reads the input CSV file, filters for patient data, and groups it by unique sample.

    Args:
        file_path (str): The path to the input CSV file.

    Returns:
        pandas.core.groupby.generic.DataFrameGroupBy: A pandas DataFrameGroupBy object
        containing the data grouped by unique patient samples.
    """
    # Step 1: Read the Input Data
    try:
        all_data = pd.read_csv(file_path)
    except FileNotFoundError:
        print(f"Error: The file at {file_path} was not found.")
        return None

    # Step 2: Filter the data to include only 'Patient' type rows
    patient_data = all_data[all_data['Type'] == 'Patient'].copy()

    # Step 3: Group Data by Unique Patient Sample (ID and Date collected)
    grouped_samples = patient_data.groupby(['ID', 'Date collected'])

    return grouped_samples

if __name__ == '__main__':
    # This is for testing purposes to ensure the data processing works as expected.
    input_file = 'data/Test_Data.csv'
    processed_data = load_and_process_data(input_file)

    if processed_data:
        print(f"Successfully loaded and processed the data from {input_file}.")
        print(f"Found {len(processed_data)} unique patient samples.")
        for (sample_id, date_collected), sample_group in processed_data:
            patient_name = sample_group['Name'].iloc[0]
            print(f"  - Sample ID: {sample_id}, Date: {date_collected}, Patient: {patient_name}, Rows: {len(sample_group)}")