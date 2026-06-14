<p align="center">
  <img src="assets/logo-lockup.svg" alt="StratLab logo" width="340">
</p>

# StratLab

**StratLab is a Streamlit web app for building, backtesting and comparing simple
portfolio strategies on real historical data.**

It works a bit like a flight simulator for investing: you can test a strategy on
past data before risking real money. You pick a set of tickers, choose a strategy
(for example Equal Weight, Momentum or Mean-Variance), and StratLab simulates how
that portfolio would have performed against a benchmark, with the key risk and
return metrics, charts and a short-term direction forecast.

We built it as our group project for the course "Programming with Advanced Computer
Languages" at the University of St. Gallen (HSG), and it brings together a lot of
what we learned in our Master in Banking and Finance courses (portfolio theory,
asset pricing and quantitative asset management) in one place.

## Try it online

The app is live here, no installation needed:

**https://stratlab.streamlit.app/**

You can register your own free account in a few seconds (Register tab), or log in
with the demo account to look around right away:

- Username: `demo`
- Password: `demo`

(If you would rather run it on your own machine, see [Run it locally](#run-it-locally)
below.)

## A look at the app

![StratLab home page](docs/home.png)

## Run it locally

You can also run the whole app on your own machine in under a minute:

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then open the URL Streamlit prints (usually http://localhost:8501) and click
**"Enter StratLab (guest)"**. That is it, every page is available immediately, no
database or sign-up required.

> Locally the app runs in guest mode, so strategies you save are kept only for the
> current session. To keep accounts and saved strategies permanently, you can connect
> a free Supabase database (see the [Developer Guide](docs/DEVELOPER.md)). This is how
> the hosted version above stores accounts.

If `pip` is not recognised, make sure Python is installed and added to your PATH
(download from [python.org](https://www.python.org/downloads/)), then try again.

## Features

- **Builder**: pick tickers, a strategy type (Equal Weight, Fixed Weight, Momentum,
  Inverse Volatility, Mean-Variance), a date range, an optional cash and risk-free
  allocation and trading or management fees, then save the strategy.
- **Evaluate**: run a full backtest of one strategy against a benchmark, with key
  metrics (CAGR, Sharpe, Max Drawdown, Alpha, Beta), a cost analysis, equity and
  drawdown charts, allocation over time, a monthly returns heatmap, the Capital
  Market Line, and a next-day direction forecast for the portfolio.
- **Compare**: run several saved strategies side by side over the period they share.
- **Explore**: browse price history, statistics, correlations between tickers, and a
  next-day direction forecast for each selected ticker.
- **Glossary**: plain-language explanations of every finance term and metric used in
  the app, each with its formula and an academic source where relevant.

## Documentation

We split the documentation by who it is for:

- **[User Guide](docs/USER_GUIDE.md)**: a walkthrough of the app from a user's point
  of view, page by page, following the Build, Evaluate, Compare and Decide flow.
- **[Developer Guide](docs/DEVELOPER.md)**: how the code is structured, how the
  finance engine works, how to connect Supabase, and how to add your own strategy.

## Project structure (short version)

```
app.py                  entry point: login / guest gate + navigation
pages/                  one file per page (Home, Builder, Evaluate, Compare, Explore, Glossary)
core/                   pure finance logic, no Streamlit (strategies, backtest, metrics, data, forecast)
services/               persistence (auth, saved strategies): Supabase, with a guest fallback
ui.py / theme.py        shared UI components and styling
strategies_config.py    registry of available strategy types
```

The full module-by-module breakdown is in the [Developer Guide](docs/DEVELOPER.md).

## Use of AI tools

In line with the course policy, we used AI assistants (Claude / Claude Code and
ChatGPT) to clean up, document and structure the code, and to understand specific
libraries (Streamlit, yfinance, Supabase, scikit-learn). The finance logic, the app
design and all decisions are our own. Each source file starts with a short AI-usage
declaration noting what the tools were used for in that file.

## About us

We are Zsuzsanna Nagy and Michèl Schlumpf, two Master in Banking and Finance
students at the University of St. Gallen. While running our own strategy analysis
for coursework, we kept rebuilding the same backtests in spreadsheets: slow, error
prone and impossible to compare cleanly. So we built StratLab, a simple and free
tool to backtest straightforward strategies in minutes instead of hours, without
writing a line of code or paying for data. The whole app follows one idea, Build a
strategy, Evaluate it in depth, then Compare and Decide, so you can go from a hunch
to an evidence-based decision fast.
