import asyncio
import json
import time
from datetime import datetime

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from playwright.async_api import async_playwright

TOKEN = "8787982429:AAGpfzIibK7e58YtvAl6g5m1EG2sZtEdFYA"
CHAT_ID = int("6318865778")

URL = "https://agropraktika.eu/vacancies"

CHECK_INTERVAL = 90
ERROR403_INTERVAL = 160

STATE_FILE = "state.json"

logs = []


def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    logs.append(line)
    if len(logs) > 50:
        logs.pop(0)


def load_state():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


state = load_state()


async def fetch_page():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        await page.goto(URL, timeout=60000)
        content = await page.content()

        await browser.close()
        return content


def parse_vacancies(html: str):
    """
    Очень простой парсер:
    если в HTML нет текста "Регистрация временно приостановлена"
    => считаем вакансию открытой
    """

    is_closed = "Регистрация временно приостановлена" in html

    return {
        "registration_closed": is_closed,
        "open": not is_closed
    }


async def check_site(app: Application):
    global state

    while True:
        try:
            log("Checking site...")

            html = await fetch_page()

            result = parse_vacancies(html)

            # если сайт "403" часто маскируется пустым/неполным HTML
            if "403" in html:
                log("403 detected → sleep 160s")
                await asyncio.sleep(ERROR403_INTERVAL)
                continue

            prev = state.get("open", None)
            current = result["open"]

            state["open"] = current
            state["last_check"] = datetime.now().isoformat()

            save_state(state)

            # если изменилось состояние → уведомляем
            if prev is not None and prev != current:
                if current:
                    msg = "🟢 Регистрация ОТКРЫЛАСЬ!\n\nhttps://agropraktika.eu/vacancies"
                    await app.bot.send_message(chat_id=CHAT_ID, text=msg)
                    log("OPEN → notified")
                else:
                    log("Closed again")

            await asyncio.sleep(CHECK_INTERVAL)

        except Exception as e:
            log(f"ERROR: {e}")
            await asyncio.sleep(CHECK_INTERVAL)


# ---------------- COMMANDS ----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Бот запущен и следит за вакансиями.")


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    open_state = state.get("open", False)
    last = state.get("last_check", "never")

    text = f"""
📊 Статус

Открыто: {"🟢 да" if open_state else "🔴 нет"}

Последняя проверка:
{last}
"""
    await update.message.reply_text(text)


async def check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Проверяю сайт...")

    html = await fetch_page()
    result = parse_vacancies(html)

    await update.message.reply_text(
        f"Open: {result['open']}\nClosed flag: {result['registration_closed']}"
    )


async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏓 alive")


async def logs_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("\n".join(logs[-20:]))


async def on_start(app: Application):
    asyncio.create_task(check_site(app))


def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("check", check))
    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(CommandHandler("logs", logs_cmd))

    app.post_init = on_start

    print("Bot started")
    app.run_polling()


if __name__ == "__main__":
    main()