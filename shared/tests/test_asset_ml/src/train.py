"""Training script for ResNet model."""

import torch
import torch.nn as nn
import yaml


def load_config(config_path):
    with open(config_path) as f:
        return yaml.safe_load(f)


def train(config):
    model = torch.hub.load("pytorch/vision", config["model"]["name"].lower())
    optimizer = torch.optim.Adam(model.parameters(), lr=config["training"]["learning_rate"])
    criterion = nn.CrossEntropyLoss()
    return model


if __name__ == "__main__":
    config = load_config("configs/train_config.yaml")
    model = train(config)
