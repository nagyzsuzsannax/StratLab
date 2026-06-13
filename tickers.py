#AI Usage Declaration
#Claude was used to clean up, document and structure this code
#Claude Code was used to generate parts of this code
#ChatGPT helped us understand how to let users search by company name
#while still allowing a free-text ticker as a fallback
#The logic and design decisions are our own product

import streamlit as st

#a curated universe of popular stocks and ETFs so users can search by company name
#instead of memorising symbols. each entry is a small dict: ticker, name, type, category.
#a free-text field stays as a fallback for any symbol not in this list.

TICKERS = [
    # --- technology ---
    {"ticker": "AAPL", "name": "Apple", "type": "Stock", "category": "Technology"},
    {"ticker": "MSFT", "name": "Microsoft", "type": "Stock", "category": "Technology"},
    {"ticker": "NVDA", "name": "NVIDIA", "type": "Stock", "category": "Technology"},
    {"ticker": "AVGO", "name": "Broadcom", "type": "Stock", "category": "Technology"},
    {"ticker": "ORCL", "name": "Oracle", "type": "Stock", "category": "Technology"},
    {"ticker": "ADBE", "name": "Adobe", "type": "Stock", "category": "Technology"},
    {"ticker": "CRM", "name": "Salesforce", "type": "Stock", "category": "Technology"},
    {"ticker": "AMD", "name": "Advanced Micro Devices", "type": "Stock", "category": "Technology"},
    {"ticker": "INTC", "name": "Intel", "type": "Stock", "category": "Technology"},
    {"ticker": "CSCO", "name": "Cisco Systems", "type": "Stock", "category": "Technology"},
    {"ticker": "QCOM", "name": "Qualcomm", "type": "Stock", "category": "Technology"},
    {"ticker": "TXN", "name": "Texas Instruments", "type": "Stock", "category": "Technology"},
    {"ticker": "IBM", "name": "IBM", "type": "Stock", "category": "Technology"},
    {"ticker": "NOW", "name": "ServiceNow", "type": "Stock", "category": "Technology"},
    {"ticker": "INTU", "name": "Intuit", "type": "Stock", "category": "Technology"},
    {"ticker": "AMAT", "name": "Applied Materials", "type": "Stock", "category": "Technology"},
    {"ticker": "MU", "name": "Micron Technology", "type": "Stock", "category": "Technology"},
    {"ticker": "LRCX", "name": "Lam Research", "type": "Stock", "category": "Technology"},
    {"ticker": "ADI", "name": "Analog Devices", "type": "Stock", "category": "Technology"},
    {"ticker": "KLAC", "name": "KLA Corporation", "type": "Stock", "category": "Technology"},
    {"ticker": "SNPS", "name": "Synopsys", "type": "Stock", "category": "Technology"},
    {"ticker": "CDNS", "name": "Cadence Design Systems", "type": "Stock", "category": "Technology"},
    {"ticker": "PANW", "name": "Palo Alto Networks", "type": "Stock", "category": "Technology"},
    {"ticker": "CRWD", "name": "CrowdStrike", "type": "Stock", "category": "Technology"},
    {"ticker": "SNOW", "name": "Snowflake", "type": "Stock", "category": "Technology"},
    {"ticker": "PLTR", "name": "Palantir Technologies", "type": "Stock", "category": "Technology"},
    {"ticker": "DELL", "name": "Dell Technologies", "type": "Stock", "category": "Technology"},
    {"ticker": "MRVL", "name": "Marvell Technology", "type": "Stock", "category": "Technology"},
    {"ticker": "FTNT", "name": "Fortinet", "type": "Stock", "category": "Technology"},

    # --- communication & internet ---
    {"ticker": "GOOGL", "name": "Alphabet (Google)", "type": "Stock", "category": "Communication"},
    {"ticker": "META", "name": "Meta Platforms", "type": "Stock", "category": "Communication"},
    {"ticker": "NFLX", "name": "Netflix", "type": "Stock", "category": "Communication"},
    {"ticker": "DIS", "name": "Walt Disney", "type": "Stock", "category": "Communication"},
    {"ticker": "CMCSA", "name": "Comcast", "type": "Stock", "category": "Communication"},
    {"ticker": "T", "name": "AT&T", "type": "Stock", "category": "Communication"},
    {"ticker": "VZ", "name": "Verizon Communications", "type": "Stock", "category": "Communication"},
    {"ticker": "TMUS", "name": "T-Mobile US", "type": "Stock", "category": "Communication"},
    {"ticker": "SPOT", "name": "Spotify", "type": "Stock", "category": "Communication"},
    {"ticker": "SNAP", "name": "Snap", "type": "Stock", "category": "Communication"},
    {"ticker": "PINS", "name": "Pinterest", "type": "Stock", "category": "Communication"},
    {"ticker": "RBLX", "name": "Roblox", "type": "Stock", "category": "Communication"},
    {"ticker": "EA", "name": "Electronic Arts", "type": "Stock", "category": "Communication"},
    {"ticker": "TTWO", "name": "Take-Two Interactive", "type": "Stock", "category": "Communication"},

    # --- consumer discretionary ---
    {"ticker": "AMZN", "name": "Amazon", "type": "Stock", "category": "Consumer Discretionary"},
    {"ticker": "TSLA", "name": "Tesla", "type": "Stock", "category": "Consumer Discretionary"},
    {"ticker": "HD", "name": "Home Depot", "type": "Stock", "category": "Consumer Discretionary"},
    {"ticker": "MCD", "name": "McDonald's", "type": "Stock", "category": "Consumer Discretionary"},
    {"ticker": "NKE", "name": "Nike", "type": "Stock", "category": "Consumer Discretionary"},
    {"ticker": "SBUX", "name": "Starbucks", "type": "Stock", "category": "Consumer Discretionary"},
    {"ticker": "LOW", "name": "Lowe's", "type": "Stock", "category": "Consumer Discretionary"},
    {"ticker": "BKNG", "name": "Booking Holdings", "type": "Stock", "category": "Consumer Discretionary"},
    {"ticker": "TGT", "name": "Target", "type": "Stock", "category": "Consumer Discretionary"},
    {"ticker": "LULU", "name": "Lululemon Athletica", "type": "Stock", "category": "Consumer Discretionary"},
    {"ticker": "ABNB", "name": "Airbnb", "type": "Stock", "category": "Consumer Discretionary"},
    {"ticker": "F", "name": "Ford Motor", "type": "Stock", "category": "Consumer Discretionary"},
    {"ticker": "GM", "name": "General Motors", "type": "Stock", "category": "Consumer Discretionary"},
    {"ticker": "MAR", "name": "Marriott International", "type": "Stock", "category": "Consumer Discretionary"},
    {"ticker": "CMG", "name": "Chipotle Mexican Grill", "type": "Stock", "category": "Consumer Discretionary"},

    # --- consumer staples ---
    {"ticker": "WMT", "name": "Walmart", "type": "Stock", "category": "Consumer Staples"},
    {"ticker": "COST", "name": "Costco Wholesale", "type": "Stock", "category": "Consumer Staples"},
    {"ticker": "PG", "name": "Procter & Gamble", "type": "Stock", "category": "Consumer Staples"},
    {"ticker": "KO", "name": "Coca-Cola", "type": "Stock", "category": "Consumer Staples"},
    {"ticker": "PEP", "name": "PepsiCo", "type": "Stock", "category": "Consumer Staples"},
    {"ticker": "PM", "name": "Philip Morris International", "type": "Stock", "category": "Consumer Staples"},
    {"ticker": "MO", "name": "Altria Group", "type": "Stock", "category": "Consumer Staples"},
    {"ticker": "MDLZ", "name": "Mondelez International", "type": "Stock", "category": "Consumer Staples"},
    {"ticker": "CL", "name": "Colgate-Palmolive", "type": "Stock", "category": "Consumer Staples"},
    {"ticker": "KHC", "name": "Kraft Heinz", "type": "Stock", "category": "Consumer Staples"},
    {"ticker": "GIS", "name": "General Mills", "type": "Stock", "category": "Consumer Staples"},

    # --- financials ---
    {"ticker": "BRK-B", "name": "Berkshire Hathaway", "type": "Stock", "category": "Financials"},
    {"ticker": "JPM", "name": "JPMorgan Chase", "type": "Stock", "category": "Financials"},
    {"ticker": "V", "name": "Visa", "type": "Stock", "category": "Financials"},
    {"ticker": "MA", "name": "Mastercard", "type": "Stock", "category": "Financials"},
    {"ticker": "BAC", "name": "Bank of America", "type": "Stock", "category": "Financials"},
    {"ticker": "WFC", "name": "Wells Fargo", "type": "Stock", "category": "Financials"},
    {"ticker": "GS", "name": "Goldman Sachs", "type": "Stock", "category": "Financials"},
    {"ticker": "MS", "name": "Morgan Stanley", "type": "Stock", "category": "Financials"},
    {"ticker": "C", "name": "Citigroup", "type": "Stock", "category": "Financials"},
    {"ticker": "AXP", "name": "American Express", "type": "Stock", "category": "Financials"},
    {"ticker": "SCHW", "name": "Charles Schwab", "type": "Stock", "category": "Financials"},
    {"ticker": "BLK", "name": "BlackRock", "type": "Stock", "category": "Financials"},
    {"ticker": "SPGI", "name": "S&P Global", "type": "Stock", "category": "Financials"},
    {"ticker": "PYPL", "name": "PayPal Holdings", "type": "Stock", "category": "Financials"},
    {"ticker": "COF", "name": "Capital One Financial", "type": "Stock", "category": "Financials"},

    # --- healthcare ---
    {"ticker": "UNH", "name": "UnitedHealth Group", "type": "Stock", "category": "Healthcare"},
    {"ticker": "JNJ", "name": "Johnson & Johnson", "type": "Stock", "category": "Healthcare"},
    {"ticker": "LLY", "name": "Eli Lilly", "type": "Stock", "category": "Healthcare"},
    {"ticker": "ABBV", "name": "AbbVie", "type": "Stock", "category": "Healthcare"},
    {"ticker": "MRK", "name": "Merck", "type": "Stock", "category": "Healthcare"},
    {"ticker": "PFE", "name": "Pfizer", "type": "Stock", "category": "Healthcare"},
    {"ticker": "TMO", "name": "Thermo Fisher Scientific", "type": "Stock", "category": "Healthcare"},
    {"ticker": "ABT", "name": "Abbott Laboratories", "type": "Stock", "category": "Healthcare"},
    {"ticker": "DHR", "name": "Danaher", "type": "Stock", "category": "Healthcare"},
    {"ticker": "AMGN", "name": "Amgen", "type": "Stock", "category": "Healthcare"},
    {"ticker": "BMY", "name": "Bristol-Myers Squibb", "type": "Stock", "category": "Healthcare"},
    {"ticker": "CVS", "name": "CVS Health", "type": "Stock", "category": "Healthcare"},
    {"ticker": "MDT", "name": "Medtronic", "type": "Stock", "category": "Healthcare"},
    {"ticker": "GILD", "name": "Gilead Sciences", "type": "Stock", "category": "Healthcare"},
    {"ticker": "ISRG", "name": "Intuitive Surgical", "type": "Stock", "category": "Healthcare"},

    # --- industrials ---
    {"ticker": "CAT", "name": "Caterpillar", "type": "Stock", "category": "Industrials"},
    {"ticker": "BA", "name": "Boeing", "type": "Stock", "category": "Industrials"},
    {"ticker": "HON", "name": "Honeywell International", "type": "Stock", "category": "Industrials"},
    {"ticker": "GE", "name": "GE Aerospace", "type": "Stock", "category": "Industrials"},
    {"ticker": "UPS", "name": "United Parcel Service", "type": "Stock", "category": "Industrials"},
    {"ticker": "RTX", "name": "RTX Corporation", "type": "Stock", "category": "Industrials"},
    {"ticker": "UNP", "name": "Union Pacific", "type": "Stock", "category": "Industrials"},
    {"ticker": "DE", "name": "Deere & Company", "type": "Stock", "category": "Industrials"},
    {"ticker": "LMT", "name": "Lockheed Martin", "type": "Stock", "category": "Industrials"},
    {"ticker": "MMM", "name": "3M", "type": "Stock", "category": "Industrials"},
    {"ticker": "FDX", "name": "FedEx", "type": "Stock", "category": "Industrials"},
    {"ticker": "EMR", "name": "Emerson Electric", "type": "Stock", "category": "Industrials"},

    # --- energy ---
    {"ticker": "XOM", "name": "Exxon Mobil", "type": "Stock", "category": "Energy"},
    {"ticker": "CVX", "name": "Chevron", "type": "Stock", "category": "Energy"},
    {"ticker": "COP", "name": "ConocoPhillips", "type": "Stock", "category": "Energy"},
    {"ticker": "SLB", "name": "Schlumberger", "type": "Stock", "category": "Energy"},
    {"ticker": "EOG", "name": "EOG Resources", "type": "Stock", "category": "Energy"},
    {"ticker": "MPC", "name": "Marathon Petroleum", "type": "Stock", "category": "Energy"},
    {"ticker": "PSX", "name": "Phillips 66", "type": "Stock", "category": "Energy"},
    {"ticker": "OXY", "name": "Occidental Petroleum", "type": "Stock", "category": "Energy"},

    # --- materials ---
    {"ticker": "LIN", "name": "Linde", "type": "Stock", "category": "Materials"},
    {"ticker": "FCX", "name": "Freeport-McMoRan", "type": "Stock", "category": "Materials"},
    {"ticker": "NEM", "name": "Newmont", "type": "Stock", "category": "Materials"},
    {"ticker": "APD", "name": "Air Products and Chemicals", "type": "Stock", "category": "Materials"},
    {"ticker": "SHW", "name": "Sherwin-Williams", "type": "Stock", "category": "Materials"},
    {"ticker": "DOW", "name": "Dow", "type": "Stock", "category": "Materials"},

    # --- utilities ---
    {"ticker": "NEE", "name": "NextEra Energy", "type": "Stock", "category": "Utilities"},
    {"ticker": "DUK", "name": "Duke Energy", "type": "Stock", "category": "Utilities"},
    {"ticker": "SO", "name": "Southern Company", "type": "Stock", "category": "Utilities"},
    {"ticker": "D", "name": "Dominion Energy", "type": "Stock", "category": "Utilities"},

    # --- real estate ---
    {"ticker": "AMT", "name": "American Tower", "type": "Stock", "category": "Real Estate"},
    {"ticker": "PLD", "name": "Prologis", "type": "Stock", "category": "Real Estate"},
    {"ticker": "EQIX", "name": "Equinix", "type": "Stock", "category": "Real Estate"},
    {"ticker": "SPG", "name": "Simon Property Group", "type": "Stock", "category": "Real Estate"},

    # --- broad US equity ETFs ---
    {"ticker": "SPY", "name": "SPDR S&P 500 ETF", "type": "ETF", "category": "US Equity"},
    {"ticker": "VOO", "name": "Vanguard S&P 500 ETF", "type": "ETF", "category": "US Equity"},
    {"ticker": "IVV", "name": "iShares Core S&P 500 ETF", "type": "ETF", "category": "US Equity"},
    {"ticker": "VTI", "name": "Vanguard Total Stock Market ETF", "type": "ETF", "category": "US Equity"},
    {"ticker": "QQQ", "name": "Invesco QQQ (Nasdaq-100)", "type": "ETF", "category": "US Equity"},
    {"ticker": "DIA", "name": "SPDR Dow Jones Industrial Average ETF", "type": "ETF", "category": "US Equity"},
    {"ticker": "IWM", "name": "iShares Russell 2000 ETF", "type": "ETF", "category": "US Equity"},
    {"ticker": "RSP", "name": "Invesco S&P 500 Equal Weight ETF", "type": "ETF", "category": "US Equity"},
    {"ticker": "VTV", "name": "Vanguard Value ETF", "type": "ETF", "category": "US Equity"},
    {"ticker": "VUG", "name": "Vanguard Growth ETF", "type": "ETF", "category": "US Equity"},
    {"ticker": "VYM", "name": "Vanguard High Dividend Yield ETF", "type": "ETF", "category": "US Equity"},
    {"ticker": "SCHD", "name": "Schwab US Dividend Equity ETF", "type": "ETF", "category": "US Equity"},

    # --- sector ETFs ---
    {"ticker": "XLK", "name": "Technology Select Sector SPDR", "type": "ETF", "category": "Sector"},
    {"ticker": "XLF", "name": "Financial Select Sector SPDR", "type": "ETF", "category": "Sector"},
    {"ticker": "XLE", "name": "Energy Select Sector SPDR", "type": "ETF", "category": "Sector"},
    {"ticker": "XLV", "name": "Health Care Select Sector SPDR", "type": "ETF", "category": "Sector"},
    {"ticker": "XLY", "name": "Consumer Discretionary Select Sector SPDR", "type": "ETF", "category": "Sector"},
    {"ticker": "XLP", "name": "Consumer Staples Select Sector SPDR", "type": "ETF", "category": "Sector"},
    {"ticker": "XLI", "name": "Industrial Select Sector SPDR", "type": "ETF", "category": "Sector"},
    {"ticker": "XLU", "name": "Utilities Select Sector SPDR", "type": "ETF", "category": "Sector"},
    {"ticker": "XLB", "name": "Materials Select Sector SPDR", "type": "ETF", "category": "Sector"},
    {"ticker": "XLRE", "name": "Real Estate Select Sector SPDR", "type": "ETF", "category": "Sector"},
    {"ticker": "XLC", "name": "Communication Services Select Sector SPDR", "type": "ETF", "category": "Sector"},
    {"ticker": "SMH", "name": "VanEck Semiconductor ETF", "type": "ETF", "category": "Sector"},

    # --- bond ETFs ---
    {"ticker": "AGG", "name": "iShares Core US Aggregate Bond ETF", "type": "ETF", "category": "Bonds"},
    {"ticker": "BND", "name": "Vanguard Total Bond Market ETF", "type": "ETF", "category": "Bonds"},
    {"ticker": "TLT", "name": "iShares 20+ Year Treasury Bond ETF", "type": "ETF", "category": "Bonds"},
    {"ticker": "IEF", "name": "iShares 7-10 Year Treasury Bond ETF", "type": "ETF", "category": "Bonds"},
    {"ticker": "SHY", "name": "iShares 1-3 Year Treasury Bond ETF", "type": "ETF", "category": "Bonds"},
    {"ticker": "LQD", "name": "iShares Investment Grade Corporate Bond ETF", "type": "ETF", "category": "Bonds"},
    {"ticker": "HYG", "name": "iShares High Yield Corporate Bond ETF", "type": "ETF", "category": "Bonds"},
    {"ticker": "TIP", "name": "iShares TIPS Bond ETF", "type": "ETF", "category": "Bonds"},
    {"ticker": "BNDX", "name": "Vanguard Total International Bond ETF", "type": "ETF", "category": "Bonds"},

    # --- cash / treasury bills (risk-free proxies) ---
    {"ticker": "BIL", "name": "SPDR Bloomberg 1-3 Month T-Bill ETF", "type": "ETF", "category": "Cash / T-Bills"},
    {"ticker": "SGOV", "name": "iShares 0-3 Month Treasury Bond ETF", "type": "ETF", "category": "Cash / T-Bills"},
    {"ticker": "SHV", "name": "iShares Short Treasury Bond ETF", "type": "ETF", "category": "Cash / T-Bills"},

    # --- world / global equity ETFs ---
    {"ticker": "URTH", "name": "iShares MSCI World ETF", "type": "ETF", "category": "World"},
    {"ticker": "VT", "name": "Vanguard Total World Stock (FTSE All-World)", "type": "ETF", "category": "World"},
    {"ticker": "ACWI", "name": "iShares MSCI ACWI ETF", "type": "ETF", "category": "World"},
    {"ticker": "VEU", "name": "Vanguard FTSE All-World ex-US ETF", "type": "ETF", "category": "World"},

    # --- international equity ETFs ---
    {"ticker": "VEA", "name": "Vanguard Developed Markets ETF", "type": "ETF", "category": "International"},
    {"ticker": "VWO", "name": "Vanguard Emerging Markets ETF", "type": "ETF", "category": "International"},
    {"ticker": "VXUS", "name": "Vanguard Total International Stock ETF", "type": "ETF", "category": "International"},
    {"ticker": "EFA", "name": "iShares MSCI EAFE ETF", "type": "ETF", "category": "International"},
    {"ticker": "IEFA", "name": "iShares Core MSCI EAFE ETF", "type": "ETF", "category": "International"},
    {"ticker": "EEM", "name": "iShares MSCI Emerging Markets ETF", "type": "ETF", "category": "International"},
    {"ticker": "EWJ", "name": "iShares MSCI Japan ETF", "type": "ETF", "category": "International"},
    {"ticker": "MCHI", "name": "iShares MSCI China ETF", "type": "ETF", "category": "International"},
    {"ticker": "INDA", "name": "iShares MSCI India ETF", "type": "ETF", "category": "International"},
    {"ticker": "FXI", "name": "iShares China Large-Cap ETF", "type": "ETF", "category": "International"},

    # --- commodity ETFs ---
    {"ticker": "GLD", "name": "SPDR Gold Shares", "type": "ETF", "category": "Commodities"},
    {"ticker": "IAU", "name": "iShares Gold Trust", "type": "ETF", "category": "Commodities"},
    {"ticker": "SLV", "name": "iShares Silver Trust", "type": "ETF", "category": "Commodities"},
    {"ticker": "USO", "name": "United States Oil Fund", "type": "ETF", "category": "Commodities"},
    {"ticker": "DBC", "name": "Invesco DB Commodity Index ETF", "type": "ETF", "category": "Commodities"},

    # --- factor & thematic ETFs ---
    {"ticker": "ARKK", "name": "ARK Innovation ETF", "type": "ETF", "category": "Thematic"},
    {"ticker": "VIG", "name": "Vanguard Dividend Appreciation ETF", "type": "ETF", "category": "Factor"},
    {"ticker": "QUAL", "name": "iShares MSCI USA Quality Factor ETF", "type": "ETF", "category": "Factor"},
    {"ticker": "MTUM", "name": "iShares MSCI USA Momentum Factor ETF", "type": "ETF", "category": "Factor"},
    {"ticker": "USMV", "name": "iShares MSCI USA Min Vol Factor ETF", "type": "ETF", "category": "Factor"},
    {"ticker": "VNQ", "name": "Vanguard Real Estate ETF", "type": "ETF", "category": "Real Estate"},
]

#index by ticker for fast lookups when formatting labels
_BY_TICKER = {entry["ticker"]: entry for entry in TICKERS}


def label(entry: dict) -> str:
    """Render one ticker entry as "Name (TICKER)" for dropdowns."""
    return f"{entry['name']} ({entry['ticker']})"


def label_for(ticker: str) -> str:
    """Return the display label for a ticker symbol, falling back to the raw symbol for custom tickers."""
    entry = _BY_TICKER.get(ticker)
    if entry is None:
        return ticker
    return label(entry)


def select_tickers(label_text: str, default: list[str] | None = None, max_selections: int | None = None, key: str | None = None, placeholder: str | None = None) -> list[str]:
    """Render one combined ticker picker and return the chosen ticker symbols.

    Lets the user search the curated universe by company name OR type any
    other symbol - `accept_new_options` turns typed text into a chip like the
    rest, so custom tickers look identical to the listed ones.
    """
    default = default or []
    options = [entry["ticker"] for entry in TICKERS]
    #include any custom defaults so they render as selected chips
    extras = [tk for tk in default if tk not in options]

    chosen = st.multiselect(
        label_text,
        options=options + extras,
        default=default,
        max_selections=max_selections,
        format_func=label_for,
        accept_new_options=True,
        key=key,
        placeholder=placeholder if placeholder else "Search by name, or type any symbol…",
        help="search by name, or type any other symbol and press Enter",
    )
    #uppercase symbols the user typed (listed tickers are already upper-case)
    return [tk.upper() if tk not in options else tk for tk in chosen]
