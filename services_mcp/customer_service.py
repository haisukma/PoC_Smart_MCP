import os
import httpx
from dotenv import load_dotenv

load_dotenv()

API_BASE_URL = os.getenv("API_BASE_URL")


async def get_customer():
    """
    Mengambil data customer dari API.
    """

    url = f"{API_BASE_URL}/customer"

    async with httpx.AsyncClient() as client:

        response = await client.get(
            url,
            timeout=30
        )

        response.raise_for_status()

        result = response.json()

        # customers = result.get("data", [])

        # #cleaned_customers = [
        # {
        #     key: value
        #     for key, value in customer.items()
        #     if key not in ["id", "created_at"]
        # }
        # for customer in customers
        # ]

        # return cleaned_customers

        return result.get("data", [])
    
