import pandas as pd
from sklearn.preprocessing import MinMaxScaler

def load_data(file_path):
    # Load your data from CSV or database
    return pd.read_csv(file_path)

def preprocess_data(df, features, target):
    scaler = MinMaxScaler(feature_range=(-1, 1))

    df_scaled = scaler.fit_transform(df[features])
    target_scaled = scaler.fit_transform(df[[target]])

    # Additional preprocessing steps like sequence creation can go here

    return df_scaled, target_scaled


# Assuming you have your data in a variable named 'data'
from state_trajectory_dataset import create_sequences, StateTrajectoryDataset

seq_length = 20  # number of previous timestamps to use as input variables to predict the next timestamp
target_column_index = -1  # waiting time is the last element in the state
sequences, targets = create_sequences(data, seq_length, target_column_index)

# Normalize your sequences and targets as needed
