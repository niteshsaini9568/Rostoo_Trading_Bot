# strategies.py
import numpy as np
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from sklearn.preprocessing import MinMaxScaler

class LSTMStrategy:
    def __init__(self, sequence_length=30):
        self.sequence_length = sequence_length
        self.scaler = MinMaxScaler()
        self.model = self._build_lstm_model()

    def _build_lstm_model(self):
        model = Sequential([
            LSTM(50, return_sequences=True, input_shape=(self.sequence_length, 3)),
            Dropout(0.2),
            LSTM(50),
            Dropout(0.2),
            Dense(1)
        ])
        model.compile(optimizer="adam", loss="mse")
        return model

    async def collect_historical_data(self, api_client, pair):
        data_points = []
        for _ in range(self.sequence_length * 2):
            data = await api_client.get_market_data(pair)
            if data.get("Success"):
                ticker = data["Data"][pair]
                data_points.append([float(ticker["LastPrice"]), float(ticker.get("CoinTradeValue", 1000)), float(ticker["Change"])])
            await asyncio.sleep(1)
        if len(data_points) < self.sequence_length + 1:
            print(f"Warning: Not enough data for {pair}: {len(data_points)} points")
            return np.array([])
        df = pd.DataFrame(data_points, columns=["price", "volume", "change"])
        return np.array(df[["price", "volume", "change"]])

    async def predict(self, api_client, pair):
        data = await self.collect_historical_data(api_client, pair)
        if data.size == 0:
            return 0.0
        scaled_data = self.scaler.fit_transform(data)
        X, y = [], []
        for i in range(len(scaled_data) - self.sequence_length):
            X.append(scaled_data[i:i + self.sequence_length])
            y.append(scaled_data[i + self.sequence_length, 0])
        X, y = np.array(X), np.array(y)
        if len(X) < 2:
            return 0.0
        train_size = len(X) - 1
        if train_size > 0:
            epochs = min(5, train_size)
            self.model.fit(X[:-1], y[1:], epochs=epochs, batch_size=1, verbose=0)
        last_sequence = X[-1].reshape(1, self.sequence_length, 3)
        predicted_scaled = self.model.predict(last_sequence, verbose=0)[0][0]
        last_price = data[-1, 0]
        scaled_last = self.scaler.transform([data[-1]])[0, 0]
        price_diff = (predicted_scaled - scaled_last) * (self.scaler.data_max_[0] - self.scaler.data_min_[0])
        predicted_price = last_price + price_diff
        return (predicted_price - last_price) / last_price

class MovingAverageCrossoverStrategy:
    def __init__(self, short_window=5, long_window=20):
        self.short_window = short_window
        self.long_window = long_window
        self.prices = []

    def update_price(self, price):
        self.prices.append(price)
        if len(self.prices) > self.long_window:
            self.prices.pop(0)

    def predict(self):
        if len(self.prices) < self.long_window:
            return "HOLD"
        short_ma = np.mean(self.prices[-self.short_window:])
        long_ma = np.mean(self.prices)
        if short_ma > long_ma:
            return "BUY"
        elif short_ma < long_ma:
            return "SELL"
        return "HOLD"