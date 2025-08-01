#!/usr/bin/env python3
"""
MCP Service Module

统一处理MCP协议请求的服务模块，供不同传输协议调用。
"""

import logging
import json
import traceback
import uuid
from typing import Any, Sequence, Dict, Optional

from mcp.server import Server
from mcp.types import Tool, TextContent
from webserver.handlers.base import BaseHandler


class MCPService:
    """MCP协议处理服务类"""
    MAX_BOOKS_COUNT_IN_RESULT = 100  # 返回结果中最大书籍数量限制

    def __init__(self, base_handler: BaseHandler = None):
        """初始化MCP服务"""
        self.server = Server("talebook-mcp")
        self.base_handler = base_handler
        self._setup_tools()

    def _setup_tools(self):
        """设置工具定义"""
        pass

    async def search_books(self, arguments: dict[str, Any]) -> Sequence[TextContent]:
        name = arguments.get("name", "")
        if not name:
            return [TextContent(type="text", text="Invalid parameter 'name'")]

        title = _(u"搜索：%(name)s") % {"name": name}
        try:
            import opencc
            ids = self.base_handler.cache.search(name)
            for profile in {'s2t', "t2s"}:
                if len(ids) >= self.MAX_BOOKS_COUNT_IN_RESULT:
                    break
                converted_name = opencc.OpenCC(profile).convert(name)
                if converted_name == name:
                    continue
                ids2 = self.base_handler.cache.search(converted_name)
                if len(ids2) > 0:
                    ids = ids.union(ids, ids2)
                    break

            if not ids:
                return [TextContent(type="text", text=_(u"没有找到相关书籍"))]

            if len(ids) > self.MAX_BOOKS_COUNT_IN_RESULT:
                ids = sorted(ids, key=lambda x: self.base_handler.cache.get_book(x).get("updated", 0), reverse=True)

            book_list = self.base_handler.get_book_list([], ids=ids, title=title)

            logging.info(f"Search books with name: {book_list}")
            logging.info(book_list)
            return [TextContent(type="text", text=json.dumps(book_list))]
        except Exception as e:
            logging.error(f"Error processing book: {e}")
            logging.error(traceback.format_exc())
            return [TextContent(type="text", text=_(u"搜索书籍时发生错误: %s") % str(e))]

    async def get_books_count(self, arguments: dict[str, Any]) -> Sequence[TextContent]:
        """Get the current count of books in the collection."""
        from sqlalchemy import func
        try:
            if self.base_handler is None:
                books_count = 0
                author_count = 0
            else:
                db = self.base_handler.db
                books_count = db.count()
                author_count = len(db.all_authors())
            result = f"Total {books_count} books, and {author_count} authors."
            logging.info(f"Books count requested, returning: {books_count}")
            return [TextContent(type="text", text=result)]
        except Exception as e:
            error_msg = f"Error getting books count: {str(e)}"
            logging.error(error_msg)
            return [TextContent(type="text", text=error_msg)]

    async def list_tools(self) -> list[Tool]:
        """获取可用工具列表"""
        return [
            Tool(
                name="get_books_count",
                description="Get the current count of books in the talebook collection",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            Tool(
                name="search_books",
                description="Search for books in the collection",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Name of the book, author to search for"
                        }
                    },
                    "required": ["name"]
                }
            )
        ]

    def create_initialization_options(self) -> Dict[str, Any]:
        """创建初始化选项，包含会话ID"""
        session_id = str(uuid.uuid4())
        logging.info(f"Creating MCP server with session ID: {session_id}")

        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}
            },
            "serverInfo": {
                "name": "talebook-mcp",
                "version": "1.0.0"
            },
            "sessionId": session_id
        }

    async def handle_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        统一处理MCP请求

        Args:
            request_data: JSON-RPC请求数据

        Returns:
            JSON-RPC响应数据
        """
        method = request_data.get("method")
        request_id = request_data.get("id")
        params = request_data.get("params", {})

        try:
            # 处理初始化请求
            if method == "initialize":
                init_options = self.create_initialization_options()
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": init_options
                }

            # 处理工具列表请求（支持新旧两种方法名）
            elif method == "tools/list":
                tools = await self.list_tools()
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {"tools": [tool.model_dump(exclude_none=True) for tool in tools]}
                }

            # 处理工具调用请求（支持新旧两种方法名）
            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})

                if tool_name == "get_books_count":
                    result = await self.get_books_count(arguments)
                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {"content": [{"type": "text", "text": result[0].text}]}
                    }
                elif tool_name == "search_books":
                    result = await self.search_books(arguments)
                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {"content": [{"type": "text", "text": result[0].text}]}
                    }
                else:
                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"}
                    }

            # 未知方法
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32601, "message": f"Method not found: {method}"}
                }

        except Exception as e:
            logging.error(f"Error handling MCP request: {e}")
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32603, "message": f"Internal error: {str(e)}"}
            }
