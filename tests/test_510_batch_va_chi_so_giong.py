r"""U-06 (đính chính) + U-14 — gộp lô trên GPU, và chỉ số theo từng giọng.

## U-06: bản kiểm toán nói SAI, và phép kiểm ở đây chốt TÍNH CHẤT chứ không
## chốt tên cửa

`VIRAL_VOICE_AUDIT_2026-09-07.md` xếp *"nối `infer_batch` vào `ban_doc_dai`"*
vào P3 như việc chưa làm. Đo 08/09/2026:

    ban_doc_dai._sinh_mot_lo(8)  ->  lo_ra_tep  ->  /v1/lo-ra-tep
      ->  c.noi_lo(...)          ->  infer_batch

Nó **đã nối từ trước**, qua một cửa **tốt hơn** cửa bản gốc đề nghị:
`/v1/batch` trả base64 qua JSON, `/v1/lo-ra-tep` để sidecar ghi thẳng ra đĩa.

🔴 Phép rà soát bỏ sót vì nó tìm **một cái tên** (`/v1/batch`) thay vì tìm
   **một tính chất** (*đường bài dài có gửi nhiều đoạn một lượt không*). Nên
   phép kiểm ở đây chốt tính chất — một bản vá đổi sang cửa khác vẫn xanh, một
   bản vá quay về gọi từng đoạn thì đỏ.

## U-14: và nó phải NÓI RA THỨ NÓ KHÔNG BIẾT

Bản kiểm toán đòi ba chỉ số: RTF · tỉ lệ hỏng · CER trung vị. Ta có hai.
`cer_trung_vi` là `None` ở **mọi** giọng, và `None` là một **câu trả lời**.

⛔ Một bảng chỉ số chỉ liệt kê thứ nó biết sẽ được đọc như thể đó là tất cả
   những gì đáng biết — và người đọc không có cách nào phát hiện phần thiếu.
"""
from __future__ import annotations

import ast
import pathlib

import pytest

GOC = pathlib.Path(__file__).resolve().parents[1]


def _ham(duong: str, ten: str):
    cay = ast.parse((GOC / duong).read_text(encoding="utf-8"))
    return next(n for n in ast.walk(cay)
                if isinstance(n, ast.FunctionDef) and n.name == ten)


# ── 1. U-06 — đường bài dài GỘP LÔ, và ta chốt tính chất ─────────────────────

def test_ban_doc_dai_gui_NHIEU_HON_MOT_doan_trong_mot_luot():
    """🔴 TÍNH CHẤT, không phải tên cửa.

    `SO_DOAN_MOI_LO > 1` là toàn bộ điều kiện để có gộp lô. Bằng 1 thì mọi thứ
    khác vẫn chạy, vẫn đúng, chỉ là **không còn gộp** — và không có triệu chứng
    nào ngoài hoá đơn GPU.
    """
    from apps.ltt_voice.ban_doc_dai import SO_DOAN_MOI_LO
    assert SO_DOAN_MOI_LO > 1, (
        "moi lo con MOT doan — duong bai dai da mat phep gop lo tren GPU")


def test_tran_lo_cua_sidecar_cung_LON_HON_MOT():
    """⛔ Hai trần, hai nơi, và **cả hai** phải > 1. App gửi 8 đoạn mà sidecar
    cắt thành 8 lượt một đoạn thì phép gộp chết ở nửa sau — và phía app không
    thấy gì khác."""
    from voice_sidecar import tham_so
    assert int(tham_so.TRAN_SO_VAN_BAN_BATCH) > 1


def test_duong_bai_dai_cham_toi_INFER_BATCH():
    """Chuỗi đầu-cuối, đọc AST ở mỗi mắt xích thay vì tin một chú thích."""
    sinh = ast.unparse(_ham("apps/ltt_voice/ban_doc_dai.py", "_sinh_mot_lo"))
    assert "lo_ra_tep" in sinh, "`_sinh_mot_lo` khong goi cua lo"

    sv = (GOC / "voice_sidecar/server.py").read_text(encoding="utf-8")
    assert "/v1/lo-ra-tep" in sv
    eng = ast.unparse(_ham("voice_sidecar/engine.py", "noi_lo"))
    assert "infer_batch" in eng, "`engine.noi_lo` khong dung `infer_batch`"


def test_lo_ra_tep_KHONG_dua_byte_am_thanh_qua_HTTP():
    """⭐ Đây là lý do cửa đang dùng **tốt hơn** cửa bản kiểm toán đề nghị.

    Nếu ai đó "thi hành U-06" theo đúng chữ của bản gốc, họ sẽ thay một cửa tốt
    bằng một cửa tệ hơn — và đo bằng thông lượng GPU thì **không thấy gì**, vì
    cả hai cùng gọi `infer_batch`.
    """
    from apps.ltt_voice import sidecar_client

    ma = ast.unparse(_ham("apps/ltt_voice/sidecar_client.py", "lo_ra_tep"))
    assert "duong_ra" in ma, "cua lo khong nhan duong ghi — byte se qua HTTP"
    assert "wav_b64" not in ma
    assert callable(sidecar_client.lo_ra_tep)


# ── 2. U-14 — GPU-giây phải được GHI LẠI, nếu không thì không đo được ────────

def test_gen_s_duoc_CONG_DON_chu_khong_lay_luot_cuoi():
    """🔴 Một bài dài là nhiều lượt `lo_ra_tep`, mỗi lượt trả `gen_s` của
    **riêng nó**. Ghi đè thay vì cộng cho ra GPU-giây của lô cuối và gọi nó là
    của cả bài — nhỏ hơn sự thật nhiều lần, và **trông hoàn toàn hợp lý**."""
    from apps.ltt_voice import ban_doc_dai

    so_ke = {"gen_s": 0.0}
    for g in (1.5, 2.25, 0.25):
        ban_doc_dai._cong_gen_s(so_ke, {"gen_s": g})
    assert so_ke["gen_s"] == pytest.approx(4.0)


@pytest.mark.parametrize("xau", [None, {}, {"gen_s": "x"}, {"gen_s": None}, 7])
def test_cong_gen_s_KHONG_NEM_voi_dau_vao_xau(xau):
    """⛔ Số liệu vận hành đi kèm một lượt sinh **đã thành công**. Một
    `TypeError` ở đây biến một chỉ số thiếu thành một job hỏng và một khoản
    credit phải hoàn."""
    from apps.ltt_voice import ban_doc_dai

    so_ke = {"gen_s": 1.0}
    ban_doc_dai._cong_gen_s(so_ke, xau)
    assert so_ke["gen_s"] == 1.0


def test_jobs_LAY_X_Gen_S_tu_header():
    ma = ast.unparse(ast.parse(
        (GOC / "apps/ltt_voice/jobs.py").read_text(encoding="utf-8")))
    assert "X-Gen-S" in ma, "jobs.py khong doc `X-Gen-S` — GPU-giay khong bao "\
                            "gio duoc luu"


@pytest.mark.parametrize("x,mong", [("1.25", 1.25), (None, 0.0), ("x", 0.0),
                                    ("-3", 0.0), (2, 2.0)])
def test_jobs_so_KHONG_NEM(x, mong):
    from apps.ltt_voice import jobs
    assert jobs._so(x) == pytest.approx(mong)


def test_gen_s_KHONG_vao_ket_qua_khi_bang_0():
    """⛔ `0.0` = KHÔNG BIẾT. Một trường luôn-luôn-có với giá trị 0 sẽ được đọc
    thành *"lượt này tốn 0 giây GPU"*, và trung vị tính trên nó là một con số
    sai một cách tự tin."""
    from apps.ltt_voice import features

    def _kq(g):
        return features.KetQua(yeu_cau=None, audio_key="k", giay=2.0,
                               text_da_chuan_hoa="x", gen_s=g)
    assert "gen_s" not in _kq(0.0).as_result()
    assert _kq(1.5).as_result()["gen_s"] == pytest.approx(1.5)


def test_gen_s_KHONG_duoc_dung_de_tinh_tien():
    """⚠️ Tiền theo **giây tiếng đo được** (chốt 3.4). Tính tiền theo GPU-giây
    là tính tiền theo tình trạng máy của **ta** — khách không điều khiển được
    nó, nên họ trả nhiều hơn vào ngày ta chạy nhiều việc khác."""
    ma = ast.unparse(_ham("apps/ltt_voice/features.py", "as_result"))
    assert "gen_s" in ma
    cay = ast.parse((GOC / "apps/ltt_voice/gia.py").read_text(encoding="utf-8"))
    assert "gen_s" not in ast.unparse(cay), (
        "`gia.py` nhac toi `gen_s` — tien dang bam vao GPU-giay")


# ── 3. U-14 — bảng chỉ số, và thứ nó KHÔNG biết ─────────────────────────────

def test_CER_luon_la_None_vi_CHUA_DO():
    """🔴 `None` là một **câu trả lời**, không phải một ô chờ điền. CER cần
    corpus có bản chép tay + bộ nhận dạng — cả hai chưa có (U-10).

    ⛔ Một số bịa trong bảng chỉ số sẽ được so sánh, xếp hạng, rồi dùng để
       **loại một giọng**."""
    ma = (GOC / "apps/ltt_voice/chi_so_giong.py").read_text(encoding="utf-8")
    cay = ast.parse(ma)
    ham = next(n for n in ast.walk(cay)
               if isinstance(n, ast.FunctionDef) and n.name == "theo_giong")
    gan = [n for n in ast.walk(ham) if isinstance(n, ast.keyword)]
    assert '"cer_trung_vi": None' in ma or "'cer_trung_vi': None" in ma
    assert gan is not None


def test_bang_chi_so_NOI_RA_thu_no_thieu():
    """⭐ Trường `chua_do` là phần đáng giá nhất của gói. Một bảng chỉ số chỉ
    liệt kê thứ nó biết sẽ được đọc như thể đó là **tất cả** những gì đáng
    biết."""
    ma = ast.unparse(_ham("apps/ltt_voice/chi_so_giong.py", "gom"))
    assert "chua_do" in ma
    assert "cer_trung_vi" in ma


def test_RTF_khong_cong_bo_khi_qua_it_mau():
    """⛔ Một mẫu cho một con số, không cho một dải. Một giọng chạy đúng một
    lượt vào lúc máy bận sẽ có RTF tệ gấp nhiều lần, rồi đứng đầu bảng "tốn GPU
    nhất" và bị đem đi loại."""
    from apps.ltt_voice import chi_so_giong
    assert chi_so_giong.SO_LUOT_TOI_THIEU_RTF >= 3


def test_RTF_bo_qua_job_CU_khong_co_gen_s():
    """🔴 `gen_s` chỉ bắt đầu được lưu từ 08/09/2026. Mọi job cũ có
    `gen_s = 0`, và `0 / giay` là một RTF bằng 0 — tức **"nhanh vô hạn"**.

    Trộn chúng vào trung vị sẽ kéo mọi giọng cũ xuống gần 0 và làm bảng nói
    ngược hẳn sự thật."""
    ma = ast.unparse(_ham("apps/ltt_voice/chi_so_giong.py", "theo_giong"))
    assert "gpu > 0" in ma or "gpu > 0.0" in ma, (
        "khong loc job thieu `gen_s` — RTF se bi keo ve 0")


def test_ti_le_hong_so_voi_TAP_HOP_trang_thai_hong():
    """⚠️ So với `!= "done"` sẽ đếm cả job **đang chạy** là hỏng — nên tỉ lệ
    hỏng phồng lên mỗi khi có lượt đang chạy, tức nó cao nhất đúng lúc hệ thống
    bận nhất."""
    ma = ast.unparse(_ham("apps/ltt_voice/chi_so_giong.py", "theo_giong"))
    assert "failed" in ma and "canceled" in ma
    assert '!= "done"' not in ma and "!= 'done'" not in ma


# ── 4. Cửa — quyền, và hình dạng câu từ chối ────────────────────────────────

def _ma_thuc(duong: str) -> str:
    """Mã THẬT của một tệp — docstring và chú thích đã bị bỏ.

    🔴 BẮT BUỘC, và hai phép kiểm ngay dưới đã đỏ vì thiếu nó.

       `_p_chi_so.py` **giải thích** vì sao nó không tự kiểm `user.role` và vì
       sao nó trả 404 thay vì 403 — nên chuỗi `"role"` và `"403"` có mặt trong
       chính đoạn văn nói rằng chúng không được dùng.

    ⭐ Một bánh cóc khớp chuỗi thô sẽ báo động trên **lời giải thích của chính
       nó**, và nó báo động **càng chắc chắn** khi lời giải thích càng kỹ. Kho
       này đã mắc lỗi ấy nhiều lần (`test_505::_ma_thuc`, `test_506::_ma_js`),
       và tôi vừa mắc lại nó ở đây sau khi viết cả hai bản kia.
    """
    import io
    import tokenize

    nguon = (GOC / duong).read_text(encoding="utf-8")
    ra = []
    try:
        for tok in tokenize.generate_tokens(io.StringIO(nguon).readline):
            if tok.type in (tokenize.COMMENT, tokenize.STRING):
                continue
            ra.append(tok.string)
    except tokenize.TokenError:
        return nguon
    return " ".join(ra)


def test_cua_chi_so_dung_is_operator_cua_NEN_TANG():
    """⚠️ Tự dựng một phép kiểm quyền thứ hai trong một app là cách hai định
    nghĩa "admin" trôi khỏi nhau — và bên trôi là bên ít người đọc hơn."""
    ma_tho = (GOC / "apps/ltt_voice/routes/_p_chi_so.py").read_text(encoding="utf-8")
    assert "from server.deps import is_operator" in ma_tho

    ma = _ma_thuc("apps/ltt_voice/routes/_p_chi_so.py")
    assert "role" not in ma, "app tu kiem `role` — dung `is_operator`"


def test_bo_loc_ma_thuc_THAT_SU_cat_chu_thich():
    """⛔ SELF-TEST. `_ma_thuc` hỏng thì **cả hai** phép kiểm quanh nó xanh vĩnh
    viễn — và chúng sẽ xanh một cách rất thuyết phục."""
    ma = _ma_thuc("apps/ltt_voice/routes/_p_chi_so.py")
    assert "is_operator" in ma, "bo loc cat ca MA THAT"
    assert "Cửa CHỈ SỐ" not in ma, "bo loc KHONG cat docstring"


def test_cua_chi_so_tra_404_chu_khong_403():
    """⛔ 403 xác nhận rằng đường dẫn **tồn tại** và người hỏi **không đủ
    quyền** — hai mẩu thông tin cho một người không có việc gì ở đây."""
    ma = _ma_thuc("apps/ltt_voice/routes/_p_chi_so.py")
    assert "404" in ma
    assert "403" not in ma


def test_route_da_duoc_DANG_KY():
    """Một tệp route không được import là một cửa không tồn tại — và nó im
    lặng: không lỗi, chỉ 404 ở mọi lượt."""
    ma = (GOC / "apps/ltt_voice/routes/__init__.py").read_text(encoding="utf-8")
    assert "_p_chi_so" in ma
