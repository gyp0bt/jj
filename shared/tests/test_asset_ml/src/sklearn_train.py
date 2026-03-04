"""scikit-learn training script."""

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split


def train_sklearn():
    df = pd.read_csv("data/raw/dataset_v1.csv")
    X = df.drop("label", axis=1)
    y = df["label"]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

    model = RandomForestClassifier(n_estimators=100)
    model.fit(X_train, y_train)

    accuracy = accuracy_score(y_test, model.predict(X_test))
    print(f"Accuracy: {accuracy}")

    joblib.dump(model, "outputs/sklearn_model.joblib")


if __name__ == "__main__":
    train_sklearn()
