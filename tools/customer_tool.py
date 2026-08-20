import io
import contextlib
import pandas as pd
from services_mcp.customer_service import get_customer_df

_CUSTOMER_DF: pd.DataFrame = None

async def _get_cached_customer_df() -> pd.DataFrame:
    global _CUSTOMER_DF
    if _CUSTOMER_DF is None or _CUSTOMER_DF.empty:
        _CUSTOMER_DF = await get_customer_df()
    return _CUSTOMER_DF

def register_customer_tools(mcp):

    @mcp.tool()
    async def execute_customer_analysis(code: str) -> str:
        """
        Gunakan tool ini untuk menganalisis data Customer dari API.
        Mengeksekusi kode Python pada variabel `df` (Pandas DataFrame customer).

        Args:
            code: kode Python yang akan dieksekusi. Wajib menggunakan print(...) untuk melihat output!
                Contoh: print(df[df['region].str.lower() == 'semarang'])
        """

        try:
            df = await _get_cached_customer_df()
            if df.empty:
                return "Data customer dari API kosong."

            local_vars_customer = {"df": df, "pd": pd}
            output_buffer_customer = io.StringIO()

            with contextlib.redirect_stdout(output_buffer_customer):
                exec(code, {}, local_vars_customer)

            result_customer = output_buffer_customer.getvalue()
            return result_customer if result_customer.strip() else "Kode berhasil diekseskusi tanpa output print"

        except Exception as e:
            return f"Error executing Python code: {str(e)}"