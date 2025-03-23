# Documentation

## Overview

This document provides a comprehensive explanation of two trading bots developed for the Roostoo <> KodeKurrent AI Web3 Trading Bot Hackathon Challenge:

- **Bot 1: RoostooMLTradingBot by Nitesh Saini** – A machine learning-driven bot using Random Forest for multi-strategy trading.
- **Bot 2: RoostooTradingBot (Hybrid)** – An LSTM-based predictive bot enhanced with Moving Average Crossover for penny coin trading.

Both bots interact with the Roostoo mock exchange APIs, aim to maximize portfolio returns while minimizing risk, and are evaluated primarily by **Sharpe Ratio** and secondarily by **Portfolio Return** over a 24-hour trading window.

---

## Bot 1: RoostooMLTradingBot

### Strategies

#### Supported Strategies
- **Trend**: Capitalizes on sustained price movements using MACD signals.
- **Mean Reversion**: Exploits price corrections when RSI indicates overbought conditions.
- **Sentiment**: Trades based on momentum and RSI oversold signals.
- **Breakout**: Identifies and acts on price breakouts above recent highs.

#### Smart Logic
A Random Forest Classifier predicts the optimal strategy per trading pair based on technical indicators, adapting to market conditions dynamically.

### Algorithm

- **Model**: Random Forest Classifier with RandomizedSearchCV for hyperparameter tuning (`n_estimators`, `max_depth`, `min_samples_split`).
- **Training Data**: Fetches 200 hourly OHLCV data points from Binance via CCXT, calculates indicators, and labels strategies based on predefined rules (e.g., MACD > Signal for Trend).
- **Prediction**: For each trading cycle, computes indicators from the last 26 price points, predicts the strategy, and maps it to a Buy/Sell/Hold action.

### Technical Indicators

- **MACD**: Fast (12) and slow (26) EMAs, with a 9-period signal line.
- **RSI**: 14-period Relative Strength Index for overbought/oversold detection.
- **ATR**: 14-period Average True Range for volatility and stop-loss calculation.
- **Momentum**: Price change over 4 periods.
- **Volatility**: 14-period standard deviation of price changes.
- **EMA Fast**: 12-period exponential moving average for trend detection.

### Smart Logic

- **Dynamic Strategy Selection**: The Random Forest model evaluates current market conditions (via indicators) to select the most suitable strategy, enhancing adaptability.
- **Kelly Criterion**: Calculates position size based on a fixed win probability (0.6) and win/loss ratio (2.0), capped at 10% of available balance per trade.
- **Trade Filtering**: Ensures trades meet a minimum profit potential (0.3%) relative to ATR, avoiding low-return opportunities.

### Stop-Loss Mechanism

- **Fixed Stop-Loss**: Set at 1.5% below the entry price for each Buy trade.
- **Profit Target**: Set at 3% above the entry price, triggering an automatic Sell.
- **Time-Based Exit**: Sells after 300 seconds if price exceeds entry by 0.5%, ensuring profit-taking.

### Risk Management

- **Position Sizing**: Kelly Criterion adjusts trade size dynamically, with a minimum of 0.0001 units and step sizes per coin (e.g., 0.0001 BTC, 1.0 XRP).
- **Max Drawdown**: Limits portfolio loss to 50% of initial value, halting trading if breached.
- **Trade Limits**: Caps daily trades at 100 per pair and enforces a 10-second minimum interval between trades.
- **Slippage**: Applies a 0.1% slippage factor to execution prices.
- **Transaction Costs**: 0.1% commission per trade, with a $0.10 minimum.

### Portfolio Tracking

- **Real-Time Value**: Calculated using current prices and wallet balances from the API.
- **Sharpe Ratio**: Not explicitly computed in code but supported implicitly through risk-adjusted returns (requires post-processing).

### Execution Flow

1. **Initialization**: Loads initial balances and positions, trains ML models.
2. **Trading Loop**: Every 10 seconds, updates prices, predicts strategies, checks risk limits, and executes trades.
3. **Runtime**: Defaults to 1 hour (3600s), adjustable to 24 hours (86400s) for the hackathon.

### Strengths

- Robust multi-strategy approach with ML adaptability.
- Comprehensive risk management with Kelly Criterion and stop-loss.
- Efficient ticker caching (5s) reduces API calls.

### Weaknesses

- High computational load from ML training and frequent indicator calculations.
- Relies on Binance data, which may misalign with Roostoo’s mock exchange.
- No explicit Sharpe Ratio calculation in runtime.

---

## Bot 2: RoostooTradingBot (Hybrid)

### Strategies

#### LSTM Predictive
- Uses a Long Short-Term Memory (LSTM) neural network to forecast price changes based on historical price, volume, and change data.
- Optimized for trend prediction over a 30-point sequence.

#### Moving Average Crossover
- Employs short (5-period) and long (20-period) simple moving averages (SMAs) to generate Buy (short > long) and Sell (short < long) signals.
- Tailored for penny coins (e.g., DOGE/USD) with high-frequency trading.

#### Hybrid Logic
Combines LSTM for trend confirmation with MA Crossover for penny coin-specific signals, prioritizing MA for Buy/Sell triggers.

### Algorithm

#### LSTM Model
- **Architecture**: Two LSTM layers (50 units each) with Dropout (0.2), followed by a Dense output layer.
- **Training**: Fits on 30-point sequences of scaled price, volume, and change data, predicting the next price change every cycle (5 epochs).

#### MA Crossover
- Calculates SMAs over the last 5 and 20 prices, triggering trades on crossovers.

#### Decision
- **Buy**: LSTM predicts >0.5% increase AND MA short > long.
- **Sell**: LSTM predicts <-0.5% decrease OR MA short < long OR stop-loss triggered.

### Technical Indicators

- **LSTM Inputs**: Price, volume, and percentage change over time.
- **Moving Averages**: Short SMA (5), Long SMA (20).

### Smart Logic

- **Hybrid Decision-Making**: Integrates LSTM’s predictive power with MA’s responsiveness, ideal for volatile penny coins.
- **Dynamic Thresholds**: Buy (+0.5%) and Sell (-0.5%) thresholds adjust based on market volatility (not fully implemented but extensible).
- **Penny Coin Focus**: Trades in bulk (10,000 units) to leverage low-price, high-volume assets.

### Stop-Loss Mechanism

- **Fixed Stop-Loss**: 2% below the entry price, checked per trade.
- **Profit Taking**: Sells on MA crossover or LSTM downturn, no fixed profit target.

### Risk Management

- **Position Sizing**: Fixed at 10,000 units per trade, adjusted by available cash for Buys.
- **Commission**: 0.1% per trade or $1 minimum, deducted from cash.
- **Stop-Loss**: Triggers at -2% price change from entry.
- **Portfolio Monitoring**: Updates value every 30 seconds, calculating Sharpe Ratio.
- **Sharpe Ratio**: Computed from portfolio value changes, annualized with a 0.1% risk-free rate.

### Portfolio Tracking

- **Real-Time Value**: Sum of cash and holdings valued at current prices.
- **Sharpe Ratio**: Calculated as `(mean(excess returns) / std(excess returns))`, updated per cycle.

### Execution Flow

1. **Initialization**: Sets up API client, strategies, and initial cash ($100,000).
2. **Trading Loop**: Asynchronously fetches market data every 30 seconds, predicts with LSTM, checks MA signals, executes trades, and updates portfolio.
3. **Runtime**: Continuous loop, suitable for 24-hour trading with no fixed end.

### Strengths

- Asynchronous design improves efficiency for real-time trading.
- Hybrid strategy balances prediction and responsiveness.
- Explicit Sharpe Ratio calculation aligns with hackathon metrics.

### Weaknesses

- LSTM requires 30+ data points, delaying initial trades.
- Simplified risk management lacks drawdown limits or dynamic sizing.
- Penny coin focus limits diversification.

---

## Comparative Analysis

| **Aspect**            | **Bot 1 (RoostooMLTradingBot)**                     | **Bot 2 (RoostooTradingBot)**                     |
|-----------------------|----------------------------------------------------|--------------------------------------------------|
| **Primary Strategy**  | Multi-strategy ML (Random Forest)                 | Hybrid LSTM + Moving Average                    |
| **Algorithm**         | Random Forest with RandomizedSearchCV             | LSTM neural network + SMA crossover             |
| **Trade Pairs**       | BTC, ETH, SOL, BCH, BNB, XRP, ADA, SAND, USTC     | DOGE/USD (extensible to others)                 |
| **Smart Logic**       | Strategy prediction + Kelly Criterion             | LSTM trend confirmation + MA signals            |
| **Stop-Loss**         | 1.5% below entry, time-based exits                | 2% below entry                                  |
| **Risk Management**   | Kelly sizing, 50% max drawdown, trade limits      | Fixed sizing, commission, Sharpe focus          |
| **Sharpe Ratio**      | Implicit (requires post-processing)               | Explicitly calculated per cycle                 |
| **Execution**         | Synchronous, 10s intervals                        | Asynchronous, 30s intervals                     |
| **Focus**             | Broad market coverage                             | Penny coin optimization                         |

---

## Recommendations for Hackathon Success

### Bot 1
- **Enhance Runtime**: Extend to 24 hours (`runtime=86400`) in `main.py`.
- **Add Sharpe Ratio**: Implement in `trading_bot.py` for real-time optimization.
- **Data Alignment**: Replace Binance data with Roostoo historical data if available.

### Bot 2
- **Expand Pairs**: Add more penny coins (e.g., XRP, SAND) in `main.py`.
- **Risk Limits**: Incorporate max drawdown or dynamic sizing in `risk_manager.py`.
- **Optimize LSTM**: Reduce sequence length (e.g., 15) for faster startup.

---

## Conclusion

- **Bot 1** excels in multi-strategy adaptability and robust risk management, making it ideal for diverse market conditions and the hackathon’s Sharpe Ratio focus with minor tweaks.
- **Bot 2** offers a penny coin-optimized hybrid approach with real-time Sharpe tracking, suitable for volatile low-value assets but needs broader risk controls.

Both bots leverage smart logic and align with the hackathon’s goals, with **Bot 1** slightly edging out due to its comprehensive design, assuming runtime and Sharpe enhancements are applied.

This documentation provides a full explanation of both bots, ready for use in development, evaluation, or presentation contexts. Save it as `Documentation.md` in a shared directory or alongside each bot’s folder.
