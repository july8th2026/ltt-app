"""`ToolSpec.params_schema` (từ vựng LTT) → tập con JSON Schema 2020-12 (§4.6).

🔴 **Hai từ vựng, và chỉ tệp này biết cả hai.** `params_schema` của LTT dùng
   `{"type": "enum", "values": [...]}`, `{"type": "int", "min", "max"}` — không
   phải JSON Schema (ledger 22/09 đã ghi lệch này). Spec §4.6 lại đòi
   `NodeDefinition.tham_so` là JSON Schema để Canvas sinh form từ MỘT bộ luật.

⛔ Đừng dịch lại ở chỗ khác. Hai bản dịch song song là đúng hình dạng lỗi mà
   `he_kieu.xuat_luat_noi_day()` sinh ra để tránh.
"""
from __future__ import annotations

from typing import Any

from platform_core.workflow import he_kieu


class LoiLuocDo(ValueError):
    """Từ vựng thiếu một dòng. ⛔ Không bao giờ bỏ qua im lặng — một tham số
    biến mất khỏi form trông y hệt một tham số không tồn tại."""


#: Kiểu tham số LTT → kiểu **cổng** của `he_kieu`.
KIEU_CONG: dict[str, str] = {
    "string": "text", "text": "text", "enum": "text",
    "int": "integer", "number": "number", "bool": "boolean",
    "model_ref": "model_ref",
    "image": "image", "image[]": "image[]",
    "video": "video", "video[]": "video[]",
    "audio": "audio",
    "json": "json", "json[]": "json[]",
}

#: Kiểu tham số LTT → khung JSON Schema. `enum` xử lý riêng (kiểu suy từ giá trị).
_KHUNG: dict[str, dict] = {
    "string": {"type": "string"},
    "text": {"type": "string", "x-ltt-control": "textarea"},
    "int": {"type": "integer"},
    "number": {"type": "number"},
    "bool": {"type": "boolean"},
    "model_ref": {"type": "string", "x-ltt-kieu": "model_ref",
                  "x-ltt-control": "dropdown-dong"},
    "image": {"type": "string", "x-ltt-kieu": "image"},
    "image[]": {"type": "array", "items": {"type": "string"},
                "x-ltt-kieu": "image[]"},
    "video": {"type": "string", "x-ltt-kieu": "video"},
    "video[]": {"type": "array", "items": {"type": "string"},
                "x-ltt-kieu": "video[]"},
    "audio": {"type": "string", "x-ltt-kieu": "audio"},
    "json": {"type": "object", "x-ltt-kieu": "json"},
    "json[]": {"type": "array", "items": {"type": "object"},
               "x-ltt-kieu": "json[]"},
}


def _la_may_tu_dien(rule: dict) -> bool:
    """Nền tảng tự điền (ffprobe qua `measured_from`) ⇒ không phải ô nhập, và
    KHÔNG phải cổng: không ai nối được vào một giá trị server tự đo."""
    return bool(rule.get("measured_from"))


def mot_tham_so(ten: str, rule: dict) -> dict:
    kieu = str(rule.get("type", ""))
    if kieu == "enum":
        gia_tri = list(rule.get("values") or [])
        # Kiểu lấy từ CHÍNH giá trị: `target_height` là enum số.
        json_kieu = ("integer" if gia_tri and all(
            isinstance(v, int) and not isinstance(v, bool) for v in gia_tri)
            else "number" if gia_tri and all(
                isinstance(v, (int, float)) and not isinstance(v, bool)
                for v in gia_tri)
            else "string")
        ra: dict[str, Any] = {"type": json_kieu, "enum": gia_tri}
    else:
        khung = _KHUNG.get(kieu)
        if khung is None:
            raise LoiLuocDo(
                f"kieu tham so chua co tu vung: {kieu!r} (tham so {ten!r}); "
                f"them mot dong vao luoc_do._KHUNG thay vi doan")
        ra = {k: (dict(v) if isinstance(v, dict) else v)
              for k, v in khung.items()}

    if "min" in rule:
        ra["minimum"] = rule["min"]
    if "max" in rule:
        ra["maximum"] = rule["max"]
    if "max_length" in rule:
        ra["maxLength"] = int(rule["max_length"])
    if "default" in rule:
        ra["default"] = rule["default"]
    if rule.get("description"):
        ra["description"] = str(rule["description"])
    # `values`/`options` đã được `agent.tools.resolve_params_schema` giải sẵn
    # cho `model_ref` — mang sang dạng JSON Schema, không giải lại.
    if kieu == "model_ref" and rule.get("values"):
        ra["enum"] = list(rule["values"])
    if rule.get("options"):
        ra["x-ltt-nhan"] = {str(o["value"]): str(o.get("label", o["value"]))
                            for o in rule["options"] if isinstance(o, dict)}
    if rule.get("depends_on"):
        ra["x-ltt-dong"] = {"nguon": "tuy_chon_dong",
                            "prop": str(rule["depends_on"])}
    if _la_may_tu_dien(rule):
        ra["readOnly"] = True
        ra["x-ltt-control"] = "may_tu_dien"
    return ra


def sang_json_schema(params_schema: dict) -> dict:
    thuoc_tinh: dict[str, dict] = {}
    bat_buoc: list[str] = []
    for ten, rule in (params_schema or {}).items():
        rule = rule if isinstance(rule, dict) else {}
        thuoc_tinh[ten] = mot_tham_so(ten, rule)
        if rule.get("required") and not _la_may_tu_dien(rule):
            bat_buoc.append(ten)
    return {"type": "object", "properties": thuoc_tinh,
            "required": bat_buoc, "additionalProperties": False}


def _cong(kieu: str, *, bat_buoc: bool, nhan: str) -> he_kieu.Cong:
    if not he_kieu.hop_le(kieu):
        raise LoiLuocDo(f"kieu cong khong hop le: {kieu!r} (cong {nhan!r})")
    return he_kieu.Cong(type=kieu, required=bat_buoc, multiple=False, nhan=nhan)


def cong_vao(params_schema: dict, cong_khai: dict) -> tuple:
    ra: list[tuple[str, he_kieu.Cong]] = []
    for ten, rule in (params_schema or {}).items():
        rule = rule if isinstance(rule, dict) else {}
        khai_tay = (cong_khai or {}).get(ten)
        # Khai báo tường minh luôn thắng suy luận (spec §4.5) — kể cả khi
        # tham số là `measured_from`. Chỉ suy luận "không phải cổng" khi
        # KHÔNG có khai báo tường minh cho tham số này.
        if khai_tay is None and _la_may_tu_dien(rule):
            continue
        kieu = str(khai_tay or KIEU_CONG.get(str(rule.get("type", "")), ""))
        if not kieu:
            raise LoiLuocDo(
                f"kieu tham so chua co tu vung: {rule.get('type')!r} "
                f"(tham so {ten!r})")
        ra.append((ten, _cong(kieu, bat_buoc=bool(rule.get("required")),
                              nhan=ten)))
    return tuple(ra)


def cong_ra(returns: dict, cong_khai: dict) -> tuple:
    ra: list[tuple[str, he_kieu.Cong]] = []
    for ten, kieu_ltt in (returns or {}).items():
        kieu = str((cong_khai or {}).get(ten) or
                   KIEU_CONG.get(str(kieu_ltt), ""))
        if not kieu:
            raise LoiLuocDo(
                f"kieu cong ra chua co tu vung: {kieu_ltt!r} (cong {ten!r})")
        ra.append((ten, _cong(kieu, bat_buoc=True, nhan=ten)))
    return tuple(ra)


__all__ = ["KIEU_CONG", "LoiLuocDo", "cong_ra", "cong_vao", "mot_tham_so",
           "sang_json_schema"]
