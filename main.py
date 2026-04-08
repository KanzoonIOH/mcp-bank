from fastmcp import FastMCP

from middleware.stripExtraFields import StripExtraFieldsMiddleware
from servers.hasanah_card import hasanah_card

mcp = FastMCP(name="bank-mcp", middleware=[StripExtraFieldsMiddleware()])
mcp.mount(hasanah_card)


if __name__ == "__main__":
    mcp.run()
