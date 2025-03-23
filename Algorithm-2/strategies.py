# strategies.py
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import RandomizedSearchCV
import ccxt
import logging

class MLStrategy:
    def __init__(self, trade_pairs: list):
        self.strategies = ['TREND', 'MEAN_REVERSION', 'SENTIMENT', 'BREAKOUT']
        self.actions = ['BUY', 'SELL', 'HOLD']
        self.models = {pair: RandomForestClassifier(random_state=42, n_estimators=100, max_depth=10) for pair in trade_pairs}
        self.fitted_models = {pair: False for pair in trade_pairs}

    def fetch_historical_data(self, pair: str, limit: int = 200) -> pd.DataFrame:
        exchange = ccxt.binance({'enableRateLimit': True})
        pair = pair.replace('USD', 'USDT')
        try:
            ohlcv = exchange.fetch_ohlcv(pair, timeframe='1h', limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            logging.info(f"Fetched {len(df)} hourly data points for {pair}")
            return df
        except Exception as e:
            logging.error(f"Error fetching data for {pair}: {e}")
            return pd.DataFrame()

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        prices = df['close']
        df['ema_fast'] = prices.ewm(span=12, adjust=False).mean()
        df['ema_slow'] = prices.ewm(span=26, adjust=False).mean()
        df['macd'] = df['ema_fast'] - df['ema_slow']
        df['signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['signal']
        df['atr'] = prices.diff().abs().rolling(window=14, min_periods=1).mean()
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14, min_periods=1).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14, min_periods=1).mean()
        rs = gain / loss.replace(0, 1e-10)
        df['rsi'] = 100 - (100 / (1 + rs))
        df['momentum'] = prices - prices.shift(4)
        df['volatility'] = prices.pct_change().rolling(window=14, min_periods=1).std()
        return df.fillna(0)

    def prepare_training_data(self, df: pd.DataFrame) -> tuple:
        if df.empty:
            return pd.DataFrame(), pd.Series()
        df = self.calculate_indicators(df)
        df['returns'] = df['close'].pct_change().shift(-1)
        
        df['strategy'] = 'HOLD'
        df.loc[(df['macd'] > df['signal']) & (df['rsi'] < 65), 'strategy'] = 'TREND'
        df.loc[(df['macd'] < df['signal']) & (df['rsi'] > 35), 'strategy'] = 'MEAN_REVERSION'
        df.loc[(df['rsi'] < 35) | (df['momentum'] > 0), 'strategy'] = 'SENTIMENT'
        df.loc[df['close'] > df['close'].rolling(window=20).max().shift(1), 'strategy'] = 'BREAKOUT'
        
        features = ['macd', 'macd_hist', 'rsi', 'momentum', 'atr', 'volatility', 'ema_fast']
        X = df[features].fillna(0)
        strategy_map = {s: i for i, s in enumerate(self.strategies)}
        y = df['strategy'].map(lambda x: strategy_map.get(x, 3))
        mask = y.notna()
        return X.loc[mask], y.loc[mask]

    def train_model(self, trade_pairs: list):
        for pair in trade_pairs:
            logging.info(f"Training model for {pair}...")
            historical_data = self.fetch_historical_data(pair)
            if not historical_data.empty:
                X, y = self.prepare_training_data(historical_data)
                if not X.empty and not y.empty:
                    param_grid = {
                        'n_estimators': [50, 100, 200],
                        'max_depth': [5, 10, 20],
                        'min_samples_split': [2, 5, 10]
                    }
                    rf = RandomForestClassifier(random_state=42)
                    search = RandomizedSearchCV(rf, param_grid, n_iter=10, cv=3, random_state=42)
                    search.fit(X, y)
                    self.models[pair] = search.best_estimator_
                    self.fitted_models[pair] = True
                    logging.info(f"Model trained for {pair} with best params: {search.best_params_}")

    def predict_strategy(self, pair: str, indicators: pd.Series) -> str:
        features = ['macd', 'macd_hist', 'rsi', 'momentum', 'atr', 'volatility', 'ema_fast']
        X = pd.DataFrame([indicators[features]], columns=features)
        strategy_idx = self.models[pair].predict(X)[0]
        logging.info(f"Predicted strategy for {pair}: {self.strategies[strategy_idx]} | RSI: {indicators['rsi']:.2f} | MACD: {indicators['macd']:.4f}")
        return self.strategies[strategy_idx]