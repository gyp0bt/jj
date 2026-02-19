"""Surrogate model training script."""
import torch
import torch.nn as nn
from torch.utils.data import DataLoader


class SurrogateNet(nn.Module):
    def __init__(self, input_dim, hidden_dim, output_dim):
        super().__init__()
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, output_dim)

    def forward(self, x):
        return self.fc2(torch.relu(self.fc1(x)))
