from mcp.server.fastmcp import FastMCP
from tools.asset_tool import register_asset_tools
# from tools.neutroncabang_tool import register_neutron_tools
from tools.customer_tool import register_customer_tools
from tools.salesperformance_tool import register_sales_performance_tools
from tools.ruleperformance_tool import register_rule_performance_tools
from tools.analisis_file import register_analisis_file
from tools.generate_grafik import register_grafik_tools
from tools.websearch_tool import register_web_search_tools
from tools.get_file_schema import register_file_schema

mcp = FastMCP("Multi Data MCP Server")

register_asset_tools(mcp)
register_customer_tools(mcp)
# register_neutron_tools(mcp)
register_file_schema(mcp)
register_sales_performance_tools(mcp)
register_rule_performance_tools(mcp)
register_analisis_file(mcp)
register_web_search_tools(mcp)
register_grafik_tools(mcp)

if __name__ == "__main__":
    mcp.run()