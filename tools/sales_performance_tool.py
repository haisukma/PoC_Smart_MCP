import io
from services_mcp.sales_rag_service import query_sales_rag

def get_sales_performance_metadata() -> dict:
    """
    Metadata tool tetap dipertahankan untuk kebutuhan Router RAG tingkat atas di main.py
    """
    return {
        "tool_name": "search_sales_performance_data",
        "description": (
            "Gunakan tool ini untuk MENCARI dan MENYARING baris data Sales Performance dari database raksasa. "
            "Sangat cocok untuk melihat kinerja, target, daerah wilayah, pencapaian, dan nama sales tertentu."
        ),
        "columns": ["sales_name", "region", "total_target", "total_achievement", "period"]
    }

def register_sales_vector_tools(mcp):

    @mcp.tool()
    async def search_sales_performance_data(query: str) -> str:
        """
        Gunakan tool ini untuk melakukan pencarian data performa sales secara spesifik dari database jutaan baris.
        Masukkan kata kunci pencarian yang jelas seperti nama sales atau region daerah.

        Args:
            query: Kata kunci pencarian spesifik (Contoh: 'Sales region Bandung' atau 'Pencapaian Andi').
        """
        try:
            context_data = query_sales_rag(user_query=query, k=10)
            
            return (
                "Berikut adalah potongan data sales terakurat yang berhasil disaring dari database:\n\n"
                f"{context_data}\n\n"
                "Gunakan data di atas sebagai acuan utama untuk menjawab pertanyaan user secara akurat."
            )

        except Exception as e:
            return f"Error saat melakukan pencarian RAG Data: {str(e)}"
