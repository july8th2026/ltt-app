"""Nghiệp vụ của App `audio_pause`: chèn khoảng lặng tại những **mốc văn bản**.

**GUI, Macro Node và (sau này) API đều gọi hàm ở đây** — bất biến #2.

## Sáu bước — y hệt `bot_pause`, bỏ đúng phần điều phối

```
1 chuẩn hoá WAV      audio_splicer.convert_to_wav()
2 STT                platform_core.stt   hồ sơ `moc_tu_vad_trong_{vi,en}`
3 khớp mốc mờ        anchor_matcher.match_all_anchors(threshold)
4 lập kế hoạch chèn  insertion_planner.generate_insertion_plan()
5 nắn về điểm im     audio_splicer.snap_all_cut_points()
6 cắt · chèn · nối   _ghep_voi_khoang_lang()
7 dịch mốc thời gian transcript_adjuster.adjust_transcript_timestamps()
```

## 🔴 Bước 5 là mục P0 dễ mất nhất của cả chương trình

Chèn lặng **đúng tại mốc** sẽ cắt giữa một từ. `find_silence_point` quét RMS
từng bước 5 ms trong một cửa sổ **chỉ nằm SAU** từ đứng trước, và khi khoảng
trống báo về nhỏ hơn 0,10 s thì nó **nới thêm 300 ms** — vì mốc của Whisper
thường sớm hơn thực tế 100–200 ms.

⛔ Một bản port "chèn tại `t`" **chạy được, ra tệp nghe được, và sai**. Không
   phép kiểm hình thức nào kêu: tệp vẫn hợp lệ, thời lượng vẫn đúng.

## `_ghep_voi_khoang_lang` đến từ `bot/worker.py`, không từ `engine/`

Ở bản legacy nó nằm lẫn trong tầng điều phối. Đó là **nghiệp vụ**, nên nó về
đây. Giữ nguyên hai luật của nó, cả hai đều là hành vi thật:

- điểm cắt là `{0.0} ∪ {mốc} ∪ {hết tệp}`, **đã khử trùng**;
- hai mốc rơi đúng cùng một giây thì **gộp, lấy khoảng lặng LỚN HƠN** — không
  cộng dồn, và không im lặng bỏ một cái.
"""
from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from platform_core.stt import service as stt

from .engine import (anchor_matcher, audio_splicer, insertion_planner,
                     transcript_adjuster)

log = logging.getLogger("apps.audio_pause")

#: Hồ sơ STT theo NĂNG LỰC (`platform_core/stt/ho_so.py`), chọn theo ngôn ngữ.
#: `moc_tu_vad_trong` = có mốc từ, VAD chạy **bên trong** whisper — và chính
#: ranh giới đoạn do VAD ấy tạo ra là thứ bước 5 dùng để quyết định cắt ở đâu.
HO_SO_STT = "moc_tu_vad_trong"

#: Ngôn ngữ mà hồ sơ STT có biến thể. Ngoài danh sách này thì không đoán.
NGON_NGU_CO_HO_SO = ("vi", "en")

KHOA_MOC = ("id", "anchor_text", "pause_ms")


class LoiChenLang(ValueError):
    """Đầu vào hoặc kết quả không dùng được."""


@dataclass(frozen=True)
class YeuCau:
    duong_audio: str
    ke_hoach: list[dict]
    ngon_ngu: str = "vi"
    nguong_khop: float = 0.65
    min_pause_ms: int = 50
    max_pause_ms: int = 15000
    min_gap_s: float = 0.8
    model: str = "large-v3"


@dataclass(frozen=True)
class KetQua:
    duong_audio_ra: str
    transcript: dict
    so_moc_khop: int
    so_moc_truot: int
    ma_moc_truot: tuple[str, ...]
    tong_lang_ms: int
    canh_bao: tuple[str, ...] = field(default_factory=tuple)

    def as_result(self) -> dict:
        return {
            "audio": self.duong_audio_ra,
            "transcript": self.transcript,
            "matched": self.so_moc_khop,
            "failed": self.so_moc_truot,
            "failed_ids": list(self.ma_moc_truot),
            "total_silence_ms": self.tong_lang_ms,
            "warnings": list(self.canh_bao),
        }


def chuan_hoa(params: dict) -> YeuCau:
    """Tham số thô → `YeuCau`. Từ chối **trước khi chạy**, không dừng giữa chừng."""
    p = dict(params or {})
    duong = str(p.get("audio") or p.get("duong_audio") or "").strip()
    if not duong:
        raise LoiChenLang("thieu tham so `audio`")

    ke_hoach = p.get("pause_plan") or p.get("ke_hoach") or []
    if not isinstance(ke_hoach, list) or not ke_hoach:
        raise LoiChenLang("`pause_plan` phai la mot danh sach khong rong")
    for i, muc in enumerate(ke_hoach):
        if not isinstance(muc, dict):
            raise LoiChenLang(f"moc {i} khong phai mot doi tuong")
        thieu = [k for k in KHOA_MOC if k not in muc]
        if thieu:
            raise LoiChenLang(f"moc {i} thieu khoa {thieu}")

    ngon_ngu = str(p.get("language") or "vi").strip().lower()
    if ngon_ngu not in NGON_NGU_CO_HO_SO:
        # ⛔ Không đoán: hồ sơ STT của App này khác nhau theo ngôn ngữ
        #    (`beam_size` 5 với `vi`, 1 với `en`). Chạy tiếng Pháp bằng hồ sơ
        #    tiếng Việt vẫn ra kết quả hợp lệ — chỉ là khác đi.
        raise LoiChenLang(
            f"`language` phai la mot trong {list(NGON_NGU_CO_HO_SO)}, "
            f"nhan {ngon_ngu!r}")

    try:
        min_ms = int(p.get("min_pause_ms", 50))
        max_ms = int(p.get("max_pause_ms", 15000))
        nguong = float(p.get("nguong_khop", 0.65))
        min_gap = float(p.get("min_gap_s", 0.8))
    except (TypeError, ValueError) as e:
        raise LoiChenLang(f"tham so so khong hop le: {e}") from e
    if min_ms <= 0 or max_ms <= 0 or min_ms >= max_ms:
        raise LoiChenLang(
            f"can 0 < min_pause_ms < max_pause_ms, nhan {min_ms}/{max_ms}")
    if not 0.0 < nguong <= 1.0:
        raise LoiChenLang(f"`nguong_khop` phai trong (0, 1], nhan {nguong}")

    return YeuCau(duong_audio=duong, ke_hoach=list(ke_hoach),
                  ngon_ngu=ngon_ngu, nguong_khop=nguong,
                  min_pause_ms=min_ms, max_pause_ms=max_ms, min_gap_s=min_gap,
                  model=str(p.get("model") or "large-v3"))


def _thoi_luong_wav(duong: str) -> float:
    """ffprobe. Ném khi không đọc được — một thời lượng đoán bừa làm hỏng điểm
    cắt cuối cùng, và hỏng theo kiểu tệp vẫn phát được."""
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", duong],
        capture_output=True, text=True)
    if r.returncode != 0:
        raise LoiChenLang(f"ffprobe that bai: {r.stderr[:200]}")
    try:
        return float(r.stdout.splitlines()[0])
    except (ValueError, IndexError) as e:
        raise LoiChenLang(f"ffprobe tra ve khong phai so: {r.stdout[:80]!r}") from e


def _ghep_voi_khoang_lang(duong_wav: str, ke_hoach_chen: list[dict],
                          thu_muc: Path, sample_rate: int,
                          channels: int = 1) -> str:
    """Cắt · chèn lặng · nối. Chuyển từ `bot/worker.py::splice_audio_with_pauses`.

    ⚠️ Hai mốc rơi đúng cùng một giây thì **gộp và lấy cái LỚN HƠN**, không cộng
       dồn. Cộng dồn nghe có vẻ hợp lý hơn, nhưng nó không phải hành vi đã chạy
       một năm — và ở đây "hợp lý hơn" chính là cách một bản port làm mất parity.
    """
    theo_thu_tu = sorted(ke_hoach_chen, key=lambda x: x["at_sec"])
    thoi_luong = _thoi_luong_wav(duong_wav)

    diem_cat = sorted(set([0.0] + [p["at_sec"] for p in theo_thu_tu]
                          + [thoi_luong]))

    lang_tai: dict[float, int] = {}
    for p in theo_thu_tu:
        khoa = p["at_sec"]
        if khoa in lang_tai:
            lang_tai[khoa] = max(lang_tai[khoa], int(p["pause_ms"]))
            log.info("pause_collision_merged at_sec=%s pause_ms=%s",
                     khoa, lang_tai[khoa])
        else:
            lang_tai[khoa] = int(p["pause_ms"])

    thu_muc_doan = thu_muc / "doan"
    thu_muc_doan.mkdir(exist_ok=True)

    cac_tep: list[str] = []
    for i in range(len(diem_cat) - 1):
        bat_dau, ket_thuc = diem_cat[i], diem_cat[i + 1]
        if ket_thuc - bat_dau < 0.001:
            continue
        if bat_dau in lang_tai:
            lang = thu_muc_doan / f"lang_{i:03d}.wav"
            audio_splicer.generate_silence(str(lang), lang_tai[bat_dau],
                                           sample_rate, channels=channels)
            cac_tep.append(str(lang))
        doan = thu_muc_doan / f"doan_{i:03d}.wav"
        audio_splicer.cut_audio_segment(duong_wav, str(doan), bat_dau, ket_thuc)
        cac_tep.append(str(doan))

    if not cac_tep:
        raise LoiChenLang("khong sinh ra doan nao de noi")

    ra = thu_muc / "ra.wav"
    audio_splicer.concat_audio_files(cac_tep, str(ra))
    return str(ra)


def chay(yc: YeuCau, thu_muc: Path, *,
         tien_do: Optional[Any] = None) -> KetQua:
    """Bảy bước. Không đụng Sheet, Drive, GPU arbiter hay hàng đợi."""
    def bao(pt: int, mo_ta: str) -> None:
        if tien_do is not None:
            tien_do(pt, mo_ta)

    nguon = Path(yc.duong_audio)
    if not nguon.is_file():
        raise LoiChenLang(f"khong co tep audio: {nguon}")

    bao(5, "chuan hoa WAV")
    wav = thu_muc / "vao.wav"
    audio_splicer.convert_to_wav(str(nguon), str(wav))

    bao(15, "phien am")
    kq_stt = stt.phien_am(wav, ten_ho_so=HO_SO_STT, model=yc.model,
                          ngon_ngu=yc.ngon_ngu)
    transcript = {"segments": kq_stt.get("segments") or [],
                  "language": kq_stt.get("language") or yc.ngon_ngu}
    if not transcript["segments"]:
        raise LoiChenLang("STT khong tra ve doan nao")

    bao(50, "khop moc")
    ban_do = anchor_matcher.match_all_anchors(
        yc.ke_hoach, transcript, threshold=yc.nguong_khop)
    khop = ban_do.get("matched") or []
    truot = ban_do.get("failed") or []
    if not khop:
        raise LoiChenLang(
            f"khong moc nao khop (nguong {yc.nguong_khop}) — "
            f"{len(truot)} moc truot")

    bao(60, "lap ke hoach chen")
    ke_hoach_chen = insertion_planner.generate_insertion_plan(
        ban_do, min_gap_s=yc.min_gap_s,
        min_pause_ms=yc.min_pause_ms, max_pause_ms=yc.max_pause_ms)
    if not ke_hoach_chen:
        raise LoiChenLang("ke hoach chen rong sau khi loc chong/gian cach")

    bao(70, "nan ve diem im")
    audio_splicer.snap_all_cut_points(str(wav), ke_hoach_chen, khop)

    bao(80, "cat va noi")
    sr, kenh = _thong_so_wav(str(wav))
    ra = _ghep_voi_khoang_lang(str(wav), ke_hoach_chen, thu_muc, sr, kenh)

    bao(95, "dich moc thoi gian")
    transcript_moi = transcript_adjuster.adjust_transcript_timestamps(
        transcript, ke_hoach_chen)

    bao(100, "xong")
    return KetQua(
        duong_audio_ra=ra,
        transcript=transcript_moi,
        so_moc_khop=len(khop),
        so_moc_truot=len(truot),
        ma_moc_truot=tuple(str(x.get("id")) for x in truot),
        tong_lang_ms=sum(int(p["pause_ms"]) for p in ke_hoach_chen),
        canh_bao=(f"{len(truot)} moc khong khop",) if truot else (),
    )


def _thong_so_wav(duong: str) -> tuple[int, int]:
    """`(sample_rate, channels)` đọc từ chính tệp — không giả định 24 kHz mono.

    Bản legacy lấy hai số này từ cấu hình. Đọc từ tệp đúng hơn: khoảng lặng
    sinh ra phải khớp **tệp thật**, và một tệp lệch tần số sẽ nối ra tiếng méo
    chứ không báo lỗi.
    """
    import wave

    with wave.open(duong, "rb") as f:
        return f.getframerate(), f.getnchannels()
