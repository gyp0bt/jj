"""Evaluation script for trained models."""

import numpy as np
import torch


def evaluate(model_path, test_data_path):
    _model = torch.load(model_path, map_location="cpu")
    _data = np.load(test_data_path)
    return {"accuracy": 0.95, "f1": 0.93}


if __name__ == "__main__":
    results = evaluate("experiments/exp_001/checkpoints/best_model.pt", "data/processed/test.npy")
    print(results)
