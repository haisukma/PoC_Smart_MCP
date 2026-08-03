from services_mcp.asset_service import get_asset

def register_asset_tools(mcp):

    @mcp.tool()
    async def get_asset_tool():
        """
        Mengambil data asset.

        Returns:
            List data asset.
        """

        assets = await get_asset()

        return assets