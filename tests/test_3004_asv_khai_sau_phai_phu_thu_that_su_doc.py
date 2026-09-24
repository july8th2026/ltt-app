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
import functools
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


def ha_nguon(ten: str, sau_cua: dict, thu_tu: dict) -> set:
    """Bao đóng HẠ NGUỒN của `ten` — ai bị vô hiệu khi `ten` chạy lại.

    🔑 Đây là bản **thuần** của `P.ha_nguon_cua`: cùng thuật toán, nhưng nhận đồ
       thị làm **dữ liệu**. `P.ha_nguon_cua` đọc thẳng `P.CHUOI` ở cấp module,
       nên không tiêm được — và `pipeline._kiem_tra_chuoi()` chặn ngay lúc nạp
       module, nên một phép tiêm trên `pipeline.py` thật **chết trước khi tới
       phần phán xử** (N-08b: một đối chứng thất bại vì lý do KHÁC thì không
       phải một đối chứng).

    ⛔ Hai bản song song là hai chỗ khai một điều, nên
       `test_ban_THUAN_ha_nguon_KHOP_pipeline_that` bắt khớp chúng bằng máy.
    """
    ra: set = set()
    bien = {ten}
    for g in sorted(sau_cua, key=lambda t: thu_tu[t]):
        if g == ten:
            continue
        if set(sau_cua[g]) & bien:
            bien.add(g)
            ra.add(g)
    return ra


def vi_pham_chay_lai(ten: str, ai_doc: dict, sau_cua: dict,
                     thu_tu: dict) -> dict:
    """Ai ĐỌC `ten` mà **không** bị vô hiệu khi `ten` chạy lại. Thuần, kiểm được.

    ⭐ Đây là chiều NGƯỢC của `vi_pham`, và hai chiều hỏi hai câu khác nhau:

        `vi_pham`           — S đọc gì mà lịch chạy không bảo đảm đã xong
                              ⇒ hỏng đường chạy XUÔI (`ke_tiep`)
        `vi_pham_chay_lai`  — ai đọc S mà chạy lại S không đụng tới
                              ⇒ hỏng đường CHẠY LẠI (`ha_nguon_cua`)

    ⚠️ Chỉ xét người đọc đứng **SAU** `ten` trong chuỗi. Đọc ngược (`edit_plan`
       đọc `qc`) là vòng sửa — có thật và đúng thiết kế — và `ha_nguon` theo
       định nghĩa không bao giờ chứa một bước đứng trước.
    """
    hn = ha_nguon(ten, sau_cua, thu_tu)
    return {g: d for g, d in ai_doc.items()
            if thu_tu[g] > thu_tu[ten] and g not in hn}


def vi_pham(ten: str, doc: dict, sau_cua: dict, thu_tu: dict) -> dict:
    """Các giai đoạn `ten` ĐỌC mà nằm NGOÀI bao đóng của `sau`. Thuần, kiểm được."""
    truoc = {g: d for g, d in doc.items() if thu_tu[g] < thu_tu[ten]}
    bd = bao_dong(ten, sau_cua)
    return {g: d for g, d in truoc.items() if g not in bd}


SAU_CUA = {g.ten: g.sau for g in P.CHUOI}


@functools.lru_cache(maxsize=None)
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


def _ai_doc(ten: str) -> dict[str, int]:
    """`{giai_doan_doc_no: dong_dau_tien}` — nghịch đảo của `_doc_cua`."""
    ra: dict[str, int] = {}
    for t, m in MODULE.items():
        d = _doc_cua(GOC / m)
        if ten in d:
            ra[t] = d[ten]
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


@pytest.mark.parametrize("ten", list(MODULE))
def test_chay_lai_mot_buoc_giua_chuoi_vo_hieu_dung_cac_buoc_phu_thuoc(ten):
    """⛔ N-08 chưa đo trên đường CHẠY LẠI — và đường đó ĐÃ cắn một lần.

    🔴 `features.py:263` ghi một sự cố THẬT: chạy lại `media_prepare` ⇒ job
       `audio_prepare` CŨ của lượt trước vẫn chạy ⇒ `transcribe` đọc bản tiếng
       thuộc lượt chạy TRƯỚC. `pipeline.py` chép lại đúng sự cố đó trong
       `tien_quyet` của `TRANSCRIBE`, gọi tên nó là *"TIEN DE IM LANG"*.

    ⭐ Phép kiểm trên (`test_doc_THAT_SU…`) phủ đường chạy **XUÔI**: S đọc gì thì
       lịch chạy phải bảo đảm thứ đó xong trước. Nó **không** trả lời được câu
       của đường chạy lại: *ai đọc S, và chạy lại S có đụng tới họ không*. Hai
       câu trùng nhau trên một chuỗi gần như đường thẳng — nhưng trùng **do hoàn
       cảnh, không do định nghĩa** (chính `ha_nguon_cua` viết ra điều đó), nên
       chúng tách ra đúng lúc ai đó xen một nhánh vào giữa.
    """
    ngoai = vi_pham_chay_lai(ten, _ai_doc(ten), SAU_CUA, THU_TU)
    assert not ngoai, (
        f"chay lai `{ten}` KHONG vo hieu cac buoc sau, trong khi chung DOC no:\n  "
        + "\n  ".join(f"{MODULE[g]}:{d}  doc `{ten}`" for g, d in sorted(
            ngoai.items(), key=lambda kv: kv[1]))
        + f"\n\nChung se giu ket qua cua LUOT TRUOC. Them `{ten}` (hoac mot "
          "buoc tren duong toi no) vao `sau=` cua chung trong `pipeline.CHUOI`.")


def test_phep_kiem_CHAY_LAI_KHONG_RONG():
    """⛔ ĐỐI CHỨNG: một phép quét nghịch đảo rỗng thì xanh, và xanh mãi mãi.

    ⭐ Neo vào ĐÚNG cặp của sự cố thật, không vào một con số tổng: `transcribe`
       đọc `media_prepare` (`features.py:263` — chạy lại `media_prepare` thì bản
       tiếng cũ đi tiếp). Ngày phép quét thôi thấy cặp đó, bài này đỏ — chứ
       không phải 12 bài trên lặng lẽ xanh với một tập rỗng.
    """
    assert "transcribe" in _ai_doc("media_prepare")
    # Va no phai la mot NGUOI DOC dung sau -> tuc mot cap that su duoc phan xu.
    assert THU_TU["transcribe"] > THU_TU["media_prepare"]


def test_ban_THUAN_ha_nguon_KHOP_pipeline_that():
    """⛔ ĐỐI CHỨNG cho chính bộ đo: bản thuần phải nói y hệt `P.ha_nguon_cua`.

    Không có bài này thì `vi_pham_chay_lai` có thể đang phán xử một đồ thị khác
    với đồ thị mà production dùng để vô hiệu hoá — và nó vẫn xanh. Đúng bẫy
    `doc-thu-dai-dien-thay-vi-doc-thu-that`.
    """
    for g in P.TEN_GIAI_DOAN:
        assert ha_nguon(g, SAU_CUA, THU_TU) == set(P.ha_nguon_cua(g)), g


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


def test_phan_xu_CHAY_LAI_BAT_DUOC_vi_pham_that():
    """⛔ ĐỐI CHỨNG Bước 4 — dựng trên ĐỒ THỊ TỔNG HỢP, ⛔ không trên `pipeline.py`.

    Đúng cảnh chủ dự án nhắm tới: **xen một bước mới vào giữa** với một nhánh rẽ
    ngoài bao đóng. `buoc_moi` chen vào sau `media_prepare` nhưng KHÔNG khai
    `sau` đi qua `transcribe`, trong khi nó ĐỌC `transcribe`.

    ⇒ Chạy lại `transcribe` sẽ vô hiệu `content_process` mà **bỏ sót**
      `buoc_moi`, và `buoc_moi` giữ bản chép lời của lượt chạy TRƯỚC — đúng hình
      dạng sự cố `features.py:263`, chỉ ở một chỗ khác.

    ⚠️ Chuỗi THẬT hôm nay gần như một đường thẳng nên mọi bao đóng đều phủ mọi
       thứ; không phép tiêm nào trên `pipeline.py` thật tạo được vi phạm
       (`_kiem_tra_chuoi` chặn ở lúc nạp module). Đó là lý do phần phán xử nhận
       đồ thị làm dữ liệu.
    """
    sau_cua = {"media_prepare": (), "transcribe": ("media_prepare",),
               "content_process": ("transcribe",),
               "buoc_moi": ("media_prepare",)}
    thu_tu = {"media_prepare": 0, "transcribe": 1, "content_process": 2,
              "buoc_moi": 3}

    # `buoc_moi` DOC `transcribe` nhung khong an theo no -> PHAI bat, kem so dong.
    assert vi_pham_chay_lai(
        "transcribe", {"content_process": 8, "buoc_moi": 42},
        sau_cua, thu_tu) == {"buoc_moi": 42}

    # Khai `sau` di qua `transcribe` -> het vi pham, khong doi gi khac.
    da_sua = dict(sau_cua, buoc_moi=("transcribe",))
    assert vi_pham_chay_lai(
        "transcribe", {"content_process": 8, "buoc_moi": 42},
        da_sua, thu_tu) == {}

    # Nguoi doc dung TRUOC (vong sua) -> KHONG phai vi pham cua duong chay lai.
    assert vi_pham_chay_lai(
        "content_process", {"transcribe": 7}, sau_cua, thu_tu) == {}
