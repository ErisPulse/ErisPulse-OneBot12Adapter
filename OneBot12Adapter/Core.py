import asyncio
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

from ErisPulse.Core import client, router
from ErisPulse.Core.Bases.adapter import BaseAdapter
from ErisPulse.Core.Bases.websocket import WSMessage
from ErisPulse.runtime.config_schema import BotAccountConfig


@dataclass
class OneBot12AccountConfig(BotAccountConfig):
    bot_id: str = field(
        default="",
        metadata={
            "description": "机器人ID",
            "required": True,
            "webui": {"widget": "text", "group": "basic", "order": 1},
        },
    )
    mode: str = field(
        default="server",
        metadata={
            "description": "连接模式: server(被动) 或 client(主动)",
            "required": False,
            "webui": {
                "widget": "select",
                "group": "connection",
                "order": 2,
                "options": [
                    {"label": "Server", "value": "server"},
                    {"label": "Client", "value": "client"},
                ],
            },
        },
    )
    server_path: Optional[str] = field(
        default="/onebot12",
        metadata={
            "description": "Server模式 WebSocket 路径",
            "required": False,
            "webui": {"widget": "text", "group": "server", "order": 3},
        },
    )
    server_token: Optional[str] = field(
        default="",
        metadata={
            "description": "Server模式认证Token",
            "required": False,
            "secret": True,
            "webui": {"widget": "password", "group": "server", "order": 4},
        },
    )
    client_url: Optional[str] = field(
        default="ws://127.0.0.1:3001",
        metadata={
            "description": "Client模式 WebSocket 地址",
            "required": False,
            "webui": {"widget": "text", "group": "client", "order": 5},
        },
    )
    client_token: Optional[str] = field(
        default="",
        metadata={
            "description": "Client模式认证Token",
            "required": False,
            "secret": True,
            "webui": {"widget": "password", "group": "client", "order": 6},
        },
    )
    implementation: Optional[str] = field(
        default="",
        metadata={
            "description": "实现标识（如 Lagrange, Napcat）",
            "required": False,
            "webui": {"widget": "text", "group": "advanced", "order": 7},
        },
    )


class OneBot12Adapter(BaseAdapter):

    AccountConfigClass = OneBot12AccountConfig

    class Send(BaseAdapter.Send):

        def __init__(self, adapter, target_type=None, target_id=None, account_id=None):
            super().__init__(adapter, target_type, target_id, account_id)

        def Text(self, text: str):
            return self.Raw_ob12([{"type": "text", "data": {"text": text}}])

        def Image(self, file: Union[str, bytes], filename: str = "image.png"):
            data = {}
            if isinstance(file, bytes):
                import base64
                data["file_base64"] = base64.b64encode(file).decode("utf-8")
                data["file_name"] = filename
            else:
                data["file_id"] = file
            return self.Raw_ob12([{"type": "image", "data": data}])

        def Audio(self, file: Union[str, bytes], filename: str = "audio.ogg"):
            data = {}
            if isinstance(file, bytes):
                import base64
                data["file_base64"] = base64.b64encode(file).decode("utf-8")
                data["file_name"] = filename
            else:
                data["file_id"] = file
            return self.Raw_ob12([{"type": "audio", "data": data}])

        def Voice(self, file: Union[str, bytes], filename: str = "voice.ogg"):
            return self.Audio(file, filename)

        def Video(self, file: Union[str, bytes], filename: str = "video.mp4"):
            data = {}
            if isinstance(file, bytes):
                import base64
                data["file_base64"] = base64.b64encode(file).decode("utf-8")
                data["file_name"] = filename
            else:
                data["file_id"] = file
            return self.Raw_ob12([{"type": "video", "data": data}])

        def Location(self, latitude: float, longitude: float, title: str = "", content: str = ""):
            data = {"latitude": latitude, "longitude": longitude}
            if title:
                data["title"] = title
            if content:
                data["content"] = content
            return self.Raw_ob12([{"type": "location", "data": data}])

        def Sticker(self, file_id: str):
            return self.Raw_ob12([{"type": "sticker", "data": {"file_id": file_id}}])

        def Raw_ob12(self, message: Union[Dict, List[Dict]], **kwargs):
            if isinstance(message, dict):
                message = [message]

            segments = self._apply_modifiers(message)
            self._reset_modifiers()

            ctx = self.send_context
            target_type = kwargs.get("target_type") or ctx["target_type"]
            target_id = kwargs.get("target_id") or ctx["target_id"]
            account_id = kwargs.get("account_id") or ctx.get("account_id")
            detail_type = (
                "private" if target_type == "user"
                else "group" if target_type == "group"
                else kwargs.get("detail_type")
            )

            extra_kwargs = {
                k: v for k, v in kwargs.items()
                if k not in ("target_type", "target_id", "account_id", "detail_type")
            }

            return asyncio.create_task(
                self._adapter.call_api(
                    endpoint="send_message",
                    _account_id=account_id,
                    detail_type=detail_type,
                    user_id=target_id if target_type == "user" else None,
                    group_id=target_id if target_type == "group" else None,
                    content=segments,
                    **extra_kwargs,
                )
            )

        def Recall(self, message_id: Union[str, int]):
            ctx = self.send_context
            return asyncio.create_task(
                self._adapter.call_api(
                    endpoint="delete_message",
                    _account_id=ctx.get("account_id"),
                    message_id=str(message_id),
                )
            )

        def Edit(self, message_id: Union[str, int], content: Union[str, List[Dict]]):
            if isinstance(content, str):
                content = [{"type": "text", "data": {"text": content}}]
            ctx = self.send_context
            return asyncio.create_task(
                self._adapter.call_api(
                    endpoint="edit_message",
                    _account_id=ctx.get("account_id"),
                    message_id=str(message_id),
                    content=content,
                )
            )

        def Batch(self, target_ids: List[str], message: Union[str, List[Dict]], target_type: str = "user"):
            ctx = self.send_context
            tasks = []
            for target_id in target_ids:
                if isinstance(message, str):
                    task = self._adapter.call_api(
                        endpoint="send_message",
                        _account_id=ctx.get("account_id"),
                        detail_type=target_type,
                        user_id=target_id if target_type == "user" else None,
                        group_id=target_id if target_type == "group" else None,
                        content=[{"type": "text", "data": {"text": message}}],
                    )
                else:
                    task = self._adapter.call_api(
                        endpoint="send_message",
                        _account_id=ctx.get("account_id"),
                        detail_type=target_type,
                        user_id=target_id if target_type == "user" else None,
                        group_id=target_id if target_type == "group" else None,
                        content=message,
                    )
                tasks.append(task)
            return tasks

    def __init__(self, sdk_ref=None):
        super().__init__(sdk_ref)
        self.connections: Dict[str, Any] = {}
        self._api_response_futures: Dict[str, Dict[str, asyncio.Future]] = {}
        self.reconnect_tasks: Dict[str, asyncio.Task] = {}
        self._running = False
        self.default_timeout = 30
        self.default_retry_interval = 30

    def _get_config_key(self) -> str:
        return "OneBotv12_Adapter"

    def _load_accounts(self) -> dict:
        from ErisPulse.runtime.config_schema import dict_to_dataclass
        from ErisPulse.Core.config import config as config_mgr

        key = "OneBotv12_Adapter.accounts"
        data = config_mgr.getConfig(key)

        if not data:
            self.logger.info("未找到配置文件，创建默认账户配置")
            default_config = {
                "default": {
                    "bot_id": "",
                    "mode": "server",
                    "server_path": "/onebot12",
                    "server_token": "",
                    "client_url": "ws://127.0.0.1:3001",
                    "client_token": "",
                    "enabled": True,
                    "implementation": "",
                }
            }
            try:
                config_mgr.setConfig(key, default_config)
            except Exception as e:
                self.logger.error(f"保存默认账户配置失败: {str(e)}")
            data = default_config

        accounts = {}
        for name, account_data in data.items():
            if not isinstance(account_data, dict):
                continue
            if "bot_id" not in account_data or not account_data["bot_id"]:
                self.logger.error(f"账户 {name} 缺少bot_id配置，已跳过")
                continue

            instance = dict_to_dataclass(OneBot12AccountConfig, account_data)
            instance.name = name
            accounts[name] = instance

        self.logger.info(f"OneBot12适配器初始化完成，共加载 {len(accounts)} 个账户")
        return accounts

    async def call_api(self, endpoint: str, _account_id: str = None, **params):
        account_name, account = self._resolve_account(_account_id)

        connection = self.connections.get(account_name)
        if not connection:
            raise ConnectionError(f"账户 {account_name} 尚未连接")

        if hasattr(connection, "closed") and connection.closed:
            raise ConnectionError(f"账户 {account_name} 的连接已关闭")

        if account_name not in self._api_response_futures:
            self._api_response_futures[account_name] = {}

        echo = str(hash((str(params), account_name, endpoint)))
        future = asyncio.get_event_loop().create_future()
        self._api_response_futures[account_name][echo] = future

        payload = {"action": endpoint, "params": params, "echo": echo}

        try:
            await connection.send_text(json.dumps(payload))
        except Exception as e:
            self.logger.error(
                f"账户 {account_name} (bot_id: {account.bot_id}) 发送请求失败: {str(e)}"
            )
            if echo in self._api_response_futures[account_name]:
                del self._api_response_futures[account_name][echo]
            raise

        try:
            self.logger.debug(
                f"账户 {account_name} (bot_id: {account.bot_id}) 请求: {payload}"
            )

            raw_response = await asyncio.wait_for(future, timeout=self.default_timeout)

            self.logger.debug(
                f"账户 {account_name} (bot_id: {account.bot_id}) 响应: {raw_response}"
            )

            message_id = ""
            if isinstance(raw_response.get("data"), dict):
                message_id = str(raw_response["data"].get("message_id", ""))

            retcode = raw_response.get("retcode", 0)
            status = "ok" if retcode == 0 else "failed"

            resp = self.make_response(
                status=status,
                retcode=retcode,
                data=raw_response.get("data"),
                message_id=message_id,
                message=raw_response.get("message", ""),
                raw=raw_response,
            )
            resp["onebot12_raw"] = raw_response

            return resp

        except asyncio.TimeoutError:
            self.logger.error(
                f"账户 {account_name} (bot_id: {account.bot_id}) API调用超时: {endpoint}"
            )
            if not future.done():
                future.cancel()

            return self.make_error(
                retcode=33001,
                message=f"账户 {account_name} (bot_id: {account.bot_id}) API调用超时: {endpoint}",
                raw=None,
            )

        finally:

            async def cleanup():
                await asyncio.sleep(0.1)
                if (
                    account_name in self._api_response_futures
                    and echo in self._api_response_futures[account_name]
                ):
                    del self._api_response_futures[account_name][echo]

            asyncio.create_task(cleanup())

    async def connect(self, account_name: str):
        if account_name not in self.accounts:
            raise ValueError(f"账户 {account_name} 不存在")

        account = self.accounts[account_name]
        if account.mode != "client":
            return

        headers = {}
        if account.client_token:
            headers["Authorization"] = f"Bearer {account.client_token}"

        url = account.client_url

        while self._running:
            try:
                self.logger.info(
                    f"账户 {account_name} (bot_id: {account.bot_id}) 正在连接: {url}"
                )
                ws = await client.ws_connect(url, headers=headers)
                self.connections[account_name] = ws
                self.logger.info(
                    f"账户 {account_name} (bot_id: {account.bot_id}) 连接成功"
                )
                await self.emit_meta("connect", account.bot_id)
                await self._listen(account_name)
                if not self._running:
                    return
                self.logger.info(
                    f"账户 {account_name} (bot_id: {account.bot_id}) "
                    f"{self.default_retry_interval}秒后重连..."
                )
                await asyncio.sleep(self.default_retry_interval)
            except Exception as e:
                if not self._running:
                    return
                self.logger.error(
                    f"账户 {account_name} (bot_id: {account.bot_id}) 连接失败: {str(e)}"
                )
                await asyncio.sleep(self.default_retry_interval)

    async def _listen(self, account_name: str):
        connection = self.connections.get(account_name)
        if not connection:
            return

        account = self.accounts.get(account_name)

        try:
            while True:
                msg = await connection.receive()
                if msg.type == WSMessage.TEXT:
                    self.logger.debug(
                        f"账户 {account_name} 收到WS文本: {str(msg.data)[:300]}"
                    )
                    asyncio.create_task(self._handle_message(msg.data, account_name))
                elif msg.type == WSMessage.BINARY:
                    self.logger.debug(f"账户 {account_name} 收到WS二进制数据")
                elif msg.type == WSMessage.CLOSE:
                    self.logger.info(
                        f"账户 {account_name} (bot_id: {account.bot_id}) 收到CLOSE帧"
                    )
                    break
                elif msg.type == WSMessage.ERROR:
                    self.logger.error(
                        f"账户 {account_name} (bot_id: {account.bot_id}) 收到ERROR帧"
                    )
                    break
                else:
                    self.logger.warning(
                        f"账户 {account_name} 收到未知消息类型: {msg.type}"
                    )
        except Exception as e:
            self.logger.error(
                f"账户 {account_name} (bot_id: {account.bot_id}) 监听异常: {str(e)}",
                exc_info=True,
            )
        finally:
            try:
                await self.emit_meta("disconnect", account.bot_id if account else "")
            except Exception:
                pass
            self.connections.pop(account_name, None)

    async def _handle_message(self, raw_msg: str, account_name: str):
        try:
            data = json.loads(raw_msg)
            account = self.accounts.get(account_name)
            if not account:
                return

            if "echo" in data:
                future = self._api_response_futures.get(account_name, {}).get(data["echo"])
                if future and not future.done():
                    future.set_result(data)
                return

            from ErisPulse.Core import adapter as adapter_mgr

            if data:
                raw_type = data.get("type", "")

                data["onebot12_raw"] = dict(data)
                if raw_type:
                    data["onebot12_raw_type"] = raw_type

                data["platform"] = self._platform

                if "self" not in data:
                    data["self"] = {}
                if not data.get("self", {}).get("user_id"):
                    data["self"]["user_id"] = account.bot_id
                data["self"]["platform"] = self._platform

                await adapter_mgr.emit(data)

        except json.JSONDecodeError:
            self.logger.error(f"JSON解析失败: {raw_msg}")
        except Exception as e:
            self.logger.error(f"消息处理异常: {str(e)}")

    async def _ws_handler(self, websocket, account_name: str = "default"):
        account = self.accounts.get(account_name)
        if account:
            self.logger.info(
                f"账户 {account_name} (bot_id: {account.bot_id}) 客户端已连接"
            )

        self.connections[account_name] = websocket

        await self.emit_meta("connect", account.bot_id if account else "")

        try:
            while True:
                msg = await websocket.receive()
                if msg.type == WSMessage.TEXT:
                    asyncio.create_task(self._handle_message(msg.data, account_name))
                elif msg.type in (WSMessage.CLOSE, WSMessage.ERROR):
                    break
        except Exception:
            self.logger.info(
                f"账户 {account_name} (bot_id: {account.bot_id if account else ''}) 客户端断开连接"
            )
        finally:
            try:
                await self.emit_meta("disconnect", account.bot_id if account else "")
            except Exception:
                pass
            if account_name in self.connections:
                del self.connections[account_name]

    async def _auth_handler(self, websocket, account_name: str = "default"):
        if account_name not in self.accounts:
            await websocket.close(code=1008)
            return False

        account = self.accounts[account_name]
        if account.server_token:
            client_token = websocket.headers.get("Authorization", "").replace(
                "Bearer ", ""
            )
            if not client_token:
                query = dict(websocket.query_params)
                client_token = query.get("token", "")

            if client_token != account.server_token:
                self.logger.warning(
                    f"账户 {account_name} (bot_id: {account.bot_id}) Token无效"
                )
                await websocket.close(code=1008)
                return False
        return True

    async def register_websocket(self):
        for account_name, account in self.enabled_accounts.items():
            if account.mode == "server":
                path = account.server_path

                def make_ws_handler(name):
                    async def handler(ws):
                        await self._ws_handler(ws, name)

                    return handler

                def make_auth_handler(name):
                    async def handler(ws):
                        return await self._auth_handler(ws, name)

                    return handler

                router.register_websocket(
                    f"onebot12_{account_name}",
                    path,
                    make_ws_handler(account_name),
                    auth_handler=make_auth_handler(account_name),
                )
                self.logger.info(
                    f"已注册账户 {account_name} (bot_id: {account.bot_id}) 的Server路由: {path}"
                )

    async def start(self):
        self._running = True

        server_accounts = [
            name for name, acc in self.enabled_accounts.items() if acc.mode == "server"
        ]
        client_accounts = [
            name for name, acc in self.enabled_accounts.items() if acc.mode == "client"
        ]

        if server_accounts:
            await self.register_websocket()

        for account_name in client_accounts:
            account = self.accounts[account_name]
            self.logger.info(
                f"启动Client模式账户: {account_name} (bot_id: {account.bot_id})"
            )
            self.reconnect_tasks[account_name] = asyncio.create_task(
                self.connect(account_name)
            )

        enabled_count = len(server_accounts) + len(client_accounts)
        self.logger.info(f"OneBot12适配器启动完成，共 {enabled_count} 个账户")

    async def shutdown(self):
        self._running = False

        for task in self.reconnect_tasks.values():
            if not task.done():
                task.cancel()
        self.reconnect_tasks.clear()

        for account_name, connection in list(self.connections.items()):
            account = self.accounts.get(account_name)
            try:
                if hasattr(connection, "closed") and not connection.closed:
                    await connection.close()
            except Exception as e:
                self.logger.error(
                    f"关闭账户 {account_name} (bot_id: {account.bot_id if account else ''}) 连接失败: {str(e)}"
                )
        self.connections.clear()

        self.logger.info("OneBot12适配器已关闭")
