# 繁簡對應

MaiBot 有些判斷寫死簡體。模型依繁體聊天回繁體時，詞的意思對，字卻對不上，功能就會失敗。

這個插件集中放繁體到簡體的對應。之後遇到同類問題，加在這裡。

## 目前對應

| 模型可能回的 | 核心認得的 | 處理位置 |
|---|---|---|
| 簡短表達 | 简短表达 | 插件 Hook `maisaka.replyer.before_request` |
| 正常回覆、正常回復 | 正常回复 | 同上 |
| 長回覆、長回復 | 长回复 | 同上 |
| 取消註冊編號17 | 取消注册编号17 | 核心補丁，見下方限制 |
| 不取消註冊、不刪除 | 不取消注册、不删除 | 核心補丁，見下方限制 |

## 繁體錯字

核心的錯字功能（`chinese_typo`）只有簡體字頻表和詞典，繁體回覆會被換進簡體錯字，例如「直接」變成「执接」。

插件在 `maisaka.reply.before_post_process` 接手：繁體回覆改用 `data/` 裡的臺灣繁體字頻表、詞典和分詞產生錯字，然後關掉核心這一輪的錯字。錯字機率照用 `bot_config.toml` 的 `[chinese_typo]`，關掉 `enable` 時插件也不會動。回覆裡只要有簡體專用字，就當成簡體回覆交回核心處理。

- 錯字演算法沿用核心 `typo_generator.py`，按檔案載入；核心搬檔或改名時插件會在日誌警告，錯字退回核心處理。
- 核心偶爾會在錯字後補一則更正訊息。Hook 只能改正文，插件接手的錯字不會有更正。
- `data/` 由 `scripts/build_typo_tables.py` 從 jieba 詞典用 OpenCC `s2twp` 轉換產生，jieba 詞典更新時再跑一次：

  ```bash
  uv run --no-project --with opencc python scripts/build_typo_tables.py <MaiBot 環境裡 jieba 的 dict.txt>
  ```

## 裝到 MaiBot

把這個目錄放到 MaiBot 的 `plugins/maibot-zh-variants`。啟用後，回覆風格會在進入 reply 前轉成簡體，繁體回覆的錯字改用繁體字頻。

在 MaiBot 根目錄跑自檢：

```bash
uv run python plugins/maibot-zh-variants/selftest.py
```

## 表情替換還沒能完全放進插件

表情庫滿 64 個時，核心用正則解析模型回答，Hook 只發生在選表情和描述產生之後，沒有「解析取消註冊編號之前」的攔截點。

所以這兩個對應目前仍在 MaiBot 映像補丁 `emoji_manager.py`：

- `不取消註冊`、`不刪除` 視同不要刪
- `取消註冊編號17`、`刪除編號17` 要能抓到 17

核心若之後提供表情替換決策的 Hook，再把這段從映像補丁移到這個插件。
