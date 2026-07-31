import os
import httpx
from dotenv import load_dotenv

load_dotenv()

API_BASE_URL = os.getenv("API_BASE_URL")


async def get_asset():
    """
    Mengambil data asset dari API.
    """

    url = f"{API_BASE_URL}/asset"

    async with httpx.AsyncClient() as client:

        response = await client.get(
            url,
            timeout=30
        )

        response.raise_for_status()

        result = response.json()

        return result.get("data", [])