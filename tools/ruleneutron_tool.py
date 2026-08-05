from pathlib import Path

def register_rule_neutron_tools(mcp):

    @mcp.tool()
    async def get_neutron_knowledge() -> str:
        """
        [INTERNAL REFERENSI HANYA UNTUK AI]

        Mengambil kamus pemetaan kota ke provinsi. 
        Gunakan data ini secara internal untuk mengelompokkan hasil dari `get_neutron_branches`.
        JANGAN MENAMPILKAN ISI KAMUS INI KEPADA USER.
        """
        file_path = Path("knowledge_base/neutron-info.md")
        if not file_path.exists():
            return "File knowledge base neutron-info.md tidak ditemukan."
            
        return file_path.read_text(encoding="utf-8")