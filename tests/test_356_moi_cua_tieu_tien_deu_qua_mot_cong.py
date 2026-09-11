r"""
test_356 — MỌI CỬA TIÊU TIỀN CỦA `ltt_voice` ĐỀU PHẢI ĐI QUA MỘT CỔNG.

## Vì sao tệp này tồn tại

`features.py` mở đầu bằng một lời hứa:

    "Nghiệp vụ ở features.py, dùng chung mọi cửa — hai cửa tự xử lý riêng ⇒
     ngày chúng lệch nhau là ngày một yêu cầu bị tính hai giá."

Lời hứa ấy **đúng**, và cho tới 2026-09-11 nó được giữ bằng **quy ước**: mỗi
người viết một cửa mới phải nhớ gọi `features.giai_giong` trước khi tiêu tiền.
Không phép kiểm nào đếm xem đã nhớ đủ chưa.

⇒ Audit 11/09 đếm thật: **năm** cửa tiêu tiền hoặc chạm GPU, **bốn** cửa nhớ,
  **một** cửa quên — `routes/_p_lich_su.py::doc_lai`.

## 🔴 Cửa quên lại đúng là cửa DỄ SÓT NHẤT, không phải cửa ít quan trọng nhất

`doc_lai` phát lại `params` **CŨ**. Theo đúng thiết kế, nó là cửa mang tham
chiếu ôi nhiều nhất: giữa lần chạy đầu và lần bấm "đọc lại", giọng có thể đã bị
thu hồi, làn ngôn ngữ có thể đã được khai lại, `preset` có thể đã biến mất sau
một lượt nâng engine.

Đo thật 2026-09-11 trên `studio_dev`, **cùng một cặp văn bản + giọng**:

    POST /ltt-voice/tao                  -> 400 voice_language_mismatch, khong job
    POST /ltt-voice/lich-su/<id>/doc-lai -> 200, job queued, so du 500 -> 499

⇒ Một credit bị giữ cho một yêu cầu mà cửa bên cạnh vừa từ chối. Worker sẽ từ
  chối tiếp rồi hoàn tiền — nên **không mất tiền**, nhưng đó đúng là sự cố
  production 31/08/2026 đã ghi: *"job vẫn được giữ credit, vẫn xếp hàng, và bị
  thử lại — cho một câu trả lời mà cửa vào đã biết ngay từ đầu."*

## ⛔ VÀ ĐÂY MỚI LÀ MỆNH ĐỀ TỆP NÀY CHỐT

Sửa `doc_lai` là sửa **một** cửa. Tệp này chốt thứ khác: **không cửa nào tiêu
tiền mà không đi qua cổng** — kể cả cửa thứ sáu chưa ai viết.

⭐ Đó là khác biệt giữa vá một lỗ và đóng một **hạng lỗi**. Bốn cửa đúng không
   chứng minh gì về cửa thứ năm; và cửa thứ năm được sửa cũng không chứng minh
   gì về cửa thứ sáu. Chỉ một phép đếm **trên toàn bộ tập cửa** mới làm được.

⚠️ Phép kiểm này đọc **CÂY CÚ PHÁP**, không khớp chuỗi: một `grep "giai_giong"`
   sẽ xanh nhờ một dòng chú thích nhắc tới tên hàm. Đã có tiền lệ trong kho này
   — xem `bo-do-quet-van-ban-trung-phat-viec-giai-thich`.
"""
from __future__ import annotations

import ast
import pathlib

GOC = pathlib.Path(__file__).resolve().parents[1]
APP = GOC / "apps" / "ltt_voice"

#: Hàm nào nghĩa là "cửa này TIÊU TIỀN hoặc CHẠM GPU".
TIEU_TIEN = {"submit_with_credit", "giu_cho"}
#: ⚠️ `"sinh"` thêm 2026-09-11 (fix round 1/5, Task 10 IMPORTANT 3):
#:    `routes/_p_nghe_thu.py::nghe_thu_van_ban` gọi `NT.sinh(...)`
#:    (`nghe_thu_cua_toi.sinh`) chứ không còn gọi thẳng `features.goi_cong` —
#:    thiếu tên này thì phép quét KHÔNG THẤY `nghe_thu_van_ban` nữa (nó không
#:    còn gọi trực tiếp bất cứ tên nào trong `CHAM_GPU` cũ), và một cửa vừa
#:    đổi hình dạng lọt ra khỏi tầm nhìn của chính bánh cóc sinh ra để canh nó.
CHAM_GPU = {"goi_cong", "noi", "noi_dan", "sinh"}

#: Cổng nghiệp vụ bắt buộc — trực tiếp hay qua một hàm bọc trong cùng tệp.
CONG = {"giai_giong", "_chot_lan"}

#: 🔴 MIỄN TRỪ PHẢI KHAI TỪNG CÁI, KÈM LÝ DO — và danh sách này càng ngắn càng
#:    tốt. Một miễn trừ không có lý do là một cửa bị quên đội lốt một quyết định.
#:
#: ⚠️ Khai bằng `(tệp, hàm)` chứ không bằng tên hàm trần: hai tệp có thể có hai
#:    hàm trùng tên, và một miễn trừ trôi sang tệp khác là một lỗ mở ra âm thầm.
MIEN_TRU = {
    ("nghe_thu_cua_toi.py", "sinh"): (
        "Nghe thu MIEN PHI: khong giu credit, chi nhan `preset` (khong nhan "
        "`voice_id`) nen khong co cau hoi so huu nao de kiem. Ham nay la ranh "
        "gioi mong quanh `features.goi_cong` — tach ra de test_526 mock duoc "
        "dung MOT cho (luot sinh THAT) ma khong dung ca sidecar gia. Cong "
        "rieng cua DUONG nay nam o nguoi goi no, `routes/_p_nghe_thu.py::"
        "nghe_thu_van_ban` — xem mien tru ngay duoi day."),
    ("routes/_p_nghe_thu.py", "nghe_thu_van_ban"): (
        "Nghe thu MIEN PHI: khong giu credit, chi nhan `preset` (khong nhan "
        "`voice_id`) nen khong co cau hoi so huu nao de kiem. Cong rieng cua "
        "no la: `giong_mau.hop_le` + tran ky tu + rate-limit theo gio "
        "(`nghe_thu_cua_toi.xin_luot`) + xep sau khach tra tien "
        "(`admission.hold_persisted`). D006 (2026-09-11): cua nay CO goi "
        "`lan_ngon_ngu.quyet_dinh`, nhung de HIEN phan quyet canh bao canh nut "
        "phat — khong de CHAN luot sinh (van khong co credit nao de bao ve o "
        "day, nen khong co gi de `giai_giong` giu chan)."),
    ("nghe_thu.py", "dung"): (
        "Vong bao tri dung tep nghe thu cho giong MAU. Khong khach nao goi, "
        "khong tien nao bi cham, va giong den tu chinh danh muc."),
    ("routes/_p_giong.py", "tao_giong"): (
        "GHI DANH mot giong MOI tu clip tai len — khong co giong cu de kiem so "
        "huu, va khong co van ban nao de doi chieu lan, nen `giai_giong` khong "
        "co menh de nao de kiem o day. Cong rieng cua no la: `dong_y == '1'` "
        "(cong phap ly, nhan than), ten khong rong, va `features.kiem_ghi_danh` "
        "(kiem dinh dang + chat luong audio). Job la `ltt_voice.enroll`, gia "
        "co dinh `gia.CREDIT_GHI_DANH`, khong phai duong sinh tieng."),
}


def _cac_ham(p: pathlib.Path):
    try:
        cay = ast.parse(p.read_text(encoding="utf-8"))
    except SyntaxError:  # pragma: no cover
        return
    for n in ast.walk(cay):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield n


def _ten_goi(n: ast.AST) -> set:
    ra = set()
    for m in ast.walk(n):
        if isinstance(m, ast.Call):
            t = getattr(m.func, "id", "") or getattr(m.func, "attr", "")
            if t:
                ra.add(t)
    return ra


def _quet() -> list:
    """`[(duong_tuong_doi, ten_ham, cac_goi)]` cho mọi cửa tiêu tiền/chạm GPU."""
    ra = []
    for p in sorted(APP.rglob("*.py")):
        if "__pycache__" in str(p):
            continue
        rel = p.relative_to(APP).as_posix()
        for n in _cac_ham(p):
            goi = _ten_goi(n)
            if goi & (TIEU_TIEN | CHAM_GPU):
                ra.append((rel, n.name, goi))
    return ra


def test_quet_tim_duoc_dung_nhung_cua_da_biet():
    """⛔ ĐỐI CHỨNG CHO CHÍNH PHÉP QUÉT, và không có nó thì tệp này vô nghĩa.

    Một phép quét trả về **rỗng** sẽ làm mọi phép kiểm dưới đây xanh — xanh vì
    không nhìn thấy gì, không phải vì không có gì sai. Nên trước hết phải chứng
    minh phép quét **thấy được** những cửa ta đã biết chắc là có.
    """
    thay = {(f, h) for f, h, _ in _quet()}
    phai_co = {
        ("routes/_p_tao.py", "tao"),
        ("routes/_p_du_an.py", "_nop_mot_khoi"),
        ("routes/_p_lich_su.py", "doc_lai"),
        ("routes/_p_phat_dan.py", "phat_dan"),
        ("nghe_thu_cua_toi.py", "sinh"),
        ("routes/_p_nghe_thu.py", "nghe_thu_van_ban"),
        ("routes/_p_giong.py", "tao_giong"),
        ("jobs.py", "_tao_tieng"),
    }
    # ⭐ `tao_giong` nằm trong danh sách này vì một lý do đáng ghi: lượt audit
    #    THỦ CÔNG 11/09 **bỏ sót nó**, và chính phép quét cơ học ở tệp này tìm
    #    ra. Đó là toàn bộ lý do một ranh giới cơ học hơn một giao ước — người
    #    đọc kỹ vẫn đếm thiếu, phép đếm thì không.
    thieu = phai_co - thay
    assert not thieu, (
        f"phep quet KHONG thay nhung cua da biet chac la co: {sorted(thieu)} — "
        f"quet hong thi moi phep kiem duoi day xanh-rong")


def test_moi_cua_tieu_tien_deu_di_qua_cong_nghiep_vu():
    """🔴 MỆNH ĐỀ CHÍNH. Bất biến với việc có bao nhiêu cửa."""
    xau = []
    for f, h, goi in _quet():
        if (f, h) in MIEN_TRU:
            continue
        if goi & CONG:
            continue
        xau.append(f"{f}::{h}  (goi: {sorted(goi & (TIEU_TIEN | CHAM_GPU))})")
    assert not xau, (
        "cua tieu tien / cham GPU ma KHONG di qua `features.giai_giong`:\n  "
        + "\n  ".join(xau)
        + "\n\nMoi cua phai kiem so huu + lan ngon ngu TRUOC khi giu credit. "
          "Neu cua nay that su khong can, khai vao MIEN_TRU KEM LY DO.")


def test_moi_MIEN_TRU_deu_tro_toi_mot_ham_CO_THAT():
    """⛔ Một miễn trừ trỏ vào hàm đã đổi tên là một lỗ mở ra **âm thầm**.

    Hàm bị đổi tên ⇒ miễn trừ không còn khớp ⇒ phép kiểm trên lẽ ra phải đỏ.
    Nhưng nếu hàm mới cũng không gọi cổng thì nó đỏ vì lý do đúng; còn nếu
    người sửa **thêm** một miễn trừ mới thay vì sửa cái cũ, ta có hai miễn trừ
    cho một cửa và một trong hai vô nghĩa. Phép kiểm này dọn đúng chỗ đó.
    """
    co_that = {(f, h) for f, h, _ in _quet()}
    mo_coi = [k for k in MIEN_TRU if k not in co_that]
    assert not mo_coi, (
        f"MIEN_TRU tro toi cua khong con ton tai: {mo_coi} — go no di, "
        f"dung de mot dieu khoan mien tru song lau hon thu no mien tru")


def test_moi_MIEN_TRU_deu_co_LY_DO_du_dai_de_cai_lai():
    """Một miễn trừ không có lý do là một cửa bị quên đội lốt một quyết định."""
    for khoa, ly_do in MIEN_TRU.items():
        assert isinstance(ly_do, str) and len(ly_do.strip()) >= 60, (
            f"mien tru {khoa} co ly do qua ngan de ai do cai lai: {ly_do!r}")


def test_doc_lai_KHONG_dung_YeuCau_lam_tai_trong():
    """⛔ `doc_lai` phải KIỂM bằng `chuan_hoa` nhưng NỘP `params` gốc.

    🔴 Hai việc khác nhau, và gộp chúng lại là một hồi quy im lặng: dựng lại
       `params` từ `YeuCau` sẽ đánh rơi mọi khoá mà `YeuCau` không biết —
       `nguon`, `project_id`, `block_id`, và khoá tiếp theo ai đó thêm vào.

       Chính docstring của `doc_lai` đã cảnh báo đúng điều này theo chiều ngược
       lại: *"Chép nguyên `params` cũ chứ không dựng lại: một bản dựng lại sẽ
       bỏ sót tham số mới thêm (như `toc_do`), và bỏ sót IM LẶNG."*

    ⇒ Phép kiểm: lời gọi `submit_with_credit` trong `doc_lai` phải truyền
      `params=p` (dict gốc), **không** phải một dict dựng từ `yc.*`.
    """
    src = (APP / "routes" / "_p_lich_su.py").read_text(encoding="utf-8")
    ham = next(n for n in _cac_ham(APP / "routes" / "_p_lich_su.py")
               if n.name == "doc_lai")
    goi = [n for n in ast.walk(ham)
           if isinstance(n, ast.Call)
           and getattr(n.func, "id", "") == "submit_with_credit"]
    assert len(goi) == 1, "khong tim thay dung mot loi nop job o `doc_lai`"
    tham = {k.arg: k.value for k in goi[0].keywords}
    assert "params" in tham, "loi nop job khong khai `params`"
    assert isinstance(tham["params"], ast.Name), (
        "`params` phai la dict GOC (mot bien), khong phai mot dict dung lai "
        "tai cho — dung lai se danh roi khoa ma `YeuCau` khong biet")
    assert "features.chuan_hoa" in src or "chuan_hoa(p)" in src
