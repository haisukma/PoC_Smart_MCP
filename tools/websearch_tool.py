from services_mcp.websearch_service import search_web

def register_web_search_tools(mcp):

    @mcp.tool()
    async def web_search(
        query: str,
        max_results: int = 5,
    ) -> str:
        """
        Mencari informasi dari internet.

        Gunakan tool ini HANYA jika informasi yang dibutuhkan
        berasal dari internet atau membutuhkan informasi terkini.

        Gunakan untuk:
        - informasi terbaru
        - berita
        - dokumentasi publik
        - informasi eksternal
        - fakta yang tidak tersedia pada data internal

        JANGAN gunakan untuk:
        - data Asset
        - data Customer
        - Sales Performance
        - data dari file upload
        - informasi yang sudah tersedia dari tool lain

        Gunakan jumlah pencarian seminimal mungkin.

        Args:
            query: Query pencarian yang spesifik dan ringkas.
            max_results: Jumlah hasil pencarian. Default 5.
        """

        try:
            results = await search_web(
                query=query,
                max_results=max_results,
            )

            if not results:
                return f"Tidak ditemukan hasil untuk query: {query}"

            output = []

            for i, result in enumerate(results, start=1):
                title = result.get("title", "")
                url = result.get("url", "")
                content = result.get("content", "")

                output.append(
                    f"""RESULT {i}
                    Title: {title}
                    URL: {url}
                    Content: {content}"""
                )

            return "\n\n".join(output)

        except Exception as e:
            return f"Web search error: {str(e)}"