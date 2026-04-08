from fastmcp.server.middleware import Middleware, MiddlewareContext


class StripExtraFieldsMiddleware(Middleware):
    """
    Strips extra fields injected by n8n's AI Agent node (sessionId, action,
    chatInput, toolCallId) before FastMCP validates the tool arguments.
    """

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        tool_name = context.message.name
        arguments = context.message.arguments or {}

        # Fetch the tool definition to get its declared parameter names
        tool = await context.fastmcp_context.fastmcp.get_tool(tool_name)
        if tool is not None:
            known_params = set(tool.parameters.get("properties", {}).keys())
            context.message.arguments = {
                k: v for k, v in arguments.items() if k in known_params
            }

        return await call_next(context)
