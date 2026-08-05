from services_mcp.asset_service import get_asset

def register_asset_tools(mcp):

    @mcp.tool()
    async def get_asset_tool():
        """
        Mengambil seluruh data daftar aset beserta detailnya.

        Gunakan tool ini ketika pengguna bertanya tentang:
        - Jumlah atau daftar aset.
        - Detail informasi aset

        Returns:
            List data asset berisi detail informasi aset.
        """

        assets = await get_asset()

        return assets