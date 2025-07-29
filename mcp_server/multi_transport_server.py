#!/usr/bin/env python3
"""
Talebook MCP Multi-Transport Server

支持多种流式HTTP传输协议的MCP服务器：
- Server-Sent Events (SSE)
- WebSocket
- HTTP Chunked Transfer
- HTTP Long Polling
"""

import asyncio
import json
import logging
import uuid
from typing import Any, Sequence

import uvicorn
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse, JSONResponse
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, TextContent, InitializeResult
import httpx

# Import MCP service
from mcp_service import mcp_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="Talebook MCP Multi-Transport Server",
    description="MCP server supporting multiple streaming HTTP transports",
    version="1.0.0"
)

@app.get("/")
async def root():
    """Root endpoint with transport information."""
    return {
        "message": "Talebook MCP Multi-Transport Server",
        "status": "running",
        "transports": {
            "sse": "/sse",
            "websocket": "/ws",
            "http_stream": "/stream",
            "long_polling": "/poll"
        },
        "tools": ["get_books_count"]
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "server": "talebook-mcp"}

# 1. Server-Sent Events (SSE) Transport
@app.post("/sse")
async def handle_sse(request: Request):
    """Handle MCP over Server-Sent Events."""
    logger.info("New SSE connection from MCP client")
    try:
        transport = SseServerTransport("/sse")
        async with transport.connect_sse(request) as streams:
            logger.info("MCP server connected via SSE transport")
            await mcp_service.server.run(
                streams[0],
                streams[1],
                mcp_service.create_initialization_options()
            )
    except Exception as e:
        logger.error(f"Error in SSE handler: {e}")
        raise

# 2. WebSocket Transport
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Handle MCP over WebSocket."""
    logger.info("New WebSocket connection from MCP client")
    await websocket.accept()

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            request_data = json.loads(data)
            logger.info(f"WebSocket request: {request_data}")

            # Process MCP request using unified service
            response = await mcp_service.handle_request(request_data)

            # Send response back to client
            await websocket.send_text(json.dumps(response))

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"Error in WebSocket handler: {e}")
        await websocket.close()

# 3. Simple HTTP Transport (No Streaming)
@app.post("/simple")
async def handle_simple_http(request: Request):
    """Handle MCP over simple HTTP (no streaming)."""
    logger.info("New simple HTTP request from MCP client")

    try:
        body = await request.body()
        if not body:
            return JSONResponse({"error": "No request body"}, status_code=400)

        request_data = json.loads(body)
        logger.info(f"Simple HTTP request: {request_data}")

        # Process MCP request using unified service
        response = await mcp_service.handle_request(request_data)
        return JSONResponse(response)

    except Exception as e:
        logger.error(f"Error in simple HTTP handler: {e}")
        return JSONResponse({
            "jsonrpc": "2.0",
            "error": {"code": -32603, "message": str(e)}
        }, status_code=500)

# 4. HTTP Chunked Streaming Transport
@app.post("/stream")
async def handle_http_stream(request: Request):
    """Handle MCP over HTTP streaming."""
    logger.info("New HTTP stream connection from MCP client")

    try:
        # Read request body
        body = await request.body()
        if not body:
            return JSONResponse({"error": "No request body"}, status_code=400)

        request_data = json.loads(body)
        logger.info(f"HTTP stream request: {request_data}")

        # Process MCP request using unified service
        response = await mcp_service.handle_request(request_data)

        # Return direct JSON response instead of streaming
        return JSONResponse(response)

    except Exception as e:
        logger.error(f"Error in HTTP stream handler: {e}")
        return JSONResponse({
            "jsonrpc": "2.0",
            "error": {"code": -32603, "message": str(e)}
        }, status_code=500)

# 4.5. True HTTP Streaming Transport
@app.post("/true-stream")
async def handle_true_http_stream(request: Request):
    """Handle MCP over HTTP with proper streaming."""
    logger.info("New true HTTP stream connection from MCP client")

    async def generate_response():
        try:
            # Read request body
            body = await request.body()
            if not body:
                error_response = {
                    "jsonrpc": "2.0",
                    "error": {"code": -32700, "message": "Parse error: No request body"}
                }
                yield json.dumps(error_response).encode()
                return

            request_data = json.loads(body)
            logger.info(f"True stream request: {request_data}")

            # Process MCP request using unified service
            response = await mcp_service.handle_request(request_data)

            # Send the response as a single chunk and close
            yield json.dumps(response).encode()

        except Exception as e:
            logger.error(f"Error in true stream handler: {e}")
            error_response = {
                "jsonrpc": "2.0",
                "error": {"code": -32603, "message": str(e)}
            }
            yield json.dumps(error_response).encode()

    return StreamingResponse(
        generate_response(),
        media_type="application/json",
        headers={
            "Connection": "close",  # 确保连接关闭
            "Cache-Control": "no-cache"
        }
    )

# 5. HTTP Long Polling Transport
polling_queues = {}

@app.post("/poll")
async def handle_long_polling(request: Request):
    """Handle MCP over HTTP long polling."""
    logger.info("New HTTP long polling connection from MCP client")

    try:
        body = await request.body()
        if not body:
            return JSONResponse({"error": "No request body"}, status_code=400)

        request_data = json.loads(body)
        logger.info(f"Long polling request: {request_data}")

        # Process MCP request using unified service
        response = await mcp_service.handle_request(request_data)
        return JSONResponse(response)

    except Exception as e:
        logger.error(f"Error in long polling handler: {e}")
        return JSONResponse({
            "jsonrpc": "2.0",
            "error": {"code": -32603, "message": str(e)}
        }, status_code=500)

@app.get("/transports")
async def get_transports():
    """Get available transport methods."""
    return {
        "available_transports": [
            {
                "name": "sse",
                "endpoint": "/sse",
                "method": "POST",
                "description": "Server-Sent Events streaming"
            },
            {
                "name": "websocket",
                "endpoint": "/ws",
                "method": "WebSocket",
                "description": "WebSocket bidirectional streaming"
            },
            {
                "name": "simple-http",
                "endpoint": "/simple",
                "method": "POST",
                "description": "Simple HTTP (no streaming)"
            },
            {
                "name": "http-stream",
                "endpoint": "/stream",
                "method": "POST",
                "description": "HTTP JSON streaming"
            },
            {
                "name": "long-polling",
                "endpoint": "/poll",
                "method": "POST",
                "description": "HTTP long polling"
            }
        ]
    }

def main():
    """Main function to run the multi-transport HTTP MCP server."""
    logger.info("Starting Talebook MCP Multi-Transport Server")
    logger.info("Server-Sent Events: http://localhost:3001/sse")
    logger.info("WebSocket: ws://localhost:3001/ws")
    logger.info("HTTP Stream: http://localhost:3001/stream")
    logger.info("Long Polling: http://localhost:3001/poll")
    logger.info("Transports info: http://localhost:3001/transports")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=3001,
        log_level="info"
    )

if __name__ == "__main__":
    main()
