import time
import requests
from datetime import datetime

# ==================== SOZLAMALAR ====================
BOT_TOKEN = "8599420009:AAG3mwpv8COm1BL0RjguYPScBHjLY-hMYKA"
CHAT_ID = "8426582765"
API_KEY = "981d9430d057487ba2f3bfac82610df7"
SYMBOL = "XAU/USD"

# Kuzatiladigan timeframelar (TwelveData formatida)
TIMEFRAMES = {
    "M5": "5min",
    "M15": "15min",
    "M30": "30min"
}

# Har bir timeframe bo'yicha oxirgi ko'rilgan sham vaqti (qayta signal bermaslik uchun)
last_processed = {
    "M5": None,
    "M15": None,
    "M30": None
}

def send_telegram(text):
    """Telegram botga xabar yuborish funksiyasi"""
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
    """Joriy oltin narxini olish"""
    url = f"https://api.twelvedata.com/price?symbol={SYMBOL}&apikey={API_KEY}"
    try:
        res = requests.get(url, timeout=10).json()
        if "price" in res:
            return float(res["price"])
    except Exception as e:
        print(f"[Xatolik] Narxni olib bo'lmadi: {e}")
    return None

def check_timeframe(tf_name, tf_interval):
    """Berilgan timeframe bo'yicha shamlarni tekshirish"""
    url = f"https://api.twelvedata.com/time_series?symbol={SYMBOL}&interval={tf_interval}&outputsize=4&apikey={API_KEY}"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()

        if "values" not in data or len(data["values"]) < 3:
            return

        # TwelveData tartibi:
        # data["values"][0] -> hozir shakllanayotgan (ochiq) sham
        # data["values"][1] -> yangi yopilgan 2-sham (Outside bar bo'lishi kerak bo'lgan)
        # data["values"][2] -> 1-sham (oldingi sham)
        c_bar = data["values"][1]
        p_bar = data["values"][2]

        c_time = c_bar["datetime"]

        # Agar bu sham allaqachon tekshirilgan bo'lsa, qaytaramiz
        if last_processed[tf_name] == c_time:
            return

        h1, l1 = float(p_bar["high"]), float(p_bar["low"])
        h2, l2 = float(c_bar["high"]), float(c_bar["low"])
        c2 = float(c_bar["close"])

        # Shart 1: 2-sham 1-shamning yuqorisini ham, pastini ham yangilagan (Sweep)
        swept_both = (h2 > h1) and (l2 < l1)

        if swept_both:
            # Shart 2: Pastga tana bilan buzib yopilsa (SELL)
            if c2 < l1:
                msg = (
                    f"🔴 <b>SELL SIGNAL | {SYMBOL}</b>\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"⏱ <b>Timeframe:</b> {tf_name}\n"
                    f"🕒 <b>Sham vaqti:</b> {c_time}\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"📌 <b>1-sham:</b> High: <code>{h1:.2f}</code> | Low: <code>{l1:.2f}</code>\n"
                    f"📌 <b>2-sham:</b> High: <code>{h2:.2f}</code> | Low: <code>{l2:.2f}</code>\n"
                    f"🎯 <b>Close:</b> <code>{c2:.2f}</code>\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"⚡️ <i>Ikkala tomondan likvidlik olinib, pastga tana bilan yopildi!</i>"
                )
                send_telegram(msg)
                last_processed[tf_name] = c_time
                print(f"[{tf_name}] SELL signali jo'natildi!")

            # Shart 3: Tepaga tana bilan buzib yopilsa (BUY)
            elif c2 > h1:
                msg = (
                    f"🟢 <b>BUY SIGNAL | {SYMBOL}</b>\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"⏱ <b>Timeframe:</b> {tf_name}\n"
                    f"🕒 <b>Sham vaqti:</b> {c_time}\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"📌 <b>1-sham:</b> High: <code>{h1:.2f}</code> | Low: <code>{l1:.2f}</code>\n"
                    f"📌 <b>2-sham:</b> High: <code>{h2:.2f}</code> | Low: <code>{l2:.2f}</code>\n"
                    f"🎯 <b>Close:</b> <code>{c2:.2f}</code>\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"⚡️ <i>Ikkala tomondan likvidlik olinib, tepaga tana bilan yopildi!</i>"
                )
                send_telegram(msg)
                last_processed[tf_name] = c_time
                print(f"[{tf_name}] BUY signali jo'natildi!")

    except Exception as e:
        print(f"[{tf_name}] Tahlilda xatolik: {e}")

def main():
    print("🚀 Oltin signallari boti ishga tushmoqda...")
    
    # Ishga tushganda boshlang'ich narxni olish va Telegramga xabar berish
    cur_price = get_current_price()
    price_str = f"{cur_price:.2f}" if cur_price else "Aniqlanmadi"
    
    start_msg = (
        f"🤖 <b>Bot muvaffaqiyatli ishga tushdi!</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📊 <b>Aktiv:</b> {SYMBOL}\n"
        f"💵 <b>Hozirgi narx:</b> <code>{price_str}</code>\n"
        f"⏱ <b>Kuzatilmoqda:</b> M5, M15, M30\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"✅ Strategiya bo'yicha signal bo'lsa, darhol xabar yuboriladi."
    )
    send_telegram(start_msg)

    # Doimiy monitoring sikli
    while True:
        for tf_name, tf_interval in TIMEFRAMES.items():
            check_timeframe(tf_name, tf_interval)
            time.sleep(1.2)  # TwelveData bepul API limitiga (daqiqasiga 8 ta so'rov) tushmaslik uchun
        time.sleep(10)

if __name__ == "__main__":
    main()
