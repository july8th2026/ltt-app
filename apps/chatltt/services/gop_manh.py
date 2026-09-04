"""
gop_manh.py — gộp `tool_call.delta` bị cắt mảnh thành lời gọi hoàn chỉnh. (H44 P03)

`platform_core/runtime_noi_bo/luong.py:475-477` phát **mỗi chunk một sự kiện**,
nguyên xi như máy B gửi. Nó **không gộp** — và đó là đúng phân vai: runtime
chuyển byte, không hiểu ngữ nghĩa. `test_800` đã ghim điều đó bằng một phép đo,
để tầng này không giả định nhầm rằng runtime đã gộp hộ.

## Hình dạng thật của một lời gọi bị cắt

Đo trên máy B 04/09 (`docs/CHATLTT_V3/artifacts/01_cong0.json`): chunk đầu mang
`id` + `name` + `arguments` rỗng; các chunk sau **chỉ** nối thêm `arguments`:

    {"index":0,"id":"call_1","type":"function",
     "function":{"name":"calculator","arguments":""}}
    {"index":0,"function":{"arguments":"{\\"expres"}}
    {"index":0,"function":{"arguments":"sion\\": \\"8123"}}
    {"index":0,"function":{"arguments":" * 4471\\"}"}}

⛔ Ba mảnh giữa **không phải JSON hợp lệ**. Phân tích từng mảnh rời là hỏng
ngẫu nhiên theo tải — cùng bài học `_DocSSE` của `luong.py` đã học với byte SSE.

## `index` là khoá, KHÔNG phải `id`

Gọi song song cho nhiều lời gọi cùng lúc, và **chỉ chunk đầu của mỗi lời gọi
mang `id`**. Gom theo `id` thì ba mảnh sau của mỗi lời gọi rơi vào nhóm `None`
và trộn lẫn nhau. `index` có mặt ở **mọi** chunk — đó là lý do OpenAI đặt nó ở đó.

⭐ P01 đo gọi song song 18/18 ra **đúng hai** lời gọi mỗi lượt, nên đây không
phải trường hợp lý thuyết: nó là đường đi thường ngày của V3.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Iterable, Optional


class DoiSoHong(ValueError):
    """Gộp xong mà `arguments` không phải JSON object.

    ⛔ Đây **không** phải lỗi để giết lượt. Bên gọi bắt nó rồi trả một
       `tool.rejected` có cấu trúc **về cho model** (`02_HOP_DONG.md` §1) — model
       sửa và gọi lại là hành vi đúng. Giết run vì model gõ hụt một dấu ngoặc là
       đổi một lỗi có thể sửa thành một lượt hỏng.
    """


@dataclass
class LoiGoi:
    """Một lời gọi tool đã gộp xong."""

    index: int
    id: str = ""
    ten: str = ""
    doi_so_tho: str = ""
    #: `type` của OpenAI. Giữ lại vì hợp đồng có nó, dù nay luôn là "function".
    loai: str = "function"

    def doi_so(self) -> dict:
        """`doi_so_tho` → dict. Ném `DoiSoHong` nếu không phải JSON object."""
        chu = (self.doi_so_tho or "").strip()
        if not chu:
            # ⭐ Tool không tham số là hợp lệ: `arguments` rỗng ⇒ `{}`, không phải lỗi.
            return {}
        try:
            gt = json.loads(chu)
        except ValueError as e:
            raise DoiSoHong(f"doi so khong phai JSON: {e}") from None
        if not isinstance(gt, dict):
            raise DoiSoHong(f"doi so phai la object, nhan {type(gt).__name__}")
        return gt


@dataclass
class BoGop:
    """Gom `tool_call.delta` qua nhiều sự kiện. Gọi `nhin()` cho từng cái."""

    _theo_index: dict = field(default_factory=dict)
    _thu_tu: list = field(default_factory=list)

    def nhin(self, su_kien: dict) -> None:
        """Áp một sự kiện `tool_call.delta`. Bỏ qua sự kiện loại khác."""
        if (su_kien or {}).get("type") != "tool_call.delta":
            return
        for manh in su_kien.get("tool_calls") or ():
            if isinstance(manh, dict):
                self._mot_manh(manh)

    def _mot_manh(self, manh: dict) -> None:
        # `index` vắng mặt ⇒ coi là 0. Một số runtime bỏ nó khi chỉ có một lời
        # gọi; coi đó là lời gọi thứ nhất chứ không phải một lời gọi vô danh mới.
        idx = manh.get("index")
        idx = 0 if idx is None else int(idx)
        lg = self._theo_index.get(idx)
        if lg is None:
            lg = LoiGoi(index=idx)
            self._theo_index[idx] = lg
            self._thu_tu.append(idx)

        if manh.get("id"):
            lg.id = str(manh["id"])
        if manh.get("type"):
            lg.loai = str(manh["type"])
        ham = manh.get("function") or {}
        if ham.get("name"):
            # ⛔ GÁN, không nối. `name` tới trọn vẹn ở chunk đầu; nối nó lại là
            #    cách tạo ra `"calculatorcalculator"` khi runtime lặp chunk đầu.
            lg.ten = str(ham["name"])
        ds = ham.get("arguments")
        if isinstance(ds, str) and ds:
            lg.doi_so_tho += ds                      # NỐI — đây mới là phần cắt mảnh

    def xong(self) -> list:
        """Danh sách lời gọi đã gộp, **theo thứ tự xuất hiện**.

        ⭐ Thứ tự xuất hiện, không phải thứ tự `index`: model sinh ra chúng theo
           một trình tự có ý, và giữ trình tự đó làm nhật ký `chatltt_step` đọc
           được như một câu chuyện.
        """
        return [self._theo_index[i] for i in self._thu_tu]

    def co_gi_khong(self) -> bool:
        return bool(self._thu_tu)


def gop(su_kien: Iterable[dict]) -> list:
    """Tiện dụng: gộp cả một dãy sự kiện trong một lần."""
    bo = BoGop()
    for sk in su_kien:
        bo.nhin(sk)
    return bo.xong()


def bam_trung(ten: str, doi_so: dict) -> str:
    """Vân tay `(tên, đối số)` để chặn gọi trùng trong cùng một run.

    ⛔ `sort_keys=True` là bắt buộc: `{"a":1,"b":2}` và `{"b":2,"a":1}` là **một**
       lời gọi. Không chuẩn hoá thì bộ chặn trùng chỉ chặn được khi model tình cờ
       sinh các khoá đúng thứ tự cũ — tức nó chặn ngẫu nhiên, và một cái rào chặn
       ngẫu nhiên tệ hơn không có rào: nó tạo cảm giác đã được bảo vệ.
    """
    import hashlib

    goi = json.dumps({"ten": str(ten), "doi_so": doi_so},
                     sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(goi.encode("utf-8")).hexdigest()[:32]


def tom_tat(lg: LoiGoi, gioi_han: int = 120) -> str:
    """Một dòng cho log và cho sự kiện `tool.requested`. Không đổ nguyên đối số."""
    ds = (lg.doi_so_tho or "").replace("\n", " ")
    if len(ds) > gioi_han:
        ds = ds[:gioi_han] + "…"
    return f"{lg.ten or '?'}({ds})"


__all__ = ["BoGop", "LoiGoi", "DoiSoHong", "gop", "bam_trung", "tom_tat"]
