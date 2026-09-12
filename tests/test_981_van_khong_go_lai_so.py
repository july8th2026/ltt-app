"""test_981 — chú thích không được gõ lại một con số đã có tên hằng.

Dải **980–989** của chương trình MASTER UPGRADE (`docs/LLM_UPGRADE_MASTER_PLAN.md`).

═══════════════════════════════════════════════════════════════════════════
 KHUYẾT TẬT: ĐOẠN VĂN ĐI SỬA SỐ TRÔI ĐÃ TỰ TRÔI
═══════════════════════════════════════════════════════════════════════════

`apps/ltt_llm/manifest.py` mang một khối mở đầu bằng
*"🔴 SỬA 01/09 — BA CON SỐ Ở ĐOẠN NÀY ĐỀU ĐÃ TRÔI"*. Bản vá ấy thay câu sai cũ
bằng một **bảng số cụ thể**:

    engine `qwen38-api`     `-c 131072`, trần vào 96.256, công bố 89K
    engine `qwen38-vision`  `-c 65536`,  trần vào 30.720, công bố 28K

Ngày 03/09 ngữ cảnh nâng lên 204.800 (và vision lên 131.072). **Cả bảng hết
đúng cùng lúc.** Đo ngày 09/09: bốn khối văn trong `apps/ltt_llm/` và
`llm_gateway/` đang nói số cũ, trong đó có cả trường khai
`Config.max_input_tokens` (*"Engine có cửa sổ 131.072; public giữ 65.000 theo
Q116"* — ba mệnh đề, ba cái sai).

⭐ ĐIỀU ĐÁNG HỌC KHÔNG PHẢI "AI ĐÓ CẨU THẢ". Bản vá 01/09 sửa **giá trị**, còn
   khuyết tật là **hình dạng**: một đoạn văn chép lại con số của nơi khác sẽ
   trôi mỗi lần nơi kia đổi, và **không ai có nghĩa vụ nhớ tới nó**. Chính
   `manifest.py` đã đặt tên cho việc này ở `_cua_so_noi_voi_khach`:

       "Sửa giá trị không phải sửa hình dạng."

   — rồi bản vá đọc câu đó và vẫn làm đúng điều nó cảnh báo. Nên lần này phải là
   một hàng rào, không phải một lần sửa nữa.

═══════════════════════════════════════════════════════════════════════════
 VÌ SAO LUẬT HẸP THẾ NÀY, KHÔNG PHẢI "CẤM MỌI SỐ TRONG CHÚ THÍCH"
═══════════════════════════════════════════════════════════════════════════

Luật rộng ấy đã được cân nhắc và **bỏ**, vì nó phá thứ đang có giá trị. Ví dụ
`llm_gateway/config.py` giải thích phép dẫn xuất bằng chính con số:

    (= CUA_SO_MODEL − TOKEN_RA_TRAN − LE = 204800 − 32768 − 2048)

Dòng đó **dạy công thức**, và người đọc kiểm tra được nó bằng mắt. Cấm nó là đổi
một tài liệu tốt lấy một hàng rào sạch. Bộ nhớ dự án gọi đúng cái bẫy này:
*"bộ dò quét văn bản trừng phạt việc giải thích"*.

⭐ Nên tệp này chỉ chốt **hai hình dạng đã thật sự trôi**, và cả hai đều là dạng
   *"khai một giá trị hiện hành"* chứ không phải *"giải thích một phép tính"*:

     A.  `-c <số>`            — khai tham số engine
     B.  `TÊN_HẰNG (<số>`     — chú giải giá trị cho một hằng có tên

⛔ Và có ĐƯỜNG THOÁT tường minh: nói rõ đó là lịch sử thì được giữ. Kể chuyện
   một con số đã chết là việc **có ích** — bốn khối văn quý nhất trong hai gói
   này đều là chuyện như vậy. Khuôn đường thoát lấy đúng của
   `test_604_q120_tran_ngu_canh_mot_nguon.py`, vốn đã dùng cách này cho `docs/`.
"""
from __future__ import annotations

import pathlib
import re

from apps.ltt_llm import ngan_sach

GOC = pathlib.Path(__file__).resolve().parents[1]

PHAM_VI = (
    "apps/ltt_llm/ngan_sach.py",
    "apps/ltt_llm/manifest.py",
    "apps/ltt_llm/features.py",
    "llm_gateway/config.py",
    "llm_gateway/catalog.py",
    "llm_gateway/ngan_sach.py",
)

#: Cửa sổ engine hợp lệ **hôm nay**. Đọc từ mã, không gõ lại.
CUA_SO_HOP_LE = set(ngan_sach.CUA_SO_THEO_MODEL.values())

#: Hằng có tên → giá trị sống. Đọc từ mã, không gõ lại.
#:
#: 🔴 `CUA_SO_MODEL_VISION` ĐÃ BỊ GỠ BỎ (D02 / dual-model 2.3, hằng gỡ ở 2.6), và
#:    dòng đó ở đây làm **cả tệp này chết ở bước COLLECT** — `AttributeError` tại
#:    cấp module, tức 12 phép kiểm bên dưới không chạy một cái nào và gate chỉ
#:    báo đúng một dòng lỗi thu thập. Một tệp chết ở collect là tệ hơn một
#:    phép kiểm đỏ: nó **ẩn** mọi điều còn lại nó biết.
#:
#: ⛔ Và cách sửa KHÔNG phải chỉ xoá dòng đó. Bộ dò này đếm *"chú thích có gõ
#:    lại giá trị của một hằng đang sống"*, nên bỏt một tên khỏi bảng là **thu
#:    hệp** phạm vi nó canh. Hai tên thêm vào đây là hai **dẫn xuất mới** của
#:    2.6 — đúng loại số một đoạn văn hay chép lại, và đúng loại số sẽ đổi
#:    lần sau ai đó sửa `-c`.
HANG_SONG = {
    "CUA_SO_MODEL": ngan_sach.CUA_SO_MODEL,
    "CUA_SO_HEP_NHAT": ngan_sach.CUA_SO_HEP_NHAT,
    "TOKEN_VAO_TRAN": ngan_sach.TOKEN_VAO_TRAN,
    "TOKEN_RA_TRAN": ngan_sach.TOKEN_RA_TRAN,
    "CONG_BO_CHO_CLIENT": ngan_sach.CONG_BO_CHO_CLIENT,
    "NEN_CHO_CLIENT": ngan_sach.NEN_CHO_CLIENT,
}

#: Dấu miễn trừ: đoạn văn tự khai nó đang kể chuyện cũ.
#: ⚠️ Phải là chữ NÓI RA Ý LỊCH SỬ. Đừng thêm từ chung chung như "cũ" trần —
#:    nó xuất hiện trong quá nhiều câu và sẽ mở toang đường thoát.
DAU_LICH_SU = (
    "lịch sử", "LỊCH SỬ", "từng ghi", "TỪNG GHI", "từng đứng", "TỪNG ĐỨNG",
    "từng viết", "hết đúng", "đã thay", "bản cũ", "Bản cũ", "câu cũ",
    "đã trôi", "ĐÃ TRÔI", "trước 03/09", "Trước 03/09", "trước 01/09",
    "khi `qwen38-vision` còn", "bảng số cụ thể",
    # Đã gỡ ở 2.6: cùng loại với "đã thay" — nói rõ đối tượng được nói tới
    # **không còn tồn tại**, nên mọi con số đi kèm nó là số của một thứ đã chết.
    # ⚠️ Thêm được vì nó **cụ thể**; đừng thêm "cũ" hay "trước đây" trần.
    "đã gỡ", "ĐÃ GỠ",
)

#: Bao nhiêu dòng phía trước còn được tính là "cùng một đoạn". Một khối chú
#: thích của kho này thường dài 5–12 dòng.
CUA_SO_DONG = 10

MAU_C = re.compile(r"-c\s+([0-9][0-9_.]*)")
MAU_HANG = re.compile(
    r"\b(" + "|".join(HANG_SONG) + r")\b`?\s*\(\s*([0-9][0-9_.]*)")


def _so(tho: str) -> int:
    """`131.072` / `131_072` / `131072` → 131072. Dấu chấm ở đây là phân cách
    hàng nghìn kiểu Việt, không phải dấu thập phân."""
    return int(tho.replace(".", "").replace("_", ""))


def _co_dau_lich_su(dong_list: list[str], i: int) -> bool:
    dau = max(0, i - CUA_SO_DONG)
    khoi = "\n".join(dong_list[dau:i + 1])
    return any(d in khoi for d in DAU_LICH_SU)


def _quet(kiem) -> list[str]:
    """Chạy `kiem(dong, i, dong_list)` trên mọi dòng của mọi tệp trong phạm vi."""
    loi: list[str] = []
    for tep in PHAM_VI:
        dong_list = (GOC / tep).read_text(encoding="utf-8").splitlines()
        for i, dong in enumerate(dong_list):
            for msg in kiem(dong, i, dong_list):
                loi.append(tep + ":" + str(i + 1) + " " + msg)
    return loi


def _kiem_c(dong: str, i: int, dong_list: list[str]):
    """⭐ HAI MỨC CHẶT, VÀ MỨC HAI SINH RA TỪ MỘT ĐỐI CHỨNG ĐỎ.

    Bản đầu chỉ hỏi *"số này có phải một cửa sổ đang sống không"*. Đối chứng
    `test_doi_chung_bang_engine_cu_bi_bat` bác nó ngay: bảng cũ của
    `manifest.py` viết ``engine `qwen38-api` `-c 131072```, và **131.072 hôm
    nay là cửa sổ hợp lệ** — của *vision*. Tức luật chỉ-thành-viên bắt được
    dòng vision cũ mà **thả** dòng api cũ.

    ⛔ Đó là một cửa giả đúng nghĩa: nó xanh trên đúng nửa khuyết tật mà nó sinh
       ra để chặn, và nửa ấy là nửa nói về model khách dùng nhiều nhất.

    ⇒ Nên khi trên cùng dòng có **tên hồ sơ**, ta đòi khớp **đúng hồ sơ đó**.
      Không có tên hồ sơ thì lùi về mức thành-viên (vẫn bắt được số chết hẳn).
    """
    if _co_dau_lich_su(dong_list, i):
        return
    for m in MAU_C.finditer(dong):
        gt = _so(m.group(1))
        ho_so = [t for t in ngan_sach.CUA_SO_THEO_MODEL if t in dong]
        if len(ho_so) == 1:
            mong = ngan_sach.CUA_SO_THEO_MODEL[ho_so[0]]
            if gt != mong:
                yield ("`-c " + m.group(1) + "` di kem `" + ho_so[0]
                       + "` nhung ho so ay chay -c " + str(mong))
            continue
        if gt not in CUA_SO_HOP_LE:
            yield ("`-c " + m.group(1) + "` khong phai cua so engine nao dang song "
                   + str(sorted(CUA_SO_HOP_LE)) + " va khong khai la lich su")


def _kiem_hang(dong: str, i: int, dong_list: list[str]):
    for m in MAU_HANG.finditer(dong):
        ten, gt = m.group(1), _so(m.group(2))
        if gt == HANG_SONG[ten] or _co_dau_lich_su(dong_list, i):
            continue
        yield (ten + " duoc chu giai la " + m.group(2) + " nhung gia tri song la "
               + str(HANG_SONG[ten]) + " va khong khai la lich su")


def test_tham_so_c_trong_chu_thich_phai_la_cua_so_dang_song():
    """Hình dạng A — `-c <số>`.

    Đây là hình dạng đã giết `ngan_sach.py` (*"`qwen38-vision` nạp với
    `-c 65536`"* trong khi giá trị gán ngay dưới đã là 131.072) và
    `manifest.py` (bảng hai dòng engine).
    """
    loi = _quet(_kiem_c)
    assert not loi, (
        "chu thich khai `-c` bang mot cua so khong con ton tai:\n  "
        + "\n  ".join(loi)
        + "\n\nSua: doc so tu `ngan_sach.CUA_SO_THEO_MODEL`, hoac neu dang KE"
          " CHUYEN CU thi noi ro trong doan (vd 'tung ghi', 'het dung').")


def test_chu_giai_gia_tri_cho_mot_hang_phai_khop_hang_do():
    """Hình dạng B — `TÊN_HẰNG (<số>`.

    Đây là hình dạng đã giết `manifest.py`: *"`TOKEN_VAO_TRAN` (96.256, vì phải
    chừa chỗ…)"* và *"`CONG_BO_CHO_CLIENT` (88.555, chừa thêm 8 %)"*.
    """
    loi = _quet(_kiem_hang)
    assert not loi, (
        "chu giai gia tri lech voi hang dang song:\n  " + "\n  ".join(loi))


# ══════════════════════════════════════════════════════════════════════════
#  ĐỐI CHỨNG — tiêm lại đúng văn bản cũ, đòi nó ĐỎ
# ══════════════════════════════════════════════════════════════════════════
#
# ⛔ KHÔNG BỎ HAI HÀM NÀY. Hai chốt trên hôm nay xanh, và **xanh-rỗng trông y
#    hệt xanh-thật**. Bộ nhớ dự án: *"Không đối chứng thì số 0 không phải phát
#    hiện"* — với một phép kiểm, đối chứng nghĩa là tiêm bản cũ xem có đỏ không.
#
# ⭐ Và đối chứng ở đây KHÔNG bịa: cả hai chuỗi dưới là **nguyên văn** thứ đã
#    nằm trong kho tới sáng 09/09.

VAN_CU_MANIFEST = [
    "   Số đúng tại thời điểm viết:",
    "",
    "     * engine `qwen38-api`     `-c 131072`, trần vào 96.256, công bố 89K",
    "     * engine `qwen38-vision`  `-c 65536`,  trần vào 30.720, công bố 28K",
]

VAN_CU_NGAN_SACH = [
    "       `TOKEN_VAO_TRAN` (96.256, vì phải chừa chỗ cho câu trả lời dài nhất",
]


def _chay_tren(dong_list: list[str], kiem) -> list[str]:
    ra: list[str] = []
    for i, dong in enumerate(dong_list):
        ra.extend(kiem(dong, i, dong_list))
    return ra


def test_doi_chung_bang_engine_cu_bi_bat():
    """Bảng `-c` cũ của `manifest.py` phải bị bắt — nếu không, chốt A là cửa giả."""
    bat = _chay_tren(VAN_CU_MANIFEST, _kiem_c)
    assert len(bat) == 2, (
        "chot A KHONG bat duoc bang engine cu (bat duoc " + str(bat) + "). "
        "Mot chot khong do duoc tren khuyet tat sinh ra no la mot cua gia.")


def test_doi_chung_chu_giai_hang_cu_bi_bat():
    """`TOKEN_VAO_TRAN (96.256` phải bị bắt."""
    bat = _chay_tren(VAN_CU_NGAN_SACH, _kiem_hang)
    assert len(bat) == 1, "chot B KHONG bat duoc chu giai cu: " + str(bat)


def test_doi_chung_duong_thoat_lich_su_that_su_mo():
    """Và đường thoát phải **thật sự** mở — nếu không, người ta sẽ xoá chuyện cũ.

    Bốn khối văn quý nhất trong hai gói này là chuyện về những con số đã chết.
    Một hàng rào không cho kể chuyện ấy sẽ được "sửa" bằng cách xoá chuyện.
    """
    co_dau = ["   ⚠️ Câu dưới là chuyện cũ, nó đã hết đúng từ 03/09:",
              "      `qwen38-vision` nạp với `-c 65536`."]
    assert not _chay_tren(co_dau, _kiem_c), "duong thoat lich su khong mo"
