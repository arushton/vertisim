import pandas as pd


def read_input_file(file_path: str, sheet_name: str = 'Sheet1') -> pd.DataFrame:
    """
    Function that can read the input file and create a pandas dataframe.
    The input file extension can be types of .csv, .parquet, .hdf5, and .xlsx
    :param sheet_name:
    :param file_path:
    :return: pd.DataFrame
    """
    file_type = detect_file_type(file_path)
    if file_type == 'csv':
        return pd.read_csv(file_path)
    elif file_type == 'parquet':
        return pd.read_parquet(file_path)
    elif file_type == 'hdf5':
        return pd.read_hdf(file_path)
    elif file_type in ['xlsx', 'xls']:
        return pd.read_excel(file_path, sheet_name=sheet_name)
    else:
        raise ValueError(f'The file type is not supported: {file_path}')


def detect_file_type(file_path: str) -> str:
    """
    Function that detects the file type of the input file
    :param file_path:
    :return: str
    """
    if file_path is None:
        raise ValueError('File path is None.')
    return file_path.split('.')[-1]
