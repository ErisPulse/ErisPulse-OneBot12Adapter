import asyncio
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

from ErisPulse.Core import client, router
from ErisPulse.Core.Bases import BaseConfig, BotAccountConfig
from ErisPulse.Core.Bases.adapter import BaseAdapter, RequestDSL
from ErisPulse.Core.Bases.websocket import WSMessage

from .i18n import OneBot12I18n

try:
    from ErisPulse.runtime.tasks import spawn_background
except ImportError:  # pragma: no cover
    spawn_background = None

__version__ = "4.3.0"

# 软依赖的框架最低版本（运行时检测，仅提示不强制）
MIN_FRAMEWORK_VERSION = (2, 7, 1)


@dataclass
class OneBot12GlobalConfig(BaseConfig):
    """OneBot12 适配器全局配置"""

    pass


@dataclass
class OneBot12AccountConfig(BotAccountConfig):
    """OneBot12 账户配置"""

    mode: str = field(
        default="server",
        metadata={
            "description": {"i18n": "OneBotv12_Adapter.mode", "default": "连接模式: server(被动) 或 client(主动)"},
            "required": False,
            "ui": {
                "widget": "select",
                "group": "connection",
                "order": 2,
                "options": [
                    {"label": {"i18n": "OneBotv12_Adapter.mode_server", "default": "Server"}, "value": "server"},
                    {"label": {"i18n": "OneBotv12_Adapter.mode_client", "default": "Client"}, "value": "client"},
                ],
            },
        },
    )
    server_path: Optional[str] = field(
        default="/onebot12",
        metadata={
            "description": {"i18n": "OneBotv12_Adapter.server_path", "default": "Server模式 WebSocket 路径"},
            "required": False,
            "ui": {"widget": "text", "group": "server", "order": 3},
        },
    )
    server_token: Optional[str] = field(
        default="",
        metadata={
            "description": {"i18n": "OneBotv12_Adapter.server_token", "default": "Server模式认证Token"},
            "required": False,
            "secret": True,
            "ui": {"widget": "password", "group": "server", "order": 4},
        },
    )
    client_url: Optional[str] = field(
        default="ws://127.0.0.1:3001",
        metadata={
            "description": {"i18n": "OneBotv12_Adapter.client_url", "default": "Client模式 WebSocket 地址"},
            "required": False,
            "ui": {"widget": "text", "group": "client", "order": 5},
        },
    )
    client_token: Optional[str] = field(
        default="",
        metadata={
            "description": {"i18n": "OneBotv12_Adapter.client_token", "default": "Client模式认证Token"},
            "required": False,
            "secret": True,
            "ui": {"widget": "password", "group": "client", "order": 6},
        },
    )
    implementation: Optional[str] = field(
        default="",
        metadata={
            "description": {"i18n": "OneBotv12_Adapter.implementation", "default": "实现标识（如 Lagrange, Napcat）"},
            "required": False,
            "ui": {"widget": "text", "group": "advanced", "order": 7},
        },
    )


# 分组显示名（WebUI 用）
OneBot12GlobalConfig._schema_meta = {
    "group_labels": {
        "connection": {"i18n": "OneBotv12_Adapter.group_connection", "default": "连接设置"},
        "server": {"i18n": "OneBotv12_Adapter.group_server", "default": "服务端模式"},
        "client": {"i18n": "OneBotv12_Adapter.group_client", "default": "客户端模式"},
        "advanced": {"i18n": "OneBotv12_Adapter.group_advanced", "default": "高级设置"},
    }
}


class OneBot12Adapter(BaseAdapter):
    """
    OneBot12 协议适配器

    作为 ErisPulse 框架的基线协议适配器，完全遵循 OneBot v12 标准。

    {!--< tips >!--}
    1. 支持 WebSocket Server/Client 混合运行模式
    2. 支持多账户并行运行，每个账户独立管理连接和状态
    3. 自动识别 bot_id，event.reply() 无需手动指定账户
    4. 提供完整的 ApiDSL 标准动作接口
    {!--< /tips >!--}
    """

    ConfigClass = OneBot12GlobalConfig
    AccountConfigClass = OneBot12AccountConfig
    I18nClass = OneBot12I18n

    class EventMixin:
        """
        OneBot12 平台事件扩展方法

        注册到事件包装类后，可在事件处理器中直接调用。
        """

        def get_raw_event(self) -> dict:
            """获取 OneBot12 原始事件数据（onebot12_raw）"""
            return self.get("onebot12_raw", {}) or {}

        def get_raw_type(self) -> str:
            """获取原始事件类型（onebot12_raw_type）"""
            return self.get("onebot12_raw_type", "") or ""

        def get_implementation(self) -> str:
            """获取 OneBot12 实现标识"""
            raw = self.get_raw_event()
            return raw.get("implementation", "") or ""

    class Api(BaseAdapter.Api):
        """
        OneBot12 标准 API 动作实现（ApiDSL）

        OneBot12 后端原生支持所有标准动作名，默认实现直接委托给 call_api。

        {!--< tips >!--}
        1. 所有标准动作（get_self_info/get_user_info/get_group_info 等）由后端原生支持
        2. 平台扩展动作通过 call("action_name", ...) 直接调用
        3. 不支持的动作由后端返回错误，透传即可
        {!--< /tips >!--}
        """

        pass

    class Send(BaseAdapter.Send):
        """
        OneBot12 消息发送 DSL

        {!--< tips >!--}
        1. 支持文本、图片、音频、视频、文件等多种消息类型
        2. 支持消息撤回和编辑
        3. 支持批量发送
        4. 支持位置和贴纸消息
        {!--< /tips >!--}
        """

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

        def Location(
            self, latitude: float, longitude: float, title: str = "", content: str = ""
        ):
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

            async def _do_send():
                return await self._adapter.call_api(
                    endpoint="send_message",
                    _account_id=self._account_id,
                    detail_type="private" if self._target_type == "user" else "group",
                    user_id=self._target_id if self._target_type == "user" else None,
                    group_id=self._target_id if self._target_type == "group" else None,
                    content=segments,
                    **kwargs,
                )

            return asyncio.create_task(_do_send())

        def Recall(self, message_id: Union[str, int]):
            return asyncio.create_task(
                self._adapter.call_api(
                    endpoint="delete_message",
                    _account_id=self._account_id,
                    message_id=str(message_id),
                )
            )

        def Edit(self, message_id: Union[str, int], content: Union[str, List[Dict]]):
            if isinstance(content, str):
                content = [{"type": "text", "data": {"text": content}}]
            return asyncio.create_task(
                self._adapter.call_api(
                    endpoint="edit_message",
                    _account_id=self._account_id,
                    message_id=str(message_id),
                    content=content,
                )
            )

        def Batch(
            self,
            target_ids: List[str],
            message: Union[str, List[Dict]],
            target_type: str = "user",
        ):
            tasks = []
            for target_id in target_ids:
                if isinstance(message, str):
                    task = self._adapter.call_api(
                        endpoint="send_message",
                        _account_id=self._account_id,
                        detail_type=target_type,
                        user_id=target_id if target_type == "user" else None,
                        group_id=target_id if target_type == "group" else None,
                        content=[{"type": "text", "data": {"text": message}}],
                    )
                else:
                    task = self._adapter.call_api(
                        endpoint="send_message",
                        _account_id=self._account_id,
                        detail_type=target_type,
                        user_id=target_id if target_type == "user" else None,
                        group_id=target_id if target_type == "group" else None,
                        content=message,
                    )
                tasks.append(task)
            return tasks

    class Request(RequestDSL):
        """
        OneBot12 请求操作 DSL

        用于处理好友请求和群请求（加群/邀请），提供接受和拒绝操作。
        基于 OneBot12 标准的 handle_quick_request 动作。
        """

        async def _do_accept(self, **kwargs) -> dict[str, Any]:
            return await self._do_action(approve=True, **kwargs)

        async def _do_reject(self, **kwargs) -> dict[str, Any]:
            return await self._do_action(approve=False, **kwargs)

        async def _do_action(self, approve: bool, **kwargs) -> dict[str, Any]:
            try:
                result = await self._adapter.call_api(
                    endpoint="handle_quick_request",
                    _account_id=self._account_id,
                    request_flag=self._request_id,
                    approve=approve,
                    **{k: v for k, v in kwargs.items() if not k.startswith("_")},
                )
                return result
            except Exception as e:
                return self._adapter.make_error(message=str(e))

    def __init__(self, sdk_ref=None):
        super().__init__(sdk_ref)
        self.connections: Dict[str, Any] = {}
        self._api_response_futures: Dict[str, Dict[str, asyncio.Future]] = {}
        self.reconnect_tasks: Dict[str, asyncio.Task] = {}
        self._bot_ids: Dict[str, str] = {}
        self._pending_connect_meta: set = set()
        self._running = False
        self.default_timeout = 30
        self.default_retry_interval = 30

        self._check_framework_version()
        self._get_logger().info(f"OneBot12Adapter v{__version__} 已加载")

    @staticmethod
    def _parse_version(version_str: str) -> tuple:
        """解析版本号为可比较的三元组（忽略 dev/预发布后缀，如 2.8.0-dev.3 → (2, 8, 0)）"""
        parts = []
        for piece in str(version_str).split("."):
            digits = "".join(ch for ch in piece if ch.isdigit())
            parts.append(int(digits) if digits else 0)
        while len(parts) < 3:
            parts.append(0)
        return tuple(parts[:3])

    def _check_framework_version(self):
        """软依赖检测：框架版本过低时打警告（不阻断加载）"""
        try:
            from importlib.metadata import version as _pkg_version

            raw = _pkg_version("ErisPulse")
        except Exception:
            return
        try:
            if self._parse_version(raw) < MIN_FRAMEWORK_VERSION:
                self._get_logger().warning(
                    f"当前 ErisPulse 版本 {raw} 过低：OneBot12Adapter v{__version__} 需要 >= "
                    f"{'.'.join(map(str, MIN_FRAMEWORK_VERSION))}"
                    "（Api DSL / spawn_background 等特性），"
                    "部分功能可能不可用，建议升级框架"
                )
        except Exception:
            pass

    def _get_config_key(self) -> str:
        return "OneBotv12_Adapter"

    def _get_bot_id(self, account_name: str) -> str:
        return self._bot_ids.get(account_name, "")

    def _bot_id_display(self, account_name: str) -> str:
        return self._bot_ids.get(account_name, "待确认")

    def _update_bot_id(self, account_name: str, self_id: str):
        old = self._bot_ids.get(account_name)
        if not old:
            self._bot_ids[account_name] = self_id
            self.logger.info(f"账户 {account_name} 自动识别 bot_id: {self_id}")
        elif old != self_id:
            self._bot_ids[account_name] = self_id
            self.logger.warning(f"账户 {account_name} bot_id 变更: {old} → {self_id}")

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
                f"账户 {account_name} (bot_id: {self._bot_id_display(account_name)}) 发送请求失败: {str(e)}"
            )
            if echo in self._api_response_futures[account_name]:
                del self._api_response_futures[account_name][echo]
            raise

        try:
            self.logger.debug(
                f"账户 {account_name} (bot_id: {self._bot_id_display(account_name)}) 请求: {payload}"
            )

            raw_response = await asyncio.wait_for(future, timeout=self.default_timeout)

            self.logger.debug(
                f"账户 {account_name} (bot_id: {self._bot_id_display(account_name)}) 响应: {raw_response}"
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
                f"账户 {account_name} (bot_id: {self._bot_id_display(account_name)}) API调用超时: {endpoint}"
            )
            if not future.done():
                future.cancel()

            return self.make_error(
                retcode=33001,
                message=f"账户 {account_name} (bot_id: {self._bot_id_display(account_name)}) API调用超时: {endpoint}",
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
                    f"账户 {account_name} (bot_id: {self._bot_id_display(account_name)}) 正在连接: {url}"
                )
                ws = await client.ws_connect(url, headers=headers)
                self.connections[account_name] = ws
                self.logger.info(
                    f"账户 {account_name} (bot_id: {self._bot_id_display(account_name)}) 连接成功"
                )
                await self.emit_meta("connect", self._get_bot_id(account_name))
                if not self._get_bot_id(account_name):
                    self._pending_connect_meta.add(account_name)
                await self._listen(account_name)
                if not self._running:
                    return
                self.logger.info(
                    f"账户 {account_name} (bot_id: {self._bot_id_display(account_name)}) "
                    f"{self.default_retry_interval}秒后重连..."
                )
                await asyncio.sleep(self.default_retry_interval)
            except Exception as e:
                if not self._running:
                    return
                self.logger.error(
                    f"账户 {account_name} (bot_id: {self._bot_id_display(account_name)}) 连接失败: {str(e)}"
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
                        f"账户 {account_name} (bot_id: {self._bot_id_display(account_name)}) 收到CLOSE帧"
                    )
                    break
                elif msg.type == WSMessage.ERROR:
                    self.logger.error(
                        f"账户 {account_name} (bot_id: {self._bot_id_display(account_name)}) 收到ERROR帧"
                    )
                    break
                else:
                    self.logger.warning(
                        f"账户 {account_name} 收到未知消息类型: {msg.type}"
                    )
        except Exception as e:
            self.logger.error(
                f"账户 {account_name} (bot_id: {self._bot_id_display(account_name)}) 监听异常: {str(e)}",
                exc_info=True,
            )
        finally:
            try:
                await self.emit_meta(
                    "disconnect", self._get_bot_id(account_name) if account else ""
                )
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
                future = self._api_response_futures.get(account_name, {}).get(
                    data["echo"]
                )
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
                    data["self"]["user_id"] = self._get_bot_id(account_name)
                data["self"]["platform"] = self._platform

                event_self_id = data.get("self", {}).get("user_id", "")
                if event_self_id:
                    self._update_bot_id(account_name, str(event_self_id))
                    if account_name in self._pending_connect_meta:
                        self._pending_connect_meta.discard(account_name)
                        await self.emit_meta("connect", str(event_self_id))

                await adapter_mgr.emit(data)

        except json.JSONDecodeError:
            self.logger.error(f"JSON解析失败: {raw_msg}")
        except Exception as e:
            self.logger.error(f"消息处理异常: {str(e)}")

    async def _ws_handler(self, websocket, account_name: str = "default"):
        account = self.accounts.get(account_name)
        if account:
            self.logger.info(
                f"账户 {account_name} (bot_id: {self._bot_id_display(account_name)}) 客户端已连接"
            )

        self.connections[account_name] = websocket

        await self.emit_meta(
            "connect", self._get_bot_id(account_name) if account else ""
        )
        if account and not self._get_bot_id(account_name):
            self._pending_connect_meta.add(account_name)

        try:
            while True:
                msg = await websocket.receive()
                if msg.type == WSMessage.TEXT:
                    asyncio.create_task(self._handle_message(msg.data, account_name))
                elif msg.type in (WSMessage.CLOSE, WSMessage.ERROR):
                    break
        except Exception:
            self.logger.info(
                f"账户 {account_name} (bot_id: {self._bot_id_display(account_name) if account else ''}) 客户端断开连接"
            )
        finally:
            try:
                await self.emit_meta(
                    "disconnect", self._get_bot_id(account_name) if account else ""
                )
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
                    f"账户 {account_name} (bot_id: {self._bot_id_display(account_name)}) Token无效"
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
                    f"{self._platform}_{account_name}",
                    path,
                    make_ws_handler(account_name),
                    auth_handler=make_auth_handler(account_name),
                )
                self.logger.info(
                    f"已注册账户 {account_name} (bot_id: {self._bot_id_display(account_name)}) 的Server路由: {path}"
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
                f"启动Client模式账户: {account_name} (bot_id: {self._bot_id_display(account_name)})"
            )
            coro = self.connect(account_name)
            # 生命周期任务使用 spawn_background（owner 归属，shutdown 自动回收）
            self.reconnect_tasks[account_name] = (
                spawn_background(coro) if spawn_background is not None else asyncio.create_task(coro)
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
                    f"关闭账户 {account_name} (bot_id: {self._bot_id_display(account_name) if account else ''}) 连接失败: {str(e)}"
                )
        self.connections.clear()

        self.logger.info("OneBot12适配器已关闭")
