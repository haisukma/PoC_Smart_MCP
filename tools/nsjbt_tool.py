from services_mcp.nsjbt_service import (
    get_master2_rows, summarize_master2_rows
)

def register_nsjbt_tools(mcp):

    @mcp.tool()
    async def get_master2_rows_tool(limit: int = 20):
        """
        Mengambil data row atau tegakan dari sistem NSJBT.

        Args:
            limit: Jumlah maksimal data yang dikembalikan.

        Returns:
            Data master2 dari API NSJBT.
        """

        data = await get_master2_rows()

        return data[:limit]

    @mcp.tool()
    async def summarize_master2_rows_tool():
        """
        Membuat ringkasan atau kesimpulan statistik data row atau tegakan
        dari sistem NSJBT.

        Returns:
            Ringkasan jumlah lokasi, jumlah row,
            jenis tegakan, pemilik, status,
            dan status data.
        """

        result = await summarize_master2_rows()

        return result
