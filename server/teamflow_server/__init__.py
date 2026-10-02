"""Team Flow 服务端（M0 原型）。

分层：
- ``service``：领域规则（任务状态机、指派子状态、"看见"闸门、信封、收件箱、hooks）。只用内存存储，
  用一把锁模拟 SQL 条件更新的原子性。
- ``rest``：/api/v1 REST 适配层（权威接口）。
- ``mcp_server``：/mcp/ 远程 MCP 适配层（FastMCP 4，无状态，两代协议）。
- ``gateway``：HTTP 层的鉴权、观测日志、路径规范化、故障注入；REST 和 MCP 共用。
"""

__version__ = "0.0.1-m0"
