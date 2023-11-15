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
