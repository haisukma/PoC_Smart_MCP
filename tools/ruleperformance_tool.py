from pathlib import Path

def register_rule_performance_tools(mcp):

    @mcp.tool()
    async def get_sales_performance_knowledge():
        """
        Mengambil aturan & standar rumus analisis performance sales.
        Gunakan tool ini WAJIB saat melakukan evaluasi, ranking, atau persentase achievement sales.
        """
        knowledge_path = Path("knowledge_base/salesperformance-info.md")
        if not knowledge_path.exists():
            return "Aturan knowledge base tidak ditemukan."
            
        return knowledge_path.read_text(encoding="utf-8")