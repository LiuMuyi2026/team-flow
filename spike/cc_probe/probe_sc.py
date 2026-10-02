#!/usr/bin/env python3
"""M0 S1/S3 附加探针（stdio MCP，不占端口）：
- probe_plain / probe_schema / probe_error：content 与 structuredContent 放不同标记，看模型实际能看到哪一份；
- echo_meta：回显 tools/call 的 _meta（看 Claude Code 带了哪些键，例如 claudecode/toolUseId）。
需要 fastmcp（团队 .venv 里有）。用法：{"mcpServers":{"probe":{"type":"stdio","command":"<.venv>/bin/python","args":["/abs/spike/cc_probe/probe_sc.py"]}}}
"""
from fastmcp import FastMCP
from fastmcp.tools import ToolResult

mcp = FastMCP("probe")

@mcp.tool(name="probe_plain", output_schema=None, annotations={"readOnlyHint": True})
def probe_plain() -> ToolResult:
    """返回一个探针结果（无 outputSchema）。"""
    return ToolResult(content="CONTENT-MARK-7731", structured_content={"marker": "STRUCT-MARK-4409"})

@mcp.tool(name="probe_schema", output_schema={"type": "object", "properties": {"marker": {"type": "string"}}, "required": ["marker"]},
          annotations={"readOnlyHint": True})
def probe_schema() -> ToolResult:
    """返回一个探针结果（声明了 outputSchema）。"""
    return ToolResult(content="CONTENT-MARK-6620", structured_content={"marker": "STRUCT-MARK-3318"})

@mcp.tool(name="probe_error", output_schema=None, annotations={"readOnlyHint": True})
def probe_error() -> ToolResult:
    """返回一个 isError 的探针结果。"""
    return ToolResult(content="ERRTEXT-5521", structured_content={"err": "STRUCTERR-8813"}, is_error=True)


from fastmcp import Context

@mcp.tool(name="echo_meta", output_schema=None, annotations={"readOnlyHint": True})
def echo_meta(ctx: Context) -> ToolResult:
    """回显本次 tools/call 请求的 _meta（S3 用）。"""
    rc = ctx.request_context
    meta = getattr(rc, "meta", None)
    try:
        md = meta.model_dump(by_alias=True, exclude_none=True) if meta is not None else None
    except Exception:
        md = repr(meta)
    return ToolResult(structured_content={"meta": md})

if __name__ == "__main__":
    mcp.run(transport="stdio", show_banner=False)
