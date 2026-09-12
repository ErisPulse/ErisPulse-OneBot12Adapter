"""
OneBot12 适配器 i18n 翻译键声明

覆盖 5 种语言：zh-CN / zh-TW / en / ja / ru
"""

from ErisPulse.Core.Bases import BaseI18n, I18nKey


class OneBot12I18n(BaseI18n):
    """OneBot12 适配器翻译键声明"""

    mode: I18nKey = I18nKey(
        default="Connection mode: server (passive) or client (active)",
        zh_CN="连接模式: server(被动) 或 client(主动)",
        zh_TW="連線模式: server(被動) 或 client(主動)",
        en="Connection mode: server (passive) or client (active)",
        ja="接続モード: server(パッシブ) または client(アクティブ)",
        ru="Режим подключения: server (пассивный) или client (активный)",
    )

    mode_server: I18nKey = I18nKey(
        default="Server",
        zh_CN="Server",
        zh_TW="Server",
        en="Server",
        ja="Server",
        ru="Server",
    )

    mode_client: I18nKey = I18nKey(
        default="Client",
        zh_CN="Client",
        zh_TW="Client",
        en="Client",
        ja="Client",
        ru="Client",
    )

    server_path: I18nKey = I18nKey(
        default="Server mode WebSocket path",
        zh_CN="Server模式 WebSocket 路径",
        zh_TW="Server模式 WebSocket 路徑",
        en="Server mode WebSocket path",
        ja="Serverモード WebSocket パス",
        ru="Путь WebSocket в режиме server",
    )

    server_token: I18nKey = I18nKey(
        default="Server mode authentication token",
        zh_CN="Server模式认证Token",
        zh_TW="Server模式認證Token",
        en="Server mode authentication token",
        ja="Serverモード認証トークン",
        ru="Токен аутентификации в режиме server",
    )

    client_url: I18nKey = I18nKey(
        default="Client mode WebSocket URL",
        zh_CN="Client模式 WebSocket 地址",
        zh_TW="Client模式 WebSocket 位址",
        en="Client mode WebSocket URL",
        ja="Clientモード WebSocket URL",
        ru="URL WebSocket в режиме client",
    )

    client_token: I18nKey = I18nKey(
        default="Client mode authentication token",
        zh_CN="Client模式认证Token",
        zh_TW="Client模式認證Token",
        en="Client mode authentication token",
        ja="Clientモード認証トークン",
        ru="Токен аутентификации в режиме client",
    )

    implementation: I18nKey = I18nKey(
        default="Implementation identifier (e.g. Lagrange, Napcat)",
        zh_CN="实现标识（如 Lagrange, Napcat）",
        zh_TW="實作標識（如 Lagrange, Napcat）",
        en="Implementation identifier (e.g. Lagrange, Napcat)",
        ja="実装識別子（例: Lagrange, Napcat）",
        ru="Идентификатор реализации (например, Lagrange, Napcat)",
    )

    group_connection: I18nKey = I18nKey(
        default="Connection",
        zh_CN="连接设置",
        zh_TW="連線設定",
        en="Connection",
        ja="接続設定",
        ru="Подключение",
    )

    group_server: I18nKey = I18nKey(
        default="Server",
        zh_CN="服务端模式",
        zh_TW="伺服器模式",
        en="Server",
        ja="サーバー",
        ru="Сервер",
    )

    group_client: I18nKey = I18nKey(
        default="Client",
        zh_CN="客户端模式",
        zh_TW="用戶端模式",
        en="Client",
        ja="クライアント",
        ru="Клиент",
    )

    group_advanced: I18nKey = I18nKey(
        default="Advanced",
        zh_CN="高级设置",
        zh_TW="進階設定",
        en="Advanced",
        ja="詳細設定",
        ru="Дополнительно",
    )
