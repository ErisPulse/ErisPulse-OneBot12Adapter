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
    """OneBot12账户配置"""
    mode: str  # "server" or "client"
    server_path: Optional[str] = "/onebot12"
    server_token: Optional[str] = ""
    client_url: Optional[str] = "ws://127.0.0.1:3001"
    client_token: Optional[str] = ""
    enabled: bool = True
    name: str = ""
    # OneBot12特有配置
    platform: Optional[str] = "onebot12"  # 平台标识
    implementation: Optional[str] = ""     # 实现标识

class OneBot12Adapter(sdk.BaseAdapter):
    """OneBot V12 协议适配器"""
    
    class Send(sdk.BaseAdapter.Send):
        """消息发送类 - OneBot12标准"""
        
        def Text(self, text: str):
            return asyncio.create_task(
                self._adapter.call_api(
                    endpoint="send_message",
                    account_id=self._account_id,
                    detail_type=self._get_detail_type(),
                    user_id=self._target_id if self._target_type == "user" else None,
                    group_id=self._target_id if self._target_type == "group" else None,
                    content={"type": "text", "data": {"text": text}}
                )
            )
        
        def Image(self, file: Union[str, bytes], filename: str = "image.png"):
            data = {}
            if isinstance(file, bytes):
                # 处理二进制图片数据
                import base64
                data["file_base64"] = base64.b64encode(file).decode('utf-8')
                data["file_name"] = filename
            else:
                data["file_id"] = file
            
            return asyncio.create_task(
                self._adapter.call_api(
                    endpoint="send_message",
                    account_id=self._account_id,
                    detail_type=self._get_detail_type(),
                    user_id=self._target_id if self._target_type == "user" else None,
                    group_id=self._target_id if self._target_type == "group" else None,
                    content={"type": "image", "data": data}
                )
            )
        
        def Audio(self, file: Union[str, bytes], filename: str = "audio.ogg"):
            data = {}
            if isinstance(file, bytes):
                import base64
                data["file_base64"] = base64.b64encode(file).decode('utf-8')
                data["file_name"] = filename
            else:
                data["file_id"] = file
            
            return asyncio.create_task(
                self._adapter.call_api(
                    endpoint="send_message",
                    account_id=self._account_id,
                    detail_type=self._get_detail_type(),
                    user_id=self._target_id if self._target_type == "user" else None,
                    group_id=self._target_id if self._target_type == "group" else None,
                    content={"type": "audio", "data": data}
                )
            )
        
        def Video(self, file: Union[str, bytes], filename: str = "video.mp4"):
            data = {}
            if isinstance(file, bytes):
                import base64
                data["file_base64"] = base64.b64encode(file).decode('utf-8')
                data["file_name"] = filename
            else:
                data["file_id"] = file
            
            return asyncio.create_task(
                self._adapter.call_api(
                    endpoint="send_message",
                    account_id=self._account_id,
                    detail_type=self._get_detail_type(),
                    user_id=self._target_id if self._target_type == "user" else None,
                    group_id=self._target_id if self._target_type == "group" else None,
                    content={"type": "video", "data": data}
                )
            )
        
        def Mention(self, user_id: Union[str, int], user_name: str = None):
            # OneBot12的mention应该作为消息段处理
            return self._send_complex_message([
                {"type": "mention", "data": {"user_id": str(user_id), "user_name": user_name or ""}}
            ])
        
        def Reply(self, message_id: Union[str, int], content: str = None):
            # OneBot12的回复消息
            message_segments = [
                {"type": "reply", "data": {"message_id": str(message_id)}}
            ]
            if content:
                message_segments.append({"type": "text", "data": {"text": content}})
            
            return self._send_complex_message(message_segments)
        
        def Location(self, latitude: float, longitude: float, title: str = "", content: str = ""):
            data = {
                "latitude": latitude,
                "longitude": longitude
            }
            if title:
                data["title"] = title
            if content:
                data["content"] = content
            
            return asyncio.create_task(
                self._adapter.call_api(
                    endpoint="send_message",
                    account_id=self._account_id,
                    detail_type=self._get_detail_type(),
                    user_id=self._target_id if self._target_type == "user" else None,
                    group_id=self._target_id if self._target_type == "group" else None,
                    content={"type": "location", "data": data}
                )
            )
        
        def Sticker(self, file_id: str):
            """发送表情包/贴纸"""
            return asyncio.create_task(
                self._adapter.call_api(
                    endpoint="send_message",
                    account_id=self._account_id,
                    detail_type=self._get_detail_type(),
                    user_id=self._target_id if self._target_type == "user" else None,
                    group_id=self._target_id if self._target_type == "group" else None,
                    content={"type": "sticker", "data": {"file_id": file_id}}
                )
            )
        
        def Raw(self, message_segments: List[Dict]):
            """发送原始OneBot12消息段列表"""
            return self._send_complex_message(message_segments)
        
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
        
        self.logger.info(f"OneBot12适配器初始化完成，共加载 {len(self.accounts)} 个账户")

    def _load_account_configs(self) -> Dict[str, OneBot12AccountConfig]:
        """加载账户配置"""
        accounts = {}
        
        # 检查新格式的账户配置
        account_configs = self.sdk.config.getConfig("OneBotv12_Adapter.accounts", {})
        
        if not account_configs:
            # 创建默认账户配置
            self.logger.info("未找到配置文件，创建默认账户配置")
            default_config = {
                "default": {
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
            merged_config = {
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
        
        return accounts
    
    async def call_api(self, endpoint: str, account_id: str = None, **params):
        """调用OneBot12 API"""
        # 确定使用的账户ID
        if account_id is None:
            if not self.accounts:
                raise ValueError("没有配置任何OneBot12账户")
            account_id = next(iter(self.accounts.keys()))
        
        if account_id not in self.accounts:
            raise ValueError(f"账户 {account_id} 不存在")
        
        account = self.accounts[account_id]
        if not account.enabled:
            raise ValueError(f"账户 {account_id} 已禁用")
        
        connection = self.connections.get(account_id)
        if not connection:
            raise ConnectionError(f"账户 {account_id} 尚未连接到OneBot12")
        
        if connection.closed:
            raise ConnectionError(f"账户 {account_id} 的WebSocket连接已关闭")

        # 确保该账户的响应Future字典存在
        if account_id not in self._api_response_futures:
            self._api_response_futures[account_id] = {}

        echo = str(hash(str(params + (account_id, endpoint))))
        future = asyncio.get_event_loop().create_future()
        self._api_response_futures[account_id][echo] = future
        self.logger.debug(f"账户 {account_id} 创建API调用Future: {echo}")

        # OneBot12标准API请求格式
        payload = {
            "action": endpoint,
            "params": params,
            "echo": echo
        }

        self.logger.debug(f"账户 {account_id} 准备发送OneBot12 API请求: {payload}")
        
        try:
            await connection.send_str(json.dumps(payload))
            self.logger.debug(f"账户 {account_id} 调用OneBot12 API: {endpoint}")
        except Exception as e:
            self.logger.error(f"账户 {account_id} 发送API请求失败: {str(e)}")
            if echo in self._api_response_futures[account_id]:
                del self._api_response_futures[account_id][echo]
            raise

        try:
            self.logger.debug(f"账户 {account_id} 开始等待Future: {echo}")
            raw_response = await asyncio.wait_for(future, timeout=self.default_timeout)
            self.logger.debug(f"账户 {account_id} OneBot12 API响应: {raw_response}")

            # OneBot12标准响应处理
            standardized_response = {
                "status": raw_response.get("status", "ok"),
                "retcode": raw_response.get("retcode", 0),
                "data": raw_response.get("data"),
                "message": raw_response.get("message", ""),
                "self": {"user_id": account_id}
            }

            if "message_id" in raw_response:
                standardized_response["message_id"] = raw_response["message_id"]

            if "echo" in params:
                standardized_response["echo"] = params["echo"]

            return standardized_response

        except asyncio.TimeoutError:
            self.logger.error(f"账户 {account_id} API调用超时: {endpoint}")
            if not future.done():
                future.cancel()
            
            timeout_response = {
                "status": "failed",
                "retcode": 33001,
                "data": None,
                "message": f"账户 {account_id} API调用超时: {endpoint}",
                "self": {"user_id": account_id}
            }
            
            if "echo" in params:
                timeout_response["echo"] = params["echo"]
                
            return timeout_response
            
        finally:
            async def delayed_cleanup():
                await asyncio.sleep(0.1)
                if account_id in self._api_response_futures and echo in self._api_response_futures[account_id]:
                    del self._api_response_futures[account_id][echo]
                    self.logger.debug(f"账户 {account_id} 已删除API响应Future: {echo}")
            
            asyncio.create_task(delayed_cleanup())

    async def connect(self, account_id: str, retry_interval=None):
        """连接指定账户的OneBot12服务"""
        if account_id not in self.accounts:
            raise ValueError(f"账户 {account_id} 不存在")
        
        account = self.accounts[account_id]
        if account.mode != "client":
            return

        # 创建该账户的session
        if account_id not in self.sessions:
            self.sessions[account_id] = aiohttp.ClientSession()
        
        headers = {}
        if account.client_token:
            headers["Authorization"] = f"Bearer {account.client_token}"

        url = account.client_url
        retry_count = 0
        retry_interval = retry_interval or self.default_retry_interval

        while self._is_running:
            try:
                self.connections[account_id] = await self.sessions[account_id].ws_connect(url, headers=headers)
                self.logger.info(f"账户 {account_id} 成功连接到OneBot12服务器: {url}")
                asyncio.create_task(self._listen(account_id))
                return
            except Exception as e:
                retry_count += 1
                self.logger.error(f"账户 {account_id} 第 {retry_count} 次连接失败: {str(e)}")
                self.logger.info(f"账户 {account_id} 将在 {retry_interval} 秒后重试...")
                await asyncio.sleep(retry_interval)

    async def _listen(self, account_id: str):
        """监听指定账户的WebSocket消息"""
        connection = self.connections.get(account_id)
        if not connection:
            return
            
        try:
            self.logger.debug(f"账户 {account_id} 开始监听OneBot12 WebSocket消息")
            async for msg in connection:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    self.logger.debug(f"账户 {account_id} 收到WebSocket消息: {msg.data[:100]}...")
                    asyncio.create_task(self._handle_message(msg.data, account_id))
                elif msg.type == aiohttp.WSMsgType.CLOSED:
                    self.logger.info(f"账户 {account_id} WebSocket连接已关闭")
                    break
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    self.logger.error(f"账户 {account_id} WebSocket错误: {connection.exception()}")
        except Exception as e:
            self.logger.error(f"账户 {account_id} WebSocket监听异常: {str(e)}")
        finally:
            self.logger.debug(f"账户 {account_id} 退出WebSocket监听")
            if account_id in self.connections:
                del self.connections[account_id]
            
            if self._is_running and self.accounts[account_id].enabled and self.accounts[account_id].mode == "client":
                self.logger.info(f"账户 {account_id} 开始重连...")
                self.reconnect_tasks[account_id] = asyncio.create_task(self.connect(account_id))

    async def _handle_api_response(self, data: Dict, account_id: str):
        """处理API响应"""
        echo = data.get("echo")
        self.logger.debug(f"账户 {account_id} 收到OneBot12 API响应, echo: {echo}")
        
        if account_id not in self._api_response_futures:
            self.logger.warning(f"账户 {account_id} 不存在响应Future字典")
            return
            
        future = self._api_response_futures[account_id].get(echo)
        
        if future:
            if not future.done():
                future.set_result(data)
            else:
                self.logger.warning(f"Future已经完成，无法设置结果: {echo}")
        else:
            self.logger.warning(f"账户 {account_id} 未找到对应的Future: {echo}")

    async def _handle_message(self, raw_msg: str, account_id: str):
        """处理WebSocket消息"""
        try:
            data = json.loads(raw_msg)
            
            # API响应优先处理
            if "echo" in data:
                self.logger.debug(f"账户 {account_id} 识别为OneBot12 API响应消息: {data.get('echo')}")
                await self._handle_api_response(data, account_id)
                return
            
            self.logger.debug(f"账户 {account_id} 处理OneBot12事件: {data.get('type')}")
            
            # OneBot12事件直接提交，无需转换
            if hasattr(self.adapter, "emit") and data:
                # 确保事件包含账户信息
                if "self" not in data:
                    data["self"] = {}
                if not data.get("self", {}).get("user_id"):
                    data["self"]["user_id"] = account_id
                
                self.logger.debug(f"账户 {account_id} 提交OneBot12事件: {json.dumps(data, ensure_ascii=False)}")
                await self.adapter.emit(data)

        except json.JSONDecodeError:
            self.logger.error(f"账户 {account_id} JSON解析失败: {raw_msg}")
        except Exception as e:
            self.logger.error(f"账户 {account_id} 消息处理异常: {str(e)}")

    async def _ws_handler(self, websocket: WebSocket, account_id: str = "default"):
        """WebSocket处理器"""
        self.connections[account_id] = websocket
        self.logger.info(f"账户 {account_id} 的OneBot12客户端已连接")

        try:
            while True:
                data = await websocket.receive_text()
                asyncio.create_task(self._handle_message(data, account_id))
        except WebSocketDisconnect:
            self.logger.info(f"账户 {account_id} 的OneBot12客户端断开连接")
        except Exception as e:
            self.logger.error(f"账户 {account_id} WebSocket处理异常: {str(e)}")
        finally:
            if account_id in self.connections:
                del self.connections[account_id]
    
    async def _auth_handler(self, websocket: WebSocket, account_id: str = "default"):
        """认证处理器"""
        if account_id not in self.accounts:
            self.logger.warning(f"账户 {account_id} 不存在")
            await websocket.close(code=1008)
            return False
            
        account = self.accounts[account_id]
        if account.server_token:
            client_token = websocket.headers.get("Authorization", "").replace("Bearer ", "")
            if not client_token:
                query = dict(websocket.query_params)
                client_token = query.get("token", "")

            if client_token != account.server_token:
                self.logger.warning(f"账户 {account_id} 客户端提供的Token无效")
                await websocket.close(code=1008)
                return False
        return True

    async def register_websocket(self):
        """注册WebSocket路由"""
        # 注册所有server模式的账户
        for account_id, account in self.accounts.items():
            if account.mode == "server" and account.enabled:
                path = account.server_path
                
                def make_ws_handler(account_id):
                    async def ws_handler(websocket):
                        await self._ws_handler(websocket, account_id)
                    return ws_handler
                
                def make_auth_handler(account_id):
                    async def auth_handler(websocket):
                        return await self._auth_handler(websocket, account_id)
                    return auth_handler
                
                router.register_websocket(
                    f"onebot12_{account_id}",
                    path,
                    make_ws_handler(account_id),
                    auth_handler=make_auth_handler(account_id)
                )
                self.logger.info(f"已注册账户 {account_id} 的Server模式WebSocket路由: {path}")

    async def start(self):
        """启动适配器"""
        self._is_running = True
        
        server_accounts = [aid for aid, acc in self.accounts.items() if acc.mode == "server" and acc.enabled]
        client_accounts = [aid for aid, acc in self.accounts.items() if acc.mode == "client" and acc.enabled]
        
        if server_accounts:
            self.logger.info(f"正在注册 {len(server_accounts)} 个Server模式账户的WebSocket路由")
            await self.register_websocket()
        
        if client_accounts:
            self.logger.info(f"正在启动 {len(client_accounts)} 个Client模式账户")
            for account_id in client_accounts:
                self.reconnect_tasks[account_id] = asyncio.create_task(self.connect(account_id))
        
        if not server_accounts and not client_accounts:
            self.logger.warning("没有启用任何账户")
        
        self.logger.info("OneBot12适配器启动完成")

    async def shutdown(self):
        """关闭适配器"""
        self._is_running = False
        
        # 取消所有重连任务
        for task in self.reconnect_tasks.values():
            if not task.done():
                task.cancel()
        self.reconnect_tasks.clear()
        
        # 关闭所有连接
        for account_id, connection in self.connections.items():
            try:
                if hasattr(connection, 'closed') and not connection.closed:
                    await connection.close()
            except Exception as e:
                self.logger.error(f"关闭账户 {account_id} 连接失败: {str(e)}")
        self.connections.clear()
        
        # 关闭所有session
        for account_id, session in self.sessions.items():
            try:
                await session.close()
            except Exception as e:
                self.logger.error(f"关闭账户 {account_id} session失败: {str(e)}")
        self.sessions.clear()
        
        self.logger.info("OneBot12适配器已关闭")