# from services_mcp.salesperformance_service import get_sales_performance
# from services_mcp.knowledge_service import get_sales_knowledge

# def register_sales_performance_tools(mcp):

#     @mcp.tool()
#     async def get_sales_performance_tool():
#         """
#         Mengambil data sales performance.

#         Returns:
#             List data sales performance.
#         """

#         sales_data = await get_sales_performance()
#         # sales_knowledge = get_sales_knowledge

#         return sales_data
    
import io
import contextlib
import pandas as pd
from services_mcp.salesperformance_service import get_sales_performance_df

_SALES_DF: pd.DataFrame = None

async def _get_cached_sales_df() -> pd.DataFrame:
    global _SALES_DF
    if _SALES_DF is None or _SALES_DF.empty:
        _SALES_DF = await get_sales_performance_df()
    return _SALES_DF

def register_sales_performance_tools(mcp):

    @mcp.tool()
    async def execute_sales_python_analysis(code: str) -> str:
        """
        Gunakan tool ini untuk menganalisis data Sales Performance dari API.
        Mengeksekusi kode Python pada variabel `df` (Pandas DataFrame sales).

        Args:
            code: Kode Python yang akan dieksekusi. WAJIB menggunakan print(...) untuk melihat output!
                  Contoh: print(df[df['region'].str.lower() == 'bandung'])
        """
        try:
            df = await _get_cached_sales_df()
            if df.empty:
                return "Data sales performance dari API kosong."

            local_vars = {"df": df, "pd": pd}
            output_buffer = io.StringIO()

            with contextlib.redirect_stdout(output_buffer):
                exec(code, {}, local_vars)

            result = output_buffer.getvalue()
            return result if result.strip() else "Kode berhasil dieksekusi tanpa output print."

        except Exception as e:
            return f"Error executing Python code: {str(e)}"