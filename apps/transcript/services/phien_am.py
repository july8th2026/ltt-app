"""Nghiệp vụ của App `transcript`: audio → dòng thời gian đã kiểm.

**GUI, Macro Node và (sau này) API đều gọi hàm ở đây.** Đó là bất biến #2 của
chương trình migrate, và là thứ làm cho ba đường không thể trôi khỏi nhau.

## Sáu bước — y hệt bot legacy, bỏ đúng phần điều phối

```
1 VAD                vad_speech_segments()          engine/vad.py
2 STT                platform_core.stt.service       ho so "moc_tu_vad_ngoai"
3 dựng dòng thời gian make_timeline_v2()             engine/segment/core.py
4 chiếu schema       _chieu_schema()
5 kiểm trùng lặp     _kiem_khong_trung_lien_tiep()
6 kiểm schema        _kiem_schema_nghiem_ngat()
```

⛔ **Cái đã bỏ, và vì sao:** vòng quét Google Sheet · khoá bằng ô · tải/đẩy
Drive · máy trạng thái cột `status` · trọng tài GPU cục bộ. Nền tảng đã có
tất cả, tốt hơn — `docs/migration/workflow_apps/07_CROSS_BOT_SYNTHESIS.md` §3.

## Ba phép kiểm ở bước 4–6 là QUÀ của bot legacy

Chúng đã tồn tại trong `bot/worker.py` dưới dạng hàm `_validate_*`, nên chúng
chuyển thẳng thành phép kiểm parity thay vì phải suy ra. Giữ **nguyên thông
điệp lỗi**: một bản port đổi lời nhắn là một bản port làm mất khả năng đối chiếu
nhật ký cũ.

## ⚠️ HAI TẦNG GIỚI HẠN ĐỘ DÀI — đừng gộp

`target_min`/`target_max` đến từ cấu hình (`segment.min_s`/`max_s`); `HARD_MIN`/
`HARD_MAX` trong `engine/segment/constants.py` là tầng **cứng**, chú thích ghi
*"NON-NEGOTIABLE"*. Ở cấu hình production chúng **tình cờ** trùng số ở đầu trên
(6.0), nên một bản port gộp chúng làm một sẽ chạy đúng **cho tới khi** ai đó đổi
`max_s` — lúc đó tầng cứng biến mất, im lặng.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from platform_core.stt import service as stt

from .engine.segment.core import make_timeline_v2
from .engine.vad import audio_duration_seconds, vad_speech_segments

log = logging.getLogger("apps.transcript")

#: Hồ sơ STT của App này — tên NĂNG LỰC, không phải tên App.
#: `moc_tu_vad_ngoai` = có mốc từ, VAD chạy ở tầng trên chứ không trong whisper.
HO_SO_STT = "moc_tu_vad_ngoai"

#: Khoá bắt buộc của MỘT đoạn ở đầu ra — đúng tập mà
#: `_validate_output_segments_strict` của bot legacy cưỡng chế.
KHOA_DOAN = ("type", "start", "end", "text")

#: Tập khoá ĐẦY ĐỦ của một đoạn, đo trên 1.932 lượt job thật: 6.934/6.934
#: đoạn có đúng sáu khoá này, không hơn không kém.
KHOA_DAY_DU = ("start", "end", "text", "type", "scene_id", "index")

LOAI_DOAN = ("speech", "silence")


class LoiPhienAm(ValueError):
    """Đầu vào hoặc kết quả không dùng được. Bên gọi biến nó thành lỗi job."""


@dataclass(frozen=True)
class YeuCau:
    """Tham số đã chuẩn hoá. Dựng từ `chuan_hoa()`, không dựng tay."""

    duong_audio: str
    ngon_ngu: str = ""
    min_s: float = 3.0
    max_s: float = 6.0
    kem_khoang_lang: bool = True
    chu_khoang_lang: str = "[B-ROLL / PAUSE]"
    nguong_khoang_lang: float = 2.0
    model: str = "large-v3"


@dataclass(frozen=True)
class KetQua:
    doan: list[dict]
    ngon_ngu: str
    do_tin_ngon_ngu: float
    thoi_luong_s: float
    so_vung_tieng: int
    canh_bao: tuple[str, ...] = field(default_factory=tuple)

    def as_result(self) -> dict:
        return {
            "transcript": self.doan,
            "language": self.ngon_ngu,
            "language_probability": round(self.do_tin_ngon_ngu, 4),
            "duration_s": round(self.thoi_luong_s, 3),
            "speech_regions": self.so_vung_tieng,
            "warnings": list(self.canh_bao),
        }


def chuan_hoa(params: dict) -> YeuCau:
    """Tham số thô → `YeuCau`. Ném `LoiPhienAm` cho mọi thứ không dùng được.

    ⚠️ `min_s >= max_s` bị từ chối **trước khi chạy**, không dừng giữa chừng:
       dừng giữa chừng nghĩa là đã tiêu một suất GPU cho một lượt chắc chắn
       thất bại — tệ hơn cả không chạy. Cùng lập luận với `ForeachVong.VuotTran`
       của Workflow V2.
    """
    p = dict(params or {})
    duong = str(p.get("audio") or p.get("duong_audio") or "").strip()
    if not duong:
        raise LoiPhienAm("thieu tham so `audio`")
    try:
        min_s = float(p.get("min_s", 3.0))
        max_s = float(p.get("max_s", 6.0))
        nguong = float(p.get("nguong_khoang_lang", 2.0))
    except (TypeError, ValueError) as e:
        raise LoiPhienAm(f"tham so do dai khong phai so: {e}") from e
    if min_s <= 0 or max_s <= 0:
        raise LoiPhienAm(f"`min_s`/`max_s` phai > 0, nhan {min_s}/{max_s}")
    if min_s >= max_s:
        raise LoiPhienAm(
            f"`min_s` ({min_s}) phai NHO HON `max_s` ({max_s}) — tu choi truoc "
            "khi chay, khong dung giua chung")
    return YeuCau(
        duong_audio=duong,
        ngon_ngu=str(p.get("language") or "").strip(),
        min_s=min_s, max_s=max_s,
        kem_khoang_lang=bool(p.get("include_silence", True)),
        chu_khoang_lang=str(p.get("chu_khoang_lang") or "[B-ROLL / PAUSE]"),
        nguong_khoang_lang=nguong,
        model=str(p.get("model") or "large-v3"),
    )


# ── Ba phép kiểm chuyển thẳng từ bot legacy ─────────────────────────────────

def _kiem_co_mocs_tu(doan_tho: list[dict]) -> None:
    """`word_timestamps=True` là HARD RULE của hồ sơ `transcript`.

    Thiếu `words` thì bước dựng dòng thời gian vẫn chạy — nó chỉ **không có gì
    để dựng**, và trả về một dòng thời gian rỗng. Nên phải bắt ở đây, nơi còn
    nói được nguyên nhân.
    """
    if not doan_tho:
        raise LoiPhienAm("STT khong tra ve doan nao")
    if not any(d.get("words") for d in doan_tho):
        raise LoiPhienAm(
            "STT tra ve doan nhung KHONG doan nao co `words` — ho so "
            f"`{HO_SO_STT}` bat buoc `word_timestamps=True`")


def _chieu_schema(doan: list[dict]) -> list[dict]:
    """Chiếu về ĐÚNG sáu khoá của hợp đồng đầu ra — bản sao của
    `bot/worker.py::_project_strict_schema`.

    🔴 Bản đầu của hàm này **giữ `words`** khi có, và **không sinh `index`**.
       Cả hai đều sai, và cả hai chỉ lộ ra khi đối chiếu với 1.932 lượt job
       thật ở `D:/FULL AUTO VIDEO/.../output/`: 6.934/6.934 đoạn ở đó có đúng
       tập khoá `{start, end, text, type, scene_id, index}`, và **0 đoạn** có
       `words`. Chú thích trong chính bot cũ nói thẳng: *"words kept internally
       in pipeline but NOT in final output"*.

    ⚠️ Sáu khoá này **luôn có mặt**, kể cả khi rỗng — `scene_id` thành `""` và
       `index` thành `0` chứ không biến mất. Một khoá vắng mặt và một khoá rỗng
       là hai thứ khác nhau với bên tiêu thụ.
    """
    ra: list[dict] = []
    for d in doan or []:
        if not isinstance(d, dict) or not d:
            continue
        ra.append({
            "start": float(d.get("start", 0.0)),
            "end": float(d.get("end", 0.0)),
            "text": str(d.get("text", "")),
            "type": str(d.get("type", "")),
            "scene_id": str(d.get("scene_id", "")),
            "index": int(d.get("index", 0)),
        })
    return ra


def _kiem_khong_trung_lien_tiep(doan: list[dict]) -> None:
    """Hai đoạn `speech` liên tiếp cùng nội dung là dấu hiệu whisper lặp.

    Đây là lỗi **nội dung**, không phải lỗi hình thức: tệp vẫn hợp lệ, khách vẫn
    đọc được, và câu bị lặp nằm giữa một bản dài. Bot legacy chặn nó, giữ nguyên.
    """
    truoc = ""
    for d in doan:
        if d.get("type") != "speech":
            truoc = ""
            continue
        van = " ".join(str(d.get("text") or "").lower().split())
        if van and van == truoc:
            raise LoiPhienAm(
                f"hai doan `speech` lien tiep trung noi dung: {van[:60]!r}")
        truoc = van


def _kiem_schema_nghiem_ngat(doan: list[dict]) -> None:
    if not doan:
        raise LoiPhienAm("dong thoi gian rong")
    for i, d in enumerate(doan):
        thieu = [k for k in KHOA_DOAN if k not in d]
        if thieu:
            raise LoiPhienAm(f"doan {i} thieu khoa {thieu}")
        if d["type"] not in LOAI_DOAN:
            raise LoiPhienAm(f"doan {i} co `type` la {d['type']!r}")
        try:
            bat_dau, ket_thuc = float(d["start"]), float(d["end"])
        except (TypeError, ValueError) as e:
            raise LoiPhienAm(f"doan {i} co moc khong phai so: {e}") from e
        if ket_thuc <= bat_dau:
            raise LoiPhienAm(
                f"doan {i} co end ({ket_thuc}) <= start ({bat_dau})")
    if not any(d["type"] == "speech" for d in doan):
        raise LoiPhienAm("dong thoi gian khong co doan `speech` nao")


# ── Đường chạy ──────────────────────────────────────────────────────────────

def chay(yc: YeuCau, *, tien_do: Optional[Any] = None) -> KetQua:
    """Sáu bước. Không đụng Sheet, Drive, GPU arbiter hay hàng đợi.

    `tien_do` là một callable `(phan_tram: int, mo_ta: str)` do worker đưa vào —
    App không tự dựng cơ chế báo tiến độ.
    """
    def bao(pt: int, mo_ta: str) -> None:
        if tien_do is not None:
            tien_do(pt, mo_ta)

    duong = Path(yc.duong_audio)
    if not duong.is_file():
        raise LoiPhienAm(f"khong co tep audio: {duong}")

    bao(5, "do vung co tieng")
    vung = vad_speech_segments(str(duong))
    thoi_luong = float(audio_duration_seconds(str(duong)) or 0.0)
    log.info("vad_done vung=%d thoi_luong=%.2f", len(vung), thoi_luong)

    canh_bao: list[str] = []
    if vung and thoi_luong > 0:
        tong_tieng = sum(float(v["end"]) - float(v["start"]) for v in vung)
        ty_le = tong_tieng / thoi_luong
        if ty_le < 0.10:
            canh_bao.append(
                f"chi {ty_le:.1%} thoi luong co tieng — kiem lai dau vao")

    bao(15, "phien am")
    kq = stt.phien_am(duong, ten_ho_so=HO_SO_STT, model=yc.model,
                      ngon_ngu=yc.ngon_ngu or None)
    doan_tho = kq.get("segments") or []
    _kiem_co_mocs_tu(doan_tho)

    bao(70, "dung dong thoi gian")
    dong_thoi_gian = make_timeline_v2(
        doan_tho,
        audio_duration=thoi_luong or None,
        target_min=yc.min_s,
        target_max=yc.max_s,
        silence_threshold=yc.nguong_khoang_lang,
        silence_text=yc.chu_khoang_lang,
    )
    if not dong_thoi_gian:
        raise LoiPhienAm("dung dong thoi gian ra ket qua rong")
    if not yc.kem_khoang_lang:
        dong_thoi_gian = [d for d in dong_thoi_gian if d.get("type") != "silence"]

    bao(90, "kiem ket qua")
    doan = _chieu_schema(dong_thoi_gian)
    _kiem_khong_trung_lien_tiep(doan)
    _kiem_schema_nghiem_ngat(doan)

    bao(100, "xong")
    return KetQua(
        doan=doan,
        ngon_ngu=str(kq.get("language") or yc.ngon_ngu or ""),
        do_tin_ngon_ngu=float(kq.get("language_probability") or 0.0),
        thoi_luong_s=thoi_luong,
        so_vung_tieng=len(vung),
        canh_bao=tuple(canh_bao),
    )
