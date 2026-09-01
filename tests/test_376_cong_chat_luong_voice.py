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


def test_ghim_phien_ban_bo_do_THAT_SU_noi_vao_bo_do():
    """Khoá baseline phải đọc phiên bản **từ bộ đo**, không từ một mặc định cứng.

    🔴 Đây là một cái ghim đã tồn tại và **không nối vào gì cả** suốt từ khi
       viết. `tools/cong_chat_luong_voice.py` tra
       `do_chat_luong.do_tat_ca.__globals__.get("_PHIEN_BAN_BO_DO", <mặc định>)`
       trong khi `do_chat_luong.py` để phiên bản **bên trong dict trả về**, chứ
       không phải ở cấp module. Tên ấy chưa bao giờ tồn tại, nên phép tra luôn
       rơi vào giá trị mặc định — và baseline **không bao giờ hết hiệu lực**,
       dù bộ đo có đổi thế nào.

    ⛔ Cùng lớp lỗi với một bánh cóc chưa từng đỏ: nó chạy, nó in ra một con số
       đúng đắn, và nó không canh gì. Phép kiểm này bắt cả hai đầu — tên phải
       tồn tại ở cấp module, VÀ giá trị phải đi tới khoá baseline.
    """
    import json
    import subprocess
    import sys

    from voice_sidecar import do_chat_luong

    # (1) ten phai ton tai o cap module
    v = getattr(do_chat_luong, "_PHIEN_BAN_BO_DO", None)
    assert isinstance(v, str) and v, "thieu _PHIEN_BAN_BO_DO cap module"

    # (2) chinh dict tra ve phai dung no, khong phai mot chuoi thu hai
    src = (GOC / "voice_sidecar" / "do_chat_luong.py").read_text(encoding="utf-8")
    assert '"phien_ban_bo_do": _PHIEN_BAN_BO_DO,' in src, (
        "dict tra ve dang ghi mot chuoi rieng thay vi dung hang cap module")

    # (3) cong phai doc no, KHONG duoc co duong lui
    cong = (GOC / "tools" / "cong_chat_luong_voice.py").read_text(encoding="utf-8")
    assert "do_chat_luong._PHIEN_BAN_BO_DO" in cong, cong[:0]
    assert "__globals__" not in cong, (
        "cong dang tra bang __globals__.get(...) — mot ten sai se im lang roi "
        "vao mac dinh thay vi vo")

    # (4) va gia tri phai THUC SU di toi khoa baseline
    r = subprocess.run(
        [sys.executable, "-c",
         "import json,sys;sys.path.insert(0,r'%s');"
         "from voice_sidecar import do_chat_luong as d;"
         "print(json.dumps({'v': d._PHIEN_BAN_BO_DO}))" % str(GOC)],
        capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout.strip().splitlines()[-1])["v"] == v


#: Bốn phép K3 phải nằm trong cổng — mỗi phép kèm hỏng hóc nó đã CHỨNG MINH bắt
#: được, đo bằng `tools/do_diem_mu_cong.py` trên sàn nhiễu n = 24.
K3_TRONG_CONG = {
    "db_dai_cao": "duc 8,6 sigma / nhieu 6,8 sigma",
    "khop_cuc_bo_dinh": "lap-o-giua 4,4 sigma",
    "vat_99_hz": "nhieu 29,4 sigma",
    "trong_tam_hz": "nhieu 7,3 sigma",
}

#: Và những thứ TUYỆT ĐỐI KHÔNG được vào cổng tương đối, kèm lý do.
K3_NGOAI_CONG = {
    "khop_cuc_bo_tai_s": "vi tri, khong phai chat luong",
    "khop_cuc_bo_tre_s": "vi tri",
    "tre_dinh_s": "vi tri",
    "nhip_troi_hz": "vi tri tren truc tan so",
    "f0_so_cua_so": "mot CAI DEM — san nhieu bang 0",
}


def test_bon_phep_K3_nam_trong_baseline():
    """Bốn phép đã chứng minh bắt được hỏng hóc phải thật sự vào cổng.

    ⛔ Không phải chuyện đầy đủ cho đẹp. Lượt ghim đầu tiên sau khi viết bốn
       phép ấy cho ra một baseline **chỉ có 5 chỉ số cũ**: `_do_mot_vong` chỉ
       thu những chiều nó biết tên, nên bốn phép mới chạy, trả số, và **rơi ra
       ngoài cổng trong im lặng**. Mã đã viết mà cổng không dùng thì cổng vẫn
       mù đúng như trước.
    """
    do = (_bl().get("do") or {})
    thieu = {k: v for k, v in K3_TRONG_CONG.items() if k not in do}
    assert not thieu, (
        f"baseline thieu {sorted(thieu)} — ghim lai sau khi them vao "
        f"`_do_mot_vong`. Ly do tung phep: {thieu}")
    for k in K3_TRONG_CONG:
        assert do[k].get("n", 0) >= 3, (k, do[k])


def test_chi_so_VI_TRI_khong_duoc_vao_cong_tuong_doi():
    """Vị trí không có chiều tốt/xấu, nên một dải dung sai quanh nó vô nghĩa.

    🔴 Cùng lớp với `f0_so_cua_so`: một con số thay đổi theo độ dài chứ không
       theo chất lượng. Nó từng lọt vào bộ dò điểm mù và in ra **1.000.000σ**
       — một phát hiện giả đủ to để tuyên bố một điểm mù đã đóng trong khi nó
       còn nguyên.
    """
    from tools import cong_chat_luong_voice as cong

    do = (_bl().get("do") or {})
    for ten, ly_do in K3_NGOAI_CONG.items():
        assert ten not in do, f"{ten} lot vao baseline ({ly_do})"
        assert ten not in cong.CHIEU, f"{ten} lot vao CHIEU ({ly_do})"


def test_db_dai_cao_phai_chan_CA_HAI_phia():
    """Quá sáng cũng sai như quá đục — nên chiều phải là 0, không phải ±1.

    Đo được: lọc thông thấp kéo `db_dai_cao` **-31 -> -49**; nhiễu trắng đẩy nó
    **-31 -> -17**. Chặn một phía là bỏ lọt đúng một nửa số cách hỏng.
    """
    from tools import cong_chat_luong_voice as cong

    for ten in ("db_dai_cao", "trong_tam_hz", "vat_99_hz"):
        assert cong.CHIEU.get(ten, "thieu") == 0, (
            f"{ten} phai hai chieu")
        m = (_bl().get("do") or {}).get(ten)
        if m:
            assert m.get("thap") is not None and m.get("cao") is not None, (ten, m)
