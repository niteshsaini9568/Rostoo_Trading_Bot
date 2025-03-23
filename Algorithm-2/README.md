# RoostooMLTradingBot

An ML-driven trading bot by Nitesh Saini for the Roostoo Hackathon, using Random Forest to predict strategies (Trend, Mean Reversion, Sentiment, Breakout).

## Setup
1. Install dependencies: `pip install -r requirements.txt`
2. Run the bot: `python main.py`

## Features
- **ML Strategy**: Random Forest predicts trading strategies based on technical indicators (MACD, RSI, ATR, etc.).
- **Multi-Pair Trading**: Supports BTC, ETH, SOL, BCH, BNB, XRP, ADA, SAND, USTC.
- **Risk Management**: Kelly Criterion sizing, stop-loss (1.5%), profit target (3%), max drawdown (50%).
- **Data Source**: Binance historical data via CCXT.