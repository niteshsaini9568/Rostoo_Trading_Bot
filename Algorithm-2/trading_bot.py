# trading_bot.py
import time
import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
from api_client import RoostooAPIClient
from strategies import MLStrategy
import logging

class RoostooMLTradingBot:
    SUPPORTED_COINS = ['BTC', 'ETH', 'SOL', 'BCH', 'BNB', 'XRP', 'ADA', 'SAND', 'USTC']
    QUANTITY_STEPS = {
        'BTC/USD': 0.0001, 'ETH/USD': 0.01, 'SOL/USD': 0.1, 'BCH/USD': 0.01,
        'BNB/USD': 0.01, 'XRP/USD': 1.0, 'ADA/USD': 1.0, 'SAND/USD': 1.0, 'USTC/USD': 10.0
    }

    def __init__(self, api_key: str, secret_key: str, base_url: str = "https://mock-api.roostoo.com"):
        self.api_client = RoostooAPIClient(api_key, secret_key, base_url)
        self.trade_pairs = [f"{coin}/USD" for coin in self.SUPPORTED_COINS]
        self.strategy = MLStrategy(self.trade_pairs)
        
        self.base_risk_per_trade = 0.10
        self.transaction_cost = 0.001
        self.min_commission = 0.1
        self.max_drawdown_limit = 0.50
        self.min_trade_interval = 10
        self.max_daily_trades = 100
        self.slippage_factor = 0.001
        self.min_quantity = 0.0001
        self.min_profit_potential = 0.003
        
        self.positions = {pair: False for pair in self.trade_pairs}
        self.trade_histories = {pair: [] for pair in self.trade_pairs}
        self.price_histories = {pair: [] for pair in self.trade_pairs}
        self.entry_prices = {pair: None for pair in self.trade_pairs}
        self.stop_loss_prices = {pair: None for pair in self.trade_pairs}
        self.profit_targets = {pair: None for pair in self.trade_pairs}
        self.last_trade_times = {pair: 0 for pair in self.trade_pairs}
        self.daily_trade_counts = {pair: 0 for pair in self.trade_pairs}
        
        self.start_time = None
        self.initial_portfolio_value = None
        self.day_start = time.time()
        self.last_request_time = 0
        self.request_interval = 0.5
        self.ticker_cache = {}
        self.cache_timestamp = 0
        
        self._initialize_positions()

    def _rate_limit(self):
        elapsed = time.time() - self.last_request_time
        if elapsed < self.request_interval:
            time.sleep(self.request_interval - elapsed)
        self.last_request_time = time.time()

    def _initialize_positions(self):
        balance = self.api_client.get_balance()
        if balance and balance.get('Success'):
            wallet = balance.get('Wallet', balance.get('SpotWallet', {}))
            for coin, pair in zip(self.SUPPORTED_COINS, self.trade_pairs):
                coin_free = float(wallet.get(coin, {}).get('Free', 0))
                self.positions[pair] = coin_free >= self.min_quantity
                if self.positions[pair]:
                    price = self.get_ticker_price(pair) or 0
                    self.entry_prices[pair] = price
                    atr = self.calculate_initial_atr(pair)
                    self.stop_loss_prices[pair] = price * (1 - 0.015)
                    self.profit_targets[pair] = price * (1 + 0.03)
                logging.info(f"Initial position for {pair}: {self.positions[pair]} ({coin}: {coin_free})")
            usd_free = float(wallet.get('USD', {}).get('Free', 0))
            logging.info(f"Initial USD balance: {usd_free}")
        else:
            logging.error("Failed to fetch initial balance")

    def calculate_initial_atr(self, pair: str) -> float:
        prices = pd.Series([self.get_ticker_price(pair) or 0] * 14)
        if len(self.price_histories[pair]) >= 14:
            prices = pd.Series([p['price'] for p in self.price_histories[pair][-14:]])
        return prices.diff().abs().rolling(window=14, min_periods=1).mean().iloc[-1] or 1.0

    def kelly_criterion(self, win_prob: float, win_loss_ratio: float) -> float:
        return max(0.01, min(self.base_risk_per_trade, (win_prob - (1 - win_prob) / win_loss_ratio)))

    def get_strategy_action(self, strategy: str, indicators: pd.Series, current_price: float, pair: str) -> Tuple[str, float]:
        volatility = indicators['volatility']
        if self.positions[pair]:
            if current_price <= self.stop_loss_prices[pair]:
                return 'SELL', 0.0
            if current_price >= self.profit_targets[pair]:
                return 'SELL', 0.0
            if time.time() - self.last_trade_times[pair] > 300 and current_price > self.entry_prices[pair] * 1.005:
                return 'SELL', 0.0
        
        win_prob = 0.6
        win_loss_ratio = 2.0
        risk_fraction = self.kelly_criterion(win_prob, win_loss_ratio)
        
        if strategy == 'TREND' and not self.positions[pair] and indicators['macd'] > indicators['signal']:
            if current_price * (1 + self.min_profit_potential) > current_price + indicators['atr']:
                return 'BUY', risk_fraction
        elif strategy == 'MEAN_REVERSION' and self.positions[pair] and indicators['rsi'] > 60:
            return 'SELL', 0.0
        elif strategy == 'SENTIMENT' and not self.positions[pair]:
            if indicators['rsi'] < 40 or volatility > 0.001:
                return 'BUY', risk_fraction
        elif strategy == 'BREAKOUT' and not self.positions[pair]:
            if indicators['momentum'] > 0 and current_price > max([p['price'] for p in self.price_histories[pair][-20:]]):
                return 'BUY', risk_fraction
        return 'HOLD', 0.0

    def calculate_portfolio_value(self, current_prices: Dict[str, float]) -> float:
        self._rate_limit()
        balance = self.api_client.get_balance()
        if not balance or not balance.get('Success'):
            logging.warning("Failed to fetch balance for portfolio value")
            return 0.0
        wallet = balance.get('Wallet', balance.get('SpotWallet', {}))
        usd_free = float(wallet.get('USD', {}).get('Free', 0))
        total_value = usd_free
        for coin, pair in zip(self.SUPPORTED_COINS, self.trade_pairs):
            coin_free = float(wallet.get(coin, {}).get('Free', 0))
            total_value += coin_free * current_prices.get(pair, 0)
        logging.info(f"Portfolio value calculated: USD={usd_free}, Total={total_value}")
        return round(total_value, 2)

    def check_risk_limits(self, pair: str, portfolio_value: float, current_time: float) -> bool:
        if current_time - self.day_start >= 86400:
            self.daily_trade_counts = {p: 0 for p in self.trade_pairs}
            self.day_start = current_time
        return (current_time - self.last_trade_times[pair] >= self.min_trade_interval and
                self.daily_trade_counts[pair] < self.max_daily_trades and
                (not self.initial_portfolio_value or portfolio_value >= self.initial_portfolio_value * (1 - self.max_drawdown_limit)))

    def get_ticker_price(self, pair: str) -> Optional[float]:
        if time.time() - self.cache_timestamp > 5:
            self._rate_limit()
            tickers = self.api_client.get_all_tickers()
            if tickers and tickers.get('Success'):
                self.ticker_cache = tickers['Data']
                self.cache_timestamp = time.time()
            else:
                return None
        try:
            return float(self.ticker_cache[pair]['LastPrice'])
        except (KeyError, TypeError):
            return None

    def execute_trade(self, pair: str, action: str, current_price: float, atr: float, risk_fraction: float) -> Optional[float]:
        self._rate_limit()
        balance = self.api_client.get_balance()
        if not balance or not balance.get('Success'):
            logging.error("Failed to fetch balance for trade execution")
            return None
        
        wallet = balance.get('Wallet', balance.get('SpotWallet', {}))
        coin = pair.split('/')[0]
        usd_balance = float(wallet.get('USD', {}).get('Free', 0))
        coin_balance = float(wallet.get(coin, {}).get('Free', 0))
        
        execution_price = current_price * (1 + self.slippage_factor if action == 'BUY' else 1 - self.slippage_factor)
        step_size = self.QUANTITY_STEPS.get(pair, 0.01)
        
        if action == 'BUY' and usd_balance >= 0.1:
            quantity = (usd_balance * risk_fraction) / execution_price
            if quantity < self.min_quantity:
                quantity = self.min_quantity
            quantity = np.floor(quantity / step_size) * step_size
            quantity_str = f"{quantity:.8f}".rstrip('0').rstrip('.')
            response = self.api_client.place_order(pair, 'BUY', 'MARKET', quantity_str)
            if response and response.get('Success'):
                filled_price = float(response['OrderDetail']['FilledAverPrice'])
                filled_quantity = float(response['OrderDetail']['FilledQuantity'])
                self.trade_histories[pair].append({
                    'type': 'BUY', 'price': filled_price, 'quantity': filled_quantity,
                    'profit': 0.0, 'timestamp': time.time()
                })
                self.positions[pair] = True
                self.entry_prices[pair] = filled_price
                self.stop_loss_prices[pair] = filled_price * (1 - 0.015)
                self.profit_targets[pair] = filled_price * (1 + 0.03)
                self.last_trade_times[pair] = time.time()
                self.daily_trade_counts[pair] += 1
                logging.info(f"BUY {pair} at {filled_price:.2f}, Quantity: {filled_quantity}")
                return filled_price
            return None
        
        elif action == 'SELL' and self.positions[pair] and coin_balance >= self.min_quantity:
            quantity = coin_balance
            quantity = np.floor(quantity / step_size) * step_size
            quantity_str = f"{quantity:.8f}".rstrip('0').rstrip('.')
            response = self.api_client.place_order(pair, 'SELL', 'MARKET', quantity_str)
            if response and response.get('Success'):
                filled_price = float(response['OrderDetail']['FilledAverPrice'])
                filled_quantity = float(response['OrderDetail']['FilledQuantity'])
                commission = max(filled_price * filled_quantity * self.transaction_cost, self.min_commission)
                net_profit = (filled_price - self.entry_prices[pair]) * filled_quantity - commission
                self.trade_histories[pair].append({
                    'type': 'SELL', 'price': filled_price, 'quantity': filled_quantity,
                    'profit': net_profit, 'timestamp': time.time()
                })
                self.positions[pair] = False
                self.entry_prices[pair] = None
                self.stop_loss_prices[pair] = None
                self.profit_targets[pair] = None
                self.last_trade_times[pair] = time.time()
                self.daily_trade_counts[pair] += 1
                logging.info(f"SELL {pair} at {filled_price:.2f}, Quantity: {filled_quantity}, Profit: {net_profit:.2f}")
                return net_profit
            return None
        return None

    def run_strategy(self, runtime: float = 3600):
        logging.info("Training ML models...")
        self.strategy.train_model(self.trade_pairs)
        if not any(self.strategy.fitted_models.values()):
            logging.error("No models fitted, exiting")
            return
        
        self.start_time = time.time()
        initial_prices = {pair: self.get_ticker_price(pair) for pair in self.trade_pairs}
        if all(p is not None for p in initial_prices.values()):
            self.initial_portfolio_value = self.calculate_portfolio_value(initial_prices)
            logging.info(f"Initial Portfolio Value: {self.initial_portfolio_value:.2f}")
        
        while time.time() - self.start_time < runtime:
            current_time = time.time()
            current_prices = {pair: self.get_ticker_price(pair) for pair in self.trade_pairs}
            if any(p is None for p in current_prices.values()):
                time.sleep(10)
                continue
            
            portfolio_value = self.calculate_portfolio_value(current_prices)
            
            for pair in self.trade_pairs:
                if not self.strategy.fitted_models[pair] or not self.check_risk_limits(pair, portfolio_value, current_time):
                    continue
                
                self.price_histories[pair].append({'price': current_prices[pair], 'timestamp': current_time})
                if len(self.price_histories[pair]) < 26:
                    continue
                
                prices_df = pd.DataFrame(self.price_histories[pair][-26:], columns=['price', 'timestamp'])
                prices_df['close'] = prices_df['price']
                indicators = self.strategy.calculate_indicators(prices_df).iloc[-1]
                strategy = self.strategy.predict_strategy(pair, indicators)
                action, risk_fraction = self.get_strategy_action(strategy, indicators, current_prices[pair], pair)
                
                if action in ['BUY', 'SELL']:
                    result = self.execute_trade(pair, action, current_prices[pair], indicators['atr'], risk_fraction)
                    if result is not None:
                        logging.info(f"Trade executed for {pair}: {action} at {result:.2f}")
                
                logging.info(f"Price: {current_prices[pair]:.2f} | Portfolio: {portfolio_value:.2f} | "
                            f"Pair: {pair} | Strategy: {strategy} | Action: {action}")
            
            time.sleep(10)