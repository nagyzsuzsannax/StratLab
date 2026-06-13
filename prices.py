import pandas as pd
import streamlit as st
import yfinance as yf

from core.data import PriceLoader, load_fama_french_factors

#thin UI-side cache around Yahoo Finance. the core data layer stays cache-free by
#design; here we add an hour-long cache so changing a dropdown does not re-download
#everything on every rerun. core.PriceLoader only returns close prices, so the extra
#info / volume the Explore page needs are fetched here (still UI-side, never in core/).

#Error handling in this file:
#- load_prices/load_factors delegate to core.data, which already catches its
#  own download/parse errors (see core/data.py).
#- load_risk_free_rate and load_info each catch any exception from yfinance
#  and fall back to (0.04, "") / {} respectively, so a Yahoo outage degrades
#  the page instead of crashing it.


@st.cache_data(ttl=3600)
def load_prices(tickers: list[str], start: str, end: str) -> pd.DataFrame:
    """Return cached close prices for `tickers` between `start` and `end`."""
    loader = PriceLoader()
    return loader.get_prices(tickers, start, end)


def clear_prices_cache() -> None:
    """Clear the cached prices so the Update button can force a fresh pull up to yesterday."""
    load_prices.clear()


@st.cache_data(ttl=86400)
def load_factors(model: str) -> pd.DataFrame:
    """Return cached monthly Fama-French factors (CAPM / FF3 / FF5), refreshed once a day."""
    return load_fama_french_factors(model)


@st.cache_data(ttl=3600)
def load_risk_free_rate() -> tuple[float, str]:
    """Return the current annualised risk-free rate and its as-of date.

    Reads the 13-week T-bill yield (^IRX) from Yahoo. Falls back to (0.04, "")
    if Yahoo is unavailable.
    """
    try:
        data = yf.download("^IRX", period="10d", auto_adjust=True, progress=False)
        close = data["Close"]
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]
        close = close.dropna()
        return float(close.iloc[-1]) / 100, close.index[-1].date().isoformat()
    except Exception:
        return 0.04, ""


@st.cache_data(ttl=3600)
def load_info(ticker: str) -> dict:
    """Return a fundamental snapshot for `ticker` (52-week range, market cap, P/E, dividend yield, ...).

    Used by the Explore stats table and single-asset view. Returns {} if
    Yahoo has nothing.
    """
    try:
        info = yf.Ticker(ticker).info
    except Exception:
        return {}
    return info or {}
