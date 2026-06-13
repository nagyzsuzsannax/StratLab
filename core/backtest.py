#AI Usage Declaration
#Claude was used to clean up, document and structure this code
#The backtest mechanics (rebalancing, return compounding) follow the AQAM
#(Advanced Quantitative Asset Management) course at the University of St. Gallen
#The logic and design decisions are our own product

import pandas as pd


class Backtest:
    """Simulates how a portfolio would have grown under a strategy.

    KPIs are computed from `self.portfolio` via core/measures.py (the `Analytics` class), not here.
    """

    def __init__(self) -> None:
        self.portfolio = None

    def run(self, strategy, prices: pd.DataFrame) -> pd.Series:
        """Simulate the portfolio day by day and return its value series (starting at 1.0)."""
        portfolio_value = 1.0
        portfolio_history = {}
        number_of_days = len(prices)

        for i in range(1, number_of_days):
            #only pass prices up to today to avoid look-ahead bias
            prices_so_far = prices.iloc[:i]
            current_date = prices.index[i]
            previous_date = prices.index[i - 1]

            try:
                #ask the strategy what weights to use today
                weights = strategy.get_weights(prices_so_far)

                if len(weights) == 0:
                    portfolio_history[current_date] = portfolio_value
                    continue

                #calculate the daily return of each ticker
                daily_return = 0
                for ticker in weights:
                    weight = weights[ticker]
                    if ticker not in prices.columns:
                        continue
                    price_today = prices.loc[current_date, ticker]
                    price_yesterday = prices.loc[previous_date, ticker]
                    if price_yesterday == 0:
                        continue
                    price_change = price_today - price_yesterday
                    ticker_return = price_change / price_yesterday
                    weighted_return = weight * ticker_return
                    daily_return = daily_return + weighted_return

                #grow the portfolio by that return
                growth = 1 + daily_return
                portfolio_value = portfolio_value * growth
                portfolio_history[current_date] = portfolio_value
            except Exception:
                #an unexpected error on one day (e.g. a strategy bug) shouldn't crash the
                #whole backtest: carry the portfolio value forward unchanged for this day
                portfolio_history[current_date] = portfolio_value

        self.portfolio = pd.Series(portfolio_history)
        return self.portfolio
