from services_mcp.salesperformance_service import get_sales_performance
from services_mcp.knowledge_service import get_sales_knowledge

def register_sales_performance_tools(mcp):

    @mcp.tool()
    async def get_sales_performance_tool():
        """
        Mengambil data sales performance.

        Returns:
            List data sales performance.
        """

        sales_data = await get_sales_performance()
        # sales_knowledge = get_sales_knowledge

        return sales_data
    