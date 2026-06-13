#AI Usage Declaration
#Claude was used to clean up, document and structure this code
#The formulas and conventions below follow the AQAM (Advanced Quantitative Asset
#Management) course at the University of St. Gallen
#The logic and design decisions are our own product

import numpy as np
import pandas as pd
from scipy import stats

# periods per year used for annualisation
TRADING_DAYS = 252
MONTHS = 12


# ----- returns -----

def simple_returns(prices: pd.Series) -> pd.Series:
    """Arithmetic returns R_t = P_t / P_{t-1} - 1."""
    return prices.pct_change(fill_method=None).dropna()


def log_returns(prices: pd.Series) -> pd.Series:
    """Continuously compounded (log) returns r_t = ln(P_t / P_{t-1}).

    These add over time, which is why they are used for drift and
    annualisation.
    """
    return np.log(prices / prices.shift(1)).dropna()


def to_monthly_returns(values: pd.Series) -> pd.Series:
    """Resample month-end values to monthly simple returns (used for the factor-model regressions)."""
    # resample groups the daily prices into monthly buckets and .last() keeps the
    # month-end price from each bucket. "ME" and "M" both mean month-end; "ME" is the
    # newer name (pandas >= 2.2), "M" the older one
    try:
        monthly = values.resample("ME").last()
    except ValueError:
        monthly = values.resample("M").last()
    return monthly.pct_change(fill_method=None).dropna()


# ----- return summaries -----

def average_return(returns: pd.Series) -> float:
    """Mean return per period (e.g. average daily return for daily returns)."""
    return float(returns.mean())


def annualized_return(returns: pd.Series, periods_per_year: int = TRADING_DAYS) -> float:
    """Arithmetic mean return annualised: mean * periods (the drift)."""
    return float(returns.mean() * periods_per_year)


def cagr(values: pd.Series, periods_per_year: int = TRADING_DAYS) -> float:
    """Geometric annual growth rate from a value/price series.

    Returns NaN instead of dividing by zero if the series is empty or starts
    at 0.
    """
    years = len(values) / periods_per_year
    if years <= 0 or values.iloc[0] == 0:
        return float("nan")
    total_growth = values.iloc[-1] / values.iloc[0]
    return float(total_growth ** (1 / years) - 1)


# ----- volatility (standard deviation) -----

def volatility(returns: pd.Series, periods_per_year: int = TRADING_DAYS, annualized: bool = True) -> float:
    """Sample standard deviation of returns, annualised with sqrt(periods) when requested."""
    sd = float(returns.std(ddof=1))
    return sd * (periods_per_year ** 0.5) if annualized else sd


# ----- risk-adjusted performance -----

def sharpe_ratio(returns: pd.Series, rf_per_period: float = 0.0, periods_per_year: int = TRADING_DAYS) -> float:
    """Annualised Sharpe ratio: SR = mean(R - Rf) / sigma, annualised (mean * P) / (sigma * sqrt(P))."""
    excess = returns - rf_per_period
    ann_excess = excess.mean() * periods_per_year
    ann_vol = excess.std(ddof=1) * (periods_per_year ** 0.5)
    return float(ann_excess / ann_vol) if ann_vol else float("nan")


def sortino_ratio(returns: pd.Series, rf_per_period: float = 0.0, periods_per_year: int = TRADING_DAYS) -> float:
    """Like Sharpe, but penalises only downside volatility (returns below the target)."""
    excess = returns - rf_per_period
    downside = excess[excess < 0]
    downside_dev = float((downside.pow(2).mean()) ** 0.5) if len(downside) else 0.0
    if downside_dev == 0:
        return float("nan")
    ann_excess = excess.mean() * periods_per_year
    return float(ann_excess / (downside_dev * (periods_per_year ** 0.5)))


def treynor_ratio(returns: pd.Series, beta: float, rf_per_period: float = 0.0, periods_per_year: int = TRADING_DAYS) -> float:
    """Annualised excess return per unit of systematic risk (beta)."""
    ann_excess = (returns - rf_per_period).mean() * periods_per_year
    return float(ann_excess / beta) if beta else float("nan")


# ----- distribution shape -----

def skewness(returns: pd.Series) -> float:
    """Third standardised moment (population); 0 for a symmetric distribution."""
    return float(stats.skew(returns, bias=True))


def excess_kurtosis(returns: pd.Series) -> float:
    """Kurtosis minus 3 (Ke = K - 3); 0 for the normal distribution, >0 = fat tails."""
    return float(stats.kurtosis(returns, fisher=True, bias=True))


def jarque_bera(returns: pd.Series) -> tuple[float, float]:
    """Jarque-Bera normality test (H0: normally distributed).

    Returns (statistic, p_value); JB ~ chi^2(2), exploiting that a normal
    has skewness 0 and kurtosis 3.
    """
    result = stats.jarque_bera(returns)
    statistic = getattr(result, "statistic", None)
    if statistic is None:  # older scipy returns a plain tuple
        statistic, p_value = result
    else:
        p_value = result.pvalue
    return float(statistic), float(p_value)


# ----- drawdown -----

def max_drawdown(values: pd.Series) -> float:
    """Largest peak-to-trough drop: min over t of (V_t / running_peak - 1), as a negative number."""
    running_peak = values.cummax()
    return float(((values - running_peak) / running_peak).min())


# ----- Value-at-Risk -----

def historic_var(returns: pd.Series, confidence: float = 0.95) -> float:
    """Next-period historic VaR: the conservative empirical quantile of the returns.

    Take N*(1-confidence), round it DOWN, and use that ranked return. Returned
    value is a loss (negative return). Returns NaN if `returns` is empty.
    """
    ordered = np.sort(np.asarray(returns, dtype=float))
    n = len(ordered)
    if n == 0:
        return float("nan")
    rank = max(int(np.floor(n * (1 - confidence))), 1)
    return float(ordered[rank - 1])


def parametric_var(returns: pd.Series, confidence: float = 0.95, horizon: int = 1, include_mean: bool = True) -> float:
    """Variance-covariance VaR over a horizon of t periods, returned as a loss (negative).

    VaR = t*mu + sqrt(t)*sigma*z_(1-conf), z the standard-normal quantile.
    Often mu = 0 is assumed; set include_mean=False for that.
    horizon=1 -> next day, 21 -> next month.
    """
    mu = float(returns.mean()) if include_mean else 0.0
    sigma = float(returns.std(ddof=1))
    z = float(stats.norm.ppf(1 - confidence))  # negative, e.g. -1.645 (95%), -2.326 (99%)
    return horizon * mu + (horizon ** 0.5) * sigma * z


# ----- factor models (CAPM / Fama-French), usually run on monthly excess returns -----

def _ols(y: np.ndarray, x: np.ndarray) -> dict:
    """Ordinary least squares with an intercept.

    Returns coefficients, residuals, R^2 and the standard error of each
    coefficient (for t-stats).
    """
    n = len(y)
    design = np.column_stack([np.ones(n), x])
    coef, _, _, _ = np.linalg.lstsq(design, y, rcond=None)
    residuals = y - design @ coef
    dof = n - design.shape[1]
    sigma2 = float(residuals @ residuals) / dof if dof > 0 else float("nan")
    cov = sigma2 * np.linalg.pinv(design.T @ design)  # pinv: robust if factors are near-collinear
    se = np.sqrt(np.diag(cov))
    with np.errstate(divide="ignore", invalid="ignore"):
        tstats = coef / se
    pvalues = 2 * stats.t.sf(np.abs(tstats), dof) if dof > 0 else np.full_like(coef, np.nan)
    ss_res = float(residuals @ residuals)
    ss_tot = float(((y - y.mean()) ** 2).sum())
    r_squared = 1 - ss_res / ss_tot if ss_tot else float("nan")
    return {"coef": coef, "residuals": residuals, "se": se, "tstats": tstats, "pvalues": pvalues, "r_squared": r_squared}


def factor_model(asset_excess: pd.Series, factors: pd.DataFrame, periods_per_year: int = MONTHS) -> dict:
    """Regress asset excess return on one or more factors: R - Rf = alpha + B*factors + eps.

    Works for CAPM (one factor Mkt-RF), FF3 (Mkt-RF, SMB, HML) and FF5
    (+ RMW, CMA).
    """
    y = np.asarray(asset_excess, dtype=float)
    fit = _ols(y, factors.values)
    coef, residuals = fit["coef"], fit["residuals"]
    residual_std = float(residuals.std(ddof=1))
    alpha = float(coef[0])
    return {
        "alpha": alpha,  # per-period (e.g. monthly) Jensen alpha
        "alpha_annualized": alpha * periods_per_year,
        "alpha_tstat": float(fit["tstats"][0]),
        "alpha_pvalue": float(fit["pvalues"][0]),
        "betas": {name: float(b) for name, b in zip(factors.columns, coef[1:])},
        "beta_pvalues": {name: float(p) for name, p in zip(factors.columns, fit["pvalues"][1:])},
        "r_squared": fit["r_squared"],
        "residual_std": residual_std,
        # appraisal / information ratio AR = alpha / sigma(eps)
        "appraisal_ratio": alpha / residual_std if residual_std else float("nan"),
    }


def capm(asset_excess: pd.Series, market_excess: pd.Series, periods_per_year: int = MONTHS) -> dict:
    """Single-factor CAPM: a convenience wrapper around factor_model with a named market beta."""
    factors = pd.DataFrame({"Mkt-RF": np.asarray(market_excess, dtype=float)})
    result = factor_model(asset_excess, factors, periods_per_year)
    result["beta"] = result["betas"]["Mkt-RF"]
    result["beta_pvalue"] = result["beta_pvalues"]["Mkt-RF"]
    return result


# ----- EWMA covariance (for the mean-variance optimiser) -----

def ewma_covariance(returns: pd.DataFrame, lam: float = 0.94) -> pd.DataFrame:
    """RiskMetrics exponentially weighted covariance: more recent observations weigh more.

    Sigma = sum_i w_i (r_i - mu)(r_i - mu)', w_i proportional to lam^(T-i)
    (newest = highest). lam in (0, 1]; lam = 1 reproduces the equally
    weighted sample covariance.
    """
    data = returns.values
    n = len(data)
    demeaned = data - data.mean(axis=0)
    weights = lam ** np.arange(n - 1, -1, -1)
    weights = weights / weights.sum()
    cov = (demeaned * weights[:, None]).T @ demeaned
    return pd.DataFrame(cov, index=returns.columns, columns=returns.columns)


# ----- data availability (so a young ticker never produces NaN, and we can warn) -----

def common_window(prices: pd.DataFrame, start: str) -> tuple[pd.DataFrame, list[str]]:
    """Drop the leading period before every ticker has data.

    Also reports tickers that only start after the requested date (they
    enter the backtest from then).
    """
    first_valid = {col: prices[col].first_valid_index() for col in prices.columns}
    clean = prices.dropna()
    requested = pd.Timestamp(start)
    warnings = [f"{col} only has data from {valid.date()}"
                for col, valid in first_valid.items()
                if valid is not None and valid > requested + pd.Timedelta(days=5)]
    return clean, warnings


# ----- cash / risk-free overlay (Builder option to hold part of the portfolio safe) -----

def apply_cash_overlay(values: pd.Series, cash: float, risk_free: float, rf_per_period: float = 0.0) -> pd.Series:
    """Blend a strategy value series with a cash sleeve and a risk-free sleeve.

    Cash earns 0, the risk-free sleeve earns rf_per_period per period, and
    the remaining (1 - cash - risk_free) stays invested.
    """
    if cash <= 0 and risk_free <= 0:
        return values
    returns = simple_returns(values)
    invested = 1 - cash - risk_free
    blended = invested * returns + risk_free * rf_per_period
    return float(values.iloc[0]) * (1 + blended).cumprod()


# ----- transaction & management costs (Builder option; turns a gross curve into a net one) -----

def _turnover_per_rebalance(weight_history: list) -> dict:
    """One-way turnover at each rebalance = sum of |w_new - w_old| (w_old = 0 before the first)."""
    turnover = {}
    previous = {}
    for when, weights in weight_history:
        keys = set(weights) | set(previous)
        turnover[pd.Timestamp(when)] = sum(abs(weights.get(k, 0.0) - previous.get(k, 0.0)) for k in keys)
        previous = weights
    return turnover


def apply_costs(values: pd.Series, weight_history: list, trading_fee: float = 0.0, mgmt_fee_annual: float = 0.0) -> pd.Series:
    """Apply a daily management fee plus a trading fee charged on turnover at each rebalance.

    Management fee: value * (1 - fee/252) per day. Trading fee: value *
    (1 - turnover * fee) on rebalance days. With both fees 0, net == gross.
    """
    if trading_fee <= 0 and mgmt_fee_annual <= 0:
        return values
    turnover = _turnover_per_rebalance(weight_history)
    daily_mgmt = 1 - mgmt_fee_annual / TRADING_DAYS
    factor = 1.0
    factors = []
    for date in values.index:
        factor *= daily_mgmt
        if date in turnover:
            factor *= max(1 - turnover[date] * trading_fee, 0.0)
        factors.append(factor)
    return values * pd.Series(factors, index=values.index)


def annual_turnover(weight_history: list, values: pd.Series) -> float:
    """Average fraction of the portfolio traded per year."""
    total = sum(_turnover_per_rebalance(weight_history).values())
    years = len(values) / TRADING_DAYS
    return float(total / years) if years else float("nan")


# ----- convenience object that bundles the measures for one strategy -----

class Analytics:
    """Wraps a strategy's value series (and optionally a benchmark) so a page can pull every measure from one object.

    rf_annual is the annual risk-free rate (e.g. 0.04 = 4%).
    """

    def __init__(self, values: pd.Series, benchmark_values: pd.Series | None = None,
                 rf_annual: float = 0.0, periods_per_year: int = TRADING_DAYS) -> None:
        self.values = values
        self.returns = simple_returns(values)
        self.periods = periods_per_year
        self.rf_per_period = rf_annual / periods_per_year
        self.benchmark_values = benchmark_values
        self.benchmark_returns = simple_returns(benchmark_values) if benchmark_values is not None else None

    # returns / volatility
    def cagr(self) -> float:
        """Geometric annualised growth rate of the value series."""
        return cagr(self.values, self.periods)

    def annualized_return(self) -> float:
        """Arithmetic mean daily return, annualised."""
        return annualized_return(self.returns, self.periods)

    def average_daily_return(self) -> float:
        """Mean daily return."""
        return average_return(self.returns)

    def average_monthly_return(self) -> float:
        """Mean monthly return."""
        return average_return(to_monthly_returns(self.values))

    def daily_volatility(self) -> float:
        """Standard deviation of daily returns (not annualised)."""
        return volatility(self.returns, self.periods, annualized=False)

    def monthly_volatility(self) -> float:
        """Standard deviation of monthly returns (not annualised)."""
        return volatility(to_monthly_returns(self.values), MONTHS, annualized=False)

    def annualized_volatility(self) -> float:
        """Standard deviation of daily returns, annualised."""
        return volatility(self.returns, self.periods, annualized=True)

    # risk-adjusted
    def sharpe(self) -> float:
        """Annualised Sharpe ratio (excess return / volatility)."""
        return sharpe_ratio(self.returns, self.rf_per_period, self.periods)

    def sortino(self) -> float:
        """Annualised Sortino ratio (excess return / downside volatility)."""
        return sortino_ratio(self.returns, self.rf_per_period, self.periods)

    def treynor(self) -> float:
        """Annualised Treynor ratio (excess return / beta)."""
        return treynor_ratio(self.returns, self.beta(), self.rf_per_period, self.periods)

    # distribution / tails
    def skewness(self) -> float:
        """Skewness of daily returns."""
        return skewness(self.returns)

    def excess_kurtosis(self) -> float:
        """Excess kurtosis of daily returns (kurtosis - 3)."""
        return excess_kurtosis(self.returns)

    def jarque_bera(self) -> tuple[float, float]:
        """Jarque-Bera normality test (statistic, p_value) on daily returns."""
        return jarque_bera(self.returns)

    def max_drawdown(self) -> float:
        """Largest peak-to-trough drop in the value series."""
        return max_drawdown(self.values)

    def historic_var(self, confidence: float = 0.95) -> float:
        """Historic (empirical quantile) Value-at-Risk on daily returns."""
        return historic_var(self.returns, confidence)

    def parametric_var(self, confidence: float = 0.95, horizon: int = 1) -> float:
        """Variance-covariance Value-at-Risk on daily returns over the given horizon."""
        return parametric_var(self.returns, confidence, horizon)

    # vs benchmark (a simple market-model beta/alpha on the aligned daily returns)
    def beta(self) -> float:
        """Market-model beta vs the benchmark's daily returns (NaN if no benchmark)."""
        if self.benchmark_returns is None:
            return float("nan")
        aligned = pd.concat([self.returns, self.benchmark_returns], axis=1, join="inner").dropna()
        cov = np.cov(aligned.iloc[:, 0], aligned.iloc[:, 1])
        # a zero (or NaN) benchmark variance would divide by zero, e.g. a flat-priced
        # benchmark or too few aligned observations
        if not cov[1, 1] > 0:
            return float("nan")
        return float(cov[0, 1] / cov[1, 1])

    def alpha_annualized(self) -> float:
        """CAGR above the benchmark's CAGR (geometric), kept simple for the basic view (NaN if no benchmark)."""
        if self.benchmark_values is None:
            return float("nan")
        return self.cagr() - cagr(self.benchmark_values, self.periods)
