# main.py
from trading_bot import RoostooMLTradingBot

API_KEY = "576SV7yQteZR8I9iw4tMMc4htqXFGI61TcPDYRz5b9YTOB3pu1viYROKoEYzk4hy"
SECRET_KEY = "XNjEBJ8Z8i5fXJVSECfMfLefgLchwWjKQK3bzXVfrjy17JbuLmVheuGUilHeoOvq"

def main():
    bot = RoostooMLTradingBot(API_KEY, SECRET_KEY)
    bot.run_strategy(runtime=3600)  # Default 1-hour runtime, adjust to 86400 for 24 hours

if __name__ == "__main__":
    main()