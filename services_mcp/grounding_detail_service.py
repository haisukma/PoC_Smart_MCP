import asyncio
import httpx
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("JARVIS_API_URL")
API_TOKEN = os.getenv("JARVIS_API_TOKEN")

async def get_grounding_detail_df() -> pd.DataFrame:
    """
    Mengambil seluruh data DETAIL GROUNDING dari API
    """

    url = f"{API_URL}/grounding"
    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Accept": "application/json"}

    per_page = 10000
    max_concurrent = 5
    all_records = []
    next_page = True
    page = 1

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(60),
        limits=httpx.Limits(
            max_connections=max_concurrent,
            max_keepalive_connections=max_concurrent
        )
    ) as client:

        async def fetch_page(page_number, semaphore):
            async with semaphore:
                response = await client.get(
                    url,
                    headers=headers,
                    params={
                        "page": page_number,
                        "per_page": per_page})

                response.raise_for_status()
                result = response.json()

                return page_number, result

        semaphore = asyncio.Semaphore(max_concurrent)
        while next_page:
            pages = range(
                page,
                page + max_concurrent)

            results = await asyncio.gather(
                *[
                    fetch_page(p, semaphore)
                    for p in pages])

            next_page = False
            for page_number, result in results:
                records = result.get("data", [])
                all_records.extend(records)
                pagination = result.get("pagination", {})
                if pagination.get("next_page", False):
                    next_page = True

            page += max_concurrent

    if not all_records:
        return pd.DataFrame()

    return pd.DataFrame(all_records)
