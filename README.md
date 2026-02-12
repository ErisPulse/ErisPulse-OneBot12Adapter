# OneBot12Adapter 模块文档

## 简介

OneBot12Adapter 是基于 [ErisPulse](https://github.com/ErisPulse/ErisPulse/) 架构开发的 **OneBot V12 协议适配器模块**。作为ErisPulse框架的基线协议适配器，它提供完全符合OneBot12标准的事件处理机制、连接管理功能，并支持Server和Client两种运行模式。

---

## 特性

- **多账户支持** - 支持同时配置和运行多个OneBot12账户
- **双运行模式** - 支持Server（服务端）和Client（客户端）模式
- **异步处理** - 全异步设计，支持高并发操作
- **自动重连** - 网络异常时自动重连机制
- **标准化响应** - 统一的API响应格式
- **大小写不敏感** - 所有发送方法支持大小写不敏感调用
- **智能错误提示** - 不支持的方法调用会返回友好的文本提示

---

## 安装与配置

### 基本安装

将适配器模块放置在ErisPulse的适配器目录中，并在配置中启用：

```toml
[adapters]
onebot12 = "OneBot12Adapter"
```

### 多账户配置

OneBot12适配器采用多账户配置结构：

```toml
# 主账户配置
[OneBotv12_Adapter.accounts.main]
mode = "server"
server_path = "/onebot12"
server_token = "your_main_token"
enabled = true
platform = "onebot12"
implementation = "go-cqhttp"

# 备用账户配置  
[OneBotv12_Adapter.accounts.backup]
mode = "client"
client_url = "ws://127.0.0.1:3002"
client_token = "your_backup_token"
enabled = true
platform = "onebot12"
implementation = "shinonome"

# 测试账户配置
[OneBotv12_Adapter.accounts.test]
mode = "client"
client_url = "ws://127.0.0.1:3003"
enabled = false
```

### 默认账户配置

如果没有配置文件，适配器会自动创建默认配置：

```toml
[OneBotv12_Adapter.accounts.default]
mode = "server"
server_path = "/onebot12"
server_token = ""
enabled = true
platform = "onebot12"
```

### 配置项说明

每个账户独立配置以下选项：

- `mode`: 运行模式，可选 "server"（服务端）或 "client"（客户端）
- `server_path`: Server模式下的WebSocket路径
- `server_token`: Server模式下的认证Token（可选）
- `client_url`: Client模式下要连接的WebSocket地址
- `client_token`: Client模式下的认证Token（可选）
- `enabled`: 是否启用该账户（true/false）
- `platform`: 平台标识，默认为 "onebot12"
- `implementation`: 实现标识，如 "go-cqhttp"（可选）

---

## 使用方法

### 基础用法

```python
from ErisPulse.Core import adapter

# 获取OneBot12适配器实例
onebot12 = adapter.get("onebot12")

# 发送文本消息
await onebot12.Send.To("group", 123456).Text("Hello World!")

# 发送图片消息
await onebot12.Send.To("user", 789012).Image("http://example.com/image.jpg")

# 发送@消息
await onebot12.Send.To("group", 123456).Mention(789012, "用户名")
```

---

## 消息发送示例（DSL 链式风格）

### 基础消息类型

#### 文本消息
```python
await onebot12.Send.To("user", 123456).Text("Hello World!")
```

#### 图片消息
```python
# 支持URL或二进制数据
await onebot12.Send.To("user", 123456).Image("http://example.com/image.jpg")

# 支持二进制数据
with open("local_image.png", "rb") as f:
    image_data = f.read()
    await onebot12.Send.To("user", 123456).Image(image_data)
```

#### 音频消息
```python
await onebot12.Send.To("user", 123456).Audio("http://example.com/audio.ogg")
```

#### 语音消息（兼容OneBot11）
```python
# Voice 是 Audio 的别名，两者完全等价
await onebot12.Send.To("user", 123456).Voice("http://example.com/voice.ogg")
```

#### 视频消息
```python
await onebot12.Send.To("user", 123456).Video("http://example.com/video.mp4")
```

### 链式修饰方法

#### @用户
```python
# @单个用户
await onebot12.Send.To("group", 123456).At(789012).Text("你好！")

# @多个用户
await onebot12.Send.To("group", 123456).At(789012).At(789013).Text("大家你好！")

# @全体成员
await onebot12.Send.To("group", 123456).AtAll().Text("全体通知！")

# 大小写不敏感调用
await onebot12.Send.To("group", 123456).at(789012).atAll().text("全体通知！")
```

#### 回复消息
```python
# 回复某条消息
await onebot12.Send.To("group", 123456).Reply("msg_id_123").Text("这是回复内容")

# 组合使用@和回复
await onebot12.Send.To("group", 123456).Reply("msg_id_123").At(789012).Text("回复并@你")
```

### 原始消息发送

#### 发送OneBot12原始格式消息
```python
# 发送单个消息段
await onebot12.Send.To("group", 123456).Raw_ob12({
    "type": "text",
    "data": {"text": "Hello"}
})

# 发送多个消息段
await onebot12.Send.To("group", 123456).Raw_ob12([
    {"type": "text", "data": {"text": "你好"}},
    {"type": "image", "data": {"file_id": "image_id"}}
])

# 原始消息配合链式修饰符
await onebot12.Send.To("group", 123456).Reply("msg_id_123").At(789012).Raw_ob12([
    {"type": "text", "data": {"text": "这是原始消息"}}
])
```

### 交互消息

#### 表情包/贴纸
```python
await onebot12.Send.To("user", 123456).Sticker("sticker_id_456")
```

#### 位置消息
```python
await onebot12.Send.To("group", 123456).Location(
    latitude=39.9042, 
    longitude=116.4074, 
    title="北京市", 
    content="中华人民共和国首都"
)
```

### 复合消息

#### 发送原始消息段
```python
message_segments = [
    {"type": "text", "data": {"text": "你好"}},
    {"type": "mention", "data": {"user_id": "123456", "user_name": "用户名"}},
    {"type": "image", "data": {"file_id": "image_id"}}
]
await onebot12.Send.To("group", 123456).Raw(message_segments)
```

#### 批量发送
```python
targets = ["user1", "user2", "user3"]
await onebot12.Send.To("user", targets).Batch(["消息1", "消息2", "消息3"])
```

### 消息管理

#### 撤回消息
```python
await onebot12.Send.To("group", 123456).Recall("message_id_123")
```

#### 编辑消息
```python
# 编辑为文本
await onebot12.Send.To("group", 123456).Edit("message_id_123", "修改后的内容")

# 编辑为复合消息
new_content = [
    {"type": "text", "data": {"text": "修改后的内容"}},
    {"type": "image", "data": {"file_id": "new_image_id"}}
]
await onebot12.Send.To("group", 123456).Edit("message_id_123", new_content)
```

### 链式修饰方法（支持链式调用）

| 方法名 | 参数说明 | 返回值 | 用途 |
|--------|----------|--------|------|
| `.At(user_id: str/int)` | @用户ID | `self` | 群聊@功能（可多次调用） |
| `.AtAll()` | @全体成员 | `self` | 群聊@全体功能 |
| `.Reply(message_id: str/int)` | 回复消息ID | `self` | 消息回复功能 |

> **链式调用示例**：`Send.To("group", 123456).At(789).Reply("msg123").Text("文本")`

### 方法名映射表

所有方法支持大小写不敏感调用，适配器会自动映射到标准方法名：

| 小写方法名 | 标准方法名 |
|-----------|-----------|
| text | Text |
| image | Image |
| audio | Audio |
| voice | Audio |
| video | Video |
| location | Location |
| sticker | Sticker |
| recall | Recall |
| edit | Edit |
| batch | Batch |
| raw_ob12 | Raw_ob12 |
| at | At |
| atall | AtAll |
| reply | Reply |

---

## API 调用方式

### 多账户消息发送

```python
# 使用指定账户发送消息
await onebot12.Send.To("group", 123456).Account("main").Text("来自主账户的消息")
await onebot12.Send.To("group", 123456).Account("backup").Text("来自备用账户的消息")

# 使用默认账户发送（第一个启用的账户）
await onebot12.Send.To("group", 123456).Text("来自默认账户的消息")
```

### 直接API调用

```python
# 发送消息
response = await onebot12.call_api(
    "send_message",
    account_id="main",
    detail_type="group",
    group_id=123456,
    content=[{"type": "text", "data": {"text": "Hello"}}]
)

# 获取自身信息
self_info = await onebot12.call_api("get_self_info", account_id="main")

# 获取用户信息
user_info = await onebot12.call_api(
    "get_user_info", 
    account_id="main",
    user_id="user123"
)

# 获取群组信息
group_info = await onebot12.call_api(
    "get_group_info",
    account_id="main", 
    group_id="group456"
)
```

---

## 事件处理

OneBot12适配器支持标准的事件监听方式：

```python
# 监听消息事件
@sdk.adapter.OneBot12.on("message")
async def handle_message(event):
    if event["detail_type"] == "private":
        print(f"收到私聊消息: {event['alt_message']}")
    elif event["detail_type"] == "group":
        print(f"收到群聊消息: {event['alt_message']}")

# 监听通知事件
@sdk.adapter.OneBot12.on("notice")
async def handle_notice(event):
    if event["detail_type"] == "group_member_increase":
        print(f"群成员增加: {event['user_id']} 加入了 {event['group_id']}")
    elif event["detail_type"] == "group_member_decrease":
        print(f"群成员减少: {event['user_id']} 离开了 {event['group_id']}")

# 监听请求事件
@sdk.adapter.OneBot12.on("request")
async def handle_request(event):
    if event["detail_type"] == "friend":
        print(f"收到好友请求: {event['user_id']}")
    elif event["detail_type"] == "group":
        print(f"收到群邀请: {event['group_id']}")

# 监听元事件
@sdk.adapter.OneBot12.on("meta_event")
async def handle_meta_event(event):
    if event["detail_type"] == "lifecycle":
        print(f"生命周期事件: {event['sub_type']}")
    elif event["detail_type"] == "heartbeat":
        print(f"心跳事件: 间隔 {event['interval']}ms")
```

### 事件数据结构

OneBot12适配器直接处理标准格式的OneBot12事件，无需转换。每个事件都会包含 `onebot12_raw_type` 字段，保留原始事件类型：

```python
# 私聊消息事件示例
{
    "id": "event-uuid",
    "type": "message",
    "onebot12_raw_type": "message",  # 原始事件类型
    "detail_type": "private", 
    "self": {"user_id": "bot-id"},
    "user_id": "user-id",
    "message": [{"type": "text", "data": {"text": "Hello"}}],
    "alt_message": "Hello",
    "time": 1234567890
}

# 群聊消息事件示例
{
    "id": "event-uuid",
    "type": "message",
    "onebot12_raw_type": "message",  # 原始事件类型
    "detail_type": "group",
    "self": {"user_id": "bot-id"},
    "user_id": "user-id", 
    "group_id": "group-id",
    "message": [{"type": "text", "data": {"text": "Hello group"}}],
    "alt_message": "Hello group",
    "time": 1234567890
}
```

---

## 运行模式说明

### 多账户运行模式

OneBot12适配器支持同时运行多个账户，每个账户可以独立配置为Server或Client模式：

```python
# 查看所有账户
accounts = onebot12.accounts
print(f"已配置账户: {list(accounts.keys())}")

# 检查特定账户状态
if "test" in accounts:
    test_account = accounts["test"]
    print(f"测试账户模式: {test_account.mode}, 启用状态: {test_account.enabled}")
```

### Server 模式（作为服务端监听连接）

- 启动一个 WebSocket 服务器等待 OneBot12 客户端连接
- 适用于部署多个 bot 客户端连接至同一服务端的场景
- 每个Server账户会注册独立的WebSocket路由路径

### Client 模式（主动连接 OneBot12）

- 主动连接到 OneBot12 服务端
- 更适合单个 bot 实例直接连接的情况
- 支持自动重连机制

---

## API响应标准

适配器遵循 ErisPulse 标准化返回规范：

```python
# 成功响应
{
    "status": "ok",              # 必须：执行状态
    "retcode": 0,                # 必须：返回码（0表示成功）
    "data": {                     # 必须：响应数据
        "message_id": "123456",
        "time": 1632847927.599013
    },
    "message_id": "123456",       # 必须：消息ID（无则为空字符串）
    "message": "",                # 必须：错误信息（成功时为空）
    "echo": "1234",               # 可选：原样返回请求中的echo
    "onebot12_raw": {...}        # 可选：原始响应数据
}

# 失败响应
{
    "status": "failed",           # 必须：执行状态
    "retcode": 10003,            # 必须：返回码（非0表示失败）
    "data": None,                # 必须：失败时为null
    "message_id": "",            # 必须：失败时为空字符串
    "message": "缺少必要参数",    # 必须：错误描述
    "echo": "1234",              # 可选：原样返回请求中的echo
    "onebot12_raw": {...}        # 可选：原始响应数据
}
```

---

## 管理接口

```python
# 获取所有账户信息
accounts = onebot12.accounts

# 检查账户连接状态
connection_status = {
    account_id: connection is not None and not connection.closed
    for account_id, connection in onebot12.connections.items()
}
print(f"账户连接状态: {connection_status}")

# 动态启用/禁用账户（需要重启适配器）
onebot12.accounts["test"].enabled = False
```

---

## 错误处理

适配器提供完善的错误处理机制：

1. **网络连接异常自动重连** - 支持每个账户独立重连，间隔30秒
2. **API调用超时处理** - 固定30秒超时机制
3. **消息发送失败重试** - 最多3次自动重试
4. **标准化错误响应** - 统一的错误格式和状态码
5. **不支持的调用提示** - 调用不存在的方法会返回友好的文本提示

---

## 注意事项

1. 生产环境建议启用 Token 认证以保证安全性
2. 对于二进制内容（如图片、音频等），支持直接传入 bytes 数据
3. 批量发送时建议适当控制并发数量，避免API限制
4. 长时间运行的机器人建议监控连接状态，确保服务可用性
5. 推荐使用标准的大驼峰命名（如 `.Text()`），但也支持小写形式
6. 利用 `onebot12_raw_type` 字段进行事件追溯和调试

---

## 参考链接

- [ErisPulse 主库](https://github.com/ErisPulse/ErisPulse/)
- [OneBot V12 协议文档](https://12.onebot.dev/)
- [平台特性文档](./platform-features.md)
