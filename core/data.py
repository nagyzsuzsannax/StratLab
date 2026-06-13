#AI Usage Declaration
#Claude was used to clean up and structure this code
#ChatGPT was used to understand how the Yahoo Finance API works
#Additional source: https://ranaroussi.github.io/yfinance/
#The logic and design decisions are our own product

import io
import re
import zipfile

import pandas as pd
import requests
import yfinance as yf

class PriceLoader:
    """Downloads historical close prices from Yahoo Finance via yfinance."""

    def get_prices(self, tickers: list[str], start: str, end: str) -> pd.DataFrame:
        """Return a DataFrame with one column per ticker (failed tickers are skipped)."""
        all_prices = {}

        for ticker in tickers:
            prices = self._download_from_yahoo(ticker, start, end)
            if prices.empty:
                continue
            all_prices[ticker] = prices

        return pd.DataFrame(all_prices)

    def _download_from_yahoo(self, ticker: str, start: str, end: str) -> pd.Series:
        """Download one ticker's close prices, returning an empty Series on any failure."""
        try:
            raw = yf.download(ticker, start=start, end=end, auto_adjust=True, progress=False)
        except Exception:
            return pd.Series(dtype=float)

        if raw.empty:
            return pd.Series(dtype=float)

        if "Close" not in raw.columns.get_level_values(0):
            return pd.Series(dtype=float)

        return raw["Close"][ticker]


#fama-french factor data (monthly) from ken french's data library, for CAPM / FF3 / FF5.
#note: data is published with a lag, so it usually ends about two months before today.
_FF_URLS = {
    "FF3": "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Research_Data_Factors_CSV.zip",
    "FF5": "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Research_Data_5_Factors_2x3_CSV.zip",
}
_FF_COLUMNS = {
    "FF3": ["Mkt-RF", "SMB", "HML", "RF"],
    "FF5": ["Mkt-RF", "SMB", "HML", "RMW", "CMA", "RF"],
}


def load_fama_french_factors(model: str = "FF3") -> pd.DataFrame:
    """Download and parse the monthly Fama-French factors (model = "FF3" or "FF5").

    Returns a DataFrame indexed by month-end date with the factor columns
    plus RF, all converted from percent to decimals.
    """
    columns = _FF_COLUMNS[model]
    try:
        response = requests.get(_FF_URLS[model], timeout=30)
        response.raise_for_status()
        archive = zipfile.ZipFile(io.BytesIO(response.content))
        text = archive.read(archive.namelist()[0]).decode("latin-1")
    except Exception:
        return pd.DataFrame(columns=["date"] + columns).set_index("date")

    rows = []
    for line in text.splitlines():
        parts = [p.strip() for p in line.split(",")]
        #monthly rows start with a 6-digit YYYYMM; the annual section below uses 4-digit years
        if re.fullmatch(r"\d{6}", parts[0]) and len(parts) >= len(columns) + 1:
            month_end = pd.to_datetime(parts[0], format="%Y%m") + pd.offsets.MonthEnd(0)
            values = [float(p) / 100 for p in parts[1:1 + len(columns)]]
            rows.append([month_end] + values)

    return pd.DataFrame(rows, columns=["date"] + columns).set_index("date")
