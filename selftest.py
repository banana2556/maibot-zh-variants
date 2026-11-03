"""自檢：繁體回覆只會被換進繁體錯字、簡體回覆和關閉錯字時交回核心、回覆風格對應保留其他參數。在 MaiBot 根目錄運行：

uv run python plugins/maibot-zh-variants/selftest.py
"""

from pathlib import Path
from types import SimpleNamespace

import asyncio
import logging
import random
import sys

sys.path[:0] = [str(Path(__file__).resolve().parent), str(Path.cwd())]
from plugin import ZhVariantsPlugin  # noqa: E402

TRADITIONAL = "可能被問就緊張吧，直接問反而不敢說懂。這個問題我們之後再討論，先把軟體裝好，記得還要回覆對方。"
SIMPLIFIED = "可能被问就紧张吧，直接问反而不敢说懂。"
# 機率調高，確保字和詞兩種替換都有跑到。
NOISY = {"enable": True, "error_rate": 0.9, "min_freq": 9, "tone_error_rate": 0.3, "word_replace_rate": 0.9}


def make_plugin(config: dict) -> ZhVariantsPlugin:
    async def get(key: str, default: object = None) -> object:
        return config.get(key.removeprefix("chinese_typo."), default)

    plugin = ZhVariantsPlugin()
    plugin._ctx = SimpleNamespace(config=SimpleNamespace(get=get), logger=logging.getLogger("zh-variants"))
    return plugin


def post_process_kwargs(response: str, **overrides: object) -> dict:
    kwargs = {
        "response": response,
        "session_id": "s1",
        "reply_message_id": "m1",
        "reply_tool_args": {},
        "skip_post_process": False,
        "enable_splitter": True,
        "enable_chinese_typo": True,
    }
    return {**kwargs, **overrides}


async def check_typo() -> None:
    plugin = make_plugin(NOISY)
    await plugin.on_load()
    assert plugin._typo is not None, "繁體錯字資料應載入成功"
    _, simplified_only = plugin._typo
    assert {"执", "问", "这", "说"} <= simplified_only and not {"執", "問", "直"} & simplified_only

    random.seed(0)
    changed = 0
    for _ in range(30):
        result = await plugin.inject_traditional_typo(**post_process_kwargs(TRADITIONAL))
        kwargs = result["modified_kwargs"]
        assert kwargs["enable_chinese_typo"] is False and kwargs["enable_splitter"] is True and kwargs["session_id"] == "s1"
        response = kwargs["response"]
        leaked = [char for char in response if char in simplified_only]
        assert not leaked, (response, leaked)
        changed += response != TRADITIONAL
    assert changed > 20, f"高錯字率下只有 {changed}/30 次有改字"

    assert await plugin.inject_traditional_typo(**post_process_kwargs(SIMPLIFIED)) is None, "簡體回覆應交回核心"
    assert await plugin.inject_traditional_typo(**post_process_kwargs(TRADITIONAL, enable_chinese_typo=False)) is None
    assert await plugin.inject_traditional_typo(**post_process_kwargs(TRADITIONAL, skip_post_process=True)) is None
    disabled = make_plugin({**NOISY, "enable": False})
    disabled._typo = plugin._typo
    assert await disabled.inject_traditional_typo(**post_process_kwargs(TRADITIONAL)) is None, "全域關閉錯字時不接手"


async def check_reply_style() -> None:
    plugin = make_plugin(NOISY)
    result = await plugin.normalize_reply_style(session_id="s1", attempt=1, reply_tool_args={"reply_style": "正常回覆", "x": 1})
    assert result == {
        "modified_kwargs": {"session_id": "s1", "attempt": 1, "reply_tool_args": {"reply_style": "正常回复", "x": 1}}
    }, result


if __name__ == "__main__":
    asyncio.run(check_typo())
    asyncio.run(check_reply_style())
    print("zh-variants selftest OK")
