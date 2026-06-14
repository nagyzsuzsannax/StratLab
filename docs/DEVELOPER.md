# StratLab Developer Guide

This guide explains how StratLab is built: the architecture, the finance engine, the
persistence layer, and how to extend it with your own strategy.

## Overview

StratLab is a web app for building, backtesting and comparing simple investment
strategies on real historical data. It is built with Python and Streamlit. All the
finance logic, meaning the data loading, strategies, backtest engine and every
metric, lives in `core/`, which knows nothing about Streamlit. The Streamlit pages
just call into `core/` and show the result.

The dependencies only go one way: `pages/` use `services/`, `prices.py` and `ui.py`,
which in turn use `core/`. Nothing in `core/` imports Streamlit or `services/`, so the
finance engine can be tested or reused on its own.

## Tech stack

- **Streamlit**: the web interface and multi-page navigation.
- **pandas / numpy**: price data and strategy maths.
- **yfinance**: historical prices from Yahoo Finance.
- **scipy**: skewness, kurtosis, the Jarque-Bera test, normal quantiles.
- **scikit-learn**: logistic regression for the next-day forecast feature.
- **matplotlib**: charts.
- **Supabase (Postgres)**: stores users and saved strategies (optional, with a guest
  fallback so the app also runs without it).

## Folder structure

```
core/                  finance engine (pure Python, no Streamlit)
    data.py            PriceLoader, Fama-French download
    strategy.py        the five strategies
    backtest.py        Backtest.run()
    measures.py        finance formulas + Analytics class
    forecast.py        next-day direction forecast (logistic regression)
services/              persistence
    db.py, auth.py, storage.py
pages/                 Streamlit pages
    0_Home.py, 1_Builder.py, 2_Evaluate.py,
    3_Compare.py, 4_Explore.py, 5_Glossary.py
app.py                 entry point: login / guest gate + navigation
theme.py               design tokens (colours, font, spacing)
ui.py                  reusable UI components + shared charts
strategies_config.py   strategy registry for the UI
prices.py              cached price/fundamentals loader
tickers.py             searchable universe of stocks/ETFs
assets/                logos, favicon, style.css
docs/                  this document and screenshots
```

## The core engine

Everything that computes a number lives in `core/`. The UI never does finance maths
itself.

### core/data.py: PriceLoader

`PriceLoader().get_prices(tickers, start, end)` returns a DataFrame of daily
adjusted-close prices from Yahoo Finance, one column per ticker. A ticker that fails
to download is skipped silently.

`load_fama_french_factors(model)` downloads monthly Fama-French factors ("FF3" or
"FF5") from Ken French's data library, wrapped in try/except so a failed download
returns an empty DataFrame instead of crashing. `core/data.py` is deliberately
cache-free; `prices.py` adds an `st.cache_data` layer for the UI.

### core/strategy.py: the five strategies

Every strategy is a small class with the same interface. `__init__` takes its own
parameters plus a shared `rebalance_every` value (the number of trading days between
rebalances, default 252). `get_weights(prices)` returns a dict of target weights for
"today", or the same weights as before if it is not yet time to rebalance. Three
shared helpers, `_should_rebalance(...)`, `_normalise_weights(...)` and
`build_weights(...)`, avoid repeating this logic in every strategy.

- **EqualWeight**: splits the portfolio evenly across all tickers (the "1/N" rule).
  DeMiguel, Garlappi and Uppal (2009) showed this is a tough benchmark to beat.
- **FixedWeight**: uses weights chosen by the user (for example 60/40 stocks/bonds).
- **Momentum**: ranks assets by their past return over a lookback window and goes long
  the top performers (optionally short the worst ones), based on Jegadeesh and Titman
  (1993).
- **InverseVolatility**: weights each asset by the inverse of its volatility, so
  calmer assets get a bigger weight.
- **MeanVariance**: the Markowitz (1952) tangency portfolio. Weights are
  `w = Sigma^-1 * mu`, normalised so they sum to 1, with negative weights clipped to
  zero. It can optionally use an exponentially weighted (EWMA / RiskMetrics)
  covariance matrix instead of the plain sample covariance.

MeanVariance and InverseVolatility need a minimum amount of return history before
their covariance or volatility is defined. Until then they hold cash (empty weights),
so the equity curve stays flat instead of showing NaN.

### core/backtest.py: Backtest

`Backtest().run(strategy, prices)` walks forward through the price history one day at
a time. On each day it gives `strategy.get_weights()` only the prices up to that day,
so there is no look-ahead bias. It then works out the weighted daily return from each
ticker's price change, and grows the portfolio value (starting at 1.0) by that
return. The result is a Series, stored on `self.portfolio` and also returned. All
KPIs are then computed from this series using `core/measures.py`; Backtest itself has
no KPI methods.

### core/measures.py: finance formulas and the Analytics class

A library of stand-alone functions, each with a short docstring explaining the
formula:

- **Returns**: simple and log returns, average and annualised return, CAGR,
  volatility (daily, monthly, annualised).
- **Risk-adjusted**: Sharpe, Sortino and Treynor ratios.
- **Distribution**: skewness, excess kurtosis, the Jarque-Bera normality test.
- **Risk**: maximum drawdown, historic VaR (empirical quantile) and
  variance-covariance VaR for 1-day and 1-month horizons.
- **Factor models**: CAPM, Fama-French 3 and 5 factor monthly regressions (alpha,
  beta, t and p-values, R-squared, appraisal ratio).
- **Portfolio construction**: EWMA covariance for MeanVariance, `common_window` to
  align tickers that start on different dates, and the cash/risk-free overlay, the
  trading/management cost application and the annual turnover used to turn a gross
  backtest into a net one.

`Analytics(values, benchmark_values, rf_annual)` bundles these into one object so a
page can pull every measure for one portfolio (and its benchmark) without re-deriving
returns each time. This is what Evaluate and Compare use for their KPI cards and
tables.

The formulas follow the conventions taught in the AQAM (Advanced Quantitative Asset
Management) course at the University of St. Gallen, plus the academic sources cited in
the Glossary. They are not AI-generated.

Note: `log_returns` is not currently called from any page or other core function. It
was added during backend development for possible future use (for example
log-return-based statistics) and left in for that reason.

### core/forecast.py: next-day direction forecast

`predict_direction(prices, n_lags=10)` is a small machine-learning add-on used on the
Explore and Evaluate pages. Each day's features are the previous `n_lags` daily
returns, and the label is whether that day's return was positive. A scikit-learn
LogisticRegression model is trained on a chronological 80/20 split, so the test set is
always later in time than the training set. The function returns the test-set accuracy
plus the predicted probability that tomorrow's return will be positive. It returns
None if there is not enough price history (fewer than `n_lags + 30` return
observations) to train and test the model.

## services/: persistence layer

Users and saved strategies live in a hosted Supabase (Postgres) database, reached
through a single cached client. Credentials sit in `.streamlit/secrets.toml` (excluded
from version control). When no credentials are configured, the app falls back to a
guest mode that keeps everything in the session instead, so it still runs end to end.

- **db.py**: `get_client()` builds the Supabase client from the `[supabase]` url and
  key in `.streamlit/secrets.toml`, decorated with `@st.cache_resource` so it is
  created once and reused across reruns. `run_query(builder)` runs a query builder,
  returns its `.data`, or shows `st.error(...)` and returns None if anything goes
  wrong, so a database error shows up as a message instead of crashing the app.
  `has_db()` reports whether credentials are present, which is what switches the app
  between full accounts and guest mode.
- **auth.py**: `login(username, password)` compares the stored SHA-256 hash against
  the hash of the entered password. `register(username, password)` checks the username
  is free, then inserts a new row. Passwords are hashed and never stored in plain
  text.
- **storage.py**: `save_strategy`, `load_strategies`, `delete_strategy` and
  `update_kpis` persist one row per saved strategy (tickers, params and kpis as
  JSONB), and rebuild the actual strategy object on load via the registry. In guest
  mode the same functions read and write a per-session list in `st.session_state`
  instead, so the pages behave identically.

### Connecting Supabase (optional)

Guest mode needs nothing. To enable real accounts and permanently saved strategies:

1. Create a free project at [supabase.com](https://supabase.com).
2. Add the credentials in `.streamlit/secrets.toml` (this file is git-ignored):

   ```toml
   [supabase]
   url = "https://your-project.supabase.co"
   key = "your-anon-key"
   ```

   When deploying on Streamlit Community Cloud, paste the same block into the app's
   Settings -> Secrets instead, because the local file is not uploaded.

3. Create the two tables in the Supabase SQL editor:

   ```sql
   create table if not exists public.users (
     username text primary key,
     password text not null
   );

   create table if not exists public.strategies (
     id          bigint generated always as identity primary key,
     username    text not null,
     name        text not null,
     type        text not null,
     tickers     jsonb,
     start_date  date,
     end_date    date,
     params      jsonb,
     kpis        jsonb
   );
   ```

   The app uses Supabase with the public anon key and its own SHA-256 password
   hashing, so for a project of this size it is simplest to leave Row Level Security
   off on these two tables.

Once the secrets are present, StratLab automatically switches from guest mode to full
login and registration with persistent storage.

## Shared UI building blocks

`theme.py` holds every colour, font and spacing value as plain constants. Both
`assets/style.css` (via `ui.inject_css`) and the matplotlib charts (via
`theme.apply_mpl_theme`) read from these constants, so each colour is only defined
once. `ui.py` provides simple Streamlit wrappers used on every page (`page_header`,
`kpi_card`, `verb_stepper`, `empty_state`, `next_step`, `data_table`) plus two shared
chart helpers (`rebase_to_100` and `cml_chart`).

`strategies_config.py` is the single registry the whole UI reads: each strategy is
listed once with its class, display label and the parameters the Builder should ask
for. Adding a strategy is therefore a two-step job (see below), and no page code needs
to change.

`prices.py` adds a thin, UI-side `st.cache_data` layer around `core/data.py`, plus two
extra Yahoo Finance lookups (`load_risk_free_rate` and `load_info`).

## The page flow

- **pages/0_Home.py**: the entry point after login. It lists saved strategies with
  their last-stored KPIs (so the page loads without re-running a backtest) and links
  into Build, Evaluate and Compare. Its Update button re-runs the backtest with fresh
  data and saves the refreshed KPIs.
- **pages/1_Builder.py**: lets you set up a strategy (tickers, type and its
  registry-driven parameters, rebalancing frequency, the optional cash/risk-free
  overlay, and fees). `_validate(...)` collects every reason the strategy cannot be
  saved yet and the page lists them together.
- **pages/2_Evaluate.py**: rebuilds one saved strategy, runs it through Backtest
  alongside a benchmark, applies the overlay and fees to get the net curve, and shows
  KPIs, factor models, charts, the CML and a forecast.
- **pages/3_Compare.py**: does the same for two or more strategies, over the period
  they all share, and ranks them in tables and a combined CML chart.
- **pages/4_Explore.py**: lets a user research tickers (price chart, stats,
  fundamentals, correlation heatmap, forecast) before building anything.
- **pages/5_Glossary.py**: a searchable, colour-coded reference explaining every
  metric and strategy with its formula and an academic citation where relevant.

## How to add your own strategy

Thanks to the registry, adding a strategy is a clean two-step change. No page code has
to be touched.

**Step 1: write the class in `core/strategy.py`.** Follow the same interface as the
existing strategies. Here is a simple example, "Single Momentum", which holds 100% of
the single asset with the highest return over a lookback window:

```python
class SingleMomentum:
    """Holds 100% of the single best performer over the lookback window."""

    def __init__(self, lookback: int = 126, rebalance_every: int = 252) -> None:
        self.lookback = lookback
        self.rebalance_every = rebalance_every
        self.last_rebalance_date = None
        self.current_weights = {}
        self.weight_history = []

    def get_weights(self, prices: pd.DataFrame) -> dict[str, float]:
        current_date = prices.index[-1]

        # reuse the shared rebalancing helper, like every other strategy
        if not _should_rebalance(self.last_rebalance_date, current_date, self.rebalance_every):
            return self.current_weights

        recent = prices.tail(self.lookback)
        if recent.empty:
            return self.current_weights

        # total return per ticker over the window, then pick the winner.
        # a 0 starting price is guarded the same way the other strategies do it.
        first, last = recent.iloc[0], recent.iloc[-1]
        returns = (last - first) / first.replace(0, pd.NA)
        winner = returns.dropna().idxmax()
        new_weights = build_weights([winner], [1.0])

        self.weight_history.append((current_date, new_weights.copy()))
        self.last_rebalance_date = current_date
        self.current_weights = new_weights
        return self.current_weights
```

**Step 2: register it in `strategies_config.py`.** Import the class and add one entry.
The `params` list tells the Builder which inputs to render, using the same small spec
the other strategies use (each item has a name, type, default and optional min, max,
step, help and show_if):

```python
from core.strategy import (
    EqualWeight, FixedWeight, InverseVolatility, MeanVariance, Momentum, SingleMomentum,
)

STRATEGIES = {
    # ... the existing entries ...
    "SingleMomentum": {
        "cls": SingleMomentum,
        "label": "Single Momentum",
        "params": [
            {"name": "lookback", "type": "int", "default": 126, "min": 20, "max": 756,
             "help": "trading days used to pick the winner"},
        ],
    },
}
```

That is it. The new strategy now appears in the Builder dropdown, with its lookback
slider, and works end to end in Evaluate and Compare. The Builder renders the
parameters straight from this spec, and the backtest, metrics and saving all go
through the same shared code. If your strategy needs extra validation rules (like
Momentum's "Top N must be less than the number of tickers"), you can add them in
`_validate(...)` in `pages/1_Builder.py`, but for most simple strategies that is not
needed.

## Error handling and collinearity

The app is built so a bad input or an outage shows a message instead of a crash. A
failed download returns an empty Series or DataFrame; division-by-zero cases (zero
prices, zero volatility, an empty portfolio) return 0 or NaN rather than raising; and
`Backtest().run(...)` is wrapped in try/except on the pages, so one failing strategy
does not take down the page.

Highly correlated inputs (near-identical tickers, or Fama-French factors that move
together) can make a covariance or design matrix singular. Instead of crashing,
MeanVariance and the factor regressions use `np.linalg.pinv` / `lstsq` (a
pseudo-inverse or least-squares solve) to still return a result, and the forecast
model relies on scikit-learn's default L2 (ridge) penalty to keep correlated
coefficients stable.

## Coding style

Small, single-purpose functions with type hints. Plain, readable loops instead of
clever one-liners, and short comments that explain why rather than what. Every
`pages/*.py` file follows the same layout: imports, then session-state setup, then
underscore-prefixed helper functions, then the page's render code after a
`# --- PAGE ---` marker. Streamlit code never appears in `core/`.

## Use of AI tools

Every source file carries its own AI Usage Declaration comment at the top describing
what AI was used for in that specific file. In summary: Claude was used throughout
`core/` and `services/` to clean up, document and structure the code, and to explain
specific concepts on request. Claude Code was used to generate parts of the frontend
(`app.py`, the `pages/`, `ui.py`, `theme.py`, `prices.py`, `strategies_config.py` and
`tickers.py`). ChatGPT was used to understand third-party tools and APIs (Supabase,
Streamlit, matplotlib, yfinance). The CSS in `assets/style.css` is AI-generated
(Claude), because Streamlit's built-in theming is not flexible enough to restyle
individual components. In every case the underlying logic and design decisions are our
own; AI was used for implementation help, clean-up, documentation and explaining
unfamiliar concepts.
