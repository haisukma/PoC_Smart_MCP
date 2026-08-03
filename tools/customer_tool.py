from services_mcp.customer_service import get_customer


def register_customer_tools(mcp):

    @mcp.tool()
    async def get_customer_tool():
        """
        Mengambil data customer.

        Returns:
            List data customer.
        """

        customers = await get_customer()

        return customers