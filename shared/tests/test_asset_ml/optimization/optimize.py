"""Optuna hyperparameter optimization script."""

import optuna


def objective(trial):
    lr = trial.suggest_float("learning_rate", 1e-4, 1e-1, log=True)
    batch_size = trial.suggest_categorical("batch_size", [16, 32, 64, 128])
    n_layers = trial.suggest_int("n_layers", 1, 5)

    model = build_model(n_layers)
    loss = train_and_evaluate(model, lr, batch_size)
    return loss


def build_model(n_layers):
    pass


def train_and_evaluate(model, lr, batch_size):
    return 0.0


if __name__ == "__main__":
    study = optuna.create_study(direction="minimize")
    study.optimize(objective, n_trials=100)
