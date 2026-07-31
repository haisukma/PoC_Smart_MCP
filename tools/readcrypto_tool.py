from services_mcp.readcrypto_service import (
    get_cryptocurrency_data
)

def register_crypto_tools(mcp):

    @mcp.tool()
    async def get_cryptocurrency():

        """
        Mengambil data cryptocurrency
        dari coinmarketcap_data.json yang telah
        disimpan sebelumnya.

        Data yang tersedia:
        - name
        - price

        Gunakan tool ini untuk menjawab
        pertanyaan terkait daftar cryptocurrency
        dan harga cryptocurrency.
        """

        result = await get_cryptocurrency_data()

        return result