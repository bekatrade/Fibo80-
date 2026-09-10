import os
import time
import threading
import requests
from flask import Flask
from datetime import datetime

# ==================== SOZLAMALAR ====================
BOT_TOKEN = "8599420009:AAG3mwpv8COm1BL0RjguYPScBHjLY-hMYKA"
CHAT_ID = "8426582765"
SYMBOL = "PAXGUSDT"  # Real Oltin (1 PAXG = 1 XAU Oltin)

# Binance timeframelari
TIMEFRAMES = {
    "M5": "5m",
    "M15": "15m",
    "M30": "30m"
}

last_processed = {
    "M5": None,
    "M15": None,
    "M30": None
}

# ==================== FLASK SERVER (Render Web Service) ====================
app = Flask(__name__)

@app.route("/")
def home():
    return "XAU/USD Oltin Signal Boti 24/7 aktiv!", 200

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
        print(f"[Telegram Xatosi]: {e}")

def get_current_price():
    """Joriy Oltin narxini Binance'dan olish (Token talab qilmaydi)"""
    url = f"https://api.binance.com/api/v3/ticker/price?symbol={SYMBOL}"
    try:
        res = requests.get(url, timeout=5).json()
        if "price" in res:
            return float(res["price"])
    except Exception as e:
        print(f"[Narx xatosi]: {e}")
    return None

def check_timeframe(tf_name, tf_interval):
    """M5, M15, M30 shamlarni tekshirish"""
    url = f"https://api.binance.com/api/v3/klines?symbol={SYMBOL}&interval={tf_interval}&limit=4"
    try:
        res = requests.get(url, timeout=5).json()
        if not isinstance(res, list) or len(res) < 3:
            return

        # Binance shamlari tuzilishi:
        # [0: Open_time, 1: Open, 2: High, 3: Low, 4: Close, ...]
        # res[-1] -> ayni damda shakllanayotgan (ochiq) sham
        # res[-2] -> yangi yopilgan 2-sham
        # res[-3] -> 1-sham (oldingi sham)

        p_bar = res[-3]
        c_bar = res[-2]

        c_time = c_bar[0]

        # Agar bu sham avval tekshirilgan bo'lsa, o'tkazib yuboramiz
        if last_processed[tf_name] == c_time:
            return

        h1, l1 = float(p_bar[2]), float(p_bar[3])
        h2, l2 = float(c_bar[2]), float(c_bar[3])
        c2 = float(c_bar[4])

        # Shart 1: 2-sham 1-shamning yuqorisini ham, pastini ham yangilagan (Sweep)
        swept_both = (h2 > h1) and (l2 < l1)

        if swept_both:
            time_str = datetime.fromtimestamp(c_time / 1000).strftime('%H:%M')

            # Shart 2: Pastga tana bilan yopilsa (SELL)
            if c2 < l1:
                msg = (
                    f"🔴 <b>SELL SIGNAL | XAU/USD (GOLD)</b>\n"
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
                    f"🟢 <b>BUY SIGNAL | XAU/USD (GOLD)</b>\n"
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
        print(f"[{tf_name}] Xatolik: {e}")

def monitor_loop():
    time.sleep(2)
    cur_price = get_current_price()
    price_str = f"{cur_price:.2f}" if cur_price else "Aniqlanmadi"

    start_msg = (
        f"🤖 <b>Web Servis muvaffaqiyatli ishga tushdi!</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📊 <b>Aktiv:</b> XAU/USD (GOLD)\n"
        f"💵 <b>Hozirgi narx:</b> <code>{price_str}</code>\n"
        f"⏱ <b>Kuzatilmoqda:</b> M5, M15, M30\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"✅ Tizim 100% aktiv. Hech qanday limit yo'q!"
    )
    send_telegram(start_msg)

    while True:
        for tf_name, tf_interval in TIMEFRAMES.items():
            check_timeframe(tf_name, tf_interval)
            time.sleep(0.5)
        time.sleep(3)  # Har 3 soniyada tekshiradi (Binance bunga bemalol ruxsat beradi)

threading.Thread(target=monitor_loop, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
