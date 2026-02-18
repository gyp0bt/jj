"""Data preprocessing script."""

import numpy as np
import pandas as pd


def preprocess(input_path, output_dir):
    df = pd.read_csv(input_path)
    train = df.sample(frac=0.8, random_state=42)
    val = df.drop(train.index).sample(frac=0.5, random_state=42)
    test = df.drop(train.index).drop(val.index)

    np.save(f"{output_dir}/train.npy", train.values)
    np.save(f"{output_dir}/val.npy", val.values)
    np.save(f"{output_dir}/test.npy", test.values)


if __name__ == "__main__":
    preprocess("data/raw/dataset_v1.csv", "data/processed")
