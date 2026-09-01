r"""
test_388 — K4: tầng lệch-tham-chiếu và tầng chẩn đoán.

## Phép kiểm quan trọng nhất trong tệp này là phép kiểm RANH GIỚI

Hệ cũ (`D:\Voiceclone_TTS`) cưỡng chế ba tầng bằng luật import:

    metrics/   → CHỈ tính số. Không diễn giải.
    diagnosis/ → CHỈ diễn giải số. KHÔNG import numpy/soundfile/torch.
    report/    → CHỈ định dạng.

⭐ Đó là thứ đáng mang sang nhất trong cả hệ ấy, hơn bất cứ luật R nào. Khi một
   tệp vừa đo vừa phán, **không ai còn tách được "số đo sai" khỏi "cách đọc
   sai"** — và K3 mất trọn hai lượt đo vì đúng chuyện đó: tôi sửa chỉ số để đuổi
   theo một ngưỡng, trong khi thứ hỏng là cái thước.

Tách ra thì hai câu hỏi tách ra, và tầng chẩn đoán **chạy được ở mọi nơi** —
không GPU, không thư viện âm thanh — nên nó test được rẻ và nhiều.
"""
from __future__ import annotations

import ast
import pathlib

import pytest

GOC = pathlib.Path(__file__).resolve().parents[1]
CD = GOC / "voice_sidecar" / "chan_doan.py"
LTC = GOC / "voice_sidecar" / "lech_tham_chieu.py"


# ── ranh giới tầng ──────────────────────────────────────────────────────────

CAM = {"numpy", "soundfile", "torch", "librosa", "scipy", "soxr"}


def test_tang_chan_doan_KHONG_import_thu_vien_am_thanh():
    """Luật Rule 2 của hệ cũ, mang sang nguyên vẹn và có bánh cóc.

    ⛔ Hỏi CÂY CÚ PHÁP, đừng khớp chuỗi: một bánh cóc khớp với chính lời giải
       thích của nó thì không chốt gì (đã mắc bốn lần trong dự án này).
    """
    cay = ast.parse(CD.read_text(encoding="utf-8"))
    xau = []
    for n in ast.walk(cay):
        if isinstance(n, ast.Import):
            xau += [a.name.split(".")[0] for a in n.names]
        elif isinstance(n, ast.ImportFrom) and n.module:
            xau.append(n.module.split(".")[0])
    lan = CAM & set(xau)
    assert not lan, (
        f"`chan_doan.py` dang import {sorted(lan)}. Tang chan doan CHI duoc "
        f"dien giai so; moi phep tinh tren am thanh thuoc `lech_tham_chieu.py`.")


def test_tang_chan_doan_nap_duoc_KHONG_CAN_gi_ca():
    """Nạp được ở một tiến trình trần — đó là cả mục đích của ranh giới."""
    import importlib.util
    sp = importlib.util.spec_from_file_location("chan_doan_thu", CD)
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    assert callable(m.chan_doan)


def test_tang_so_lieu_KHONG_phan_tot_xau():
    """`lech_tham_chieu.py` chỉ được trả SỐ, không được trả nhãn phán xét.

    Một tệp đo mà lỡ trả `{"dat": True}` thì tầng trên sẽ dùng nhãn ấy, và
    ngưỡng nằm rải ở hai nơi — đúng thứ ranh giới này sinh ra để ngăn.
    """
    src = LTC.read_text(encoding="utf-8")
    cay = ast.parse(src)
    for n in ast.walk(cay):
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            v = n.value
            if len(v) < 40 and v in ("dat", "hong", "canh_bao", "nghiem_trong",
                                     "pass", "fail", "warn"):
                pytest.fail(f"tang so lieu dang tra nhan phan xet: {v!r}")


# ── hợp đồng của tầng chẩn đoán ─────────────────────────────────────────────

def _cd():
    import importlib.util
    sp = importlib.util.spec_from_file_location("chan_doan_thu", CD)
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


def test_khong_co_baseline_thi_NOI_RA_chu_khong_im_lang():
    """🔴 Đây là chỗ một tầng chẩn đoán hỏng theo kiểu tệ nhất.

    Thiếu ngưỡng mà trả danh sách rỗng thì nó trông **y hệt** "đã soi và không
    thấy gì bất thường". Hai câu ấy dẫn tới hai hành động ngược nhau: một câu
    bảo đi đo baseline, câu kia bảo yên tâm.
    """
    m = _cd()
    for san in (None, {}, ):
        kq = m.chan_doan({"delta_lufs": 9.0}, san)
        assert kq["da_do"] is False
        assert kq["phat_hien"] == []
        assert kq["ly_do_khong_do"], "phai noi VI SAO khong do duoc"


def test_khong_lech_thi_khong_phat_hien():
    m = _cd()
    san = {"delta_lufs": {"tb": 0.0, "lech": 1.0}}
    kq = m.chan_doan({"delta_lufs": 0.2}, san)
    assert kq["da_do"] is True and kq["phat_hien"] == []


def test_bat_dung_CHIEU():
    """R13 (trầm hơn) chỉ nổ khi lệch ÂM; R14 (cao hơn) chỉ khi DƯƠNG.

    ⛔ Đảo chiều một luật là biến nó thành luật ngược lại — nó sẽ im đúng lúc
       chất lượng tụt và kêu đúng lúc mọi thứ ổn. Cùng lớp lỗi với
       `on_dinh_giong` từng suýt bị đặt sai chiều trong cổng V10.
    """
    m = _cd()
    san = {"delta_f0_trung_vi_hz_ti_le": {"tb": 0.0, "lech": 0.01}}
    tram = m.chan_doan({"delta_f0_trung_vi_hz_ti_le": -0.30}, san)
    cao = m.chan_doan({"delta_f0_trung_vi_hz_ti_le": +0.30}, san)
    assert [p["ma"] for p in tram["phat_hien"]] == ["R13"]
    assert [p["ma"] for p in cao["phat_hien"]] == ["R14"]


def test_luat_hai_chieu_no_o_ca_hai_phia():
    m = _cd()
    san = {"delta_lufs": {"tb": 0.0, "lech": 0.1}}
    for v in (-9.0, +9.0):
        ma = [p["ma"] for p in m.chan_doan({"delta_lufs": v}, san)["phat_hien"]]
        assert "R17" in ma, (v, ma)


def test_SAN_tuyet_doi_chan_dai_dung_sai_qua_hep():
    """Một chỉ số tình cờ rất ổn định trong lô baseline có `lech` bé xíu.

    4×lech khi ấy là một dải hẹp tới mức MỌI bản đều "bất thường" — và một cổng
    kêu ở mọi bản là một cổng bị tắt trong một tuần.
    """
    m = _cd()
    san = {"delta_lufs": {"tb": 0.0, "lech": 1e-9}}
    kq = m.chan_doan({"delta_lufs": 0.5}, san)
    assert kq["phat_hien"] == [], (
        f"SAN['delta_lufs']={m.SAN['delta_lufs']} phai chan dai dung sai lai")


def test_moi_luat_deu_co_KHUYEN_NGHI():
    """Một phát hiện không kèm việc phải làm là một phát hiện bị bỏ qua."""
    m = _cd()
    for ma, chi_so, chieu, nhan, khuyen in m.LUAT:
        assert nhan.strip() and khuyen.strip(), ma
        assert chieu in (-1, 0, 1), (ma, chieu)


def test_moi_luat_deu_co_SAN_tuyet_doi():
    """Thiếu sàn cho một chỉ số ⇒ luật ấy phụ thuộc hoàn toàn vào `lech` đo được.

    Và `lech` có thể bé bất thường ở một lô baseline không may.
    """
    m = _cd()
    thieu = sorted({c for _, c, _, _, _ in m.LUAT} - set(m.SAN))
    assert not thieu, f"chi so thieu SAN tuyet doi: {thieu}"


def test_ma_luat_GIU_NGUYEN_so_cua_he_cu():
    """R11–R17 giữ nguyên số, có chủ ý.

    Ai đọc báo cáo của hệ cũ sẽ nhận ra ngay, và ai đi tìm "R12 là gì" sẽ tìm
    thấy cùng một khái niệm ở cả hai nơi. Đổi số cho gọn là vứt đi phần duy
    nhất của hệ cũ mà người dùng đã thuộc.
    """
    m = _cd()
    ma = {x[0] for x in m.LUAT}
    assert {"R13", "R14", "R15", "R16", "R17"} <= ma, sorted(ma)
    assert any(x.startswith("R12") for x in ma), sorted(ma)


def test_xep_nang_truoc():
    m = _cd()
    san = {"delta_lufs": {"tb": 0.0, "lech": 0.1},
           "delta_f0_tan_tuong_doi": {"tb": 0.0, "lech": 0.01}}
    kq = m.chan_doan({"delta_lufs": 1.6, "delta_f0_tan_tuong_doi": -5.0}, san)
    muc = [p["muc"] for p in kq["phat_hien"]]
    assert muc == sorted(muc, key=lambda x: {"nang": 0, "vua": 1, "nhe": 2}[x])


def test_tom_tat_phan_biet_KHONG_DO_voi_KHONG_LECH():
    m = _cd()
    a = m.tom_tat(m.chan_doan({"delta_lufs": 9.0}, None))
    b = m.tom_tat(m.chan_doan({"delta_lufs": 0.0},
                              {"delta_lufs": {"tb": 0.0, "lech": 1.0}}))
    assert "KHONG DO" in a and "KHONG DO" not in b, (a, b)


# ── tầng số liệu ────────────────────────────────────────────────────────────

def test_lech_KHONG_tra_ra_cai_dem():
    """Cùng luật với K3: một cái đếm có sàn nhiễu bằng 0 và đẻ ra sigma giả."""
    src = LTC.read_text(encoding="utf-8")
    cay = ast.parse(src)
    for n in ast.walk(cay):
        if isinstance(n, ast.Assign) and len(n.targets) == 1:
            t = n.targets[0]
            if (isinstance(t, ast.Subscript) and isinstance(t.slice, ast.Constant)
                    and isinstance(t.slice.value, str)
                    and t.slice.value.startswith("so_")):
                pytest.fail(f"tang so lieu dang tra mot cai dem: {t.slice.value}")


def test_dau_luon_la_SINH_RA_tru_THAM_CHIEU():
    """Chốt chiều của phép trừ bằng một lượt chạy thật trên tín hiệu tổng hợp."""
    np = pytest.importorskip("numpy")
    from voice_sidecar import lech_tham_chieu as L

    sr = 24000
    t = np.arange(int(sr * 4.0)) / sr
    goc = (0.4 * np.sin(2 * np.pi * 130.0 * t)).astype("float32")
    # bản "sinh ra" TRẦM hơn: 100 Hz so với 130 Hz
    ra = (0.4 * np.sin(2 * np.pi * 100.0 * t)).astype("float32")
    d = L.do_lech(ra, sr, goc, sr)
    k = "delta_f0_trung_vi_hz_ti_le"
    assert k in d, d
    assert d[k] < 0, (
        f"{k}={d[k]} — ban sinh ra TRAM hon nen hieu phai AM. Dao dau la bien "
        f"R13 thanh R14.")


# ── nối vào bộ đo ───────────────────────────────────────────────────────────

def test_do_tat_ca_LUON_co_muc_lech_tham_chieu():
    """Không có `ref` thì mục ấy phải NÓI RA, không được vắng mặt.

    ⛔ Trong một dict JSON, một khoá vắng mặt và một khoá `{"co": false}` trông
       khác nhau với máy nhưng **giống hệt nhau** với người đọc lướt một báo
       cáo. Cái thứ hai nói được "đã xét, thiếu đầu vào"; cái thứ nhất không
       nói gì, và người đọc điền vào chỗ trống bằng giả định của họ.
    """
    src = (GOC / "voice_sidecar" / "do_chat_luong.py").read_text(encoding="utf-8")
    ham = next(n for n in ast.walk(ast.parse(src))
               if isinstance(n, ast.FunctionDef) and n.name == "do_tat_ca")
    doan = ast.unparse(ham)
    assert "lech_tham_chieu" in doan, (
        "do_tat_ca chua goi tang lech — K4 da viet nhung khong ai dung")

    ph = next(n for n in ast.walk(ast.parse(src))
              if isinstance(n, ast.FunctionDef) and n.name == "_lech_va_chan_doan")
    d2 = ast.unparse(ph)
    assert "'co': False" in d2 or '"co": False' in d2, (
        "thieu ref phai tra {'co': False, 'ly_do': ...}")


def test_baseline_lech_thieu_thi_KHONG_NEM():
    """Bộ đo phải chạy được khi chưa có baseline lệch.

    ⛔ Một bộ đo ném vì thiếu MỘT baseline phụ là một bộ đo không dùng được ở
       máy mới — và người ta sẽ gỡ lời gọi ấy đi thay vì đi đo baseline.
    """
    import importlib.util
    sp = importlib.util.spec_from_file_location(
        "dcl_thu", GOC / "voice_sidecar" / "do_chat_luong.py")
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    assert m._lech_va_chan_doan(None, 24000, "")["co"] is False
    # `_san_lech` phai tra None (chua do) chu khong phai {} hay nem
    v = m._san_lech()
    assert v is None or isinstance(v, dict)


def test_cong_cu_do_baseline_GHEP_bang_xuat_xu_chu_khong_bang_TEN():
    """Ghép hồ sơ với clip gốc phải qua `ghi_chu.ma_cu`, không qua tên hiển thị.

    🔴 Bốn giọng đầu tiên của kho chung có `ghi_chu` RỖNG và tên đã đổi hoàn
       toàn ("Ivy - EN female, expressive" ← `hoathinh_female`). Ghép bằng tên
       là ghép trượt cả bốn — và trượt **im lặng**, ra một baseline đo trên ít
       giọng hơn mình tưởng.
    """
    src = (GOC / "tools" / "do_lech_tham_chieu.py").read_text(encoding="utf-8")
    cay = ast.parse(src)
    assert '"ma_cu"' in src or "'ma_cu'" in src
    # khong duoc ghep bang `ten` / `ten_hien_thi`
    for n in ast.walk(cay):
        if isinstance(n, ast.Compare):
            doan = ast.unparse(n)
            assert "ten_hien_thi" not in doan, f"ghep bang ten: {doan}"


def test_ban_xuat_ref_KEM_ghi_chu():
    """Bản xuất phải mang `ghi_chu` — nó là đường ghép duy nhất tới clip gốc.

    🔴 Bản đầu chỉ xuất `public_id` / `ten` / `ngon_ngu_khai` / `ref_b64`, và
       `do_lech_tham_chieu.py` ghép được **0 giọng**. Nó vỡ to tiếng với đúng lý
       do — đó là điều tốt — nhưng chỉ ở **cuối** một chuỗi ba bước có nâng
       quyền, sau khi đã chạy xong bước xuất.

    ⭐ Một phép kiểm tĩnh bắt cùng lỗi ấy trong 0,2 giây. Vỡ to tiếng là mức
       sàn; bắt sớm mới là thứ đáng thêm.
    """
    src = (GOC / "tools" / "xuat_ref_kho_chung.py").read_text(encoding="utf-8")
    cay = ast.parse(src)
    khoa = set()
    for n in ast.walk(cay):
        if isinstance(n, ast.Dict):
            khoa |= {k.value for k in n.keys
                     if isinstance(k, ast.Constant) and isinstance(k.value, str)}
    can = {"public_id", "ten", "ngon_ngu_khai", "ghi_chu", "ref_b64"}
    thieu = sorted(can - khoa)
    assert not thieu, f"ban xuat thieu truong: {thieu}"


def test_chan_doan_KHONG_anh_huong_PHAN_QUYET():
    """Chẩn đoán là TƯ VẤN, không phải phán quyết — và đó là một quyết định.

    Phần lớn luật R11–R17 chỉ ra vấn đề ở **clip tham chiếu của khách**, không
    phải ở đầu ra của ta. Đánh trượt lượt sinh vì đầu vào của khách là bắt họ
    trả tiền cho một lượt bị chặn mà họ không sửa được từ phía ta.

    ⛔ Nếu ai đó sau này muốn cho chẩn đoán chặn phán quyết thì phải sửa phép
       kiểm này TRƯỚC — tức phải đọc lý do ở trên và phản bác nó, chứ không phải
       thêm một dòng rồi thấy gate vẫn xanh.
    """
    src = (GOC / "voice_sidecar" / "do_chat_luong.py").read_text(encoding="utf-8")
    ham = next(n for n in ast.walk(ast.parse(src))
               if isinstance(n, ast.FunctionDef) and n.name == "phan_quyet")
    doan = ast.unparse(ham)
    for x in ("chan_doan", "lech_tham_chieu", "phat_hien"):
        assert x not in doan, (
            f"`phan_quyet` dang doc `{x}` — chan doan phai la TU VAN. "
            f"Xem chu thich o `chan_doan.LUAT`.")
