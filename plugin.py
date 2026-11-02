"""繁簡對應：模型回繁體時，轉成 MaiBot 內建邏輯認得的簡體。

之後新增的繁簡對應都加在 VARIANTS。能用 Hook 改寫的在這裡處理；
沒有 Hook 的核心正則仍要放在映像補丁，並在 README 登記。
"""

from typing import Any

from maibot_sdk import HookHandler, MaiBotPlugin

# 左側是模型可能回的寫法，右側是核心程式目前只認的簡體。
REPLY_STYLES = {
    "簡短表達": "简短表达",
    "簡短表达": "简短表达",
    "简短表達": "简短表达",
    "正常回覆": "正常回复",
    "正常回復": "正常回复",
    "長回覆": "长回复",
    "長回復": "长回复",
    "长回覆": "长回复",
}


def canonicalize(value: str, mapping: dict[str, str]) -> str:
    """只替換完整匹配的詞，不改句子裡的其他文字。"""

    return mapping.get(value.strip(), value)


class ZhVariantsPlugin(MaiBotPlugin):
    """集中處理繁體與簡體的工具參數對應。"""

    async def on_load(self) -> None:
        """對應表在程式裡，載入時不需要額外狀態。"""

    async def on_unload(self) -> None:
        """沒有背景任務。"""

    async def on_config_update(self, scope: str = "", config_data: dict[str, Any] | None = None, version: str = "") -> None:
        """此版本 MaiBot 要求插件實作設定更新入口。"""

        return None

    @HookHandler("maisaka.replyer.before_request", description="把繁體回覆風格轉成核心認得的簡體")
    async def normalize_reply_style(self, reply_tool_args: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
        """reply 收到簡短表達、正常回覆、長回覆時，改成簡體列舉值。"""

        del kwargs
        args = dict(reply_tool_args or {})
        style = args.get("reply_style")
        if isinstance(style, str):
            args["reply_style"] = canonicalize(style, REPLY_STYLES)
        return {"reply_tool_args": args}


def create_plugin() -> ZhVariantsPlugin:
    """插件載入器要求的工廠函式。"""

    return ZhVariantsPlugin()
