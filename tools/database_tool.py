from services_mcp.database_service import (
    get_database_schema,
    execute_read_query
)

def register_database_tools(mcp):

    @mcp.tool()
    def get_database_schema_tool():
        """
        Mendapatkan struktur database company_db.

        Gunakan tool ini terlebih dahulu untuk mengetahui:
        - tabel yang tersedia
        - kolom setiap tabel
        - tipe data
        - primary key

        Tool ini membantu memahami struktur database
        sebelum membuat query SQL.
        """

        return get_database_schema()

    @mcp.tool()
    def execute_read_query_tool(query: str):
        """
        Menjalankan query SQL SELECT secara read-only
        pada database company_db.

        Gunakan hanya untuk membaca data.
        Query INSERT, UPDATE, DELETE, DROP, ALTER,
        CREATE, dan operasi perubahan data lainnya
        tidak diperbolehkan.

        Args:
            query: Query SQL SELECT yang akan dijalankan.
        """

        try:

            results = execute_read_query(query)

            return {
                "success": True,
                "row_count": len(results),
                "data": results
            }

        except Exception as e:

            return {
                "success": False,
                "error": str(e)
            }