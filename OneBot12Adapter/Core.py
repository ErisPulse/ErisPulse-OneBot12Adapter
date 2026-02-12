# OneBot12Adapter/Core.py
import asyncio
import json
import aiohttp
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List, Optional, Union
from dataclasses import dataclass
from ErisPulse import sdk
from ErisPulse.Core import router

@dataclass
class OneBot12AccountConfig:
    """OneBot12 账户配置"""
    bot_id: str  # 机器人ID（必填，用于SDK路由）
    mode: str  # "server" or "client"
    server_path: Optional[str] = "/onebot12"
    server_token: Optional[str] = ""
    client_url: Optional[str] = "ws://127.0.0.1:3001"
    client_token: Optional[str] = ""
    enabled: bool = True
    name: str = ""  # 账户名称
    # OneBot12特有配置
    platform: Optional[str] = "onebot12"  # 平台标识
    implementation: Optional[str] = ""     # 实现标识

class OneBot12Adapter(sdk.BaseAdapter):
    """
    OneBot V12 协议适配器实现

    {!--< tips >!--}
    1. 支持多账户管理，每个账户有独立的 bot_id
    2. 支持指定 bot_id 作为 self._account_id
    3. 提供 WebSocket Server/Client 混合运行模式
    4. 完整的 DSL 消息发送接口
    {!--< /tips >!--}
    """
    
    class Send(sdk.BaseAdapter.Send):
        """消息发送类 - OneBot12标准"""

        # 方法名映射表（全小写 -> 实际方法名）
        _METHOD_MAP = {
            # 消息发送方法
            "text": "Text",
            "image": "Image",
            "audio": "Audio",
            "voice": "Audio",  # Voice 映射到 Audio
            "video": "Video",
            "location": "Location",
            "sticker": "Sticker",
            "recall": "Recall",
            "edit": "Edit",
            "batch": "Batch",
            "raw_ob12": "Raw_ob12",
            # 链式修饰方法
            "at": "At",
            "atall": "AtAll",
            "reply": "Reply",
        }

        def __init__(self, adapter, target_type=None, target_id=None, account_id=None):
            """初始化Send类，设置链式调用状态"""
            super().__init__(adapter, target_type, target_id, account_id)
            self._at_user_ids = []        # @用户ID列表
            self._at_all = False          # 是否@全体
            self._reply_message_id = None # 回复的消息ID
        
        def At(self, user_id: Union[str, int]):
            """
            @用户（可多次调用，支持链式）
            
            :param user_id: 用户ID
            :return: self 支持链式调用
            """
            self._at_user_ids.append(str(user_id))
            return self
        
        def AtAll(self):
            """
            @全体成员（支持链式）
            
            :return: self 支持链式调用
            """
            self._at_all = True
            return self
        
        def Reply(self, message_id: Union[str, int]):
            """
            回复消息（支持链式）
            
            :param message_id: 要回复的消息ID
            :return: self 支持链式调用
            """
            self._reply_message_id = str(message_id)
            return self
        
        def _build_message_content(self, content):
            """
            构建完整的消息内容，包含链式修饰符
            
            :param content: 基础消息内容
            :return: 完整的消息段数组
            """
            message_segments = []
            
            # 如果设置了回复，先添加回复消息段
            if self._reply_message_id:
                message_segments.append({
                    "type": "reply",
                    "data": {"message_id": self._reply_message_id}
                })
            
            # 添加@全体
            if self._at_all:
                message_segments.append({
                    "type": "mention_all",
                    "data": {}
                })
            
            # 添加@用户
            for user_id in self._at_user_ids:
                message_segments.append({
                    "type": "mention",
                    "data": {"user_id": user_id}
                })
            
            # 添加基础内容
            if isinstance(content, dict):
                message_segments.append(content)
            elif isinstance(content, list):
                message_segments.extend(content)
            
            return message_segments
        
        def _reset_chain_state(self):
            """重置链式状态"""
            self._at_user_ids = []
            self._at_all = False
            self._reply_message_id = None
        
        def Text(self, text: str):
            """发送文本消息"""
            content = {"type": "text", "data": {"text": text}}
            full_content = self._build_message_content(content)
            self._reset_chain_state()
            
            return asyncio.create_task(
                self._adapter.call_api(
                    endpoint="send_message",
                    account_id=self._account_id,
                    detail_type=self._get_detail_type(),
                    user_id=self._target_id if self._target_type == "user" else None,
                    group_id=self._target_id if self._target_type == "group" else None,
                    content=full_content
                )
            )
        
        def Image(self, file: Union[str, bytes], filename: str = "image.png"):
            """发送图片消息"""
            data = {}
            if isinstance(file, bytes):
                import base64
                data["file_base64"] = base64.b64encode(file).decode('utf-8')
                data["file_name"] = filename
            else:
                data["file_id"] = file
            
            content = {"type": "image", "data": data}
            full_content = self._build_message_content(content)
            self._reset_chain_state()
            
            return asyncio.create_task(
                self._adapter.call_api(
                    endpoint="send_message",
                    account_id=self._account_id,
                    detail_type=self._get_detail_type(),
                    user_id=self._target_id if self._target_type == "user" else None,
                    group_id=self._target_id if self._target_type == "group" else None,
                    content=full_content
                )
            )
        
        def Audio(self, file: Union[str, bytes], filename: str = "audio.ogg"):
            """发送语音消息"""
            data = {}
            if isinstance(file, bytes):
                import base64
                data["file_base64"] = base64.b64encode(file).decode('utf-8')
                data["file_name"] = filename
            else:
                data["file_id"] = file
            
            content = {"type": "audio", "data": data}
            full_content = self._build_message_content(content)
            self._reset_chain_state()
            
            return asyncio.create_task(
                self._adapter.call_api(
                    endpoint="send_message",
                    account_id=self._account_id,
                    detail_type=self._get_detail_type(),
                    user_id=self._target_id if self._target_type == "user" else None,
                    group_id=self._target_id if self._target_type == "group" else None,
                    content=full_content
                )
            )
        
        def Vocie(self, file: Union[str, bytes], filename: str = "voice.ogg"):
            return self.Audio(file, filename)

        def Video(self, file: Union[str, bytes], filename: str = "video.mp4"):
            """发送视频消息"""
            data = {}
            if isinstance(file, bytes):
                import base64
                data["file_base64"] = base64.b64encode(file).decode('utf-8')
                data["file_name"] = filename
            else:
                data["file_id"] = file
            
            content = {"type": "video", "data": data}
            full_content = self._build_message_content(content)
            self._reset_chain_state()
            
            return asyncio.create_task(
                self._adapter.call_api(
                    endpoint="send_message",
                    account_id=self._account_id,
                    detail_type=self._get_detail_type(),
                    user_id=self._target_id if self._target_type == "user" else None,
                    group_id=self._target_id if self._target_type == "group" else None,
                    content=full_content
                )
            )
        
        def Location(self, latitude: float, longitude: float, title: str = "", content: str = ""):
            """发送位置消息"""
            data = {
                "latitude": latitude,
                "longitude": longitude
            }
            if title:
                data["title"] = title
            if content:
                data["content"] = content
            
            content = {"type": "location", "data": data}
            full_content = self._build_message_content(content)
            self._reset_chain_state()
            
            return asyncio.create_task(
                self._adapter.call_api(
                    endpoint="send_message",
                    account_id=self._account_id,
                    detail_type=self._get_detail_type(),
                    user_id=self._target_id if self._target_type == "user" else None,
                    group_id=self._target_id if self._target_type == "group" else None,
                    content=full_content
                )
            )
        
        def Sticker(self, file_id: str):
            """发送表情包/贴纸"""
            content = {"type": "sticker", "data": {"file_id": file_id}}
            full_content = self._build_message_content(content)
            self._reset_chain_state()
            
            return asyncio.create_task(
                self._adapter.call_api(
                    endpoint="send_message",
                    account_id=self._account_id,
                    detail_type=self._get_detail_type(),
                    user_id=self._target_id if self._target_type == "user" else None,
                    group_id=self._target_id if self._target_type == "group" else None,
                    content=full_content
                )
            )
        
        def Raw_ob12(self, message: Union[Dict, List[Dict]], **kwargs):
            """
            发送原始OneBot12格式消息
            
            :param message: OneBot12格式的消息段或消息段数组
            :param kwargs: 额外参数（如target_type, target_id等，优先使用链式设置的值）
            :return: asyncio.Task对象
            """
            # 确保message是列表格式
            if isinstance(message, dict):
                message = [message]
            
            # 应用链式修饰符
            full_content = self._build_message_content(message)
            self._reset_chain_state()
            
            # 使用链式设置的值或kwargs中的值
            target_type = kwargs.get('target_type') or self._target_type
            target_id = kwargs.get('target_id') or self._target_id
            account_id = kwargs.get('account_id') or self._account_id
            
            # 确定detail_type
            detail_type = "private" if target_type == "user" else "group" if target_type == "group" else kwargs.get('detail_type')
            
            return asyncio.create_task(
                self._adapter.call_api(
                    endpoint="send_message",
                    account_id=account_id,
                    detail_type=detail_type,
                    user_id=target_id if target_type == "user" else None,
                    group_id=target_id if target_type == "group" else None,
                    content=full_content,
                    **{k: v for k, v in kwargs.items() if k not in ['target_type', 'target_id', 'account_id', 'detail_type']}
                )
            )
        
        def Recall(self, message_id: Union[str, int]):
            """撤回消息"""
            return asyncio.create_task(
                self._adapter.call_api(
                    endpoint="delete_message",
                    account_id=self._account_id,
                    message_id=str(message_id)
                )
            )
        
        def Edit(self, message_id: Union[str, int], content: Union[str, List[Dict]]):
            """编辑消息"""
            if isinstance(content, str):
                content = [{"type": "text", "data": {"text": content}}]
            
            return asyncio.create_task(
                self._adapter.call_api(
                    endpoint="edit_message",
                    account_id=self._account_id,
                    message_id=str(message_id),
                    content=content
                )
            )
        
        def Batch(self, target_ids: List[str], message: Union[str, List[Dict]], target_type: str = "user"):
            """批量发送消息"""
            tasks = []
            for target_id in target_ids:
                if isinstance(message, str):
                    task = self._adapter.call_api(
                        endpoint="send_message",
                        account_id=self._account_id,
                        detail_type=target_type,
                        user_id=target_id if target_type == "user" else None,
                        group_id=target_id if target_type == "group" else None,
                        content=[{"type": "text", "data": {"text": message}}]
                    )
                else:
                    task = self._adapter.call_api(
                        endpoint="send_message",
                        account_id=self._account_id,
                        detail_type=target_type,
                        user_id=target_id if target_type == "user" else None,
                        group_id=target_id if target_type == "group" else None,
                        content=message
                    )
                tasks.append(task)
            return tasks
        
        def _get_detail_type(self):
            """获取消息详细类型"""
            return "private" if self._target_type == "user" else "group"
        
        def _send_complex_message(self, message_segments: List[Dict]):
            """发送复合消息"""
            return asyncio.create_task(
                self._adapter.call_api(
                    endpoint="send_message",
                    account_id=self._account_id,
                    detail_type=self._get_detail_type(),
                    user_id=self._target_id if self._target_type == "user" else None,
                    group_id=self._target_id if self._target_type == "group" else None,
                    content=message_segments
                )
            )

        def __getattr__(self, name):
            """
            处理未定义的发送方法（支持大小写不敏感）

            当调用不存在的消息类型方法时：
            1. 通过映射表查找对应的方法
            2. 如果找到则调用该方法
            3. 如果找不到，则发送文本提示不支持
            """
            name_lower = name.lower()

            # 查找映射
            if name_lower in self._METHOD_MAP:
                actual_method_name = self._METHOD_MAP[name_lower]
                return getattr(self, actual_method_name)

            # 方法不存在，返回文本提示
            def unsupported_method(*args, **kwargs):
                # 格式化参数信息
                params_info = []
                for i, arg in enumerate(args):
                    if isinstance(arg, bytes):
                        params_info.append(f"args[{i}]: <bytes: {len(arg)} bytes>")
                    else:
                        params_info.append(f"args[{i}]: {repr(arg)[:100]}")

                for k, v in kwargs.items():
                    if isinstance(v, bytes):
                        params_info.append(f"{k}: <bytes: {len(v)} bytes>")
                    else:
                        params_info.append(f"{k}: {repr(v)[:100]}")

                params_str = ", ".join(params_info)
                error_msg = f"[不支持的发送类型] 方法名: {name}, 参数: [{params_str}]"

                return self.Text(error_msg)

            return unsupported_method

    def __init__(self, sdk):
        super().__init__()
        self.sdk = sdk
        self.logger = sdk.logger
        self.adapter = self.sdk.adapter

        # 加载配置
        self.accounts: Dict[str, OneBot12AccountConfig] = self._load_account_configs()
        
        # 连接池 - 每个账户一个连接
        self._api_response_futures: Dict[str, Dict[str, asyncio.Future]] = {}
        self.sessions: Dict[str, aiohttp.ClientSession] = {}
        self.connections: Dict[str, aiohttp.ClientWebSocketResponse] = {}
        
        # 轮询任务
        self.reconnect_tasks: Dict[str, asyncio.Task] = {}
        
        # 初始化状态
        self._is_running = False
        
        # 默认配置值
        self.default_retry_interval = 30
        self.default_timeout = 30
        self.default_max_retries = 3

    def _load_account_configs(self) -> Dict[str, OneBot12AccountConfig]:
        """加载多账户配置"""
        accounts = {}

        # 检查新格式的账户配置
        account_configs = self.sdk.config.getConfig("OneBotv12_Adapter.accounts", {})

        if not account_configs:
            # 创建默认账户配置
            self.logger.info("未找到配置文件，创建默认账户配置")
            default_config = {
                "default": {
                    "bot_id": "机器人ID/QQ号",  # 用户需修改为实际的机器人ID
                    "mode": "server",
                    "server_path": "/onebot12",
                    "server_token": "",
                    "client_url": "ws://127.0.0.1:3001",
                    "client_token": "",
                    "enabled": True,
                    "platform": "onebot12",
                    "implementation": ""
                }
            }

            try:
                self.sdk.config.setConfig("OneBotv12_Adapter.accounts", default_config)
                account_configs = default_config
            except Exception as e:
                self.logger.error(f"保存默认账户配置失败: {str(e)}")
                account_configs = default_config

        # 创建账户配置对象
        for account_name, config in account_configs.items():
            # 检查必填字段
            if "bot_id" not in config or not config["bot_id"]:
                self.logger.error(f"账户 {account_name} 缺少bot_id配置，已跳过")
                continue

            # 使用内置默认值
            merged_config = {
                "bot_id": config["bot_id"],
                "mode": config.get("mode", "server"),
                "server_path": config.get("server_path", "/onebot12"),
                "server_token": config.get("server_token", ""),
                "client_url": config.get("client_url", "ws://127.0.0.1:3001"),
                "client_token": config.get("client_token", ""),
                "enabled": config.get("enabled", True),
                "name": account_name,
                "platform": config.get("platform", "onebot12"),
                "implementation": config.get("implementation", "")
            }

            accounts[account_name] = OneBot12AccountConfig(**merged_config)

        self.logger.info(f"OneBot12适配器初始化完成，共加载 {len(accounts)} 个账户")
        return accounts
    
    async def call_api(self, endpoint: str, account_id: str = None, **params):
        """
        调用 OneBot12 API

        :param endpoint: API端点
        :param account_id: 账户名或bot_id
        :param params: 其他API参数
        :return: 标准化的响应
        """
        # 确定使用的账户
        if account_id is None:
            if not self.accounts:
                raise ValueError("没有配置任何OneBot12账户")
            account = next(iter(self.accounts.values()))
            account_name = next(iter(self.accounts.keys()))
        else:
            # 判断 account_id 是账户名还是 bot_id
            if account_id in self.accounts:
                # account_id 是账户名，直接使用
                account = self.accounts[account_id]
                account_name = account_id
            else:
                # account_id 是 bot_id，查找对应的账户
                for account_name, acc_config in self.accounts.items():
                    if acc_config.bot_id == account_id:
                        account = acc_config
                        break
                else:
                    raise ValueError(f"找不到bot_id或账户名为 {account_id} 的账户")

        if not account.enabled:
            raise ValueError(f"账户 {account_name} 已禁用")

        connection = self.connections.get(account_name)
        if not connection:
            raise ConnectionError(f"账户 {account_name} 尚未连接到OneBot12")

        if connection.closed:
            raise ConnectionError(f"账户 {account_name} 的WebSocket连接已关闭")

        # 确保该账户的响应Future字典存在
        if account_name not in self._api_response_futures:
            self._api_response_futures[account_name] = {}

        echo = str(hash(str(params + (account_name, endpoint))))
        future = asyncio.get_event_loop().create_future()
        self._api_response_futures[account_name][echo] = future
        self.logger.debug(f"账户 {account_name} (bot_id: {account.bot_id}) 创建API调用Future: {echo}")

        # OneBot12标准API请求格式
        payload = {
            "action": endpoint,
            "params": params,
            "echo": echo
        }

        self.logger.debug(f"账户 {account_name} (bot_id: {account.bot_id}) 准备发送OneBot12 API请求: {payload}")

        try:
            await connection.send_str(json.dumps(payload))
            self.logger.debug(f"账户 {account_name} (bot_id: {account.bot_id}) 调用OneBot12 API: {endpoint}")
        except Exception as e:
            self.logger.error(f"账户 {account_name} (bot_id: {account.bot_id}) 发送API请求失败: {str(e)}")
            if echo in self._api_response_futures[account_name]:
                del self._api_response_futures[account_name][echo]
            raise

        try:
            self.logger.debug(f"账户 {account_name} (bot_id: {account.bot_id}) 开始等待Future: {echo}")
            raw_response = await asyncio.wait_for(future, timeout=self.default_timeout)
            self.logger.debug(f"账户 {account_name} (bot_id: {account.bot_id}) OneBot12 API响应: {raw_response}")

            # OneBot12标准响应处理（符合api-response.md规范）
            message_id = ""
            # 从data中提取message_id（OneBot12标准）
            if isinstance(raw_response.get("data"), dict):
                message_id = raw_response["data"].get("message_id", "")
            
            standardized_response = {
                "status": raw_response.get("status", "ok"),
                "retcode": raw_response.get("retcode", 0),
                "data": raw_response.get("data"),
                "message_id": message_id,  # 必须字段，没有则为空字符串
                "message": raw_response.get("message", ""),
                "onebot12_raw": raw_response  # 保存原始响应数据
            }

            # 如果请求中包含echo，原样返回
            if "echo" in params:
                standardized_response["echo"] = params["echo"]

            return standardized_response

        except asyncio.TimeoutError:
            self.logger.error(f"账户 {account_name} (bot_id: {account.bot_id}) API调用超时: {endpoint}")
            if not future.done():
                future.cancel()

            timeout_response = {
                "status": "failed",
                "retcode": 33001,
                "data": None,
                "message_id": "",  # 超时失败时为空字符串
                "message": f"账户 {account_name} (bot_id: {account.bot_id}) API调用超时: {endpoint}",
                "onebot12_raw": {}  # 保存原始响应（超时时为空）
            }

            if "echo" in params:
                timeout_response["echo"] = params["echo"]

            return timeout_response

        finally:
            async def delayed_cleanup():
                await asyncio.sleep(0.1)
                if account_name in self._api_response_futures and echo in self._api_response_futures[account_name]:
                    del self._api_response_futures[account_name][echo]
                    self.logger.debug(f"账户 {account_name} (bot_id: {account.bot_id}) 已删除API响应Future: {echo}")

            asyncio.create_task(delayed_cleanup())

    async def connect(self, account_name: str, retry_interval=None):
        """连接指定账户的OneBot12服务

        :param account_name: 账户名称
        :param retry_interval: 重试间隔
        """
        if account_name not in self.accounts:
            raise ValueError(f"账户 {account_name} 不存在")

        account = self.accounts[account_name]
        if account.mode != "client":
            return

        # 创建该账户的session
        if account_name not in self.sessions:
            self.sessions[account_name] = aiohttp.ClientSession()

        headers = {}
        if account.client_token:
            headers["Authorization"] = f"Bearer {account.client_token}"

        url = account.client_url
        retry_count = 0
        retry_interval = retry_interval or self.default_retry_interval

        while self._is_running:
            try:
                self.connections[account_name] = await self.sessions[account_name].ws_connect(url, headers=headers)
                self.logger.info(f"账户 {account_name} (bot_id: {account.bot_id}) 成功连接到OneBot12服务器: {url}")
                asyncio.create_task(self._listen(account_name))
                return
            except Exception as e:
                retry_count += 1
                self.logger.error(f"账户 {account_name} (bot_id: {account.bot_id}) 第 {retry_count} 次连接失败: {str(e)}")
                self.logger.info(f"账户 {account_name} (bot_id: {account.bot_id}) 将在 {retry_interval} 秒后重试...")
                await asyncio.sleep(retry_interval)

    async def _listen(self, account_name: str):
        """监听指定账户的WebSocket消息

        :param account_name: 账户名称
        """
        connection = self.connections.get(account_name)
        if not connection:
            return

        account = self.accounts.get(account_name)

        try:
            self.logger.debug(f"账户 {account_name} (bot_id: {account.bot_id}) 开始监听OneBot12 WebSocket消息")
            async for msg in connection:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    self.logger.debug(f"账户 {account_name} (bot_id: {account.bot_id}) 收到WebSocket消息: {msg.data[:100]}...")
                    asyncio.create_task(self._handle_message(msg.data, account_name))
                elif msg.type == aiohttp.WSMsgType.CLOSED:
                    self.logger.info(f"账户 {account_name} (bot_id: {account.bot_id}) WebSocket连接已关闭")
                    break
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    self.logger.error(f"账户 {account_name} (bot_id: {account.bot_id}) WebSocket错误: {connection.exception()}")
        except Exception as e:
            self.logger.error(f"账户 {account_name} (bot_id: {account.bot_id}) WebSocket监听异常: {str(e)}")
        finally:
            self.logger.debug(f"账户 {account_name} (bot_id: {account.bot_id}) 退出WebSocket监听")
            if account_name in self.connections:
                del self.connections[account_name]

            if self._is_running and account.enabled and account.mode == "client":
                self.logger.info(f"账户 {account_name} (bot_id: {account.bot_id}) 开始重连...")
                self.reconnect_tasks[account_name] = asyncio.create_task(self.connect(account_name))

    async def _handle_api_response(self, data: Dict, account_name: str):
        """处理API响应

        :param data: 响应数据
        :param account_name: 账户名称
        """
        echo = data.get("echo")
        account = self.accounts.get(account_name)
        self.logger.debug(f"账户 {account_name} (bot_id: {account.bot_id}) 收到OneBot12 API响应, echo: {echo}")

        if account_name not in self._api_response_futures:
            self.logger.warning(f"账户 {account_name} (bot_id: {account.bot_id}) 不存在响应Future字典")
            return

        future = self._api_response_futures[account_name].get(echo)

        if future:
            if not future.done():
                future.set_result(data)
            else:
                self.logger.warning(f"Future已经完成，无法设置结果: {echo}")
        else:
            self.logger.warning(f"账户 {account_name} (bot_id: {account.bot_id}) 未找到对应的Future: {echo}")

    async def _handle_message(self, raw_msg: str, account_name: str):
        """处理WebSocket消息

        :param raw_msg: 原始消息字符串
        :param account_name: 账户名称
        """
        try:
            data = json.loads(raw_msg)
            account = self.accounts.get(account_name)

            # API响应优先处理
            if "echo" in data:
                self.logger.debug(f"账户 {account_name} (bot_id: {account.bot_id}) 识别为OneBot12 API响应消息: {data.get('echo')}")
                await self._handle_api_response(data, account_name)
                return

            self.logger.debug(f"账户 {account_name} (bot_id: {account.bot_id}) 处理OneBot12事件: {data.get('type')}")

            # OneBot12事件直接提交，无需转换
            if hasattr(self.adapter, "emit") and data:
                # 确保事件包含账户信息
                if "self" not in data:
                    data["self"] = {}
                if not data.get("self", {}).get("user_id"):
                    data["self"]["user_id"] = account.bot_id
                    
                if "onebot12_raw_type" not in data and "type" in data:
                    data["onebot12_raw_type"] = data["type"]

                self.logger.debug(f"账户 {account_name} (bot_id: {account.bot_id}) 提交OneBot12事件: {json.dumps(data, ensure_ascii=False)}")
                await self.adapter.emit(data)

        except json.JSONDecodeError:
            self.logger.error(f"账户 {account_name} (bot_id: {account.bot_id}) JSON解析失败: {raw_msg}")
        except Exception as e:
            self.logger.error(f"账户 {account_name} (bot_id: {account.bot_id}) 消息处理异常: {str(e)}")

    async def _ws_handler(self, websocket: WebSocket, account_name: str = "default"):
        """WebSocket处理器

        :param websocket: WebSocket连接对象
        :param account_name: 账户名称
        """
        account = self.accounts.get(account_name)
        if account:
            self.logger.info(f"账户 {account_name} (bot_id: {account.bot_id}) 的OneBot12客户端已连接")
        else:
            self.logger.warning(f"账户 {account_name} 不存在")

        self.connections[account_name] = websocket

        try:
            while True:
                data = await websocket.receive_text()
                asyncio.create_task(self._handle_message(data, account_name))
        except WebSocketDisconnect:
            self.logger.info(f"账户 {account_name} (bot_id: {account.bot_id}) 的OneBot12客户端断开连接")
        except Exception as e:
            self.logger.error(f"账户 {account_name} (bot_id: {account.bot_id}) WebSocket处理异常: {str(e)}")
        finally:
            if account_name in self.connections:
                del self.connections[account_name]
    
    async def _auth_handler(self, websocket: WebSocket, account_name: str = "default"):
        """认证处理器

        :param websocket: WebSocket连接对象
        :param account_name: 账户名称
        :return: 是否认证成功
        """
        if account_name not in self.accounts:
            self.logger.warning(f"账户 {account_name} 不存在")
            await websocket.close(code=1008)
            return False

        account = self.accounts[account_name]
        if account.server_token:
            client_token = websocket.headers.get("Authorization", "").replace("Bearer ", "")
            if not client_token:
                query = dict(websocket.query_params)
                client_token = query.get("token", "")

            if client_token != account.server_token:
                self.logger.warning(f"账户 {account_name} (bot_id: {account.bot_id}) 客户端提供的Token无效")
                await websocket.close(code=1008)
                return False
        return True

    async def register_websocket(self):
        """为每个启用的账户注册WebSocket路由"""
        for account_name, account in self.accounts.items():
            if account.mode == "server" and account.enabled:
                path = account.server_path

                def make_ws_handler(account_name):
                    async def ws_handler(websocket):
                        await self._ws_handler(websocket, account_name)
                    return ws_handler

                def make_auth_handler(account_name):
                    async def auth_handler(websocket):
                        return await self._auth_handler(websocket, account_name)
                    return auth_handler

                router.register_websocket(
                    f"onebot12_{account_name}",
                    path,
                    make_ws_handler(account_name),
                    auth_handler=make_auth_handler(account_name)
                )
                self.logger.info(f"已注册账户 {account_name} (bot_id: {account.bot_id}) 的Server模式WebSocket路由: {path}")

    async def start(self):
        """启动OneBot12适配器"""
        self._is_running = True

        server_accounts = [name for name, acc in self.accounts.items() if acc.mode == "server" and acc.enabled]
        client_accounts = [name for name, acc in self.accounts.items() if acc.mode == "client" and acc.enabled]

        if server_accounts:
            self.logger.info(f"正在注册 {len(server_accounts)} 个Server模式账户的WebSocket路由")
            await self.register_websocket()

        if client_accounts:
            self.logger.info(f"正在启动 {len(client_accounts)} 个Client模式账户")
            for account_name in client_accounts:
                account = self.accounts[account_name]
                self.logger.info(f"启动Client模式账户: {account_name} (bot_id: {account.bot_id})")
                self.reconnect_tasks[account_name] = asyncio.create_task(self.connect(account_name))

        if not server_accounts and not client_accounts:
            self.logger.warning("没有启用任何账户")

        enabled_count = len(server_accounts) + len(client_accounts)
        self.logger.info(f"OneBot12适配器启动完成，共启动 {enabled_count} 个账户")

    async def shutdown(self):
        """关闭OneBot12适配器"""
        self._is_running = False

        # 取消所有重连任务
        for task in self.reconnect_tasks.values():
            if not task.done():
                task.cancel()
        self.reconnect_tasks.clear()

        # 关闭所有连接
        for account_name, connection in self.connections.items():
            account = self.accounts.get(account_name)
            try:
                if hasattr(connection, 'closed') and not connection.closed:
                    if account:
                        self.logger.debug(f"关闭账户 {account_name} (bot_id: {account.bot_id}) 的连接")
                    await connection.close()
            except Exception as e:
                if account:
                    self.logger.error(f"关闭账户 {account_name} (bot_id: {account.bot_id}) 连接失败: {str(e)}")
                else:
                    self.logger.error(f"关闭账户 {account_name} 连接失败: {str(e)}")
        self.connections.clear()

        # 关闭所有session
        for account_name, session in self.sessions.items():
            account = self.accounts.get(account_name)
            try:
                await session.close()
            except Exception as e:
                if account:
                    self.logger.error(f"关闭账户 {account_name} (bot_id: {account.bot_id}) session失败: {str(e)}")
                else:
                    self.logger.error(f"关闭账户 {account_name} session失败: {str(e)}")
        self.sessions.clear()

        self.logger.info("OneBot12适配器已关闭")