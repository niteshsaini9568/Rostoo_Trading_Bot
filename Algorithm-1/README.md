# RoostooTradingBot

A hybrid trading bot for the Roostoo Hackathon, combining LSTM predictions and Moving Average Crossover strategies, optimized for penny coins like DOGE/USD.

## Setup
1. Install dependencies: `pip install -r requirements.txt`
2. Run the bot: `python main.py`

## Features
- **LSTM Strategy**: Predicts price movements using neural networks.
- **MA Crossover**: Uses short (5) and long (20) moving averages for trading signals.
- **Penny Coin Focus**: Trades in bulk (10,000 coins) for low-value assets.
- **Risk Management**: Includes stop-loss and Sharpe Ratio calculation.