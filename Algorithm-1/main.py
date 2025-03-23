# main.py
import asyncio
from trading_bot import RoostooTradingBot

API_KEY = "4LAQ6W6OePhQcuGBE1kZE04b5KxBWs3323mKlDOniWxRToH6MUoiHiSOhjCVlPDI"
SECRET_KEY = "40JcYReJc7FocuvE2ytZwmFGdD1ArClXLl3oAFacyJvNejLxzxDQpBRZ65LYbAkK"

async def main():
    bot = RoostooTradingBot(API_KEY, SECRET_KEY, trade_pairs=["DOGE/USD"])
    await bot.run_trading_strategy()

if __name__ == "__main__":
    asyncio.run(main())