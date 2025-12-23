#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import json
import logging
import tornado.websocket
from webserver.handlers.base import BaseHandler
from webserver.assistant.deepseek_agent import DeepSeekMCPAgent

class AssistantWebSocketHandler(tornado.websocket.WebSocketHandler, BaseHandler):
    # 保存连接的实例，以便后台服务管理
    clients = set()
    _agent = None

    def check_origin(self, origin):
        return True

    async def open(self):
        if not self.get_current_user():
            logging.info("WebSocket connection attempt without login.")
            self.close(code=4003, reason="Authentication required")
            return

        logging.info("WebSocket assistant opened")
        self.clients.add(self)

        # 延迟初始化Agent，如果还没创建
        if AssistantWebSocketHandler._agent is None:
            AssistantWebSocketHandler._agent = DeepSeekMCPAgent()
            await AssistantWebSocketHandler._agent.initialize()

        self.write_message(json.dumps({"type": "status", "content": "AI助手连接成功"}))

    async def on_message(self, message):
        try:
            data = json.loads(message)
            user_input = data.get("content", "")
            if not user_input:
                return

            logging.info(f"AI Assistant Task: {user_input}")

            # 开启处理
            self.write_message(json.dumps({"type": "start"}))

            async for chunk in AssistantWebSocketHandler._agent.process_user_input(user_input):
                self.write_message(json.dumps(chunk))

            # 处理完成
            self.write_message(json.dumps({"type": "end"}))

        except Exception as e:
            logging.error(f"Error processing AI message: {e}")
            self.write_message(json.dumps({"type": "error", "content": str(e)}))

    def on_close(self):
        logging.info("WebSocket assistant closed")
        self.clients.remove(self)

def routes():
    return [
        (r"/api/assistant/ws", AssistantWebSocketHandler),
    ]
