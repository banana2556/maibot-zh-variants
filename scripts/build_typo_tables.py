"""從 jieba 內建的簡體詞典產生錯字用的臺灣繁體詞典與字頻表。

字頻算法與 MaiBot 核心 typo_generator 相同，只是先把每個詞轉成繁體。

    uv run --no-project --with opencc python scripts/build_typo_tables.py <jieba 的 dict.txt>
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

import opencc

source = Path(sys.argv[1])
output = Path(__file__).resolve().parent.parent / "data"
convert = opencc.OpenCC("s2twp").convert

# 不同簡體詞可能轉成同一個繁體詞，詞頻相加。
words: dict[str, int] = defaultdict(int)
for line in source.read_text(encoding="utf-8").splitlines():
    word, freq = line.split()[:2]
    words[convert(word)] += int(freq)

chars: dict[str, int] = defaultdict(int)
for word, freq in words.items():
    for char in word:
        if "一" <= char <= "鿿":
            chars[char] += freq
top = max(chars.values())

output.mkdir(exist_ok=True)
(output / "dict.txt").write_text("".join(f"{word} {freq}\n" for word, freq in words.items()), encoding="utf-8")
(output / "char_frequency.json").write_text(
    json.dumps({char: freq / top * 1000 for char, freq in chars.items()}, ensure_ascii=False, indent=2),
    encoding="utf-8",
)
