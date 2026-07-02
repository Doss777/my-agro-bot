import os
import time
import requests
from bs4 import BeautifulSoup
from telegram import Bot

BOT_TOKEN = os.getenv("8787982429:AAGpfzIibK7e58YtvAl6g5m1EG2sZtEdFYA")
CHAT_ID = os.getenv("6318865778")

BASE_URL = "https://agropraktika.ru"
URL = f"{BASE_URL}/vacancies"

bot = Bot("8787982429:AAGpfzIibK7e58YtvAl6g5m1EG2sZtEdFYA")

seen = set()
was_closed = {}

CHECK_INTERVAL = 90
BLOCKED_SLEEP = 160

BLOCK_TEXT = "Регистрация временно приостановлена"


def send(msg):
    bot.send_message(chat_id=CHAT_ID, text=msg)


def get_html(url):
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)

    if r.status_code == 403:
        raise PermissionError("403")

    return r.text


def parse_list(html):
    soup = BeautifulSoup(html, "html.parser")

    results = []

    for a in soup.select("a[href]"):
        href = a.get("href")
        title = a.get_text(strip=True)

        if not href or not title:
            continue

        if "/vac" not in href:
            continue

        if href.startswith("/"):
            href = BASE_URL + href

        results.append((title, href))

    return results


def is_closed(url):
    html = get_html(url)
    return BLOCK_TEXT in html


def run():
    send("🤖 Бот запущен")

    while True:
        try:
            html = get_html(URL)
            vacancies = parse_list(html)

            for title, link in vacancies:

                if link not in seen:
                    seen.add(link)
                    send(f"📢 Новая вакансия:\n{title}\n{link}")

                try:
                    closed = is_closed(link)
                except:
                    continue

                prev = was_closed.get(link, True)

                if prev and not closed:
                    send(f"🔥 ВАКАНСИЯ ОТКРЫЛАСЬ:\n{title}\n{link}")

                was_closed[link] = closed

            time.sleep(CHECK_INTERVAL)

        except PermissionError:
            send("⚠️ 403 блокировка — пауза 160 сек")
            time.sleep(BLOCKED_SLEEP)

        except Exception as e:
            print("Error:", e)
            time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    run()