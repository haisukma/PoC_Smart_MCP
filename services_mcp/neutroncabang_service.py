from playwright.async_api import async_playwright

BASE_URL = "https://neutron.co.id"
CABANG_URL = f"{BASE_URL}/cabang"

async def scrape_neutron_branches():

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True
        )

        page = await browser.new_page(
            viewport={
                "width": 1440,
                "height": 900
            }
        )

        await page.goto(
            CABANG_URL,
            wait_until="networkidle"
        )

        print(
            "Halaman Neutron berhasil dibuka"
        )

        click_count = 0

        while True:

            button = page.get_by_text(
                "Lihat Lebih Banyak",
                exact=True
            )

            if await button.count() == 0:

                print(
                    "Tombol Lihat Lebih Banyak "
                    "sudah tidak ditemukan."
                )

                break

            print(
                f"Klik Lihat Lebih Banyak "
                f"ke-{click_count + 1}"
            )

            await button.first.scroll_into_view_if_needed()

            await button.first.click()

            click_count += 1

            await page.wait_for_timeout(
                2000
            )

        names = await page.locator(
            'a[href*="/cabang/"]'
        ).evaluate_all("""
            elements => elements.map(
                a => a.innerText.trim()
            )
        """)

        unique_names = list(
            dict.fromkeys(names)
        )

        branches = [
            " ".join(name.split())
            for name in unique_names
        ]

        await browser.close()

        return {
            "total_click": click_count,
            "total_branches": len(branches),
            "data": branches
        }