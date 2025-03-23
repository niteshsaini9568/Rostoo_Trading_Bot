# risk_manager.py
import numpy as np

class RiskManager:
    def __init__(self, risk_free_rate=0.001):
        self.portfolio_values = []
        self.risk_free_rate = risk_free_rate

    def update_portfolio(self, value):
        self.portfolio_values.append(value)

    def calculate_sharpe_ratio(self):
        if len(self.portfolio_values) < 2:
            return 0.0
        returns = np.diff(self.portfolio_values) / self.portfolio_values[:-1]
        excess_returns = returns - self.risk_free_rate
        mean_return = np.mean(excess_returns)
        std_return = np.std(excess_returns)
        return mean_return / std_return if std_return > 0 else 0.0