import os

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor

#regenerates docs/StratLab_Documentation.docx from scratch so the document always
#reflects the current state of the app. run `python make_docs.py` after structural changes.

#colours mirror the app palette in theme.py so the document looks on-brand
PRIMARY = RGBColor(0x43, 0x38, 0xCA)
MUTED = RGBColor(0x64, 0x74, 0x8B)
CODE_FILL = "F1F5F9"

OUTPUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs", "StratLab_Documentation.docx")


#--- small formatting helpers so the content below stays readable ---

def add_title(doc: Document, text: str) -> None:
    paragraph = doc.add_paragraph()
    run = paragraph.add_run(text)
    run.bold = True
    run.font.size = Pt(26)
    run.font.color.rgb = PRIMARY


def add_heading(doc: Document, text: str, size: int = 15) -> None:
    paragraph = doc.add_paragraph()
    paragraph.paragraph_format.space_before = Pt(14)
    paragraph.paragraph_format.space_after = Pt(4)
    run = paragraph.add_run(text)
    run.bold = True
    run.font.size = Pt(size)
    run.font.color.rgb = PRIMARY


def add_para(doc: Document, text: str) -> None:
    doc.add_paragraph(text)


def add_caption(doc: Document, text: str) -> None:
    paragraph = doc.add_paragraph()
    run = paragraph.add_run(text)
    run.italic = True
    run.font.size = Pt(9)
    run.font.color.rgb = MUTED


def add_bullets(doc: Document, items: list[str]) -> None:
    for item in items:
        doc.add_paragraph(item, style="List Bullet")


def add_code(doc: Document, code_text: str) -> None:
    paragraph = doc.add_paragraph()
    run = paragraph.add_run(code_text)
    run.font.name = "Consolas"
    run.font.size = Pt(9)
    #light grey background so code blocks stand out from prose
    properties = paragraph._p.get_or_add_pPr()
    shading = OxmlElement("w:shd")
    shading.set(qn("w:val"), "clear")
    shading.set(qn("w:fill"), CODE_FILL)
    properties.append(shading)


#--- the document content, section by section ---

def write_intro(doc: Document) -> None:
    add_title(doc, "StratLab — Project Documentation")
    add_para(doc, "StratLab is a web app for building, backtesting and comparing simple "
                  "investment strategies on real historical data — a flight simulator for "
                  "investing: test a strategy on the past before risking real money.")
    add_para(doc, "It is built with Python and Streamlit. All finance logic — data, strategies, "
                  "the backtest engine, and every metric — lives in core/, which knows nothing "
                  "about Streamlit. Streamlit pages only call into core/ and render the result.")

    add_heading(doc, "About the authors")
    add_para(doc, "StratLab was built by two Master in Banking and Finance students at the "
                  "University of St. Gallen as a tool to backtest straightforward strategies in "
                  "minutes instead of hours, without writing a line of code or paying for data.")

    add_heading(doc, "AI Usage Declaration")
    add_para(doc, "Claude was used to clean up and structure the code. ChatGPT was used to "
                  "understand the Yahoo Finance API and the strategies conceptually. The logic "
                  "and design decisions are our own.")
    add_caption(doc, "Additional source: https://ranaroussi.github.io/yfinance/")

    add_heading(doc, "Sources for the finance formulas")
    add_para(doc, "The metrics and formulas in core/measures.py (Sharpe, Sortino, Treynor, VaR, "
                  "CAPM/Fama-French factor models, the Markowitz tangency portfolio, EWMA "
                  "covariance, etc.) follow the conventions taught in the AQAM (Advanced "
                  "Quantitative Asset Management) course at the University of St. Gallen, plus "
                  "the academic sources cited in the Glossary. They are not AI-generated.")

    add_heading(doc, "Tech stack")
    add_bullets(doc, [
        "Streamlit — web interface and multi-page navigation",
        "pandas / numpy — price data and strategy maths",
        "yfinance — historical prices from Yahoo Finance",
        "scipy — skewness, kurtosis, Jarque-Bera, normal quantiles",
        "scikit-learn — logistic regression for the Explore page's forecast",
        "matplotlib — charts",
        "Supabase (Postgres) — users and saved strategies",
        "python-docx — generates this document",
    ])

    add_heading(doc, "Folder structure")
    add_code(doc,
        "stratlab_final/\n"
        "    core/                  <- finance engine (pure Python, no Streamlit)\n"
        "        data.py            <- PriceLoader, Fama-French download\n"
        "        strategy.py        <- the five strategies\n"
        "        backtest.py        <- Backtest.run()\n"
        "        measures.py        <- finance formulas + Analytics class\n"
        "        forecast.py        <- next-day direction forecast (logistic regression)\n"
        "    services/              <- persistence (Supabase)\n"
        "        db.py, auth.py, storage.py\n"
        "    pages/                 <- Streamlit pages\n"
        "        0_Home.py, 1_Builder.py, 2_Evaluate.py,\n"
        "        3_Compare.py, 4_Explore.py, 5_Glossary.py\n"
        "    app.py                 <- entry point: login + navigation\n"
        "    theme.py               <- design tokens (colours, font, spacing)\n"
        "    ui.py                  <- reusable UI components + shared charts\n"
        "    strategies_config.py   <- strategy registry for the UI\n"
        "    prices.py              <- cached price/fundamentals loader\n"
        "    tickers.py             <- searchable universe of stocks/ETFs\n"
        "    assets/                <- logos, favicon, style.css\n"
        "    docs/                  <- this document\n"
        "    make_docs.py           <- regenerates this document\n")
    add_para(doc, "Dependency direction is one-way: pages/ -> services/, prices.py, ui.py -> "
                  "core/. Nothing in core/ imports Streamlit or services/, so the finance "
                  "engine can be tested or reused on its own.")


def write_core(doc: Document) -> None:
    add_heading(doc, "The core/ engine")
    add_para(doc, "Everything that computes a number lives in core/. The UI never does finance "
                  "maths itself.")

    add_heading(doc, "core/data.py — PriceLoader", size=13)
    add_bullets(doc, [
        "PriceLoader().get_prices(tickers, start, end) -> DataFrame downloads daily "
        "adjusted-close prices from Yahoo Finance, one column per ticker. A ticker that "
        "fails to download is skipped silently.",
        "load_fama_french_factors(model) downloads monthly Fama-French factors "
        "(\"FF3\" or \"FF5\") from Ken French's data library, wrapped in try/except so a "
        "failed download returns an empty DataFrame instead of crashing.",
        "core/data.py is deliberately cache-free; prices.py adds an st.cache_data layer for "
        "the UI.",
    ])

    add_heading(doc, "core/strategy.py — the five strategies", size=13)
    add_para(doc, "Every strategy is a small class with the same interface: __init__ takes its "
                  "own parameters plus a shared rebalance_every (trading days between "
                  "rebalances, default 252), and get_weights(prices) -> dict[ticker, weight] "
                  "returns the target weights for \"today\" (or the unchanged current_weights "
                  "if it is not yet time to rebalance). Two shared helpers, "
                  "_should_rebalance(...) and _normalise_weights(...), factor out logic that "
                  "would otherwise repeat in every strategy.")
    add_bullets(doc, [
        "EqualWeight — splits the portfolio evenly across all tickers (the \"1/N\" rule), "
        "shown by DeMiguel, Garlappi & Uppal (2009) to be a tough benchmark to beat.",
        "FixedWeight — uses weights the user specifies (e.g. 60/40 stocks/bonds).",
        "Momentum — ranks assets by past return over a lookback window and goes long the "
        "top performers (optionally short the worst), per Jegadeesh & Titman (1993).",
        "InverseVolatility — weights each asset by the inverse of its volatility, so calmer "
        "assets get more weight.",
        "MeanVariance — the Markowitz (1952) tangency portfolio: w = Sigma^-1 * mu, "
        "normalised, with negative weights clipped to zero. Optionally uses an "
        "exponentially weighted (EWMA / RiskMetrics) covariance matrix instead of the "
        "sample covariance.",
    ])
    add_para(doc, "MeanVariance and InverseVolatility need a minimum amount of return history "
                  "(more observations than assets, or at least two observations) before their "
                  "covariance/volatility is defined; until then they hold cash (empty weights), "
                  "so the equity curve stays flat instead of producing NaN.")

    add_heading(doc, "core/backtest.py — Backtest", size=13)
    add_para(doc, "Backtest().run(strategy, prices) -> Series walks forward through the price "
                  "history one day at a time. On each day it passes only the prices up to that "
                  "day to strategy.get_weights() (no look-ahead bias), computes the weighted "
                  "daily return from each ticker's price change, and grows the portfolio value "
                  "(starting at 1.0) by that return. The result is stored on self.portfolio and "
                  "returned. All KPIs are then computed from this series via "
                  "core/measures.py — Backtest itself has no KPI methods.")

    add_heading(doc, "core/measures.py — finance formulas + Analytics", size=13)
    add_para(doc, "A library of stand-alone functions, each with a short docstring explaining "
                  "the formula:")
    add_bullets(doc, [
        "Returns: simple and log returns, average/annualised return, CAGR, volatility "
        "(daily, monthly, annualised).",
        "Risk-adjusted: Sharpe, Sortino and Treynor ratios (risk-free-adjusted).",
        "Distribution: skewness, excess kurtosis (K-3), Jarque-Bera normality test.",
        "Risk: maximum drawdown, historic VaR (empirical quantile) and "
        "variance-covariance VaR (t*mu + sqrt(t)*sigma*z, for 1-day and 1-month horizons).",
        "Factor models: CAPM, Fama-French 3- and 5-factor monthly regressions "
        "(alpha, beta, t-/p-values, R-squared, appraisal ratio).",
        "Portfolio construction: EWMA covariance (RiskMetrics), the cash/risk-free "
        "overlay, trading/management cost application, annual turnover, and the "
        "Markowitz (1952) minimum-variance frontier.",
    ])
    add_para(doc, "Analytics(values, benchmark_values, rf_annual) bundles these into one object "
                  "so a page can pull every measure for one portfolio (and its benchmark) "
                  "without re-deriving returns each time. This is what Evaluate and Compare "
                  "use for their KPI cards and tables.")

    add_heading(doc, "core/forecast.py — next-day direction forecast", size=13)
    add_para(doc, "predict_direction(prices, n_lags=10) is a small machine-learning add-on for "
                  "the Explore page. Each day's features are the previous n_lags daily "
                  "returns, and the label is whether that day's return was positive. A "
                  "scikit-learn LogisticRegression is trained on a chronological 80/20 "
                  "split (so the test set is always later in time than the training set), "
                  "and the function returns the test-set accuracy plus the predicted "
                  "probability that tomorrow's return is positive, based on the most recent "
                  "n_lags returns. Returns None if there is not enough price history "
                  "(fewer than n_lags + 30 return observations) to train and test the model.")


def write_services(doc: Document) -> None:
    add_heading(doc, "services/ — persistence layer")
    add_para(doc, "Users and saved strategies live in a hosted Supabase (Postgres) database, "
                  "reached through a single cached client. Credentials sit in "
                  ".streamlit/secrets.toml (excluded from version control).")
    add_bullets(doc, [
        "db.py — get_client() returns a cached Supabase client. run_query(builder) executes "
        "a query and returns its data, or shows st.error(...) and returns None on any "
        "exception, so a database error surfaces as a message instead of a crash.",
        "auth.py — login(username, password) and register(username, password); passwords "
        "are hashed with SHA256 and never stored in plain text.",
        "storage.py — save_strategy, load_strategies, delete_strategy and update_kpis. Each "
        "saved strategy is one row (tickers/params/kpis as JSONB); load_strategies rebuilds "
        "the strategy object via strategies_config.STRATEGIES and returns [] if the "
        "database is unreachable.",
    ])


def write_ui(doc: Document) -> None:
    add_heading(doc, "Shared UI building blocks")
    add_para(doc, "theme.py holds every colour, font and spacing value as plain constants; "
                  "both assets/style.css (via ui.inject_css) and the matplotlib charts (via "
                  "theme.apply_mpl_theme) read from it, so a colour is only ever defined once. "
                  "ui.py provides thin Streamlit "
                  "wrappers used on every page: page_header, kpi_card, verb_stepper, "
                  "empty_state, next_step and data_table, plus two shared chart helpers — "
                  "rebase_to_100 (index a series/frame to 100, used for every equity-curve "
                  "chart) and cml_chart (the risk/return scatter with the Capital Market Line, "
                  "used by Evaluate and Compare).")
    add_para(doc, "strategies_config.py is the single registry the whole UI reads: each "
                  "strategy is listed once with its class, display label and the "
                  "strategy-specific parameters the Builder should ask for. Adding a strategy "
                  "is therefore a two-step job: write the class in core/strategy.py, then add "
                  "one registry entry — no page code changes.")

    add_heading(doc, "Build -> Evaluate -> Compare", size=13)
    add_bullets(doc, [
        "Builder (pages/1_Builder.py) — configure a strategy: tickers, type and its "
        "registry-driven parameters, rebalancing frequency, an optional cash/risk-free "
        "overlay, and trading/management fees. _validate(...) collects every reason the "
        "strategy cannot be saved yet and the page lists them together. On success, "
        "storage.save_strategy persists the configuration (not a backtest result).",
        "Evaluate (pages/2_Evaluate.py) — reconstructs one saved strategy via the registry, "
        "runs it through Backtest alongside a benchmark (EqualWeight on the chosen "
        "benchmark ticker), applies the cash/risk-free overlay and fees to turn the gross "
        "curve into the net curve, and renders KPIs, factor models, charts and the CML for "
        "that one strategy.",
        "Compare (pages/3_Compare.py) — does the same for two or more saved strategies over "
        "the period they all share (latest common start to earliest common end), ranking "
        "them in a Key Metrics table, a Costs table and a combined CML chart.",
    ])
    add_para(doc, "pages/0_Home.py is the entry point: it lists saved strategies with their "
                  "last-stored KPIs (so the page loads without re-running a backtest) and "
                  "links into Build/Evaluate/Compare. Its Update button re-runs Backtest with "
                  "fresh data up to yesterday and persists the refreshed KPIs.")
    add_para(doc, "pages/4_Explore.py lets a user research tickers (price chart, CAGR/volatility "
                  "stats, fundamentals, correlation heatmap) before building a strategy. For a "
                  "single selected ticker, it also shows a Forecast section powered by "
                  "core/forecast.py: the model's historical test accuracy and its predicted "
                  "probability that tomorrow's return is positive, with a note that this is "
                  "for educational purposes only. "
                  "pages/5_Glossary.py is a searchable, colour-coded reference explaining every "
                  "metric and strategy with its formula and an academic citation where "
                  "relevant (Markowitz, 1952; DeMiguel, Garlappi & Uppal, 2009; Jegadeesh & "
                  "Titman, 1993; Fama & French, 1993/2015).")


def write_error_handling(doc: Document) -> None:
    add_heading(doc, "Error handling")
    add_para(doc, "A consistent, lightweight safety net prevents unhandled tracebacks without "
                  "changing the golden-path UI:")
    add_bullets(doc, [
        "services/db.py — every Supabase call goes through run_query, which catches "
        "exceptions, shows st.error(...), and returns None/[] so callers fall back to their "
        "normal empty-state rendering. login()/register() in services/auth.py treat that "
        "None as \"not found\"/\"taken\", so a database outage fails safe.",
        "core/data.py — _download_from_yahoo and load_fama_french_factors wrap their "
        "download/parse in try/except and return an empty Series/DataFrame on failure, so "
        "one bad ticker or a Ken French download outage does not crash the page.",
        "prices.py — load_risk_free_rate and load_info each catch any yfinance exception and "
        "fall back to (0.04, \"\") / {} respectively.",
        "core/strategy.py — _normalise_weights returns all-zero weights instead of dividing "
        "by zero (e.g. when MeanVariance clips every weight to 0); EqualWeight and Momentum "
        "stay in cash if there are no tickers/top performers; Momentum treats a 0 starting "
        "price as a 0% return; InverseVolatility gives a zero-volatility ticker weight 0; "
        "MeanVariance uses np.linalg.pinv instead of inv so a singular covariance matrix "
        "(e.g. two identical tickers) does not raise.",
        "core/backtest.py — Backtest.run skips a ticker for a day if its previous price is 0, "
        "instead of dividing by zero.",
        "core/measures.py — sharpe_ratio, sortino_ratio, treynor_ratio, cagr and historic_var "
        "all return NaN instead of dividing by zero or indexing into empty data for very "
        "short or degenerate return series.",
        "core/forecast.py — predict_direction returns None if there is not enough price "
        "history to train and test a model, and the Explore page shows an info message "
        "instead of the Forecast section in that case.",
        "Backtest runs — Backtest().run(...) in Home (Update), Evaluate and Compare are "
        "wrapped in try/except: Home shows a toast and keeps the existing KPIs, Evaluate "
        "shows a warning instead of the charts, and Compare skips the failing strategy with "
        "a warning and continues with the others.",
        "ui.cml_chart — renders nothing if the benchmark has zero or negative volatility, "
        "avoiding a division by zero in the Capital Market Line slope.",
    ])


def write_collinearity(doc: Document) -> None:
    add_heading(doc, "Collinearity handling")
    add_para(doc, "Several models in StratLab use inputs that can be highly correlated with "
                  "each other (e.g. two near-identical tickers, or Fama-French factors that "
                  "move together). Rather than letting that crash the page with a singular-"
                  "matrix error, each model is built on a numerically robust method:")
    add_bullets(doc, [
        "core/strategy.py — MeanVariance computes weights as the inverse covariance matrix "
        "times the mean returns (w = Sigma^-1 * mu). If two tickers are perfectly or near-"
        "perfectly correlated, Sigma is singular; np.linalg.pinv (pseudo-inverse) is used "
        "instead of np.linalg.inv, so the calculation returns a result instead of raising.",
        "core/measures.py — the CAPM/FF3/FF5 factor regressions (_ols/factor_model) use "
        "np.linalg.lstsq for the coefficients (robust to a rank-deficient design matrix when "
        "factors are collinear) and np.linalg.pinv for the standard-error covariance matrix, "
        "for the same reason.",
        "core/forecast.py — the next-day forecast uses the last n_lags daily returns as "
        "features, which are often correlated with each other (momentum/mean reversion). "
        "scikit-learn's LogisticRegression is used with its default L2 (ridge) penalty, "
        "which shrinks correlated coefficients to stable, finite values instead of the "
        "unstable estimates an unregularised fit would produce.",
    ])


def write_style(doc: Document) -> None:
    add_heading(doc, "Coding style")
    add_para(doc, "Small, single-purpose functions with type hints, plain readable loops over "
                  "clever one-liners, and short comments that explain why rather than what. "
                  "Every pages/*.py file follows the same layout: imports, then session-state "
                  "setup, then _-prefixed helper functions, then the page render code after a "
                  "'# --- PAGE ---' marker. Streamlit code never appears in core/.")


def build_document() -> None:
    doc = Document()
    #use a clean sans-serif default for body text
    doc.styles["Normal"].font.name = "Calibri"
    doc.styles["Normal"].font.size = Pt(11)

    write_intro(doc)
    write_core(doc)
    write_services(doc)
    write_ui(doc)
    write_error_handling(doc)
    write_collinearity(doc)
    write_style(doc)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    #the file is locked while it is open in Word or syncing in OneDrive - fail with a
    #clear instruction instead of a confusing traceback
    try:
        doc.save(OUTPUT_PATH)
    except PermissionError:
        print(f"could not write {OUTPUT_PATH} - it is probably open in Word or syncing "
              f"in OneDrive. close it and run 'python make_docs.py' again.")
        return
    print(f"wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    build_document()
