#AI Usage Declaration
#Claude was used to clean up, document and structure this code
#Claude Code was used to generate parts of this code
#ChatGPT helped us understand how to build a simple text-search filter over
#a list of entries in Streamlit
#The logic and design decisions are our own product

import streamlit as st

import ui

#a searchable, colour-coded reference for every metric and strategy used in the app.
#the categories follow the analyst's "quant flow": isolated performance -> the dangers ->
#the basic reward -> the stress test against the market -> the actual implementation.
#notation is consistent throughout:
#  r_t period return · r̄ mean return · r_f risk-free · r_p portfolio · r_m market/benchmark
#  σ volatility · β beta · α alpha · ε residual · w_i weights · Σ covariance matrix · λ decay

CATEGORY_COLOR = {
    "Performance": "#14B8A6",
    "Downside & Tail": "#F59E0B",
    "Risk-adjusted": "#4338CA",
    "Benchmark & Factors": "#7C3AED",
    "Portfolio": "#10B981",
}

GLOSSARY = [
    # ---------- 1 · absolute performance & volatility ----------
    {"term": "Simple return", "category": "Performance",
     "body": "The arithmetic return of one period (daily, monthly, …). The 'daily return' is just "
             "this computed on daily prices.",
     "latex": r"r_t = \frac{P_t}{P_{t-1}} - 1"},
    {"term": "Log return", "category": "Performance",
     "body": "Continuously compounded return. Log returns add up over time, which is why they "
             "are used for the drift and for annualisation.",
     "latex": r"r_t = \ln\!\left(\frac{P_t}{P_{t-1}}\right)"},
    {"term": "Average return", "category": "Performance",
     "body": "The mean of the period returns. Multiply by the periods per year (252 / 12) to annualise it.",
     "latex": r"\bar{r} = \frac{1}{T}\sum_{t=1}^{T} r_t"},
    {"term": "CAGR", "category": "Performance",
     "body": "Compound annual growth rate: the constant yearly rate from the start value V₀ to the end "
             "value V_T over n years.",
     "latex": r"\text{CAGR} = \left(\frac{V_T}{V_0}\right)^{1/n} - 1"},
    {"term": "Volatility (annualised)", "category": "Performance",
     "body": "Standard deviation of returns, which scales with the square root of time. P is the periods "
             "per year (252 daily, 12 monthly).",
     "latex": r"\sigma_\text{ann} = \sigma\,\sqrt{P}"},

    # ---------- 2 · downside & tail risk ----------
    {"term": "Maximum Drawdown", "category": "Downside & Tail",
     "body": "The largest peak-to-trough fall in value: the worst loss from a previous high.",
     "latex": r"\text{MDD} = \min_{t}\ \frac{V_t - \max_{s\le t} V_s}{\max_{s\le t} V_s}"},
    {"term": "Value-at-Risk (historic)", "category": "Downside & Tail",
     "body": "Sort the historic returns and take the empirical quantile: the loss not expected to be "
             "exceeded at confidence c. k is rounded down to stay conservative.",
     "latex": r"\text{VaR}_c = r_{(k)},\qquad k = \big\lfloor T\,(1-c)\big\rfloor"},
    {"term": "Value-at-Risk (variance-covariance)", "category": "Downside & Tail",
     "body": "Parametric VaR assuming normal returns, scaled to a t-period horizon (mean × t, volatility × "
             "√t). z is the standard-normal quantile (−1.65 at 95%, −2.33 at 99%); μ is often set to 0.",
     "latex": r"\text{VaR}_{c,t} = t\,\mu + \sqrt{t}\,\sigma\,z_{1-c}"},
    {"term": "Skewness", "category": "Downside & Tail",
     "body": "Asymmetry of the return distribution. 0 = symmetric, <0 = a longer left tail (crash risk) — "
             "a key reason VaR and drawdowns can explode in a crisis.",
     "latex": r"S = \frac{1}{T}\sum_{t=1}^{T}\left(\frac{r_t-\bar{r}}{\sigma}\right)^{3}"},
    {"term": "Excess Kurtosis", "category": "Downside & Tail",
     "body": "Fat-tailedness relative to the normal (whose kurtosis is 3). 0 = normal, >0 = fatter tails "
             "(more extreme moves).",
     "latex": r"K_e = \frac{1}{T}\sum_{t=1}^{T}\left(\frac{r_t-\bar{r}}{\sigma}\right)^{4} - 3"},
    {"term": "Jarque-Bera Test", "category": "Downside & Tail",
     "body": "Tests whether returns are normal using skewness and excess kurtosis. H₀: normal. A small "
             "p-value rejects normality (fat tails / skew).",
     "latex": r"\text{JB} = \frac{T}{6}\left(S^{2} + \frac{K_e^{2}}{4}\right)\ \sim\ \chi^2_2"},

    # ---------- 3 · risk-adjusted, no benchmark ----------
    {"term": "Sharpe Ratio", "category": "Risk-adjusted",
     "body": "Excess return over the risk-free rate per unit of total risk (volatility). Annualised; "
             "above 1 is generally considered good.",
     "latex": r"\text{SR} = \frac{\bar{r}_p - r_f}{\sigma_p}"},
    {"term": "Sortino Ratio", "category": "Risk-adjusted",
     "body": "Like the Sharpe ratio but only downside volatility is penalised, so upside swings are not "
             "counted as risk.",
     "latex": r"\text{Sortino} = \frac{\bar{r}_p - r_f}{\sigma_\text{down}}"},

    # ---------- 4 · benchmark & factor models (the regression layer) ----------
    {"term": "Beta", "category": "Benchmark & Factors",
     "body": "Market risk: how strongly the portfolio moves with the benchmark. 1 = with it, >1 more, "
             "<1 less, <0 opposite. It is the slope of the CAPM regression.",
     "latex": r"\beta = \frac{\operatorname{Cov}(r_p, r_m)}{\operatorname{Var}(r_m)}"},
    {"term": "Alpha (Jensen / CAPM)", "category": "Benchmark & Factors",
     "body": "Out-performance: the return above what the CAPM predicts for the portfolio's beta. It is the "
             "intercept of the same regression that gives beta.",
     "latex": r"\alpha = \bar{r}_p - \big[r_f + \beta\,(\bar{r}_m - r_f)\big]"},
    {"term": "Treynor Ratio", "category": "Benchmark & Factors",
     "body": "Excess return per unit of systematic risk (beta) rather than total risk. Best for "
             "well-diversified portfolios.",
     "latex": r"\text{TR} = \frac{\bar{r}_p - r_f}{\beta_p}"},
    {"term": "Appraisal / Information Ratio", "category": "Benchmark & Factors",
     "body": "Jensen's alpha divided by the residual (portfolio-specific) risk: reward for stock-picking "
             "skill per unit of the risk taken to earn it.",
     "latex": r"\text{AR} = \frac{\alpha}{\sigma(\varepsilon)} = \frac{\alpha}{\sigma_p\,\sqrt{1-R^2}}"},
    {"term": "CAPM", "category": "Benchmark & Factors",
     "body": "The single-factor regression that produces alpha and beta: excess return explained by "
             "exposure to the market excess return. Estimated on monthly data.",
     "latex": r"r_p - r_f = \alpha + \beta\,(r_m - r_f) + \varepsilon"},
    {"term": "Fama-French 3-factor", "category": "Benchmark & Factors",
     "body": "Adds size (SMB) and value (HML) to the market factor (MKT), following Fama & French (1993). "
             "Alpha is the return left unexplained by these three risks.",
     "latex": r"r_p - r_f = \alpha + \beta_1\,\text{MKT} + \beta_2\,\text{SMB} + \beta_3\,\text{HML} + \varepsilon"},
    {"term": "Fama-French 5-factor", "category": "Benchmark & Factors",
     "body": "Extends FF3 with profitability (RMW) and investment (CMA), following Fama & French (2015): "
             "the most demanding test of whether a strategy earns true alpha.",
     "latex": r"r_p - r_f = \alpha + \beta_1\text{MKT} + \beta_2\text{SMB} + \beta_3\text{HML} + \beta_4\text{RMW} + \beta_5\text{CMA} + \varepsilon"},

    # ---------- 5 · portfolio construction & allocation (solved for the weights w) ----------
    {"term": "Equal Weight", "category": "Portfolio",
     "body": "Splits the portfolio evenly across all N assets and rebalances back to equal. The naive "
             "\"1/N\" rule, shown by DeMiguel, Garlappi & Uppal (2009) to be a tough benchmark to beat.",
     "latex": r"w_i = \frac{1}{N}"},
    {"term": "Fixed Weight", "category": "Portfolio",
     "body": "Uses weights you choose (e.g. 60/40) that must sum to 1, and rebalances back to them.",
     "latex": r"w_i\ \text{chosen},\qquad \sum_{i=1}^{N} w_i = 1"},
    {"term": "Inverse Volatility", "category": "Portfolio",
     "body": "Weights each asset by the inverse of its volatility, then normalises so the weights sum to "
             "1: calmer assets get more.",
     "latex": r"w_i = \frac{1/\sigma_i}{\sum_{j} 1/\sigma_j}"},
    {"term": "Mean-Variance (tangency)", "category": "Portfolio",
     "body": "The Markowitz (1952) portfolio that maximises the Sharpe ratio. Negative weights are then clipped "
             "to 0 and the rest renormalised (no short selling). The covariance matrix Σ is computed over "
             "past returns with a decay factor λ: λ = 1 gives the normal (sample) covariance, while λ < 1 "
             "gives an exponentially weighted (EWMA / RiskMetrics) covariance that weighs recent "
             "observations more heavily.",
     "latex": r"w = \frac{\Sigma^{-1}\mu}{\mathbf{1}^{\top}\Sigma^{-1}\mu} \qquad "
              r"\Sigma = (1-\lambda)\sum_{i=1}^{T} \lambda^{\,T-i}\,(r_i-\bar{r})(r_i-\bar{r})^{\top}"},
    {"term": "Momentum", "category": "Portfolio",
     "body": "Ranks assets by past return over the lookback, goes long the top n (and optionally shorts "
             "the bottom m). Recent winners tend to keep winning, as documented by Jegadeesh & Titman (1993).",
     "latex": r"w_i = \begin{cases} +\tfrac{1}{n} & i \in \text{top } n \\ -\tfrac{1}{m} & i \in \text{bottom } m \\ 0 & \text{otherwise} \end{cases}"},
]

CATEGORIES = ["All"] + list(CATEGORY_COLOR.keys())


def _matches(entry: dict, query: str, category: str) -> bool:
    """Return True if `entry` matches the selected category and (lowercased) search query."""
    if category != "All" and entry["category"] != category:
        return False
    if not query:
        return True
    haystack = f"{entry['term']} {entry['category']} {entry['body']}".lower()
    return query in haystack


def _chip(category: str) -> str:
    """Render a coloured category chip (tinted background + matching text colour)."""
    color = CATEGORY_COLOR[category]
    return f"<span class='chip' style='background:{color}1f;color:{color}'>{category}</span>"


# --- PAGE ---

ui.page_header("Glossary", "Plain-language reference for every metric and strategy.", icon="menu_book")

left, middle, right = st.columns([1, 3, 1])
with middle:
    filters = st.columns([2, 1])
    with filters[0]:
        query = st.text_input("Search", placeholder="🔍 Search metrics and strategies…",
                              label_visibility="collapsed", key="glossary_search")
    with filters[1]:
        category = st.selectbox("Category", CATEGORIES, label_visibility="collapsed", key="glossary_category")

    matches = [entry for entry in GLOSSARY if _matches(entry, query.strip().lower(), category)]
    if not matches:
        st.caption("No terms match your search.")

    for entry in matches:
        with st.container(border=True):
            st.markdown(
                f"<div class='strategy-head'><span class='strategy-name'>{entry['term']}</span>"
                f"{_chip(entry['category'])}</div>",
                unsafe_allow_html=True,
            )
            st.write(entry["body"])
            st.latex(entry["latex"])
