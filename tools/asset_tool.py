from services_mcp.asset_service import get_asset

def register_asset_tools(mcp):

    @mcp.tool()
    async def get_asset_tool(limit: int = 50):
        """
        Mengambil data asset.

        Args:
            limit: Jumlah maksimal data asset yang dikembalikan.

        Returns:
            List data asset.
        """

        assets = await get_asset()

        return assets[:limit]