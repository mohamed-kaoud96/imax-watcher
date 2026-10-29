"""Check whether a movie has an IMAX showing at a Premiere Cinemas branch.

Opens the movie page in a headless browser and clicks through it like a
person would: cinema -> each date -> each format, looking for an "IMAX"
button under "Choose Experience". Sends a push notification via ntfy.sh
when one is found.

Env:
  MOVIE_URL    movie page (default: Dune: Part Three)
  CINEMA       cinema button text (default: Premiere Plaza = Americana Plaza)
  EXPERIENCE   experience to look for (default: IMAX)
  NTFY_TOPIC   ntfy.sh topic to notify; if unset, only prints
"""

import os
import sys
import urllib.request

from playwright.sync_api import TimeoutError as PWTimeout
from playwright.sync_api import sync_playwright

MOVIE_URL = os.getenv("MOVIE_URL", "https://www.premiere-cinemas.com/en/movie-details/2790.503/1")
CINEMA = os.getenv("CINEMA", "Premiere Plaza")
EXPERIENCE = os.getenv("EXPERIENCE", "IMAX")
NTFY_TOPIC = os.getenv("NTFY_TOPIC", "")

# Buttons that are never a format or an experience.
NON_FORMAT_BUTTONS = {"Read More", ""}


def notify(title, message):
    print(f"NOTIFY: {title} - {message}")
    if not NTFY_TOPIC:
        return
    req = urllib.request.Request(
        f"https://ntfy.sh/{NTFY_TOPIC}",
        data=message.encode(),
        headers={"Title": title, "Priority": "urgent", "Tags": "movie_camera", "Click": MOVIE_URL},
    )
    urllib.request.urlopen(req, timeout=20)


def button_texts(page):
    return [t.strip() for t in page.locator("button").all_inner_texts()]


def settle(page):
    try:
        page.wait_for_load_state("networkidle", timeout=8000)
    except PWTimeout:
        pass
    page.wait_for_timeout(800)


def find_showing(page):
    """Return a list of 'date / format' strings that offer EXPERIENCE at CINEMA."""
    page.goto(MOVIE_URL, wait_until="domcontentloaded", timeout=60000)
    page.get_by_text("CHOOSE YOUR CINEMA", exact=False).first.wait_for(timeout=30000)
    settle(page)

    # The cinema buttons can render a moment after the heading.
    try:
        page.get_by_role("button", name=CINEMA, exact=True).wait_for(timeout=10000)
    except PWTimeout:
        print(f"{CINEMA} is not scheduled yet. Cinemas listed: {button_texts(page)}")
        return []

    cinemas = set(button_texts(page)) - NON_FORMAT_BUTTONS
    page.get_by_role("button", name=CINEMA, exact=True).click()
    settle(page)

    hits = []
    dates = page.locator(".dates-container")
    print(f"{CINEMA}: {dates.count()} date(s)")
    for i in range(dates.count()):
        date = dates.nth(i)
        label = " ".join(date.inner_text().split())
        date.click()
        settle(page)
        try:
            page.get_by_text("Choose Formats").wait_for(timeout=10000)
        except PWTimeout:
            print(f"  {label}: no formats offered")
            continue
        settle(page)

        formats = [t for t in button_texts(page) if t not in cinemas | NON_FORMAT_BUTTONS | {EXPERIENCE}]
        found = []
        for fmt in formats:
            # A format button toggles, and may still be selected from the
            # previous date, so give it a second click before giving up.
            for _ in range(2):
                page.get_by_role("button", name=fmt, exact=True).first.click()
                settle(page)
                if EXPERIENCE in button_texts(page):
                    found.append(f"{label} / {fmt}")
                    break
        print(f"  {label}: formats={formats} -> {found or 'no ' + EXPERIENCE}")
        hits += found
    return hits


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900}, locale="en-US")
        try:
            hits = find_showing(page)
        except PWTimeout:
            print(f"Page did not load as expected. URL: {page.url}  Title: {page.title()!r}")
            print("Page text:", " ".join(page.inner_text("body").split())[:800])
            page.screenshot(path="failure.png", full_page=True)
            raise
        finally:
            browser.close()

    if hits:
        notify(f"{EXPERIENCE} tickets are up at {CINEMA}!", "Showings: " + "; ".join(hits))
        out = os.getenv("GITHUB_OUTPUT")
        if out:
            with open(out, "a") as f:
                f.write("found=true\n")
    else:
        print(f"No {EXPERIENCE} at {CINEMA} yet.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
