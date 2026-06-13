# StratLab

A Streamlit app for building, backtesting and comparing simple portfolio strategies.

## Features

- **Builder** — pick tickers, a strategy type (Equal Weight, Fixed Weight, Momentum,
  Inverse Volatility, Mean-Variance), a date range, optional cash/risk-free allocation
  and trading/management fees, then save the strategy.
- **Evaluate** — run a full backtest of one strategy against a benchmark: key metrics
  (CAGR, Sharpe, Max Drawdown, Alpha, Beta), cost analysis, equity/drawdown charts,
  allocation over time, monthly returns heatmap, the Capital Market Line, and a
  next-day direction forecast for the portfolio.
- **Compare** — run several saved strategies side by side.
- **Explore** — browse price history, statistics, correlations between tickers, and a
  next-day direction forecast for each selected ticker.
- **Glossary** — explanations of the finance terms and metrics used across the app.

Accounts and saved strategies are stored in Supabase.

## Project structure

```
app.py                 entry point: login gate + navigation
pages/                  one file per page (Home, Builder, Evaluate, Compare, Explore, Glossary)
core/                   pure finance logic, no Streamlit
  strategy.py           strategy classes (weight calculation)
  backtest.py           day-by-day portfolio simulation
  measures.py           performance/risk metrics, factor models
  data.py               price + Fama-French data loading
  forecast.py           next-day direction forecast (scikit-learn)
services/               Supabase persistence (auth, saved strategies)
ui.py / theme.py        shared UI components and styling
strategies_config.py    registry of available strategy types
make_docs.py            regenerates docs/StratLab_Documentation.docx
```

## Setup

1. Install dependencies (this includes Streamlit itself, so there's no separate
   install step needed):

   ```
   pip install -r requirements.txt
   ```

   If `pip` isn't recognized, make sure Python is installed and added to your PATH
   (download from [python.org](https://www.python.org/downloads/)), then try again.

2. Add your Supabase credentials in `.streamlit/secrets.toml` (not committed):

   ```toml
   [supabase]
   url = "https://your-project.supabase.co"
   key = "your-anon-key"
   ```

3. Run the app:

   ```
   streamlit run app.py
   ```

## Documentation

`docs/StratLab_Documentation.docx` describes the app's architecture, finance logic,
error handling and collinearity handling in more depth. Regenerate it with:

```
python make_docs.py
```
