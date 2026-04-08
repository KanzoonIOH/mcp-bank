import os

from fastmcp import FastMCP

from middleware.stripExtraFields import StripExtraFieldsMiddleware
from servers.hasanah_card import hasanah_card
from servers.kpr import kpr

mcp_syariah = FastMCP(name="bank-mcp", middleware=[StripExtraFieldsMiddleware()])
mcp_syariah.mount(hasanah_card)


mcp_conventional = FastMCP(
    name="bank-conventional", middleware=[StripExtraFieldsMiddleware()]
)
mcp_conventional.mount(kpr)


if __name__ == "__main__":
    mode = os.getenv("BANK_MODE")

    match mode:
        case "syariah":
            mcp_syariah.run()
        case "conventional":
            mcp_conventional.run()
        case _:
            raise ValueError(f"Unknown BANK_MODE: {mode}")
