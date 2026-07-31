import json
from playwright.async_api import async_playwright

BASE_URL = (
    "https://coinmarketcap.com/"
)

TOTAL_PAGES = 3

async def scrape_cryptocurrency():

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=False
        )

        page = await browser.new_page(
            viewport={
                "width": 1440,
                "height": 900
            }
        )

        all_data = []

        for page_number in range(
            1,
            TOTAL_PAGES + 1
        ):

            url = (
                f"{BASE_URL}"
                f"?page={page_number}"
            )

            await page.goto(
                url,
                wait_until="domcontentloaded"
            )

            try:

                await page.wait_for_selector(
                    "tbody tr",
                    timeout=15000
                )

            except Exception:

                continue

            # rows = page.locator(
            #     "tbody tr"
            # )

            rows = page.locator("tbody tr")

            count = await rows.count()


            for i in range(count):

                row = rows.nth(i)

                cells = row.locator("td")

                # full_name = cells.nth(2)

                # name_element = full_name.locator(
                #     "p.coin-item-name"
                # )

                # name = await name_element.first.inner_text()

                # name = name.strip()

                # cells = row.locator("td")

                name = await cells.nth(2).inner_text()
                price = await cells.nth(3).inner_text()
                # change_1h = await cells.nth(4).inner_text()
                # change_24h = await cells.nth(5).inner_text()
                # change_7d = await cells.nth(6).inner_text()
                # market_cap = await cells.nth(7).inner_text()
                # volume_24h = await cells.nth(8).inner_text()

                data = {
                    # "page": page_number,
                    "name": name,
                    "price": price,
                    # "change_1h": change_1h,
                    # "change_24h": change_24h,
                    # "change_7d": change_7d,
                    # "market_cap": market_cap,
                    # "volume_24h": volume_24h
                }

                all_data.append(data)

        with open(
            "coinmarketcap_data.json",
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                all_data,
                f,
                ensure_ascii=False,
                indent=4
            )

        await browser.close()

        return all_data