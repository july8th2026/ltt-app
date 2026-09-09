"""Nghiệp vụ của App `prompt_canh`: kịch bản → khoá nhân vật → danh sách cảnh → JSON prompt.

**GUI, Macro Node và (sau này) API đều gọi hàm ở đây** — bất biến #2.

## Đây là VIẾT LẠI, không phải port

Chủ dự án quyết 2026-09-09: bỏ hẳn đường lái trình duyệt, chỉ gọi qua
`runtime_noi_bo`. Toàn văn và hệ quả:
`docs/migration/workflow_apps/09_QUYET_DINH_GEM_BO_TRINH_DUYET.md`.

⇒ Hệ quả phải nhớ khi đọc tệp này: **parity với legacy không đo được**. Chuẩn
nghiệm thu là **hợp đồng đầu ra** (G1–G7 trong tệp trên), không phải so từng ký
tự với bản cũ.

## Cái GIỮ, và vì sao đúng ba thứ này

| Giữ | Lý do nó sống sót qua việc đổi provider |
|---|---|
| ba template `prompts/step*.txt` | **tài sản**, không phải mã — chúng tạo ra giá trị |
| cấu trúc ba bước, đúng thứ tự | khoá nhân vật → liệt kê cảnh → sinh JSON |
| `LICH_SU_CANH = 5` | nói về **ngữ cảnh của mô hình**, không về trình duyệt |
| lô `10 / 5` | kích thước lô đổi **chất lượng** đầu ra, không chỉ tốc độ |

## Cái BỎ — chúng chỉ tồn tại vì phía kia là một trình duyệt

`8s` giữa lô · `+3s` mỗi lô · trần `60s` · nghỉ `45s` mỗi `12` lô · hội thoại mới
mỗi `25` lô. Sáu hằng số ấy là nhịp chống throttle của một **phiên web**, và
chiến trường ấy không còn: `runtime_noi_bo` có **admission** thật, dùng chung
với mọi sản phẩm khác, và nó đo được.

## ⚠️ Điền template bằng `replace` TUẦN TỰ, không bằng `format`

Bản legacy cố ý làm vậy, và lý do vẫn đúng nguyên: giá trị điền vào **chứa
`{` `}`** (chính là JSON của bước 3). `str.format` sẽ ném `KeyError` giữa một
lượt đã tiêu tiền.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

log = logging.getLogger("apps.prompt_canh")

THU_MUC_PROMPT = Path(__file__).resolve().parent.parent / "prompts"

#: Giữ 5 cảnh gần nhất làm ngữ cảnh cho lô kế.
#:
#: 🔴 Legacy ghi thẳng lý do: *"bug cũ: chỉ giữ 2 scene cuối → qua 100+ scenes
#:    drift character/style"*. Đây là chống **trôi ngữ cảnh của mô hình**, nên
#:    nó sống tiếp sau khi bỏ trình duyệt.
LICH_SU_CANH = 5

#: Kích thước lô của bước 2 và bước 3 — giữ từ legacy.
LO_BUOC2 = 10
LO_BUOC3 = 5

TOOL_LLM = "text.chat"


class LoiKichBan(ValueError):
    """Đầu vào hoặc kết quả không dùng được."""


@dataclass(frozen=True)
class YeuCau:
    kich_ban: str
    so_canh: int = 20
    lo_buoc2: int = LO_BUOC2
    lo_buoc3: int = LO_BUOC3
    model: str = ""
    visual_style: str = ""
    duration: str = ""


@dataclass(frozen=True)
class KetQua:
    char_bible: str
    canh: list[dict]
    prompt_json: list[dict]
    so_luot_model: int
    canh_bao: tuple[str, ...] = field(default_factory=tuple)

    def as_result(self) -> dict:
        return {
            "ket_qua": {"char_bible": self.char_bible,
                        "scenes": self.canh,
                        "prompts": self.prompt_json},
            "model_calls": self.so_luot_model,
            "warnings": list(self.canh_bao),
            # ⛔ KHÔNG có `credit_cost`: mọi credit của lượt này đã chảy qua
            #    `runtime_noi_bo` theo từng lượt model. Khai một số ở đây là
            #    thu HAI LẦN — xem `apps/chatltt/gia_nghien_cuu.py`.
        }


def chuan_hoa(params: dict) -> YeuCau:
    p = dict(params or {})
    kich_ban = str(p.get("kich_ban") or "").strip()
    if not kich_ban:
        raise LoiKichBan("thieu tham so `kich_ban`")
    try:
        so_canh = int(p.get("so_canh", 20))
        lo2 = int(p.get("batch_step2", LO_BUOC2))
        lo3 = int(p.get("batch_step3", LO_BUOC3))
    except (TypeError, ValueError) as e:
        raise LoiKichBan(f"tham so so khong hop le: {e}") from e
    if so_canh < 1:
        raise LoiKichBan(f"`so_canh` phai >= 1, nhan {so_canh}")
    if lo2 < 1 or lo3 < 1:
        raise LoiKichBan(f"kich thuoc lo phai >= 1, nhan {lo2}/{lo3}")
    return YeuCau(kich_ban=kich_ban, so_canh=so_canh, lo_buoc2=lo2,
                  lo_buoc3=lo3, model=str(p.get("model") or ""),
                  visual_style=str(p.get("visual_style") or ""),
                  duration=str(p.get("duration") or ""))


def doc_template(ten: str) -> str:
    tep = THU_MUC_PROMPT / ten
    if not tep.is_file():
        raise LoiKichBan(f"thieu template `{ten}`")
    return tep.read_text(encoding="utf-8")


def dien(mau: str, gia_tri: dict[str, Any]) -> str:
    """Thay `{khoa}` bằng `str.replace` **tuần tự**.

    ⛔ Không dùng `str.format`: giá trị điền vào chứa `{` `}` (JSON của bước 3),
       và `format` sẽ ném `KeyError` giữa một lượt đã tiêu tiền. Legacy cố ý
       làm vậy và ghi rõ lý do; giữ nguyên.
    """
    ra = mau
    for khoa, gt in gia_tri.items():
        ra = ra.replace("{" + khoa + "}", str(gt))
    return ra


def _tach_json(van: str) -> Any:
    """Lấy khối JSON đầu tiên trong câu trả lời của model.

    ⚠️ Model hay bọc JSON trong ```json … ```, và hay nói thêm một câu trước
       hoặc sau. Bắt lỗi ở đây, đừng để một `JSONDecodeError` trần nổi lên —
       bên gọi cần biết **model trả về cái gì**, không chỉ biết nó không parse
       được.
    """
    van = (van or "").strip()
    khoi = re.search(r"```(?:json)?\s*(.+?)\s*```", van, re.S)
    tho = khoi.group(1) if khoi else van
    dau = min([i for i in (tho.find("["), tho.find("{")) if i >= 0] or [-1])
    if dau < 0:
        raise LoiKichBan(f"model khong tra ve JSON: {van[:200]!r}")
    try:
        return json.loads(tho[dau:])
    except ValueError as e:
        raise LoiKichBan(
            f"model tra ve JSON hong ({e}): {tho[dau:dau + 200]!r}") from e


def _lich_su(canh: list[dict]) -> str:
    """`LICH_SU_CANH` cảnh gần nhất, dạng JSON gọn — ngữ cảnh cho lô kế."""
    return json.dumps(canh[-LICH_SU_CANH:], ensure_ascii=False)


def chay(yc: YeuCau, goi_model, *, tien_do: Optional[Any] = None) -> KetQua:
    """Ba bước. `goi_model(nhac: str) -> str` do bên gọi đưa vào.

    ⭐ Tiêm `goi_model` chứ không gọi thẳng `runtime_noi_bo` ở đây: nhờ vậy phép
       kiểm chạy được **không cần model thật và không cần CSDL**, mà vẫn đi qua
       đúng đường mà production đi. Cùng khuôn `apps/chatltt` đã dùng.
    """
    def bao(pt: int, mo_ta: str) -> None:
        if tien_do is not None:
            tien_do(pt, mo_ta)

    so_luot = 0
    canh_bao: list[str] = []

    # ── Bước 1: khoá nhân vật ───────────────────────────────────────────────
    bao(5, "khoa nhan vat")
    nhac1 = dien(doc_template("step1_character_lock.txt"),
                 {"kichban": yc.kich_ban, "n_scenes": yc.so_canh,
                  "visual_style": yc.visual_style, "duration": yc.duration})
    char_bible = str(goi_model(nhac1) or "").strip()
    so_luot += 1
    if not char_bible:
        raise LoiKichBan("buoc 1 tra ve rong")

    # ── Bước 2: danh sách cảnh, theo lô ────────────────────────────────────
    mau2 = doc_template("step2_scene_list.txt")
    canh: list[dict] = []
    so_lo2 = (yc.so_canh + yc.lo_buoc2 - 1) // yc.lo_buoc2
    for i in range(so_lo2):
        dau = i * yc.lo_buoc2 + 1
        cuoi = min(dau + yc.lo_buoc2 - 1, yc.so_canh)
        bao(10 + int(50 * (i + 1) / max(1, so_lo2)),
            f"canh {dau}-{cuoi}/{yc.so_canh}")
        nhac2 = dien(mau2, {
            "kichban": yc.kich_ban, "char_bible": char_bible,
            "n_scenes": yc.so_canh, "n_scenes_batch": cuoi - dau + 1,
            "scene_start": dau, "scene_end": cuoi,
            "scene_id_start": dau, "scene_id_end": cuoi,
            "visual_style": yc.visual_style, "duration": yc.duration,
            "source_scenes_section": _lich_su(canh) if canh else "",
        })
        ra = _tach_json(str(goi_model(nhac2) or ""))
        so_luot += 1
        if not isinstance(ra, list):
            raise LoiKichBan(f"buoc 2 lo {i + 1} khong tra ve mot danh sach")
        canh.extend(ra)

    if len(canh) < yc.so_canh:
        canh_bao.append(f"xin {yc.so_canh} canh, nhan {len(canh)}")

    # ── Bước 3: JSON prompt, theo lô ───────────────────────────────────────
    mau3 = doc_template("step3_json_prompt.txt")
    prompts: list[dict] = []
    so_lo3 = (len(canh) + yc.lo_buoc3 - 1) // max(1, yc.lo_buoc3)
    for i in range(so_lo3):
        lo = canh[i * yc.lo_buoc3:(i + 1) * yc.lo_buoc3]
        if not lo:
            continue
        bao(60 + int(38 * (i + 1) / max(1, so_lo3)), f"prompt lo {i + 1}/{so_lo3}")
        nhac3 = dien(mau3, {
            "char_bible": char_bible,
            "loi_thoai": json.dumps(lo, ensure_ascii=False),
            "n_scenes_batch": len(lo),
            "scene_id_start": i * yc.lo_buoc3 + 1,
            "scene_id_end": i * yc.lo_buoc3 + len(lo),
            "visual_style": yc.visual_style, "duration": yc.duration,
        })
        ra = _tach_json(str(goi_model(nhac3) or ""))
        so_luot += 1
        if not isinstance(ra, list):
            raise LoiKichBan(f"buoc 3 lo {i + 1} khong tra ve mot danh sach")
        prompts.extend(ra)

    bao(100, "xong")
    return KetQua(char_bible=char_bible, canh=canh, prompt_json=prompts,
                  so_luot_model=so_luot, canh_bao=tuple(canh_bao))
