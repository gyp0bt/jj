"""Hyperparameter optimization with Optuna."""

import optuna


def objective(trial):
    lr = trial.suggest_float("learning_rate", 1e-4, 1e-2, log=True)
    batch_size = trial.suggest_categorical("batch_size", [16, 32, 64, 128])
    dropout = trial.suggest_float("dropout", 0.1, 0.5)
    return 0.5  # placeholder


def run_optimization():
    study = optuna.create_study(direction="minimize")
    study.optimize(objective, n_trials=100)
    return study.best_params


if __name__ == "__main__":
    best = run_optimization()
    print(best)
