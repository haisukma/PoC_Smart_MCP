from services_mcp.crypto_service import (
    scrape_cryptocurrency
)

def register_crypto_tools(mcp):

    @mcp.tool()
    async def get_cryptocurrency():

        """
        Mengambil daftar cryptocurrency yang trending hari ini
        dari halaman Trending Cryptocurrencies
        CoinMarketCap.
        """

        result = await scrape_cryptocurrency()

        return result