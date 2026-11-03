"""繁簡對應：模型回繁體時，轉成 MaiBot 內建邏輯認得的簡體。

之後新增的繁簡對應都加在 VARIANTS。能用 Hook 改寫的在這裡處理；
沒有 Hook 的核心正則仍要放在映像補丁，並在 README 登記。
"""

from pathlib import Path
from typing import Any

import asyncio
import importlib.util
import json

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

# 由 scripts/build_typo_tables.py 從 jieba 詞典轉成臺灣繁體產生。
DATA_DIR = Path(__file__).resolve().parent / "data"
TYPO_OPTIONS = ("error_rate", "min_freq", "tone_error_rate", "word_replace_rate")


def canonicalize(value: str, mapping: dict[str, str]) -> str:
    """只替換完整匹配的詞，不改句子裡的其他文字。"""

    return mapping.get(value.strip(), value)


def load_traditional_typo() -> tuple[type, frozenset[str]]:
    """沿用核心錯字生成器，只把字頻、詞典和分詞換成繁體。

    另外回傳核心字頻裡有、繁體字頻裡沒有的字，用來認出簡體回覆。
    """

    import jieba
    import src

    # 按檔案載入核心錯字模組：匯入 src.chat 會在 Runner 再初始化一份表情包管理器和資料庫。
    # 核心改名或搬檔時這裡會失敗，錯字就留給核心。
    maibot_root = Path(src.__file__).resolve().parent.parent
    spec = importlib.util.spec_from_file_location(
        "zh_variants_typo_generator", maibot_root / "src" / "chat" / "utils" / "typo_generator.py"
    )
    typo_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(typo_module)
    ChineseTypoGenerator = typo_module.ChineseTypoGenerator

    char_frequency = json.loads((DATA_DIR / "char_frequency.json").read_text(encoding="utf-8"))
    core_frequency = json.loads((maibot_root / "depends-data" / "char_frequency.json").read_text(encoding="utf-8"))
    tokenizer = jieba.Tokenizer(str(DATA_DIR / "dict.txt"))
    tokenizer.initialize()
    ChineseTypoGenerator._create_pinyin_dict()

    class TraditionalTypoGenerator(ChineseTypoGenerator):
        _load_or_create_char_frequency = staticmethod(lambda: char_frequency)
        # FREQ 裡的前綴詞頻為 0，核心選同音詞時本來就會略過。
        _load_word_frequencies = staticmethod(lambda: tokenizer.FREQ)
        _segment_sentence = staticmethod(lambda sentence: list(tokenizer.cut(sentence)))

    return TraditionalTypoGenerator, frozenset(core_frequency.keys() - char_frequency.keys())


class ZhVariantsPlugin(MaiBotPlugin):
    """集中處理繁體與簡體的工具參數對應。"""

    _typo: tuple[type, frozenset[str]] | None = None

    async def on_load(self) -> None:
        """先載入繁體錯字資料，第一次回覆才不會卡在 Hook 逾時裡。"""

        try:
            self._typo = await asyncio.to_thread(load_traditional_typo)
        except Exception:
            self.ctx.logger.exception("繁體錯字資料載入失敗，錯字仍由核心用簡體字頻處理")

    async def on_unload(self) -> None:
        """沒有背景任務。"""

    async def on_config_update(self, scope: str = "", config_data: dict[str, Any] | None = None, version: str = "") -> None:
        """此版本 MaiBot 要求插件實作設定更新入口。"""

        return None

    @HookHandler("maisaka.replyer.before_request", description="把繁體回覆風格轉成核心認得的簡體")
    async def normalize_reply_style(self, **kwargs: Any) -> dict[str, Any]:
        """reply 收到簡短表達、正常回覆、長回覆時，改成簡體列舉值。"""

        args = dict(kwargs.get("reply_tool_args") or {})
        style = args.get("reply_style")
        if isinstance(style, str):
            args["reply_style"] = canonicalize(style, REPLY_STYLES)
        return {"modified_kwargs": {**kwargs, "reply_tool_args": args}}

    @HookHandler("maisaka.reply.before_post_process", description="繁體回覆改用繁體字頻注入錯字")
    async def inject_traditional_typo(self, **kwargs: Any) -> dict[str, Any] | None:
        """核心字頻只有簡體，會把繁體回覆的字換成簡體錯字；繁體回覆改在這裡注入，再關掉核心那一輪。

        核心偶爾會在錯字後補一則更正訊息，Hook 只能改正文，這裡接手的錯字不會有更正。
        """

        response = str(kwargs.get("response") or "")
        if self._typo is None or kwargs.get("skip_post_process") or not kwargs.get("enable_chinese_typo"):
            return None
        if not await self.ctx.config.get("chinese_typo.enable", False):
            return None
        generator_class, simplified_only = self._typo
        if any(char in simplified_only for char in response):
            return None
        options = {name: await self.ctx.config.get(f"chinese_typo.{name}") for name in TYPO_OPTIONS}
        typo_response, _ = await asyncio.to_thread(generator_class(**options).create_typo_sentence, response)
        return {"modified_kwargs": {**kwargs, "response": typo_response, "enable_chinese_typo": False}}


def create_plugin() -> ZhVariantsPlugin:
    """插件載入器要求的工廠函式。"""

    return ZhVariantsPlugin()
