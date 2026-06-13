#AI Usage Declaration
#Claude was used to clean up, document and structure this code
#Claude Code was used to generate parts of this code
#ChatGPT helped us understand how to look up a ticker's company info via
#yfinance
#The logic and design decisions are our own product

import math
from datetime import date, timedelta

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

import prices
import theme
import tickers
import ui
from core import forecast, measures


# --- small display helpers: formatting only ---

def _is_missing(value: float | None) -> bool:
    """Return True if `value` is None or NaN (Yahoo leaves fundamentals blank this way)."""
    return value is None or (isinstance(value, float) and math.isnan(value))


def _format_market_cap(value: float | None) -> str:
    """Format a market cap as e.g. "$2.45T" / "$890.00B" / "$12,345"."""
    if _is_missing(value):
        return "—"
    for suffix, threshold in [("T", 1e12), ("B", 1e9), ("M", 1e6)]:
        if value >= threshold:
            return f"${value / threshold:.2f}{suffix}"
    return f"${value:,.0f}"


def _format_ratio(value: float | None) -> str:
    """Format a ratio (e.g. P/E) to one decimal, or "—" if missing."""
    return "—" if _is_missing(value) else f"{value:.1f}"


def _format_div_yield(value: float | None) -> str:
    """Format a dividend yield as a percentage, handling Yahoo's mixed fraction/percent units."""
    if _is_missing(value):
        return "—"
    percent = value * 100 if value < 1 else value
    return f"{percent:.2f}%"


def _stats_table(price_df: pd.DataFrame) -> pd.DataFrame:
    """Build a per-ticker table of CAGR/volatility (daily, monthly, annual) plus key Yahoo fundamentals."""
    rows = {}
    for symbol in price_df.columns:
        series = price_df[symbol].dropna()
        info = prices.load_info(symbol)
        if len(series) >= 3:
            returns = measures.simple_returns(series)
            stats = {
                "CAGR": theme.format_pct(measures.cagr(series)),
                "Vol (daily)": theme.format_pct(measures.volatility(returns, annualized=False), 2),
                "Vol (monthly)": theme.format_pct(measures.volatility(measures.to_monthly_returns(series), measures.MONTHS, annualized=False), 2),
                "Vol (annual)": theme.format_pct(measures.volatility(returns, annualized=True)),
            }
        else:
            stats = {k: "—" for k in ("CAGR", "Vol (daily)", "Vol (monthly)", "Vol (annual)")}
        rows[symbol] = {
            **stats,
            "52W High": theme.format_money(info.get("fiftyTwoWeekHigh"), 2),
            "52W Low": theme.format_money(info.get("fiftyTwoWeekLow"), 2),
            "Market Cap": _format_market_cap(info.get("marketCap")),
            "P/E": _format_ratio(info.get("trailingPE")),
            "Div Yield": _format_div_yield(info.get("dividendYield")),
        }
    return pd.DataFrame.from_dict(rows, orient="index")


# --- the single view (works for one ticker or many) ---

def _explore_view(price_df: pd.DataFrame) -> None:
    """Render the price chart, statistics table and (for several tickers) the correlation heatmap."""
    multi = price_df.shape[1] >= 2

    #normalise to 100 to compare several series; for a single ticker show its actual price
    normalise = st.checkbox("Normalise to 100", value=multi, key="explore_normalise")
    plot_df = ui.rebase_to_100(price_df) if normalise else price_df

    fig, ax = plt.subplots(figsize=(10, 4.2))
    for column in plot_df.columns:
        ax.plot(plot_df.index, plot_df[column], linewidth=1.5, label=column)
    ax.set_xlabel("Date")
    ax.set_ylabel("Indexed to 100" if normalise else "Price")
    #legend further below the chart, so it never overlaps the "Date" label
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=min(plot_df.shape[1], 6))
    fig.tight_layout()
    ui.show_figure(fig)

    st.subheader("Statistics")
    ui.data_table(_stats_table(price_df))

    if multi:
        st.subheader("Correlation")
        returns = price_df.pct_change(fill_method=None).dropna()
        if returns.shape[0] >= 2 and returns.shape[1] >= 2:
            corr = returns.corr()
            cmap = mcolors.LinearSegmentedColormap.from_list("corr", [theme.NEGATIVE, "#FFFFFF", theme.PRIMARY])

            fig, ax = plt.subplots(figsize=(0.7 * len(corr) + 2, 0.7 * len(corr) + 1))
            im = ax.imshow(corr.values, cmap=cmap, vmin=-1, vmax=1)
            ax.set_xticks(range(len(corr.columns)))
            ax.set_xticklabels(corr.columns, rotation=45, ha="right")
            ax.set_yticks(range(len(corr.index)))
            ax.set_yticklabels(corr.index)
            ax.grid(False)
            for i in range(corr.shape[0]):
                for j in range(corr.shape[1]):
                    ax.text(j, i, f"{corr.values[i, j]:.2f}", ha="center", va="center", fontsize=9, color=theme.TEXT)
            fig.colorbar(im, ax=ax, label="ρ", shrink=0.8)
            fig.tight_layout()
            ui.show_figure(fig)
        else:
            st.info("Not enough overlapping data to compute correlations.")
    st.subheader("Forecast")
    forecast_cols = st.columns(min(len(price_df.columns), 3))
    for i, column in enumerate(price_df.columns):
        with forecast_cols[i % len(forecast_cols)]:
            result = forecast.predict_direction(price_df[column])
            if result is None:
                st.info(f"{column}: not enough price history for a forecast.")
            else:
                st.metric(f"{column}: probability of a positive return tomorrow", theme.format_pct(result["probability_up"]))
                st.caption(f"Model accuracy on historical test data: {theme.format_pct(result['accuracy'])}")
    st.caption("Logistic regression on the last 10 days' returns. For educational purposes only, not investment advice.")


# --- PAGE ---

ui.page_header("Explore the Investment Universe", "Compare prices, fundamentals and correlations.", icon="search")

controls = st.columns([3, 1, 1])
with controls[0]:
    symbols = tickers.select_tickers("Tickers (up to 10)", max_selections=10, key="explore_tickers")
with controls[1]:
    start_date = st.date_input("From", value=date.today() - timedelta(days=5 * 365), max_value=date.today(), key="explore_from")
with controls[2]:
    end_date = st.date_input("To", value=date.today(), max_value=date.today(), key="explore_to")

if start_date > end_date:
    st.error("'From' date can't be later than 'To' date.")
    st.stop()

if not symbols:
    st.info("Pick one or more tickers above to start exploring.")
    st.stop()

if start_date >= end_date:
    st.warning("The From date must be before the To date.")
    st.stop()

with st.spinner("Loading prices…"):
    price_df = prices.load_prices(symbols, start_date.isoformat(), end_date.isoformat())

if price_df.empty:
    st.warning("No price data for the current selection. Try a different ticker or date range.")
    st.stop()

#a ticker that doesn't exist on Yahoo Finance (or has no data for this range) is silently
#dropped by the loader, so flag it here instead of just showing fewer columns
missing = [s for s in symbols if s not in price_df.columns]
if missing:
    st.warning(f"No data found for: {', '.join(missing)}. Check the symbol or try a different date range.")

_explore_view(price_df)
