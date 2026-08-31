"""
V10 · bánh cóc cho chính **cổng** chất lượng.

`tools/cong_chat_luong_voice.py` chạm GPU nên nó không vào bộ test được. Nhưng
ba tính chất khiến nó là một **cổng** chứ không phải một bản báo cáo thì kiểm
được mà không cần GPU, và đó là ba thứ dễ mất nhất khi ai đó sửa nhanh:

  ① baseline phải TỒN TẠI và ĐÚNG cấu hình hiện tại — đổi `tham_so.py` mà không
    đo lại thì đỏ;
  ② dung sai phải đến từ SỐ ĐO, không phải một hằng số gõ tay;
  ③ cổng không được chứa phép đo đã có ngưỡng tuyệt đối có nguồn — một dải
    quanh trung bình có thể **nới lỏng** một bảo đảm.

⭐ Điều kiện V10 nói: *"baseline ghim theo phiên bản; v3 full không được lên chỉ
   vì nghe hay hơn; đổi `tham_so.py` cũng phải qua cổng này"*. Ba câu ấy đều quy
   về ① — khoá phiên bản là thứ biến "một bản báo cáo" thành "một cái cổng".
"""
from __future__ import annotations

import json
import pathlib

import pytest

GOC = pathlib.Path(__file__).resolve().parents[1]
TEP = GOC / "voice_sidecar" / "baseline_chat_luong.json"


def _bl() -> dict:
    assert TEP.is_file(), (
        f"khong co baseline ({TEP}). Chay "
        f"`setup\\cong_chat_luong_voice.ps1 -Ghim`.")
    return json.loads(TEP.read_text(encoding="utf-8"))


def test_baseline_DUNG_cho_phien_ban_tham_so_HIEN_TAI():
    """🔴 Đây là câu chốt của V10, và nó chỉ là một phép so chuỗi.

    `tham_so.py` giữ `temperature`, `top_k`, `top_p`, `max_new_frames` — đổi bất
    cứ số nào cũng đổi **mọi** chỉ số chất lượng. Trước hôm nay không có gì bắt
    người đổi phải đo lại: `do_chat_luong.phan_quyet` tự khai rằng CER, tương
    đồng người nói và trôi giọng *"được BÁO SỐ và đánh dấu `chua_hieu_chuan` —
    chúng không tham gia kết luận"*.

    ⭐ Nên "cổng" ở đây không phải một ngưỡng chất lượng tuyệt đối — không có
       ngưỡng tuyệt đối nào đúng cho CER cả. Nó là một **khoá phiên bản**: đổi
       tham số ⇒ baseline hết hiệu lực ⇒ phải đo lại ⇒ và lúc đo lại thì mọi con
       số nằm trên bàn cho người ta nhìn.

       Đó cũng là cách duy nhất chặn được *"v3 full nghe hay hơn nên cho lên"*.
    """
    from voice_sidecar import tham_so

    bl = _bl()
    khoa = bl.get("khoa") or {}
    assert khoa.get("phien_ban_tham_so") == tham_so.PHIEN_BAN_THAM_SO, (
        f"baseline ghim cho tham so {khoa.get('phien_ban_tham_so')!r}, hien tai "
        f"la {tham_so.PHIEN_BAN_THAM_SO!r}.\n"
        f"Doi tham so la DOI PHEP DO — chay lai "
        f"`setup\\cong_chat_luong_voice.ps1 -Ghim` de do lai, dung sua tay "
        f"chuoi phien ban trong baseline.")


def test_baseline_DUNG_cho_corpus_HIEN_TAI():
    """Đổi corpus cũng là đổi phép đo — CER của bộ câu này không so được với CER
    của bộ câu khác."""
    import hashlib

    from tools import cong_chat_luong_voice as cong

    bam = hashlib.sha256(chr(10).join(cong.CORPUS).encode()).hexdigest()[:16]
    khoa = _bl().get("khoa") or {}
    assert khoa.get("bam_corpus") == bam, (
        "baseline ghim cho mot corpus KHAC. Chay lai `-Ghim`.")
    assert khoa.get("so_cau") == len(cong.CORPUS)


def test_moi_cau_trong_corpus_DU_DAI_de_do_duoc_troi_giong():
    """🔴 Corpus quá ngắn thì chỉ số quan trọng nhất VẮNG MẶT, và cổng vẫn xanh.

    `do_troi_giong` cắt cửa sổ `CUA_SO_TROI_S` giây và cần **ít nhất hai** cửa
    sổ; ngắn hơn thì nó trả `{"co": False}`. Lô ghim đầu tiên (01/09) dùng tám
    câu ngắn, và baseline dựng lên **thiếu hẳn** `on_dinh_giong` — không có gì
    báo, nó chỉ đơn giản không có trong bảng.

    ⛔ Một cổng thiếu một mục vẫn in ra `CONG XANH`. Đó là kiểu hỏng tệ nhất của
       một cổng: nó không nói dối, nó chỉ **không nhắc tới** thứ nó không đo.

    Phép kiểm ước độ dài từ số ký tự bằng `gia.giay_uoc` — chính hàm nền tảng
    dùng để giữ chỗ credit, nên không cần chạm GPU.
    """
    from apps.ltt_voice import gia
    from tools import cong_chat_luong_voice as cong
    from voice_sidecar.do_chat_luong import CUA_SO_TROI_S

    can = 2 * CUA_SO_TROI_S
    ngan = [(i, len(c), round(gia.giay_uoc(len(c)), 1))
            for i, c in enumerate(cong.CORPUS)
            if gia.giay_uoc(len(c)) < can]
    assert not ngan, (
        f"{len(ngan)}/{len(cong.CORPUS)} cau uoc ngan hon {can}s nen "
        f"`do_troi_giong` se khong chay: {ngan}")


def test_baseline_co_DU_moi_phep_do_ma_cong_se_hoi():
    """Baseline thiếu một mục ⇒ cổng không bao giờ kiểm mục đó, và vẫn xanh."""
    bl = _bl()
    co = set(bl.get("do") or {})
    can = {"cer", "wer", "on_dinh_giong", "rtf", "_ty_le_hong"}
    assert can <= co, f"baseline thieu {sorted(can - co)}"


def test_dung_sai_den_tu_SO_DO_chu_khong_go_tay():
    """⛔ Một dung sai gõ tay là chọn giữa hai cái sai.

    Rộng quá thì cổng không bắt được gì; hẹp quá thì nó đỏ vì nhiễu và **sẽ bị
    tắt trong một tuần** — kéo theo cả những mục nó bảo vệ đúng.

    Nên mỗi mục phải mang theo `lech` **đo được giữa các vòng**, và ngưỡng phải
    nằm cách trung bình đúng bằng `HE_SO_DUNG_SAI × lech` (hoặc sàn tối thiểu,
    tuỳ cái nào lớn hơn).
    """
    from tools import cong_chat_luong_voice as cong

    bl = _bl()
    assert bl.get("so_vong", 0) >= 2, (
        "baseline ghim bang 1 vong — mot vong khong do duoc DO LECH, va khong "
        "co do lech thi dung sai phai go tay")

    for ten, muc in (bl.get("do") or {}).items():
        assert "lech" in muc, f"{ten}: baseline khong mang do lech"
        thap, cao = cong._nguong(ten, muc["tb"], muc["lech"])
        assert muc.get("thap") == thap and muc.get("cao") == cao, (
            f"{ten}: nguong trong baseline ({muc.get('thap')}, {muc.get('cao')}) "
            f"khac nguong tinh lai ({thap}, {cao}) — ai do da sua tay")


@pytest.mark.parametrize("ten", ["lufs", "true_peak_dbtp"])
def test_cong_KHONG_chua_phep_do_da_co_nguong_tuyet_doi(ten):
    """🔴 Một dải quanh trung bình có thể NỚI LỎNG một bảo đảm tuyệt đối.

    `lufs` và `true_peak_dbtp` đã có ngưỡng có nguồn (EBU R128 / ITU-R BS.1770-4)
    và `do_chat_luong.phan_quyet` đã chốt chúng. Đưa chúng vào cổng tương đối
    này là thay một bảo đảm bằng một dải.

    ⭐ Không phải lo xa. Lô ghim đầu tiên (01/09) tính ra trần `true_peak`
       **+0,0479 dBTP** — tức cổng sẽ cho qua một bản **vỡ tiếng**, trong khi
       hợp đồng nói trần là **−1,0**. Một cổng làm cho hệ thống lỏng hơn lúc
       chưa có nó.
    """
    from tools import cong_chat_luong_voice as cong

    assert ten not in cong.CHIEU, f"{ten} khong duoc nam trong cong tuong doi"
    assert ten not in (_bl().get("do") or {}), (
        f"baseline con giu {ten} — ghim lai sau khi bo no khoi bo do")
