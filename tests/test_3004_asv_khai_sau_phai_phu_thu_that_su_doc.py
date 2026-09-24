"""Bản khai `sau=` phải PHỦ được mọi giai đoạn mà mã THẬT SỰ đọc.

## Bất biến được chốt, và nó KHÔNG phải cái tôi tưởng lúc đầu

🔴 **Tôi đã phát biểu N-08 quá một bậc.** Ghi lại vì chỗ sai mới là chỗ dạy được:

    tôi viết   : *"khai `sau` HẸP HƠN thứ mã thật sự đọc"* — nghe như một khiếm
                 khuyết tiềm ẩn ở 8/12 giai đoạn;
    đo ra      : khai **TRỰC TIẾP** đúng là hẹp hơn đọc trực tiếp, nhưng
                 **bao đóng bắc cầu** của `sau` **phủ hết** mọi lần đọc thật.

⇒ Hôm nay lịch chạy (`ke_tiep`) và vô hiệu hoá (`ha_nguon_cua`) đều **đúng** — và
  đúng **nhờ bao đóng**, không phải nhờ may. Nhưng bao đóng đó đang **chịu lực mà
  không được khai**: nó không xuất hiện trong bản khai nào, không ai kiểm nó, và
  nó **thôi phủ trong im lặng** ngay khi có người xen một bước vào giữa — đúng
  việc thang đo từng bước nhắm tới.

⇒ Nên bất biến đáng chốt là bất biến **thật sự chịu lực**:

        moi giai doan ma module cua buoc S DOC (va dung TRUOC S trong CHUOI)
        phai nam trong BAO DONG BAC CAU cua `S.sau`

⛔ Và chốt bằng **máy**, không bằng một dòng trong tài liệu: đây đúng bẫy
   `hai-cho-khai-cung-mot-dieu-khong-ai-bat-khop`, và cách kho này đã chọn nhiều
   lần là **cơ học thắng giao ước**. Bản khai thành thứ **phái sinh kiểm được**,
   không phải thứ người viết phải nhớ.

## ⚠️ Đọc NGƯỢC (`edit_plan` đọc `qc`) là ĐƯỜNG VÒNG SỬA, không phải vi phạm

`edit_plan`, `voice_synthesis`, `qc_ai`, `qc_do_luong` đọc phán quyết của các bước
**sau** chúng — đó là vòng sửa (`sua_chua`), có thật và đúng thiết kế. Nên phép
kiểm chỉ xét phần đọc **ngược lên thượng nguồn**.
"""
from __future__ import annotations

import ast
import pathlib

import pytest

from apps.auto_scan_video import pipeline as P

#: Module thực thi của từng giai đoạn. ⛔ Không đoán theo tên: bảng này phải khớp
#: `thi_hanh`, và `test_moi_giai_doan_deu_co_module` dưới chốt rằng nó đủ 12 dòng.
MODULE = {
    P.MEDIA_PREPARE: "giai_doan_media.py",
    P.AUDIO_PREPARE: "giai_doan_am_thanh.py",
    P.TRANSCRIBE: "giai_doan_chep_loi.py",
    P.EDIT_PLAN: "giai_doan_ban_bien_tap.py",
    P.CONTENT_PROCESS: "giai_doan_noi_dung.py",
    P.VOICE_SYNTHESIS: "giai_doan_giong.py",
    P.TIMING_ALIGN: "giai_doan_thoi_gian.py",
    P.COMPOSE: "giai_doan_ban_dung.py",
    P.RENDER: "giai_doan_ket_xuat.py",
    P.QC: "giai_doan_qc.py",
    P.QC_DO_LUONG: "giai_doan_qc_do_luong.py",
    P.QC_AI: "giai_doan_qc_ai.py",
}

GOC = pathlib.Path(P.__file__).parent
THU_TU = {g.ten: i for i, g in enumerate(P.CHUOI)}


def bao_dong(ten: str, sau_cua: dict, thay: set | None = None) -> set:
    """Bao đóng bắc cầu của `sau`, trên MỘT ĐỒ THỊ TRUYỀN VÀO.

    🔑 Nhận đồ thị làm **dữ liệu** chứ không đọc thẳng `P.THEO_TEN`, và đó là cả
       điểm của lần sửa này: nhờ vậy phần phán xử **đối chứng được** trên một đồ
       thị tổng hợp (xem `test_phan_xu_BAT_DUOC_vi_pham_that`).

    🔴 Trước đó hàm này đọc thẳng `P.THEO_TEN`, nên cách duy nhất để thử nó là
       **sửa `pipeline.py` thật** — và lần thử đó **vô hiệu**: `pipeline` đã có
       `_kiem_tra_chuoi()` chặn phụ thuộc tiến, nên phép tiêm chết ở lúc nạp
       module chứ không bao giờ tới phần phán xử. ⇒ Lúc đó phép kiểm **chưa được
       chứng minh là bắt được gì**, mà nhìn thì y hệt một phép kiểm đã xanh.
    """
    thay = set() if thay is None else thay
    for t in sau_cua.get(ten, ()):
        if t not in thay:
            thay.add(t)
            bao_dong(t, sau_cua, thay)
    return thay


def vi_pham(ten: str, doc: dict, sau_cua: dict, thu_tu: dict) -> dict:
    """Các giai đoạn `ten` ĐỌC mà nằm NGOÀI bao đóng của `sau`. Thuần, kiểm được."""
    truoc = {g: d for g, d in doc.items() if thu_tu[g] < thu_tu[ten]}
    bd = bao_dong(ten, sau_cua)
    return {g: d for g, d in truoc.items() if g not in bd}


SAU_CUA = {g.ten: g.sau for g in P.CHUOI}


def _doc_cua(duong: pathlib.Path) -> dict[str, int]:
    """`{ten_giai_doan: dong_dau_tien}` mà module này tham chiếu `pipeline.X`.

    Phân giải `pipeline.MEDIA_PREPARE` → `"media_prepare"` bằng `getattr` chứ
    không so tên hằng. ⛔ Bản nháp đầu so `n.attr` với tên giai đoạn và ra RỖNG cho
    cả 12 module — một phép kiểm rỗng thì **xanh**, và nó sẽ xanh mãi mãi.
    """
    cay = ast.parse(duong.read_text(encoding="utf-8"))
    ra: dict[str, int] = {}
    for n in ast.walk(cay):
        if not (isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name)
                and n.value.id == "pipeline" and n.attr.isupper()):
            continue
        gt = getattr(P, n.attr, None)
        if isinstance(gt, str) and gt in THU_TU:
            ra.setdefault(gt, n.lineno)
    return ra


def test_moi_giai_doan_deu_co_module_thuc_thi():
    """⛔ Thiếu một dòng ở `MODULE` là im lặng bỏ qua một giai đoạn.

    Và đó là cách một phép kiểm quét-tất-cả chết: nó vẫn xanh, chỉ là nó quét ít
    hơn người đọc tưởng.
    """
    assert set(MODULE) == set(P.TEN_GIAI_DOAN), (
        sorted(set(P.TEN_GIAI_DOAN) ^ set(MODULE)))
    for ten, m in MODULE.items():
        assert (GOC / m).is_file(), f"{ten}: khong thay {m}"


@pytest.mark.parametrize("ten", list(MODULE))
def test_doc_THAT_SU_nam_trong_bao_dong_cua_khai_sau(ten):
    """Bất biến chịu lực: đọc thượng nguồn ⊆ bao đóng bắc cầu của `sau`."""
    doc = _doc_cua(GOC / MODULE[ten])
    ngoai = vi_pham(ten, doc, SAU_CUA, THU_TU)
    assert not ngoai, (
        f"`{ten}` ({MODULE[ten]}) DOC cac giai doan nam NGOAI bao dong cua "
        f"`sau={P.THEO_TEN[ten].sau}`:\n  "
        + "\n  ".join(f"{MODULE[ten]}:{d}  doc `{g}`" for g, d in sorted(
            ngoai.items(), key=lambda kv: kv[1]))
        + "\n\nThem `{}` vao `sau=` cua no trong `pipeline.CHUOI`, hoac bo lan "
          "doc do.".format("`, `".join(sorted(ngoai))))


def test_phep_kiem_nay_KHONG_RONG():
    """⛔ Đối chứng: một phép kiểm quét-AST rỗng thì xanh, và xanh mãi mãi.

    🔴 Bản nháp đầu của `_doc_cua` so `n.attr` (tên HẰNG, `"MEDIA_PREPARE"`) với
       tên giai đoạn (`"media_prepare"`) ⇒ trả rỗng cho **cả 12** module, và
       `test_doc_THAT_SU…` **xanh hết**. Nó sẽ xanh kể cả khi mọi bản khai đều sai.

    ⇒ Nên phải có một bài chốt rằng phép quét **thật sự thấy** thứ nó đi tìm.
    """
    doc = _doc_cua(GOC / MODULE[P.COMPOSE])
    assert {P.MEDIA_PREPARE, P.AUDIO_PREPARE, P.CONTENT_PROCESS,
            P.VOICE_SYNTHESIS, P.TIMING_ALIGN} <= set(doc), sorted(doc)


def test_khai_TRUC_TIEP_hep_hon_doc_truc_tiep_o_NHIEU_giai_doan():
    """Ghi lại HIỆN TRẠNG — đây là mô tả, không phải một bất biến.

    ⚠️ Bài này KHÔNG đòi sửa. Nó tồn tại để con số *"khai trực tiếp hẹp hơn đọc
       trực tiếp ở N giai đoạn"* là một thứ ĐO ĐƯỢC chứ không phải một câu trong
       tài liệu — và để nếu ai đó thu hẹp khoảng cách đó, bài này đỏ và người ta
       biết là mình vừa làm điều tốt, cần cập nhật con số.

    ⛔ Và nó nói rõ vì sao khoảng cách đó chưa phải khiếm khuyết: bao đóng phủ hết
       (bài trên chốt), nên lịch chạy và vô hiệu hoá đều đúng HÔM NAY.
    """
    lech = []
    for ten, m in MODULE.items():
        doc = _doc_cua(GOC / m)
        truoc = {g for g in doc if THU_TU[g] < THU_TU[ten]}
        if truoc - set(P.THEO_TEN[ten].sau):
            lech.append(ten)
    assert len(lech) >= 6, (
        "khoang cach khai-truc-tiep vs doc-truc-tiep da HEP lai "
        f"({len(lech)} giai doan). Neu do la co y thi cap nhat con so o day.")


def test_phan_xu_BAT_DUOC_vi_pham_that():
    """⛔ ĐỐI CHỨNG. Không có bài này thì `test_doc_THAT_SU…` chỉ chứng minh được
    rằng nó **chưa đỏ**, chứ không chứng minh được rằng nó **đỏ khi cần**.

    Tình huống dựng đúng cái chủ dự án nhắm tới: **xen một bước mới vào giữa**.
    `buoc_moi` khai `sau=("media_prepare",)` nhưng đọc `content_process` — một
    nhánh rẽ không đi qua xương sống, nên bao đóng **thôi phủ**.

    ⚠️ Chuỗi THẬT hôm nay gần như một đường thẳng, nên mọi bao đóng đều phủ mọi
       thứ và **không phép tiêm nào trên `pipeline.py` thật tạo được vi phạm**
       (thử rồi: `_kiem_tra_chuoi` chặn ngay). Đó chính là lý do phần phán xử
       phải nhận đồ thị làm dữ liệu.
    """
    sau_cua = {"media_prepare": (), "transcribe": ("media_prepare",),
               "content_process": ("transcribe",),
               "buoc_moi": ("media_prepare",)}
    thu_tu = {"media_prepare": 0, "transcribe": 1, "content_process": 2,
              "buoc_moi": 3}

    # Đọc đúng thượng nguồn đã khai -> KHÔNG vi phạm.
    assert vi_pham("buoc_moi", {"media_prepare": 10}, sau_cua, thu_tu) == {}
    # Đọc một nhánh ngoài bao đóng -> PHẢI bắt, và phải mang số dòng.
    assert vi_pham("buoc_moi", {"content_process": 42}, sau_cua, thu_tu) == {
        "content_process": 42}
    # Đọc NGƯỢC (bước sau) -> đường vòng sửa, KHÔNG phải vi phạm.
    assert vi_pham("transcribe", {"content_process": 7}, sau_cua, thu_tu) == {}
