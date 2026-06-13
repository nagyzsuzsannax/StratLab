from core.strategy import EqualWeight, FixedWeight, InverseVolatility, MeanVariance, Momentum

#the strategy registry — the single place the whole UI learns about strategies.
#adding a new strategy is a one-place change: write the class in core/strategy.py,
#then add one entry here. no page code has to change.
#
#each entry holds:
#  cls    -> the class from core.strategy
#  label  -> the human-readable name shown in the UI
#  params -> the strategy-specific inputs the Builder should ask for (a small spec each)
#
#a param spec uses: name, type ("int"|"float"|"bool"), default, and optionally
#min, max, step, help, and show_if (only show when another param has a given value).
#
#the rebalancing interval is deliberately NOT listed here: every strategy takes it, so
#the Builder renders one shared rebalancing control for all of them. FixedWeight also
#needs one weight per ticker, flagged with needs_weights and handled specially.

STRATEGIES = {
    "EqualWeight": {
        "cls": EqualWeight,
        "label": "Equal Weight",
        "params": [],
    },
    "FixedWeight": {
        "cls": FixedWeight,
        "label": "Fixed Weight",
        "needs_weights": True,
        "params": [],
    },
    "Momentum": {
        "cls": Momentum,
        "label": "Momentum",
        "params": [
            {"name": "lookback", "type": "int", "default": 252, "min": 20, "max": 756, "help": "trading days to look back"},
            {"name": "top_n", "type": "int", "default": 3, "min": 1, "help": "how many top tickers to go long"},
            {"name": "short", "type": "bool", "default": False, "help": "also short the worst performers"},
            {"name": "bottom_n", "type": "int", "default": 2, "min": 1, "show_if": {"short": True}, "help": "how many bottom tickers to short"},
        ],
    },
    "MeanVariance": {
        "cls": MeanVariance,
        "label": "Mean-Variance",
        "params": [
            {"name": "use_ewma", "type": "bool", "default": False, "help": "use an exponentially weighted (EWMA) covariance matrix"},
            {"name": "ewma_lambda", "type": "float", "default": 0.94, "min": 0.80, "max": 0.99, "step": 0.01, "show_if": {"use_ewma": True}, "help": "EWMA decay factor (RiskMetrics uses 0.94)"},
        ],
    },
    "InverseVolatility": {
        "cls": InverseVolatility,
        "label": "Inverse Volatility",
        "params": [],
    },
}
