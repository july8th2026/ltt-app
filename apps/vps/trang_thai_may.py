"""Mô hình trạng thái của một máy — và **chỗ DUY NHẤT** được phép ghi nó.

## Vì sao một cột không đủ

Trước tệp này, `vps_instance.trang_thai` là một chuỗi 16 ký tự gánh **năm** câu hỏi
khác nhau cùng lúc:

| Câu hỏi | Ai trả lời đúng | Giá trị cũ trộn lẫn |
|---|---|---|
| Máy này còn là khách hàng của ta không? | nghiệp vụ | `dang_tao`, `da_xoa` |
| Khách **muốn** nó bật hay tắt? | ý định | `dang_chay`, `da_tat` |
| Nó **thực sự** đang bật hay tắt? | Proxmox | `dang_chay`, `da_tat` |
| Có việc gì đang chạy dở trên nó không? | hàng đợi | *(không có chỗ nào)* |
| Ta còn nói chuyện được với nó không? | phép đo | *(không có chỗ nào)* |

Hai câu cuối **không có chỗ nào để ghi**, nên chúng bị nhét vào hai câu trước. Kết
quả cụ thể: một máy vừa nhận lệnh tắt được ghi ngay là `da_tat` — nhưng đó là *ý
định*, không phải *quan sát*. Máy có tắt thật hay không thì không ai hỏi lại, và
`upid` mà Proxmox trả về được ghi vào nhật ký rồi **không ai đọc**.

Và tổ hợp mà hợp đồng đòi phải biểu diễn được — *nghiệp vụ đang hoạt động · khách
muốn tắt · quan sát thấy đang chạy · tác vụ đang tắt* — không viết ra được bằng một
chuỗi, vì bốn mệnh đề ấy đúng **cùng lúc**.

## `trang_thai` không bị xoá — nó thành hình chiếu

18 tệp test, 7 template và bốn bảng tra trong `nhan.py` đọc cột đó. Xoá nó là một
cuộc viết lại toàn app mà **không giảm rủi ro nào**: rủi ro nằm ở chỗ code *ghi* nó
tuỳ tiện, không ở chỗ code *đọc* nó.

Nên `trang_thai` ở lại, nhưng đổi vai: từ **nguồn sự thật** thành **hình chiếu** —
một giá trị tính ra từ các cột mới, ở đúng một chỗ (`chieu()`), và chỉ được ghi qua
`dat()`. Ai gán thẳng `may.trang_thai = "..."` ở nơi khác là đang dựng nguồn sự thật
thứ hai, và hai nguồn thì sớm muộn lệch nhau. `tests/test_550_vps_trang_thai.py`
canh đúng điều đó.

## Quan sát không rõ **không** được thành "đã tắt"

Đây là luật đắt nhất ở đây, và nó ngược với trực giác.

Khi Proxmox không trả lời, cám dỗ là ghi `da_tat` — nó "an toàn", nó im lặng. Nhưng
`da_tat` là một **khẳng định**: nó nói ta đã hỏi và máy đã tắt. Với khách, nó nghĩa
là "bấm Bật đi"; với vòng thu phí, nó nghĩa là máy vẫn thuộc diện thu. Ghi một
khẳng định ta không đo được là nói dối theo hướng làm người đọc hành động sai.

Nên `khong_ro` là một giá trị **thật**, và hình chiếu khi quan sát không rõ đi theo
**ý định của khách** (`dien_mong_muon`) — thứ duy nhất ta biết chắc. Sự thật rằng ta
đang không biết nằm ở `suc_khoe` + `quan_sat_luc`, và giao diện phải nói ra
(Pha 08/09).
"""
from __future__ import annotations

from datetime import datetime, timezone

# ── Vòng đời nghiệp vụ ───────────────────────────────────────────────────────
#
# Trả lời: *máy này còn là một khách hàng đang phục vụ không.* Không nói gì về
# điện. `bi_treo` ở đây là một khái niệm **TIỀN**: nó nghĩa là hết hạn thanh
# toán, và nó phải sống sót qua mọi thứ xảy ra với nguồn điện của máy.

DANG_TAO = "dang_tao"
HOAT_DONG = "hoat_dong"
BI_TREO = "bi_treo"
LOI = "loi"
DA_XOA = "da_xoa"

VONG_DOI = frozenset({DANG_TAO, HOAT_DONG, BI_TREO, LOI, DA_XOA})

# ── Điện: mong muốn và quan sát ──────────────────────────────────────────────

CHAY = "chay"
TAT = "tat"
TAM_DUNG = "tam_dung"
KHONG_RO = "khong_ro"

#: Khách **muốn** gì. Chỉ hai giá trị: không có "tôi không biết tôi muốn gì".
DIEN_MONG_MUON = frozenset({CHAY, TAT})

#: Ta **đo được** gì. `tam_dung` là trạng thái `paused` của QEMU — nó không phải
#: chạy và cũng không phải tắt, và gộp nó vào một trong hai là mất thông tin.
DIEN_QUAN_SAT = frozenset({CHAY, TAT, TAM_DUNG, KHONG_RO})

# ── Tác vụ đang chạy dở ──────────────────────────────────────────────────────
#
# Rỗng = không có gì đang chạy. Đây là thứ trả lời câu "vì sao trang không đổi
# gì sau khi tôi bấm" — trước đây không có chỗ nào ghi nó, nên câu trả lời duy
# nhất là một lời nói dối ("đã tắt") phát ra ngay lúc bấm.

KHONG_CO = ""
DANG_BAT = "dang_bat"
DANG_TAT = "dang_tat"
DANG_KD_LAI = "dang_kd_lai"
DANG_CHUP = "dang_chup"
DANG_KHOI_PHUC = "dang_khoi_phuc"
DANG_DUNG_LAI = "dang_dung_lai"
DANG_XOA = "dang_xoa"
DANG_CAP_PHAT = "dang_cap_phat"

TAC_VU = frozenset({KHONG_CO, DANG_BAT, DANG_TAT, DANG_KD_LAI, DANG_CHUP,
                    DANG_KHOI_PHUC, DANG_DUNG_LAI, DANG_XOA, DANG_CAP_PHAT})

#: Tác vụ nào **cấm** một tác vụ khác chen vào. Tất cả — nhưng viết ra thành một
#: tập hợp có tên để chỗ khác hỏi được, thay vì mỗi nơi tự liệt kê một danh sách.
TAC_VU_DOC_QUYEN = frozenset(TAC_VU - {KHONG_CO})

# ── Sức khoẻ / độ tươi của phép đo ───────────────────────────────────────────

KHOE = "khoe"
SUY_GIAM = "suy_giam"
MAT_LIEN_LAC = "mat_lien_lac"

SUC_KHOE = frozenset({KHOE, SUY_GIAM, MAT_LIEN_LAC, KHONG_RO})

#: Quan sát cũ hơn ngần này giây thì không còn được coi là "vừa đo".
#:
#: 15 phút, không phải 60 giây. Vòng đối chiếu chạy theo nhịp bảo trì (3600 giây),
#: nên đặt ngưỡng dưới nhịp đó là dán nhãn "cũ" cho **mọi** máy suốt gần cả tiếng
#: giữa hai lượt — tức một cảnh báo luôn bật, và một cảnh báo luôn bật là một
#: cảnh báo người ta học cách bỏ qua.
QUA_CU_SAU_S = 15 * 60

# ── Hình chiếu về mã cũ ──────────────────────────────────────────────────────

#: Vòng đời nào chiếu thẳng thành mã cũ mà không cần hỏi tới điện.
_CHIEU_THANG = {
    DANG_TAO: "dang_tao",
    BI_TREO: "bi_treo",
    LOI: "loi",
    DA_XOA: "da_xoa",
}


def chieu(vong_doi: str, dien_quan_sat: str, dien_mong_muon: str) -> str:
    """Mã `trang_thai` cũ, tính từ mô hình mới. **Chỗ duy nhất** biết công thức này.

    Bốn vòng đời chiếu thẳng: một máy `bi_treo` thì khách cần biết nó bị treo,
    chuyện nó đang bật hay tắt là chuyện phụ. Chỉ `hoat_dong` mới phải hỏi tới
    điện — và khi quan sát không rõ thì lấy **ý định** làm câu trả lời, vì đó là
    thứ duy nhất ta biết chắc. Xem docstring đầu tệp.
    """
    thang = _CHIEU_THANG.get(vong_doi)
    if thang is not None:
        return thang
    if dien_quan_sat == CHAY:
        return "dang_chay"
    if dien_quan_sat == TAT:
        return "da_tat"
    # `tam_dung` và `khong_ro` đều rơi vào đây: không khẳng định được, nên nói
    # theo ý định. KHÔNG mặc định về `da_tat`.
    return "dang_chay" if dien_mong_muon == CHAY else "da_tat"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def moi() -> dict:
    """Bộ trường trạng thái cho một máy **vừa được đặt mua**.

    Trả dict để `VpsInstance(**trang_thai_may.moi(), ...)` dựng được thẳng — không
    có bước "tạo rồi sửa" nào ở giữa để quên.
    """
    return {
        "vong_doi": DANG_TAO,
        "dien_mong_muon": CHAY,
        "dien_quan_sat": KHONG_RO,
        "tac_vu": DANG_CAP_PHAT,
        "suc_khoe": KHONG_RO,
        "quan_sat_luc": None,
        "trang_thai": "dang_tao",
    }


#: Mã `trang_thai` cũ → `(vong_doi, dien_mong_muon, dien_quan_sat, tac_vu)`.
#:
#: ⚠️ Bảng này phải **giống hệt** `_BACKFILL` trong
#: `alembic/versions/20260909_1000_vps_v2_tach_trang_thai.py`. Hai bản sao là cố
#: ý — migration không được import mã ứng dụng (mã đổi, migration thì không được
#: đổi nghĩa sau khi đã chạy trên production). Nhưng hai bản sao lệch nhau thì
#: một hàng di trú một kiểu và một hàng dựng trong RAM một kiểu khác, cho ra hai
#: máy "giống nhau" hành xử khác nhau. `tests/test_550_vps_trang_thai.py` đối
#: chiếu hai bảng bằng cách đọc AST của migration.
TU_MA_CU = {
    "dang_tao": (DANG_TAO, CHAY, KHONG_RO, DANG_CAP_PHAT),
    "dang_chay": (HOAT_DONG, CHAY, KHONG_RO, KHONG_CO),
    "da_tat": (HOAT_DONG, TAT, KHONG_RO, KHONG_CO),
    "bi_treo": (BI_TREO, TAT, KHONG_RO, KHONG_CO),
    "loi": (LOI, CHAY, KHONG_RO, KHONG_CO),
    "da_xoa": (DA_XOA, TAT, TAT, KHONG_CO),
}

#: Mã lạ đi về đâu. `loi` chứ không phải `hoat_dong`: `loi` vẫn điều khiển được
#: và vẫn hiện lý do cho khách, còn `hoat_dong` là một khẳng định rằng mọi thứ
#: bình thường — và ta vừa gặp một mã ta không hiểu.
_MA_LA = (LOI, CHAY, KHONG_RO, KHONG_CO)


def chuan_hoa(may):
    """Suy các cột mới từ `trang_thai` cũ **khi chúng chưa từng được đặt**.

    Đây là lớp tương thích mà ADR-01 hứa, và nó phục vụ ba loại đối tượng: hàng
    CSDL cũ chưa qua di trú, đối tượng dựng trong test chỉ khai `trang_thai`, và
    `VpsInstance(...)` dựng bằng tay mà quên các cột mới.

    **Chỉ điền khi `vong_doi` còn rỗng.** Đã có mô hình mới thì không đụng vào —
    nếu không, một máy `hoat_dong` mang hình chiếu `bi_treo` (đúng lúc giữa hai
    lệnh gán) sẽ bị kéo ngược về `bi_treo`, tức hình chiếu điều khiển ngược lại
    nguồn sự thật. Đó đúng là thứ ADR-01 sinh ra để chặn.
    """
    if str(getattr(may, "vong_doi", "") or ""):
        return may
    # Rỗng ≠ lạ. `VpsInstance()` trần chưa có `trang_thai` (mặc định của cột chỉ
    # áp lúc flush), và nó là một máy **vừa đặt mua** — không phải một mã hỏng.
    cu = str(getattr(may, "trang_thai", "") or "") or "dang_tao"
    vd, mm, qs, tv = TU_MA_CU.get(cu, _MA_LA)
    may.vong_doi, may.dien_mong_muon = vd, mm
    may.dien_quan_sat, may.tac_vu = qs, tv
    if not str(getattr(may, "suc_khoe", "") or ""):
        may.suc_khoe = KHONG_RO
    if not hasattr(may, "quan_sat_luc"):
        may.quan_sat_luc = None
    return may


def _kiem(ten: str, gt: str, hop_le: frozenset) -> str:
    gt = str(gt or "")
    if gt not in hop_le:
        raise ValueError(f"{ten}={gt!r} khong hop le; nhan: {sorted(hop_le)}")
    return gt


_KHONG_DOI = object()


def dat(may, *, vong_doi=_KHONG_DOI, dien_mong_muon=_KHONG_DOI,
        dien_quan_sat=_KHONG_DOI, tac_vu=_KHONG_DOI, suc_khoe=_KHONG_DOI,
        quan_sat_luc=_KHONG_DOI, ly_do=_KHONG_DOI):
    """Đổi trạng thái của một máy. **Đường ghi duy nhất.**

    Chỉ đổi những gì được truyền vào; phần còn lại giữ nguyên. Sau khi đổi, tính
    lại `trang_thai` — nên hình chiếu **không bao giờ** lệch khỏi mô hình, kể cả
    khi người gọi quên nghĩ tới nó.

    Giá trị sai ném `ValueError` ngay tại chỗ gọi. Đó là cố ý: một mã trạng thái
    gõ nhầm mà lọt vào CSDL sẽ hiện ra ở giao diện dưới dạng một badge xám vô
    nghĩa, và không ai truy được nó vào từ đâu.
    """
    chuan_hoa(may)
    if vong_doi is not _KHONG_DOI:
        may.vong_doi = _kiem("vong_doi", vong_doi, VONG_DOI)
    if dien_mong_muon is not _KHONG_DOI:
        may.dien_mong_muon = _kiem("dien_mong_muon", dien_mong_muon,
                                   DIEN_MONG_MUON)
    if dien_quan_sat is not _KHONG_DOI:
        may.dien_quan_sat = _kiem("dien_quan_sat", dien_quan_sat,
                                  DIEN_QUAN_SAT)
    if tac_vu is not _KHONG_DOI:
        may.tac_vu = _kiem("tac_vu", tac_vu, TAC_VU)
    if suc_khoe is not _KHONG_DOI:
        may.suc_khoe = _kiem("suc_khoe", suc_khoe, SUC_KHOE)
    if quan_sat_luc is not _KHONG_DOI:
        may.quan_sat_luc = quan_sat_luc
    if ly_do is not _KHONG_DOI:
        may.ly_do = str(ly_do or "")
    may.trang_thai = chieu(may.vong_doi, may.dien_quan_sat, may.dien_mong_muon)
    return may


def ghi_quan_sat(may, dien: str, *, now: datetime | None = None):
    """Ghi lại một lần **đo thật** trạng thái điện của máy trên hypervisor.

    Khác `dat(dien_quan_sat=...)` ở chỗ nó cũng đóng dấu thời điểm và suy ra sức
    khoẻ — hai thứ luôn phải đi cùng phép đo, và tách ra là để quên một trong hai.

    Đo được `khong_ro` **không** phải một lần đo: nó là một lần hỏi thất bại, nên
    nó đặt `mat_lien_lac` và vẫn đóng dấu thời điểm (ta biết ta đã thử lúc nào).
    """
    dien = _kiem("dien_quan_sat", dien, DIEN_QUAN_SAT)
    return dat(may, dien_quan_sat=dien, quan_sat_luc=now or _now(),
               suc_khoe=MAT_LIEN_LAC if dien == KHONG_RO else KHOE)


def bat_dau_tac_vu(may, loai: str):
    """Đánh dấu một tác vụ dài đang chạy trên máy.

    KHÔNG đổi vòng đời và KHÔNG đổi quan sát: một máy đang tắt dở vẫn đang chạy
    cho tới khi ta đo được ngược lại. Đây chính là chỗ mà bản cũ nói dối.
    """
    return dat(may, tac_vu=_kiem("tac_vu", loai, TAC_VU_DOC_QUYEN))


def ket_thuc_tac_vu(may):
    """Tác vụ đã tới hồi kết — thành công hay thất bại đều gọi hàm này."""
    return dat(may, tac_vu=KHONG_CO)


def dang_ban(may) -> bool:
    """Máy này có tác vụ dài đang chạy dở không."""
    return str(getattr(may, "tac_vu", "") or "") in TAC_VU_DOC_QUYEN


def tuoi_quan_sat(may, *, now: datetime | None = None):
    """Phép đo gần nhất cách đây bao nhiêu giây. `None` = chưa đo lần nào."""
    luc = getattr(may, "quan_sat_luc", None)
    if luc is None:
        return None
    if luc.tzinfo is None:
        luc = luc.replace(tzinfo=timezone.utc)
    return max(0.0, ((now or _now()) - luc).total_seconds())


def qua_cu(may, *, now: datetime | None = None,
           nguong_s: float = QUA_CU_SAU_S) -> bool:
    """Phép đo gần nhất đã quá cũ để tin chưa.

    **Chưa đo lần nào cũng tính là quá cũ.** Đó không phải chi tiết kỹ thuật: một
    máy chưa từng được đo và một máy đo từ tuần trước cho ta cùng một lượng hiểu
    biết về hiện tại, tức là không có gì.
    """
    tuoi = tuoi_quan_sat(may, now=now)
    return tuoi is None or tuoi > nguong_s
