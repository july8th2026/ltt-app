"""
prompt_fragments.py — "nhà máy di trú" (Đợt R): ghép prompt từ FRAGMENT .txt.

Dùng chung cho MỌI app di trú từ BOT GEMINI có kho prompt dạng thư mục:

    apps/<slug>/prompts/
    ├── base_prompt.txt              # template có {placeholder}
    └── <nhóm>/                      # vd text_style, phong_cach, kieu_trend, ngon_ngu
        ├── _labels.json             # {id: "Nhãn hiển thị"}  (giữ THỨ TỰ)
        └── <id>.txt                 # đoạn prompt chèn nguyên văn

Vì sao tách ra platform_core (không để trong app): đây là NĂNG LỰC nền tảng tái
dùng (như storage/api_pool) — app sau chỉ cần đổ tài nguyên vào `prompts/` là
chạy, KHÔNG hardcode prompt trong `jobs.py` (bài học di trú app đầu tiên: hardcode
= mất toàn bộ hệ lựa chọn của bản gốc; xem docs/DOI_CHIEU_*.md).

An toàn: `id` chỉ nhận từ `_labels.json` (khoá đã biết) — chống path traversal;
file thiếu → trả rỗng, không làm sập job.
"""
from __future__ import annotations

import json
import pathlib
import re
from typing import Optional


def _dir(prompts_dir) -> pathlib.Path:
    return prompts_dir if isinstance(prompts_dir, pathlib.Path) else pathlib.Path(prompts_dir)


def load_labels(prompts_dir, group: str) -> dict:
    """Đọc `<group>/_labels.json` → dict {id: nhãn}, giữ nguyên thứ tự khai. Lỗi → {}."""
    p = _dir(prompts_dir) / group / "_labels.json"
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def options(prompts_dir, group: str) -> list:
    """Danh sách (id, nhãn) theo đúng thứ tự trong `_labels.json` — để render UI."""
    return list(load_labels(prompts_dir, group).items())


def default_option(prompts_dir, group: str) -> str:
    """id mặc định = mục ĐẦU TIÊN trong `_labels.json` (đúng quy ước BOT GEMINI)."""
    labels = load_labels(prompts_dir, group)
    return next(iter(labels), "")


def read_fragment(prompts_dir, group: str, option_id: str) -> str:
    """Đọc đoạn prompt `<group>/<id>.txt`. `id` PHẢI thuộc `_labels.json` (chặn
    path traversal). Không hợp lệ / thiếu file → chuỗi rỗng."""
    labels = load_labels(prompts_dir, group)
    if option_id not in labels:
        return ""
    p = _dir(prompts_dir) / group / f"{option_id}.txt"
    try:
        return p.read_text(encoding="utf-8").strip()
    except Exception:
        return ""


def build(prompts_dir, mapping: dict, *, base: str = "base_prompt.txt") -> str:
    """Ghép prompt cuối: đọc `base` rồi thay TỪNG placeholder `{key}` bằng giá trị.

    KHÔNG dùng `str.format` — vì `base` có thể chứa dấu `{ }` VĂN BẢN THẬT (vd khối
    JSON mẫu trong prompt youtube_script) mà `.format` sẽ hiểu nhầm là field và vỡ.
    Thay có mục tiêu thì giữ nguyên mọi dấu ngoặc nhọn không phải placeholder."""
    text = (_dir(prompts_dir) / base).read_text(encoding="utf-8")
    for k, v in mapping.items():
        text = text.replace("{" + k + "}", "" if v is None else str(v))
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
