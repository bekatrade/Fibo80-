import os
import time
import threading
import requests
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

# --- SOZLAMALAR ---
BOT_TOKEN = "8599420009:AAG3mwpv8COm1BL0RjguYPScBHjLY-hMYKA"
CHAT_ID = "8426582765"
API_KEY = "9ffe2e86b6bd4d35ba2800101c9cfdb9"
SYMBOL = "XAU/USD"
TIMEFRAMES = ["5min", "15min"]

last_processed_candle = {
    "5min": None,
    "15min": None
}

# --- RENDER PORT XATOSINI YO'QOTUVCHI KICHIK SERVER ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive and running!")

def run_fake_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

# ----------------------------------------------------

def send_telegram(text, reply_markup=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        requests.post(url, json=payload, timeout=8)
    except Exception as e:
        print(f"Telegram yuborishda xatolik: {e}")

def send_telegram_alert(tf, direction, p_high, p_low, c_high, c_low, c_close):
    icon = "🟢 BUY" if direction == "BUY" else "🔴 SELL"
    tf_display = "M5" if tf == "5min" else "M15"
    msg = (
        f"⚡️ {icon} SIGNAL | GOLD (XAUUSD)\n"
        f"⏱ Timeframe: {tf_display}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📌 1-sham: High={p_high:.2f} | Low={p_low:.2f}\n"
        f"📌 2-sham: High={c_high:.2f} | Low={c_low:.2f}\n"
        f"🎯 Yopilish narxi: {c_close:.2f}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"✅ Ikkala tomondan likvidlik olinib, tana bilan buzib yopildi!"
    )
    send_telegram(msg)

def get_current_price_info():
    try:
        url = f"https://api.twelvedata.com/quote?symbol={SYMBOL}&apikey={API_KEY}"
        res = requests.get(url, timeout=8).json()

        if "close" not in res:
            return None

        price = round(float(res["close"]), 2)
        high = round(float(res.get("high", price)), 2)
        low = round(float(res.get("low", price)), 2)
        change = round(float(res.get("change", 0)), 2)
        pct_change = round(float(res.get("percent_change", 0)), 2)
        sign = "+" if change >= 0 else ""
        now_str = datetime.now().strftime("%H:%M:%S")

        msg = (
            f"📊 *Aktiv: XAU/USD (GOLD)*\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💵 *Hozirgi narx:* `${price}`\n"
            f"📈 *High:* `${high}`\n"
            f"📉 *Low:* `${low}`\n"
            f"📊 *O'zgarish:* `{sign}{change} ({sign}{pct_change}%)`\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"⏱ *Vaqt:* `{now_str}`\n"
            f"✅ Manba: Twelve Data"
        )
        return msg
    except Exception as e:
        print(f"Narx olishda xatolik: {e}")
        return None

def check_candles(tf):
    url = f"https://api.twelvedata.com/time_series?symbol={SYMBOL}&interval={tf}&outputsize=3&apikey={API_KEY}"
    try:
        res = requests.get(url, timeout=8).json()
        if "values" not in res or len(res["values"]) < 3:
            return

        bars = res["values"]
        c_bar = bars[1]
        p_bar = bars[2]

        curr_time = c_bar["datetime"]
        if last_processed_candle[tf] == curr_time:
            return

        p_high, p_low = float(p_bar["high"]), float(p_bar["low"])
        c_high, c_low = float(c_bar["high"]), float(c_bar["low"])
        c_close = float(c_bar["close"])

        swept_both = (c_high > p_high) and (c_low < p_low)

        if swept_both:
            if c_close < p_low:
                send_telegram_alert(tf, "SELL", p_high, p_low, c_high, c_low, c_close)
                last_processed_candle[tf] = curr_time
            elif c_close > p_high:
                send_telegram_alert(tf, "BUY", p_high, p_low, c_high, c_low, c_close)
                last_processed_candle[tf] = curr_time

    except Exception as ex:
        print(f"[{tf}] Xatolik: {ex}")

def listen_telegram_button():
    offset = None
    keyboard = {
        "keyboard": [[{"text": "💵 Narx"}]],
        "resize_keyboard": True
    }
    send_telegram("🤖 Tizim ishga tushdi! XAU/USD narxini ko'rish uchun tugmani bosing:", keyboard)

    while True:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
            params = {"timeout": 20}
            if offset:
                params["offset"] = offset

            res = requests.get(url, params=params, timeout=25).json()
            if "result" in res:
                for update in res["result"]:
                    offset = update["update_id"] + 1
                    msg = update.get("message", {})
                    text = msg.get("text", "")

                    if text in ["💵 Narx", "/narx", "/price"]:
                        info = get_current_price_info()
                        if info:
                            send_telegram(info, keyboard)
                        else:
                            send_telegram("⚠️ Narxni olib bo'lmadi, qaytadan urinib ko'ring.", keyboard)
        except Exception:
            time.sleep(2)

def main():
    print("🚀 XAU/USD signallari va monitoring boti ishga tushdi...")
    
    # 1. Render talab qilgan portni orqa fonda ochamiz (xato bermasligi uchun)
    threading.Thread(target=run_fake_server, daemon=True).start()

    # 2. Tugmalarni eshitish foni
    threading.Thread(target=listen_telegram_button, daemon=True).start()

    # 3. Bozor shamlari tahlili sikli
    while True:
        for tf in TIMEFRAMES:
            check_candles(tf)
            time.sleep(2)

        time.sleep(300)

if __name__ == "__main__":
    main()
