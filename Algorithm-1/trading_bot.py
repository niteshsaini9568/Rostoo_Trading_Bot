# trading_bot.py
import asyncio
from datetime import datetime
from api_client import RoostooAPIClient
from strategies import LSTMStrategy, MovingAverageCrossoverStrategy
from risk_manager import RiskManager

class RoostooTradingBot:
    def __init__(self, api_key, secret_key, trade_pairs=["DOGE/USD"], base_url="https://mock-api.roostoo.com"):
        self.api_client = RoostooAPIClient(api_key, secret_key, base_url)
        self.trade_pairs = trade_pairs
        self.lstm_strategies = {pair: LSTMStrategy() for pair in trade_pairs}
        self.ma_strategies = {pair: MovingAverageCrossoverStrategy() for pair in trade_pairs}
        self.risk_manager = RiskManager()
        self.holdings = {pair: 0.0 for pair in trade_pairs}
        self.cash = 100000  # Starting cash in USD
        self.trade_history = {pair: [] for pair in trade_pairs}
        self.min_order_size = 10000  # Bulk trade amount for penny coins
        self.commission_rate = 0.001
        self.stop_loss_threshold = -0.02
        self.thresholds = {pair: {"buy": 0.005, "sell": -0.005} for pair in trade_pairs}

    async def get_portfolio_value(self, current_prices):
        total_value = self.cash
        for pair, price in current_prices.items():
            total_value += self.holdings[pair] * price
        self.risk_manager.update_portfolio(total_value)
        return total_value

    async def execute_trade(self, pair, signal, price):
        if signal == "BUY" and self.cash >= self.min_order_size * price:
            quantity = self.min_order_size
            commission = quantity * price * self.commission_rate
            self.holdings[pair] += quantity
            self.cash -= (quantity * price + commission)
            self.trade_history[pair].append({"time": datetime.now(), "action": "BUY", "price": price, "amount": quantity})
            print(f"Executed BUY: {quantity} {pair} at {price}")
            await self.api_client.place_order(pair, "BUY", quantity)
        elif signal == "SELL" and self.holdings[pair] >= self.min_order_size:
            quantity = self.min_order_size
            commission = quantity * price * self.commission_rate
            self.holdings[pair] -= quantity
            self.cash += (quantity * price - commission)
            self.trade_history[pair].append({"time": datetime.now(), "action": "SELL", "price": price, "amount": quantity})
            print(f"Executed SELL: {quantity} {pair} at {price}")
            await self.api_client.place_order(pair, "SELL", quantity)

    async def run_trading_strategy(self):
        print("Starting trading strategy...")
        while True:
            try:
                market_data_tasks = [self.api_client.get_market_data(pair) for pair in self.trade_pairs]
                market_data = await asyncio.gather(*market_data_tasks)
                current_prices = {}
                for pair, data in zip(self.trade_pairs, market_data):
                    if data.get("Success"):
                        current_prices[pair] = float(data["Data"][pair]["LastPrice"])
                    else:
                        print(f"Failed to get market data for {pair}: {data}")
                        continue

                for pair in self.trade_pairs:
                    if pair not in current_prices:
                        continue
                    price = current_prices[pair]
                    self.ma_strategies[pair].update_price(price)
                    lstm_pred = await self.lstm_strategies[pair].predict(self.api_client, pair)
                    ma_signal = self.ma_strategies[pair].predict()

                    # Hybrid decision: Use MA for penny coins, LSTM for trend confirmation
                    if lstm_pred > self.thresholds[pair]["buy"] and ma_signal == "BUY":
                        await self.execute_trade(pair, "BUY", price)
                    elif (lstm_pred < self.thresholds[pair]["sell"] or ma_signal == "SELL") and self.holdings[pair] > 0:
                        price_change = (price - self.trade_history[pair][-1]["price"]) / self.trade_history[pair][-1]["price"] if self.trade_history[pair] else 0
                        if price_change < self.stop_loss_threshold or ma_signal == "SELL":
                            await self.execute_trade(pair, "SELL", price)

                portfolio_value = await self.get_portfolio_value(current_prices)
                sharpe_ratio = self.risk_manager.calculate_sharpe_ratio()
                print(f"Portfolio Value: {portfolio_value:.2f} | Sharpe Ratio: {sharpe_ratio:.4f}")
                await asyncio.sleep(30)
            except Exception as e:
                print(f"Error in trading loop: {str(e)}")
                await asyncio.sleep(5)