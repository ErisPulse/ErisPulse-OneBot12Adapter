# ErisPulse OneBot12 适配器

基于 [ErisPulse](https://github.com/ErisPulse/ErisPulse/) 框架的 OneBot V12 基线协议适配器，支持多账号、Server/Client 双模式运行。

## 安装

```bash
epsdk install OneBot12Adapter
```

## 配置

在 `config/config.toml` 中添加：

```toml
[OneBotv12_Adapter.accounts.main]
bot_id = "机器人ID"
mode = "server"
server_path = "/onebot12"
server_token = ""
enabled = true

# Client 模式示例
[OneBotv12_Adapter.accounts.backup]
bot_id = "另一个机器人ID"
mode = "client"
client_url = "ws://127.0.0.1:3002"
client_token = ""
enabled = true
```

### 配置字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `bot_id` | string | 是 | 机器人ID，用于SDK路由 |
| `mode` | string | 否 | 运行模式：`server`（被动）或 `client`（主动），默认 `server` |
| `server_path` | string | 否 | Server 模式 WS 路径，默认 `/onebot12` |
| `server_token` | string | 否 | Server 模式认证 Token |
| `client_url` | string | 否 | Client 模式 WS 地址，默认 `ws://127.0.0.1:3001` |
| `client_token` | string | 否 | Client 模式认证 Token |
| `enabled` | bool | 否 | 是否启用（默认 true） |
| `platform` | string | 否 | 平台标识，默认 `onebot12` |
| `implementation` | string | 否 | 实现标识（如 `go-cqhttp`） |

## 快速开始

```python
from ErisPulse import sdk
from ErisPulse.Core.Event import command, message

@command("hello")
async def hello_handler(event):
    await event.reply("Hello from OneBot12!")

async def main():
    await sdk.run(keep_running=True)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

## 消息发送

```python
onebot12 = sdk.adapter.get("onebot12")

# 文本消息
await onebot12.Send.To("user", "123456").Text("Hello!")
await onebot12.Send.To("group", "789012").Text("群消息")

# 媒体消息
await onebot12.Send.To("user", "123456").Image("file_id_or_url")
await onebot12.Send.To("user", "123456").Video("file_id_or_url")
await onebot12.Send.To("user", "123456").Audio("file_id_or_url")

# 发送 bytes
with open("image.png", "rb") as f:
    await onebot12.Send.To("user", "123456").Image(f.read())

# 位置
await onebot12.Send.To("group", "789012").Location(39.9042, 116.4074, title="北京")
```

### 链式修饰

```python
# @用户
await onebot12.Send.To("group", "789012").At("123456").Text("你好！")

# @全体
await onebot12.Send.To("group", "789012").AtAll().Text("通知！")

# 回复消息
await onebot12.Send.To("group", "789012").Reply("msg_id").Text("回复内容")

# 组合使用
await onebot12.Send.To("group", "789012").Reply("msg_id").At("123456").Text("回复并@")
```

### 指定账户发送

```python
# 使用 Using 指定账户
await onebot12.Send.Using("backup").To("user", "123456").Text("来自备用账户")
```

### 消息操作

```python
# 撤回
await onebot12.Send.To("group", "789012").Recall("message_id")

# 编辑
await onebot12.Send.To("group", "789012").Edit("message_id", "新内容")

# 原始 OB12 消息段
await onebot12.Send.To("group", "789012").Raw_ob12([
    {"type": "text", "data": {"text": "你好"}},
    {"type": "image", "data": {"file_id": "xxx"}}
])
```

## 运行模式

### Server 模式（默认）

启动 WS 服务器等待 OneBot12 实现端连接。适用于多客户端连接同一服务端的场景。

### Client 模式

主动连接 OneBot12 实现端。支持自动重连（间隔 30 秒）。

## 事件处理

OneBot12 适配器直接 pass-through 标准格式事件，无需转换。使用 ErisPulse 标准事件处理器：

```python
from ErisPulse.Core.Event import message, notice, request, meta

@message.on_message()
async def handle_message(event):
    text = event.get_text()
    user_id = event.get_user_id()
    group_id = event.get_group_id()
    await event.reply(f"收到: {text}")

@notice.on_group_increase()
async def handle_member_increase(event):
    group_id = event.get_group_id()
    user_id = event.get_user_id()
    await event.reply(f"欢迎 {user_id} 加入群!")

@request.on_friend_request()
async def handle_friend_request(event):
    user_id = event.get_user_id()
    comment = event.get_comment()
```

### 事件扩展字段

所有事件自动添加 `onebot12_raw_type` 字段保留原始事件类型。

## API 调用

```python
# 直接 API 调用
resp = await onebot12.call_api(
    "get_user_info",
    _account_id="main",
    user_id="123456"
)

# 获取自身信息
info = await onebot12.call_api("get_self_info", _account_id="main")
```

### 响应格式

```python
# 成功
{"status": "ok", "retcode": 0, "data": {...}, "message_id": "xxx", "message": ""}

# 失败
{"status": "failed", "retcode": 10003, "data": None, "message_id": "", "message": "错误描述"}
```

## 参考链接

- [ErisPulse 主库](https://github.com/ErisPulse/ErisPulse/)
- [OneBot V12 协议文档](https://12.onebot.dev/)
