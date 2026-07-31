from services_mcp.salesperformance_service import get_sales_performance

def register_sales_performance_tools(mcp):

    @mcp.tool()
    async def get_sales_performance_tool(limit: int = 20):
        """
        Mengambil data sales performance.

        Args:
            limit: Jumlah maksimal data sales performance yang dikembalikan.

        Returns:
            List data sales performance.
        """

        sales_performance = await get_sales_performance()

        return sales_performance[:limit]