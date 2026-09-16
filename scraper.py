"""Ekantipur scraper using Playwright's sync API."""

import json

from playwright.sync_api import ElementHandle, Page, sync_playwright

OUTPUT_FILE = "output.json"
ENTERTAINMENT_URL = "https://ekantipur.com/entertainment"
ARTICLE_CARD_SELECTOR = "div.category-wrapper div.category"
CARTOON_URL = "https://ekantipur.com/cartoon"


def extract_cartoon_of_the_day(page: Page) -> dict:
    """Navigate to the cartoon page and extract the cartoon of the day.

    Each field falls back to None instead of crashing.
    """
    page.goto(CARTOON_URL, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_selector("div.cartoon-wrapper", timeout=30000)

    wrapper = page.query_selector("div.cartoon-wrapper")

    def text_of(selector: str) -> str | None:
        el = wrapper.query_selector(selector) if wrapper else None
        if el is None:
            return None
        try:
            text = el.text_content()
            return text.strip() if text else None
        except Exception:
            return None

    image_url = None
    if wrapper is not None:
        img = wrapper.query_selector("div.cartoon-image figure img")
        if img is not None:
            try:
                # prefer data-src in case the image is still lazy-loading
                image_url = img.get_attribute("data-src") or img.get_attribute("src")
            except Exception:
                image_url = None

    return {
        "title": text_of("div.cartoon-description p"),
        "image_url": image_url,
        "published_date": text_of("div.cartoon-description div.date p"),
    }


def extract_article_card(article: ElementHandle) -> dict:
    """Extract data from a single entertainment article card element.

    Each field falls back to None if the selector is missing or
    extraction fails, instead of raising an exception.
    """

    def get_text(selector: str) -> str | None:
        el = article.query_selector(selector)
        if el is None:
            return None
        try:
            text = el.text_content()
            return text.strip() if text else None
        except Exception:
            return None

    def get_attr(selector: str, attribute: str) -> str | None:
        el = article.query_selector(selector)
        if el is None:
            return None
        try:
            return el.get_attribute(attribute)
        except Exception:
            return None

    img = article.query_selector("div.category-image img")
    image_url = None
    if img is not None:
        try:
            # lazy-loaded images only have the real URL in data-src, so try it first
            image_url = img.get_attribute("data-src") or img.get_attribute("src")
        except Exception:
            image_url = None

    return {
        "title": get_text("div.category-description h2 a"),
        "image_url": image_url,
        "author_name": get_text("div.author-name p"),
        # direct-child selector so we skip the <p> inside div.author-name
        "description": get_text("div.category-description > p"),
        "published_date": get_text("div.date-wrapper p"),
        "time": get_text("div.category-description div.time-wrapper span"),
    }


def extract_entertainment_news(page: Page) -> list[dict]:
    """Navigate to the entertainment section and extract the top 5 article cards."""
    page.goto(ENTERTAINMENT_URL, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_selector(ARTICLE_CARD_SELECTOR, timeout=30000)

    cards = page.query_selector_all(ARTICLE_CARD_SELECTOR)[:5]

    articles = []
    for card in cards:
        article = extract_article_card(card)
        articles.append(article)
        # print(json.dumps(article, ensure_ascii=False, indent=2))

    return articles


def main() -> None:
    """Launch Chromium, scrape both sections, and dump results to output.json."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        output = {
            "entertainment_news": extract_entertainment_news(page),
            "cartoon_of_the_day": extract_cartoon_of_the_day(page),
        }

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        browser.close()


if __name__ == "__main__":
    main()
