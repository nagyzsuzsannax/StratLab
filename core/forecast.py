#AI Usage Declaration
#Claude was used to clean up, document and structure this code
#The logic and design decisions are our own product

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

# minimum number of (feature, label) rows needed before a train/test split makes sense
_MIN_SAMPLES = 30


def predict_direction(prices: pd.Series, n_lags: int = 10, test_frac: float = 0.2) -> dict | None:
    """Predict whether tomorrow's return will be positive, using the past `n_lags` daily returns as features.

    Trains a logistic regression on a chronological train/test split and
    returns the test-set accuracy alongside tomorrow's predicted probability
    of a positive return. Returns None if there is not enough data.
    """
    returns = prices.pct_change().dropna()
    if len(returns) < n_lags + _MIN_SAMPLES:
        return None

    # build one row of features per day: the n_lags returns before it, and the
    # label: whether that day's return was positive
    features, labels = [], []
    for i in range(n_lags, len(returns)):
        features.append(returns.iloc[i - n_lags:i].values)
        labels.append(1 if returns.iloc[i] > 0 else 0)
    features = np.array(features)
    labels = np.array(labels)

    # chronological split, so the test set is always "the future" relative to training
    split = int(len(features) * (1 - test_frac))
    x_train, x_test = features[:split], features[split:]
    y_train, y_test = labels[:split], labels[split:]

    # the n_lags daily returns are often correlated with each other (e.g. momentum/mean
    # reversion), so collinearity is handled the same way as elsewhere in the app: instead
    # of an unregularised fit (which could blow up on collinear features), scikit-learn's
    # default L2 penalty shrinks correlated coefficients to stable, finite values
    model = LogisticRegression()
    model.fit(x_train, y_train)
    accuracy = float(model.score(x_test, y_test))

    # predict tomorrow using the most recent n_lags returns
    latest_features = returns.iloc[-n_lags:].values.reshape(1, -1)
    probability_up = float(model.predict_proba(latest_features)[0, 1])

    return {"probability_up": probability_up, "accuracy": accuracy, "n_test": len(y_test)}
