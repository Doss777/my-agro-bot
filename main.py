import os
import time
import requests
from bs4 import BeautifulSoup

BOT_TOKEN = os.getenv("8787982429:AAGpfzIibK7e58YtvAl6g5m1EG2sZtEdFYA")
CHAT_ID = os.getenv("6318865778")

BASE_URL = "https://agropraktika.ru"
URL = f"{BASE_URL}/vacancies"

seen = set()
was_closed = {}

CHECK_INTERVAL = 90
BLOCKED_SLEEP = 160

BLOCK_TEXT = "Регистрация временно приостановлена"


def send(msg):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        r = requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
        print("TG:", r.status_code, r.text)
    except Exception as e:
        print("TG ERROR:", e)


def get_html(url):
    print("GET:", url)

    r = requests.get(
        url,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=20
    )

    print("STATUS:", r.status_code)

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
    print("BOT STARTED")
    send("🤖 Бот запущен (DEBUG MODE)")

    while True:
        try:
            print("STEP 1: load vacancies page")

            html = get_html(URL)

            print("STEP 2: parse")
            vacancies = parse_list(html)

            print("FOUND:", len(vacancies))

            for title, link in vacancies:

                print("VAC:", title)

                if link not in seen:
                    seen.add(link)
                    send(f"📢 Новая вакансия:\n{title}\n{link}")

                try:
                    closed = is_closed(link)
                except Exception as e:
                    print("CHECK ERROR:", e)
                    continue

                prev = was_closed.get(link, True)

                if prev and not closed:
                    send(f"🔥 ВАКАНСИЯ ОТКРЫЛАСЬ:\n{title}\n{link}")

                was_closed[link] = closed

            time.sleep(CHECK_INTERVAL)

        except PermissionError:
            print("403 BLOCKED")
            send("⚠️ 403 блокировка — жду 160 сек")
            time.sleep(BLOCKED_SLEEP)

        except Exception as e:
            print("MAIN ERROR:", e)
            send(f"❌ Ошибка:\n{e}")
            time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    run()
