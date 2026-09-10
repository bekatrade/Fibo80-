import os
import time
import threading
import requests
from flask import Flask
from datetime import datetime

# ==================== SOZLAMALAR ====================
BOT_TOKEN = "8599420009:AAG3mwpv8COm1BL0RjguYPScBHjLY-hMYKA"
CHAT_ID = "8426582765"
API_KEY = "dah628pr01qomffmt32gdah628pr01qomffmt330"
SYMBOL = "OANDA:XAU_USD"

TIMEFRAMES = {
    "M5": "5",
    "M15": "15",
    "M30": "30"
}

last_processed = {
    "M5": None,
    "M15": None,
    "M30": None
}

# ==================== FLASK SERVER (Render uchun) ====================
app = Flask(__name__)

@app.route("/")
def home():
    return "XAU/USD Finnhub Signal Bot ishlamoqda!", 200

# ==================== TELEGRAM VA BOZOR FUNKSIYALARI ====================
def send_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"[Xatolik] Telegramga yuborib bo'lmadi: {e}")

def get_current_price():
    url = f"https://finnhub.io/api/v1/quote?symbol={SYMBOL}&token={API_KEY}"
    try:
        res = requests.get(url, timeout=10).json()
        if "c" in res and res["c"] != 0:
            return float(res["c"])
    except Exception as e:
        print(f"[Xatolik] Narx olinmadi: {e}")
    return None

def check_timeframe(tf_name, tf_resolution):
    now_ts = int(time.time())
    from_ts = now_ts - (86400 * 2)

    url = f"https://finnhub.io/api/v1/forex/candle?symbol={SYMBOL}&resolution={tf_resolution}&from={from_ts}&to={now_ts}&token={API_KEY}"
    try:
        res = requests.get(url, timeout=10).json()
        if res.get("s") != "ok" or len(res.get("t", [])) < 3:
            return

        # -1: Hozir ochiq turgan sham
        # -2: Yangi yopilgan 2-sham
        # -3: Undan oldingi 1-sham
        c_time = res["t"][-2]
        if last_processed[tf_name] == c_time:
            return

        h1, l1 = float(res["h"][-3]), float(res["l"][-3])
        h2, l2 = float(res["h"][-2]), float(res["l"][-2])
        c2 = float(res["c"][-2])

        # Shart 1: 2-sham 1-shamning yuqorisini ham, pastini ham yangilagan (Sweep)
        swept_both = (h2 > h1) and (l2 < l1)

        if swept_both:
            time_str = datetime.fromtimestamp(c_time).strftime('%H:%M')

            # Shart 2: Pastga tana bilan yopilsa (SELL)
            if c2 < l1:
                msg = (
                    f"🔴 <b>SELL SIGNAL | XAU/USD</b>\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"⏱ <b>Timeframe:</b> {tf_name}\n"
                    f"🕒 <b>Sham yopilgan vaqt:</b> {time_str}\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"📌 <b>1-sham:</b> High: <code>{h1:.2f}</code> | Low: <code>{l1:.2f}</code>\n"
                    f"📌 <b>2-sham:</b> High: <code>{h2:.2f}</code> | Low: <code>{l2:.2f}</code>\n"
                    f"🎯 <b>Close:</b> <code>{c2:.2f}</code>\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"⚡️ <i>Ikkala tomondan likvidlik olindi va pastga tana bilan yopildi!</i>"
                )
                send_telegram(msg)
                last_processed[tf_name] = c_time
                print(f"[{tf_name}] SELL signali jo'natildi!")

            # Shart 3: Tepaga tana bilan yopilsa (BUY)
            elif c2 > h1:
                msg = (
                    f"🟢 <b>BUY SIGNAL | XAU/USD</b>\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"⏱ <b>Timeframe:</b> {tf_name}\n"
                    f"🕒 <b>Sham yopilgan vaqt:</b> {time_str}\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"📌 <b>1-sham:</b> High: <code>{h1:.2f}</code> | Low: <code>{l1:.2f}</code>\n"
                    f"📌 <b>2-sham:</b> High: <code>{h2:.2f}</code> | Low: <code>{l2:.2f}</code>\n"
                    f"🎯 <b>Close:</b> <code>{c2:.2f}</code>\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"⚡️ <i>Ikkala tomondan likvidlik olindi va tepaga tana bilan yopildi!</i>"
                )
                send_telegram(msg)
                last_processed[tf_name] = c_time
                print(f"[{tf_name}] BUY signali jo'natildi!")

    except Exception as e:
        print(f"[{tf_name}] Tahlilda xatolik: {e}")

def monitor_loop():
    time.sleep(3)
    cur_price = get_current_price()
    price_str = f"{cur_price:.2f}" if cur_price else "Aniqlanmadi"

    start_msg = (
        f"🤖 <b>Web Servis ishga tushdi! (Finnhub API)</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📊 <b>Aktiv:</b> XAU/USD (GOLD)\n"
        f"💵 <b>Hozirgi narx:</b> <code>{price_str}</code>\n"
        f"⏱ <b>Kuzatilmoqda:</b> M5, M15, M30\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"✅ Tizim faol. Shart bajarilishi bilan darhol signal yuboriladi."
    )
    send_telegram(start_msg)

    while True:
        for tf_name, tf_res in TIMEFRAMES.items():
            check_timeframe(tf_name, tf_res)
            time.sleep(1)
        time.sleep(5)

# Monitoringni alohida tahrir oqimida fonda yurgizish
threading.Thread(target=monitor_loop, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
