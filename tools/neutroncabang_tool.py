from services_mcp.neutroncabang_service import (
    scrape_neutron_branches
)

def register_neutron_tools(mcp):

    @mcp.tool()
    async def get_neutron_branches():

        """
        Mengambil seluruh daftar cabang Neutron
        dari website neutron.co.id.
        """

        result = await scrape_neutron_branches()

        return result