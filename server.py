from mcp.server.fastmcp import FastMCP
from tools.asset_tool import register_asset_tools
# from tools.neutroncabang_tool import register_neutron_tools
from tools.customer_tool import register_customer_tools
from tools.salesperformance_tool import register_sales_performance_tools
from tools.ruleperformance_tool import register_rule_performance_tools
from tools.file_tools import register_file_tools
from tools.websearch_tool import register_web_search_tools
from tools.database_tool import register_database_tools

mcp = FastMCP(
    "Multi Data MCP Server"
)

register_asset_tools(mcp)
register_customer_tools(mcp)
# register_neutron_tools(mcp)
register_sales_performance_tools(mcp)
register_rule_performance_tools(mcp)
register_file_tools(mcp)
register_web_search_tools(mcp)
register_database_tools(mcp)

if __name__ == "__main__":
    mcp.run()