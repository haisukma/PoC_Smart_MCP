from pathlib import Path

def register_rule_performance_tools(mcp):

    @mcp.tool()
    async def get_sales_performance_knowledge():
        """
        Mengambil aturan analisis performance sales.

        Gunakan tool ini ketika user meminta:
        - analisis performance
        - evaluasi sales
        - ranking sales
        - achievement sales
        """

        return Path(
            "knowledge_base/sales-performance.md"
        ).read_text(encoding="utf-8")