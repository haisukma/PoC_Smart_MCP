import os
import httpx
from dotenv import load_dotenv

load_dotenv()

TAVILY_API_URL = "https://api.tavily.com/search"

async def search_web(
    query: str,
    max_results: int = 5,
) -> list[dict]:
    """
    Mencari informasi dari internet menggunakan Tavily.

    Args:
        query: Query pencarian.
        max_results: Jumlah maksimal hasil.

    Returns:
        List hasil pencarian.
    """

    api_key = os.getenv("TAVILY_API_KEY")

    if not api_key:
        raise RuntimeError("TAVILY_API_KEY belum dikonfigurasi.")

    payload = {
        "api_key": api_key,
        "query": query,
        "search_depth": "basic",
        "max_results": max_results,
        "include_answer": False,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            TAVILY_API_URL,
            json=payload,
        )

        response.raise_for_status()

    data = response.json()

    return data.get("results", [])