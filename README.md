# StratLab

**StratLab is a Streamlit web app for building, backtesting and comparing simple
portfolio strategies**

It was built as a group project for course "Programming with Advanced Computer Languages" at the University of St.Gallen (HSG). You pick a set of tickers, choose a strategy (e.g. Equal Weight,
Momentum, Mean-Variance), and StratLab simulates how that portfolio would have
performed against a benchmark, with the key risk/return metrics, charts and a
short-term direction forecast.

---

## Quick start — no account needed

You can run the whole app locally in under a minute:

```bash
pip install -r requirements.txt
streamlit run app.py
```

On the welcome screen, click **“Enter StratLab (guest)”**. That's it — every page
is available immediately, no database or sign-up required.

> In guest mode, strategies you save are kept only for the current session. To keep
> accounts and saved strategies permanently, configure Supabase (see
> [Optional: persistent accounts](#optional-persistent-accounts-with-supabase)).

---

## Screenshots

<!--
  Add 2–3 screenshots so reviewers see the app at a glance.
  In the GitHub web UI: open docs/screenshots/ → "Add file" → "Upload files",
  drag your PNGs in, and name them builder.png / evaluate.png / compare.png.
  If you don't add images, delete this whole section so no broken images show.
-->

| Builder | Evaluate |
| --- | --- |
| ![Building a strategy](docs/screenshots/builder.png) | ![Evaluating a backtest](docs/screenshots/evaluate.png) |

---

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

## Project structure

```
app.py                  entry point: login / guest gate + navigation
pages/                  one file per page (Home, Builder, Evaluate, Compare, Explore, Glossary)
core/                   pure finance logic, no Streamlit
  strategy.py           strategy classes (weight calculation)
  backtest.py           day-by-day portfolio simulation
  measures.py           performance/risk metrics, factor models
  data.py               price + Fama-French data loading
  forecast.py           next-day direction forecast (scikit-learn)
services/               persistence (auth, saved strategies) — Supabase, with a guest fallback
ui.py / theme.py        shared UI components and styling
strategies_config.py    registry of available strategy types
make_docs.py            regenerates docs/StratLab_Documentation.docx
```

## Setup

1. Install dependencies (this includes Streamlit itself, so there's no separate
   install step needed):

   ```bash
   pip install -r requirements.txt
   ```

   If `pip` isn't recognized, make sure Python is installed and added to your PATH
   (download from [python.org](https://www.python.org/downloads/)), then try again.

2. Run the app:

   ```bash
   streamlit run app.py
   ```

   Then open the URL Streamlit prints (usually http://localhost:8501) and click
   **“Enter StratLab (guest)”**.

### Optional: persistent accounts with Supabase

Guest mode needs nothing. To enable real accounts and permanently saved strategies,
add your [Supabase](https://supabase.com) credentials in `.streamlit/secrets.toml`
(this file is git-ignored and never committed):

```toml
[supabase]
url = "https://your-project.supabase.co"
key = "your-anon-key"
```

The app expects two tables in your Supabase project:

- `users` — columns: `username` (text), `password` (text, stores a SHA-256 hash)
- `strategies` — columns: `id`, `username` (text), `name` (text), `type` (text),
  `tickers` (jsonb), `start_date` (date), `end_date` (date), `params` (jsonb),
  `kpis` (jsonb)

When these secrets are present, StratLab automatically switches from guest mode to
full login/registration with persistent storage.

## Documentation

`docs/StratLab_Documentation.docx` describes the app's architecture, finance logic,
error handling and collinearity handling in more depth. Regenerate it with:

```bash
python make_docs.py
```

## Use of AI tools

We used AI assistants (Claude / Claude Code and
ChatGPT) to clean up, document and structure the code, and to understand specific
libraries (Streamlit, yfinance, Supabase, scikit-learn). The finance logic, the app
design and all decisions are our own. Each source file starts with a short AI-usage
declaration noting what the tools were used for.

## Authors

Built by the StratLab team for the course "Programming with Advanced Computer Languages" at the University of St.Gallen (HSG), spring 2026.
Zsuzsanna Nagy & Michèl Schlumpf

## License

Released under the MIT License — see [LICENSE](LICENSE).
