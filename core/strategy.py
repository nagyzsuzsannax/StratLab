#AI Usage Declaration
#Claude was used to clean up, document and structure this code
#The strategy logic (rebalancing, weighting schemes) follows the AQAM (Advanced
#Quantitative Asset Management) course at the University of St. Gallen
#The logic and design decisions are our own product

import numpy as np
import pandas as pd

from core import measures


def build_weights(tickers: list[str], values: list[float]) -> dict[str, float]:
    """Zip tickers and values into the {ticker: weight} dict every strategy returns."""
    weights = {}
    for ticker, value in zip(tickers, values):
        weights[ticker] = value
    return weights


def _should_rebalance(last_rebalance_date, current_date, rebalance_every: int) -> bool:
    """Return True if it is time to recompute weights.

    True on the very first call (last_rebalance_date is None) or once at
    least `rebalance_every` days have passed since the last rebalance.
    """
    if last_rebalance_date is None:
        return True
    days_since_rebalance = (current_date - last_rebalance_date).days
    return days_since_rebalance >= rebalance_every


def _normalise_weights(values: list[float]) -> list[float]:
    """Scale a list of non-negative values so that they sum to 1.

    Returns all zeros if the values sum to 0, instead of dividing by zero.
    """
    total = sum(values)
    if total == 0:
        return [0.0 for _ in values]
    return [value / total for value in values]


class Momentum:
    """Ranks assets by past return over a lookback period and invests in the top performers.

    Based on the cross-sectional momentum effect documented by Jegadeesh &
    Titman (1993). `lookback` and `top_n` are passed by the user. Rebalances
    every `rebalance_every` days (default 252 = 1 year). `short`: optionally
    short the bottom performers (off by default). `bottom_n`: how many
    laggards to short (only used when short=True).
    """

    def __init__(self, lookback: int, top_n: int, short: bool = False, bottom_n: int = 3, rebalance_every: int = 252) -> None:
        self.lookback = lookback
        self.top_n = top_n
        self.short = short
        self.bottom_n = bottom_n
        self.rebalance_every = rebalance_every
        self.last_rebalance_date = None
        self.current_weights = {}
        self.weight_history = []

    def get_weights(self, prices: pd.DataFrame) -> dict[str, float]:
        """Return the current target weights, rebalancing if it is due."""
        current_date = prices.index[-1]

        if not _should_rebalance(self.last_rebalance_date, current_date, self.rebalance_every):
            return self.current_weights

        # use only the most recent lookback days
        recent_prices = prices.tail(self.lookback)

        # calculate total return for each ticker over the lookback period
        total_returns = {}
        for ticker in recent_prices.columns:
            first_price = recent_prices[ticker].iloc[0]
            last_price = recent_prices[ticker].iloc[-1]
            # a 0 starting price would divide by zero; treat it as a 0% return instead
            total_return = (last_price - first_price) / first_price if first_price != 0 else 0.0
            total_returns[ticker] = total_return

        total_returns = pd.Series(total_returns)

        # long positions: top n tickers get equal positive weights
        top_tickers = total_returns.nlargest(self.top_n).index.tolist()
        if not top_tickers:
            return self.current_weights
        long_weight = 1 / len(top_tickers)
        long_values = [long_weight] * len(top_tickers)
        new_weights = build_weights(top_tickers, long_values)

        # short positions: bottom n tickers get equal negative weights
        if self.short:
            bottom_tickers = total_returns.nsmallest(self.bottom_n).index.tolist()
            if bottom_tickers:
                short_weight = -1 / len(bottom_tickers)
                short_values = [short_weight] * len(bottom_tickers)
                short_weights = build_weights(bottom_tickers, short_values)
                new_weights.update(short_weights)

        self.weight_history.append((current_date, new_weights.copy()))
        self.last_rebalance_date = current_date
        self.current_weights = new_weights

        return self.current_weights


class EqualWeight:
    """Splits the portfolio evenly across all tickers (the "1/N" rule).

    Example: 3 tickers -> each gets 33.3%. DeMiguel, Garlappi & Uppal (2009)
    show this naive rule is a surprisingly hard benchmark to beat in practice.
    Rebalances every `rebalance_every` days (default 252 = 1 year).
    """

    def __init__(self, rebalance_every: int = 252) -> None:
        self.rebalance_every = rebalance_every
        self.last_rebalance_date = None
        self.current_weights = {}
        self.weight_history = []

    def get_weights(self, prices: pd.DataFrame) -> dict[str, float]:
        """Return the current target weights, rebalancing if it is due."""
        current_date = prices.index[-1]

        if not _should_rebalance(self.last_rebalance_date, current_date, self.rebalance_every):
            return self.current_weights

        tickers = prices.columns.tolist()
        if not tickers:
            return self.current_weights
        weight = 1 / len(tickers)
        values = [weight] * len(tickers)
        new_weights = build_weights(tickers, values)

        self.weight_history.append((current_date, new_weights.copy()))
        self.last_rebalance_date = current_date
        self.current_weights = new_weights

        return self.current_weights


class FixedWeight:
    """Uses weights you specify yourself.

    Example: {"SPY": 0.6, "AGG": 0.4} -> 60% SPY, 40% AGG. Rebalances every
    `rebalance_every` days (default 252 = 1 year).
    """

    def __init__(self, weights: dict[str, float], rebalance_every: int = 252) -> None:
        self.weights = weights
        self.rebalance_every = rebalance_every
        self.last_rebalance_date = None
        self.current_weights = {}
        self.weight_history = []

    def get_weights(self, prices: pd.DataFrame) -> dict[str, float]:
        """Return the current target weights, rebalancing if it is due."""
        current_date = prices.index[-1]

        if not _should_rebalance(self.last_rebalance_date, current_date, self.rebalance_every):
            return self.current_weights

        new_weights = self.weights.copy()

        self.weight_history.append((current_date, new_weights.copy()))
        self.last_rebalance_date = current_date
        self.current_weights = new_weights

        return self.current_weights


class InverseVolatility:
    """Weights each asset by the inverse of its volatility.

    Less volatile assets get a higher weight, more volatile assets get a
    lower weight. Rebalances every `rebalance_every` days (default 252 = 1
    year).
    """

    def __init__(self, rebalance_every: int = 252) -> None:
        self.rebalance_every = rebalance_every
        self.last_rebalance_date = None
        self.current_weights = {}
        self.weight_history = []

    def get_weights(self, prices: pd.DataFrame) -> dict[str, float]:
        """Return the current target weights, rebalancing if it is due."""
        current_date = prices.index[-1]

        if not _should_rebalance(self.last_rebalance_date, current_date, self.rebalance_every):
            return self.current_weights

        returns = prices.pct_change().dropna()

        # need at least two return observations before volatility is meaningful; until then
        # stay in cash (empty weights) so the backtest holds value flat instead of going NaN
        if len(returns) < 2:
            return self.current_weights

        # calculate volatility (standard deviation) for each ticker, then take
        # the inverse so stable assets get more weight, and normalise to sum to 1.
        # a 0-volatility ticker (e.g. a constant price) would divide by zero, so
        # it gets weight 0 instead.
        volatility = returns.std()
        tickers = volatility.index.tolist()
        inverse_vol = [1 / volatility[ticker] if volatility[ticker] > 0 else 0.0 for ticker in tickers]
        normalised = _normalise_weights(inverse_vol)

        new_weights = build_weights(tickers, normalised)

        self.weight_history.append((current_date, new_weights.copy()))
        self.last_rebalance_date = current_date
        self.current_weights = new_weights

        return self.current_weights


class MeanVariance:
    """Finds the weights that maximise the Sharpe ratio (return per unit of risk).

    This is the Markowitz (1952) tangency portfolio, implemented by hand
    using numpy: w = covariance^-1 * expected_returns, then normalised so
    weights sum to 1. Negative weights are clipped to 0 (no short selling).
    Rebalances every `rebalance_every` days (default 252 = 1 year).

    Note: the textbook tangency portfolio uses excess returns,
    w = covariance^-1 * (expected_returns - risk_free_rate). Here we use the
    raw expected returns, which implicitly assumes a risk-free rate of 0.
    """

    def __init__(self, rebalance_every: int = 252, use_ewma: bool = False, ewma_lambda: float = 0.94) -> None:
        self.rebalance_every = rebalance_every
        # use_ewma switches the covariance estimate to an exponentially weighted one (EWMA)
        self.use_ewma = use_ewma
        self.ewma_lambda = ewma_lambda
        self.last_rebalance_date = None
        self.current_weights = {}
        self.weight_history = []

    def get_weights(self, prices: pd.DataFrame) -> dict[str, float]:
        """Return the current target weights, rebalancing if it is due."""
        current_date = prices.index[-1]

        if not _should_rebalance(self.last_rebalance_date, current_date, self.rebalance_every):
            return self.current_weights

        returns = prices.pct_change().dropna()

        # the sample covariance is only invertible with more return observations than
        # assets; until then stay in cash (empty weights) so the backtest holds value flat
        if len(returns) <= prices.shape[1]:
            return self.current_weights

        # expected return and covariance matrix
        mean_returns = returns.mean()
        mu = mean_returns.values
        # covariance: equally weighted, or exponentially weighted (EWMA) when enabled
        if self.use_ewma:
            cov = measures.ewma_covariance(returns, self.ewma_lambda).values
        else:
            cov = returns.cov().values

        # the core formula: inverse covariance matrix times mean returns.
        # pinv (pseudo-inverse) is used instead of inv so a singular covariance
        # matrix (e.g. two perfectly correlated tickers) does not raise an error
        cov_inv = np.linalg.pinv(cov)
        raw_weights = cov_inv @ mu

        # drop negative weights (no short selling), then normalise to sum to 1
        raw_weights = np.clip(raw_weights, 0, None)
        normalised = _normalise_weights(raw_weights.tolist())

        tickers = prices.columns.tolist()
        new_weights = build_weights(tickers, normalised)

        self.weight_history.append((current_date, new_weights.copy()))
        self.last_rebalance_date = current_date
        self.current_weights = new_weights

        return self.current_weights
