from mcp.server.fastmcp import FastMCP
# from tools.nsjbt_tool import register_nsjbt_tools
from tools.asset_tool import register_asset_tools
from tools.neutroncabang_tool import register_neutron_tools
from tools.customer_tool import register_customer_tools
from tools.salesperformance_tool import register_sales_performance_tools

mcp = FastMCP(
    "Multi Data MCP Server"
)

# register_nsjbt_tools(mcp)
register_asset_tools(mcp)
register_neutron_tools(mcp)
register_customer_tools(mcp)
register_sales_performance_tools()

if __name__ == "__main__":
    mcp.run()