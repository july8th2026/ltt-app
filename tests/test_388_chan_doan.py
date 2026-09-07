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
    """R12–R17 giữ nguyên số của hệ cũ, có chủ ý.

    Ai đọc báo cáo của hệ cũ sẽ nhận ra ngay, và ai đi tìm "R12 là gì" sẽ tìm
    thấy cùng một khái niệm ở cả hai nơi. Đổi số cho gọn là vứt đi phần duy
    nhất của hệ cũ mà người dùng đã thuộc.
    """
    m = _cd()
    ma = {x[0] for x in m.LUAT}
    assert {"R13", "R14", "R17"} <= ma, sorted(ma)
    assert any(x.startswith("R12") for x in ma), sorted(ma)


def test_R16_DA_GO_va_phai_GIU_NGUYEN_nhu_the():
    """🔴 R16 (rung biên độ) đã gỡ, và việc đưa lại phải kèm một PHÉP ĐO.

    Không gỡ vì nó không quan trọng, mà vì **ta không có phép đo nào thấy được
    nó** — và điều đó đã chứng minh hai lần:

      · K3 thử BA cơ chế (năng lượng dải 3–8 Hz · độ nhọn trên bao tuyến tính ·
        độ nhọn trên **log** bao). Cao nhất 1,7σ, ngưỡng 4σ. Lý do là vật lý:
        nhịp rung giọng người (~5,5 Hz) **trùng nhịp âm tiết** tiếng Việt.
      · Ca tái hiện của K4 xác nhận lần nữa: rung **35%** — mạnh gấp sáu lần
        mức K3 thử — chỉ đẩy `delta_dao_dong_khung` đi −0,005 trên dung sai
        0,135, tức **sai chiều và bằng 1/27 ngưỡng**.

    ⛔ Một luật không bao giờ nổ tệ hơn không có luật: nó tạo ảo giác rằng rung
       giọng đang được canh. Phép kiểm này đỏ nếu ai đó đưa R16 về — buộc họ
       đọc lý do và mang theo một phép đo THẤY được nó, chứ không mang lại
       mỗi cái tên.
    """
    m = _cd()
    assert "R16" not in {x[0] for x in m.LUAT}, (
        "R16 quay lai — no co kem mot phep do THAY duoc rung bien do khong? "
        "Neu co thi sua phep kiem nay va ghi so do vao docstring.")
    assert "delta_dao_dong_khung" not in m.SAN, (
        "SAN con giu nguong cho mot chi so khong luat nao dung")


def test_R15_o_thang_TUONG_DOI_de_no_VOI_TOI_DUOC():
    """🔴 Ở thang tuyệt đối, R15 **không thể nổ dưới bất kỳ đầu vào nào**.

    `f0_tan_tuong_doi` là độ tản F0 chuẩn hoá, thực tế ~0,15 và không âm được.
    Nên hiệu tuyệt đối `ra − ref` bị chặn dưới ở khoảng **−0,15**: một bản đọc
    phẳng lì hoàn toàn cũng chỉ tới đó. Dung sai đo được là 4×0,042 = **0,168**
    — lớn hơn giá trị cực đại có thể đạt.

    ⭐ Ca tái hiện của K4 phát hiện điều này, và nó là loại lỗi mà đọc mã không
       thấy: luật đúng, ngưỡng đúng cách tính, chỉ là hai con số không bao giờ
       gặp nhau.

    🔴 **SỬA 01/09, CÙNG NGÀY: đổi sang thang tỉ lệ VẪN CHƯA ĐỦ, và R15 đã gỡ.**

    Đo lại sau khi đổi thang:

        nen  -0,4556   lech 0,2519   =>  dung sai 4x0,2519 = 1,0077
        R15 no khi gia tri < -1,4633
        can duoi TUYET DOI cua thang ti le = -1,0  (ban phang li hoan toan)

    Nền -0,4556 nghĩa là bản sinh ra **chỉ giữ 54% biến thiên cao độ** của clip
    gốc ở MỌI bản khoẻ mạnh. Nên câu hỏi *"bản này có phẳng hơn bình thường
    không"* hỏi sai — "bình thường" đã là 54%. Và độ lệch 0,2519 lớn tới mức
    một bản phẳng lì chỉ cách trung bình **2,2σ**.

    ⛔ Hạ hệ số σ riêng cho R15 chỉ là chỉnh ngưỡng cho tới khi luật chịu nổ.
    """
    m = _cd()
    assert "R15" not in {x[0] for x in m.LUAT}, (
        "R15 quay lai — dung sai co con vuot can duoi -1,0 khong?")


def test_KHONG_luat_nao_co_dung_sai_VUOT_DAI_gia_tri():
    """Bất biến mà R15 vi phạm hai lần theo hai cách khác nhau.

    Một luật có dung sai vượt dải khả dĩ của chính chỉ số nó đọc thì **không
    thể nổ** — và nó trông y hệt một luật đang canh tốt. Chốt được cho các chỉ
    số ở thang **tỉ lệ**, vì chỉ chúng mới có cận dưới biết trước: −1,0, tức
    bản sinh ra bằng 0 so với tham chiếu.
    """
    import json
    m = _cd()
    bl = GOC / "voice_sidecar" / "baseline_lech.json"
    # ⛔ KHÔNG `pytest.skip`. `baseline_lech.json` **đã commit**, nên thiếu nó
    #    là một lỗi thật đáng báo — không phải một điều kiện môi trường đáng bỏ
    #    qua.
    #
    # 🔴 Và phép bỏ qua ấy hỏng theo kiểu tệ nhất: chạy riêng thì test XANH
    #    (tệp có mặt), chạy trong gate thì nó BỎ QUA — nên `check_bo_qua.py`
    #    báo một mục bỏ qua mới mà chạy tay không tài nào tái hiện. Một phép
    #    kiểm chỉ im lặng ở một trong hai chỗ là một phép kiểm không ai tin.
    #
    # ⭐ *"Một test bị bỏ qua là một test KHÔNG canh gì cả"* — nguyên văn thông
    #    điệp của `check_bo_qua.py`, và ở đây nó đúng theo nghĩa đen.
    assert bl.exists(), (
        f"thieu {bl.relative_to(GOC)} — tep nay DA COMMIT, nen no vang mat la "
        f"mot loi. Ghim lai: `setup/do_lech_tham_chieu.ps1 -Ghim`")
    san = (json.loads(bl.read_text(encoding="utf-8")) or {}).get("do") or {}
    xau, so_luat_xet = [], 0
    for ma, chi, chieu, _, _ in m.LUAT:
        if not chi.endswith("_ti_le") or chi not in san:
            continue
        so_luat_xet += 1
        s = san[chi]
        dung = max(m.HE_SO_LECH * float(s["lech"]), m.SAN.get(chi, 0.0))
        if chieu <= 0 and float(s["tb"]) - dung < -1.0:
            xau.append(f"{ma}/{chi}: no khi < {float(s['tb']) - dung:.4f}, "
                       f"nhung can duoi la -1,0")
    # ⛔ ĐỐI CHỨNG (Bẫy 31) — thêm 07/09/2026.
    #
    #    Vòng lặp lọc hai lần: chỉ số phải kết thúc `_ti_le` VÀ phải có mặt
    #    trong sàn. Nếu `m.LUAT` đổi tên chỉ số, hoặc `baseline_lech.json` được
    #    ghim lại thiếu mấy chỉ số ấy, thân vòng **không chạy lần nào**, `xau`
    #    rỗng, và phép kiểm XANH.
    #
    # 🔴 Trớ trêu vì chính phép kiểm này sinh ra để bắt *"một luật không thể
    #    nổ nhìn y hệt một luật đang canh tốt"*. Xanh rỗng làm **chính nó**
    #    thành thứ nó đang săn.
    #
    #    Đo 07/09/2026: 3/6 luật qua bộ lọc.
    assert so_luat_xet >= 3, (
        f"chi xet duoc {so_luat_xet} luat thang ti le — mong doi >= 3. Hoac "
        f"ten chi so da doi, hoac baseline_lech.json ghim thieu. Ca hai deu "
        f"lam phep kiem nay canh RONG.")

    assert not xau, "; ".join(xau)


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


# ── EQ sửa độ sáng: giữ làm BẰNG CHỨNG, không phải tính năng ─────────────────

EQ = GOC / "voice_sidecar" / "eq_sua_sang.py"


def _eq():
    import importlib.util
    sp = importlib.util.spec_from_file_location("eq_thu", EQ)
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


def test_EQ_KHONG_duoc_noi_vao_duong_sinh():
    """🔴 DV-004: EQ sửa độ sáng KHÔNG đóng được khoảng cách. Đã đo.

    Quét sáu mức 0→4 dB trên 12 bản: `|lệch sáng|` giảm đẹp 7,9 → 4,6 nhưng
    **DNSMOS phẳng lì** — dao động ±0,003 trên một độ lệch nội tại 0,180.

    Vì sao: codec neural **không suy giảm** dải cao, nó **không mã hoá** dải
    cao. Bù tuyến tính chỉ nâng phần còn lại — kể cả phần dư nhiễu — chứ không
    khôi phục thông tin đã bị vứt.

    ⛔ Đây đúng là kiểu hỏng bộ đo sinh ra để bắt: **một con số đẹp lên trong
       khi tiếng không đổi.** Nếu chỉ nhìn `db_dai_cao` thì EQ trông như một
       thành công rõ ràng, và ta đã ship một tính năng không làm gì.

    Phép kiểm này đỏ nếu ai đó nối EQ vào — buộc họ đọc DV-004 và mang theo số
    đo mới, chứ không phải mang lại một ý tưởng nghe hợp lý.
    """
    for f in ("engine.py", "server.py", "noi_dai.py"):
        p = GOC / "voice_sidecar" / f
        if not p.exists():
            continue
        assert "eq_sua_sang" not in p.read_text(encoding="utf-8"), (
            f"`{f}` dang goi eq_sua_sang — xem DV-004 truoc khi bat no.")


def test_EQ_kep_o_TRONG_ham_chu_khong_o_noi_goi():
    """Chốt an toàn đặt ở nơi gọi là chốt mà nơi gọi thứ hai sẽ quên."""
    m = _eq()
    np = pytest.importorskip("numpy")
    pytest.importorskip("scipy")
    sr = 24000
    x = (0.2 * np.sin(2 * np.pi * 6000 * np.arange(sr) / sr)).astype("float32")
    a = m.ap(x, sr, ke_cao_db=4.0)
    b = m.ap(x, sr, ke_cao_db=40.0)      # vuot tran 10 lan
    assert float(np.abs(a).max()) == pytest.approx(float(np.abs(b).max()),
                                                   rel=0.02), (
        "40 dB va 4 dB cho ket qua khac nhau — phep kep khong nam trong `ap()`")


def test_EQ_khong_CAT_NGON_khi_vuot_tran():
    """Hạ đều cả bản, KHÔNG cắt ngọn.

    ⛔ Cắt ngọn là méo phi tuyến — đúng thứ `chot_toan_ven` của K1 sinh ra để
       bắt. Một bước "sửa chất lượng" tự tạo ra hỏng hóc mà một chốt khác phải
       bắt là một bước đi lùi.
    """
    m = _eq()
    np = pytest.importorskip("numpy")
    pytest.importorskip("scipy")
    sr = 24000
    # ⛔ KHONG dung 6000 Hz o sr 24000: do la DUNG 4 mau moi chu ky, nen mot
    #    nua so mau roi chinh xac vao ±dinh va phep dem duoi day bao "da cat
    #    ngon" cho mot tin hieu hoan toan sach. Khuon thu tu tao ra dung hien
    #    tuong no dinh bat — cung lop loi voi khuon `_tieng_gia` cua test_383.
    rng = np.random.default_rng(4)
    t = np.arange(sr) / sr
    x = (0.55 * np.sin(2 * np.pi * 5300 * t)
         + 0.35 * np.sin(2 * np.pi * 1700 * t)
         + 0.05 * rng.standard_normal(sr)).astype("float32")
    x = (x / np.abs(x).max() * 0.95).astype("float32")
    y = m.ap(x, sr, ke_cao_db=4.0)
    assert float(np.abs(y).max()) <= 1.0
    # neu cat ngon thi se co nhieu mau NAM DUNG o tran; ha deu thi khong
    tran = float(np.abs(y).max())
    dinh = int((np.abs(y) > tran * 0.999).sum())
    assert dinh < 20, f"{dinh} mau nam sat tran — nhieu kha nang da cat ngon"


def test_EQ_0dB_la_di_qua_khong_doi():
    m = _eq()
    np = pytest.importorskip("numpy")
    sr = 24000
    x = (0.3 * np.sin(2 * np.pi * 800 * np.arange(sr) / sr)).astype("float32")
    assert np.allclose(m.ap(x, sr, ke_cao_db=0.0), x)


def test_TRAN_DB_giu_nguyen_4_nhu_he_cu():
    """±4 dB kế thừa từ hệ cũ, và nó là chốt AN TOÀN không phải tham số.

    Vượt nó thì tiếng nghe chói và giả, và nhiễu của codec trong dải ấy lên
    theo cùng một lượng.
    """
    assert _eq().TRAN_DB == 4.0
