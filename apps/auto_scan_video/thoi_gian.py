"""Lập kế hoạch thời gian: đặt từng đoạn tiếng vào đúng chỗ trên trục thời gian.

Thi hành `ADR-003-mo-hinh-thoi-gian.md`.

## Một câu tóm tắt cả tệp

Người ta **không nói liền mạch**. Giữa các câu luôn có khoảng nghỉ, và khoảng nghỉ
đó là ngân sách thời gian chưa ai dùng. Nên một câu tiếng Việt dài hơn câu gốc thì
**tràn sang khoảng lặng phía sau** thay vì bị nén cho vừa — và phần tràn đó là
một món **nợ** được trả lại ở khoảng lặng kế tiếp.

## Ba con số, ba nguồn gốc khác nhau — và điều đó quan trọng

    TY_LE_MUON_KHOANG_LANG = 0.7    ← mượn từ SoniTranslate (đã chạy thật)
    TRAN_TANG_TOC          = 1.15   ← mượn từ Subdub (đã chạy thật)
    TRAN_TROI_SO_DOAN      = 3      ← TA TỰ ĐẶT, chưa dự án nào có

⚠️ Hai số đầu là ngưỡng **mượn**, và kho này có luật: mượn ngưỡng thì phải đo lại.
   Số thứ ba là một **lựa chọn có lý lẽ, chưa phải một phép đo** — nó tồn tại vì
   Subdub không có trần nào cả, và không có trần thì trên một video nói dồn, nợ
   tăng đơn điệu tới khi tiếng rời hình cả chục giây.

## Vì sao ngân sách là "tới lúc đoạn sau bắt đầu"

Đây là dòng quan trọng nhất, và nó lấy từ `Subdub/src/subdub/media/audio.py`:

    block_duration = next_block_start_ms - block_start_ms   # KHÔNG phải end - start

Lấy `het - bat` là chỉ lấy thời gian **đang nói**, tức vứt đi toàn bộ khoảng lặng.
Trên một video có nhịp nghỉ bình thường, đó là vứt đi phần lớn ngân sách sẵn có.

⛔ Tệp này **không** chạm tới tệp âm thanh nào. Nó ra một **kế hoạch**; việc ghép
   là của COMPOSE/RENDER. Trộn hai việc lại là giấu một quyết định thời gian bên
   trong một phép ghép, nơi không ai đi tìm nó.
"""
from __future__ import annotations

import hashlib
import json

from platform_core.i18n import _ as _t

#: Phần khoảng lặng được phép mượn. Còn lại 30 % để bản lồng tiếng vẫn có nhịp nghỉ.
#:
#: ⭐ Mượn từ `SoniTranslate` (`acceleration_rate_regulation`): 0,5 khi cùng người
#:    nói, 0,7 khi khác người. MVP chưa phân biệt người nói (không có diarization
#:    trong chuỗi), nên lấy 0,7 — con số rộng hơn — và ghi rằng đó là lý do.
TY_LE_MUON_KHOANG_LANG = 0.7

#: Trần tăng tốc. Chỉ dùng để TRẢ NỢ, không dùng để ép vừa.
#:
#: ⛔ Cố ý KHÔNG lấy `2.1` của SoniTranslate: nhanh gấp đôi thì không còn là giọng
#:    người. 1,15 là mặc định của Subdub và nằm trong vùng `atempo` gần như không
#:    nghe ra.
TRAN_TANG_TOC = 1.15

#: Trần **KỸ THUẬT** của `ffmpeg atempo` cho MỘT lần gọi — ⛔ KHÔNG phải một
#: chính sách sản phẩm (đó là `TRAN_TANG_TOC` ngay trên).
#:
#: 🔑 Qua trần này thuật toán WSOLA của `atempo` ⛔ không còn giữ được dạng sóng,
#:    cho ra **TIẾNG RÁC** chứ ⛔ không phải "tiếng nhanh" — khác hẳn cái giá của
#:    việc vượt `TRAN_TANG_TOC` (giọng hơi méo nhưng vẫn nghe được lời).
#:
#: ⭐ **Khai ở ĐÂY từ 28/09 (B13-A4), ⛔ không còn ở `giai_doan_thoi_gian`.** Lý do
#:    cơ học: từ A4, `lap_ke_hoach` chừa chỗ theo hệ số **SẼ ĐƯỢC ÁP** (đã kẹp về
#:    trần này), nên `kiem()` phải biết trần ấy. `giai_doan_thoi_gian` giữ tên
#:    `TRAN_KY_THUAT_ATEMPO` như một **bí danh** trỏ về đây — một con số, một chỗ
#:    khai. ⛔ Đừng gõ lại `2.0` ở đâu nữa.
TRAN_KY_THUAT_ATEMPO = 2.0

#: Trần cứng cho nợ trôi, tính bằng **ngân sách của N đoạn kế tiếp**.
#:
#: 🔴 Không dự án tham chiếu nào có trần này, và đó là một thiếu sót của chúng:
#:    trên video nói dồn, nợ tăng đơn điệu và không gì chặn lại. Ta cần trần vì
#:    D-ASV-03 sao chép luồng hình — tổng thời lượng là một con số cố định.
TRAN_TROI_SO_DOAN = 3

#: Chồng lấn nhỏ được chấp nhận giữa hai đoạn liền nhau.
#: Theo `avoid_overlap` của SoniTranslate cho trường hợp cùng người nói (0,2 s).
TRAN_CHONG_LAN_MS = 200

#: Đổi khi đổi bất kỳ hằng số nào ở trên. Vào vân tay (O13).
#:
#: ⛔ **25/09: `lap_ke_hoach` nhận thêm `nhom_gop` và con số này CỐ Ý ĐỨNG YÊN.**
#:    Điều kiện của chính nó là *"đổi bất kỳ hằng số nào ở trên"* — không hằng nào
#:    đổi. Và cache vẫn không thể nói dối: với một lượt chạy **không gộp** kế hoạch
#:    ra **y hệt từng mili-giây** (`test_4700` chốt), còn với một lượt **có gộp**
#:    thì `ban_ke.json` khác ⇒ `checksum` của nó khác ⇒ `van_tay_ke_hoach` đã khác.
#:
#: 🔴 **1 → 2 (b4 hai giai đoạn, 25/09): `ban_do` RỜI KHỎI hàm này.** Lần này thì
#:    PHẢI nâng, và lý do ngược hẳn đoạn trên: kế hoạch ra **khác** — mọi mốc giờ
#:    nằm trên trục NGUỒN, và trường `ban_do` không còn trong tệp. Một kế hoạch
#:    cũ và một kế hoạch mới cho cùng đầu vào là hai tệp khác nhau, nên một cache
#:    cũ dùng lại được là một cache nói dối.
#: ⛔ **28/09 (B13-A2): `he_so_co_gian` đổi mẫu số và con số này CỐ Ý ĐỨNG YÊN.**
#:    Điều kiện của chính nó là *"đổi bất kỳ hằng số nào ở trên"* — ⛔ không hằng
#:    nào đổi, và `lap_ke_hoach` ra **y hệt từng mili-giây** cho cùng đầu vào.
#:
#: ⭐ Và cache vẫn ⛔ không thể nói dối: `he_so_co_gian` nằm **trong** `ban_ke.json`
#:    (`giai_doan_giong._ke_nan`), nên bản vá đổi `checksum` của bản kê ⇒ đổi
#:    `van_tay_ke_hoach` (nó bấm `ban_ke_tieng`) ⇒ `timing_align` trộn lại.
#:
#: ⚠️ Cái ⛔ KHÔNG được nâng: vân tay từng đoạn tiếng (`giai_doan_giong._van_tay`
#:    = `ma + chu + giọng + preset + từ điển`). Tệp `.wav` ⛔ không đổi một byte —
#:    cùng chữ, cùng giọng — nên nâng nó là mua lại toàn bộ lượt TTS bằng tiền
#:    thật cho một thay đổi ⛔ không chạm âm thanh sinh ra.
#:
#: ⚠️ Một lượt chạy có `voice_synthesis` ĐÃ `succeeded` TRƯỚC bản vá thì `ban_ke`
#:    của nó vẫn ghi `he_so_co_gian` theo luật CŨ, và `timing_align` sẽ thi hành
#:    đúng bản kê ấy. Đó là ĐÚNG (bản kê là bản ghi của lượt đọc đã trả tiền),
#:    ⛔ không phải một lỗi cache — bản vá ăn từ lượt chạy mới.
#:
#: 🔴 **2 → 3 (28/09, B13-A4): `lap_ke_hoach` thôi tự tăng tốc để trả nợ.** Lần
#:    này thì PHẢI nâng, và lý do ngược hẳn đoạn trên: `dai_ms` của **mọi** đoạn
#:    đổi (⛔ không còn chia cho một `he_so_toc` do chính hàm này bịa ra), nên
#:    `dat_tai_ms` của mọi đoạn sau nó đổi theo. Một kế hoạch cũ và một kế hoạch
#:    mới cho cùng đầu vào là HAI tệp khác nhau ⇒ một cache cũ dùng lại được là
#:    một cache **nói dối**. Hằng số `TRAN_KY_THUAT_ATEMPO` cũng mới, và điều
#:    kiện *"đổi bất kỳ hằng số nào ở trên"* cũng đòi đúng lần nâng này.
#: 🔴 **3 → 4 (28/09, B15): `so_doan_bi_cat` tách thành HAI khoá.** Hình dạng
#:    `ke_hoach` đổi (hai khoá mới), nên một kế hoạch cũ đọc bằng mã mới sẽ báo
#:    `0`/`0` cho hai khoá ấy — tức một lời khai SAI về nguyên nhân, ⛔ không
#:    phải một trường thiếu. `kiem()` đọc `schema`, còn vân tay đọc số này.
PHIEN_BAN_THOI_GIAN = 4

#: ⬆️ 1 → 2: bỏ trường `ban_do` (b4 hai giai đoạn). `kiem()` đọc số này, nên một
#:    kế hoạch của lượt chạy cũ bị TỪ CHỐI thay vì được đọc thiếu một trường.
SCHEMA_KE_HOACH = 2


class ThoiGianError(ValueError):
    """Kế hoạch thời gian không dựng được."""


def _ms(giay: float) -> int:
    return int(round(float(giay) * 1000))


def ngan_sach_doan(moc_ms: list[int], i: int, tong_ms: int) -> int:
    """Ngân sách của đoạn `i`: **tới lúc đoạn sau bắt đầu**.

    Đoạn cuối lấy tới hết nguồn — phần đuôi sau câu cuối cũng là khoảng lặng dùng
    được, và bỏ nó đi là tự làm chặt chính chỗ dễ thở nhất.

    🔴 **`moc_ms` là các mốc đã đổi sang trục BẢN RA, không phải `muc` gốc.**

       Bản trước nhận `muc` rồi tự đọc `muc[i]["bat"]` — tức giờ **nguồn** — rồi
       trừ vào `tong_ms`. Khi pha 16 đổi `tong_ms` sang giờ **bản ra**, hàm này
       lặng lẽ trộn hai đồng hồ: hiệu hai mốc nguồn **không bằng** khoảng cách
       của chúng ở bản ra khi giữa chúng có một cảnh bị cắt.

    ⭐ Nên nó không được phép tự đọc mốc nữa. Người gọi đã đổi mốc một lần, ở một
       chỗ, và truyền kết quả xuống — một phép đổi ở một nơi thì kiểm được; một
       phép đổi rải rác thì sớm muộn có một chỗ bị quên.
    """
    bat = int(moc_ms[i])
    if i + 1 < len(moc_ms):
        return max(0, int(moc_ms[i + 1]) - bat)
    return max(0, int(tong_ms) - bat)


def ngan_sach_nan_s(khe_s: float, ngan_sach_s: float) -> float:
    """Ngân sách mà **bậc thang nắn** được phép dùng cho một đoạn, tính bằng giây.

    🔴 **Vì sao hàm này tồn tại (26/09/2026).** `giai_doan_giong.py:211` hỏi
       `nan_cho_vua.khe_cua(m)` = `ket - bat`, tức **⛔ không có khoảng lặng**, rồi
       lấy con số đó làm **cửa tiêu tiền** (`nen_viet_lai` → gọi LLM 16 giây).
       Nhưng cửa **thực thi** (`lap_ke_hoach` ở `timing_align`) lại mượn tới
       `TY_LE_MUON_KHOANG_LANG` của khoảng lặng. ⇒ Một đoạn chỉ cần mượn 0,3 giây
       **miễn phí** vẫn phải trả **2 lời gọi LLM + 3 lượt TTS**.

    ⭐ Và chính `nan_thoi_luong.Khe.ngan_sach_s` đã viết ra lời buộc tội:
       *"⛔ Lấy `ket - bat` là vứt hết khoảng lặng, tức vứt phần lớn ngân sách."*

    ⛔ **Không** sửa `khe_cua` để nó tự cộng khoảng lặng: `khe_cua` đang trả lời
       ĐÚNG câu hỏi của nó (*"khe của đoạn này rộng bao nhiêu"*). Sai là **câu được
       hỏi** ở cửa tiêu tiền, ⛔ không phải câu trả lời.

    ⚠️ Tỉ lệ mượn lấy từ `TY_LE_MUON_KHOANG_LANG` — **cùng** hằng số mà
       `lap_ke_hoach` dùng. ⛔ Không gõ lại `0.7`: hai bản sao của một chính sách là
       thứ kho này đã trả giá.
    """
    khe_s = max(0.0, float(khe_s))
    ngan_sach_s = max(khe_s, float(ngan_sach_s))
    return khe_s + (ngan_sach_s - khe_s) * TY_LE_MUON_KHOANG_LANG


def doi_chieu_he_so_toc(he_so_ke_hoach: dict[str, float],
                        he_so_da_ap: dict[str, float]) -> dict:
    """HAI máy tăng tốc, đối chiếu trên cùng tập `ma` — hàm THUẦN (B13-B3/B4).

    `he_so_ke_hoach`  `{ma: he_so_toc}` của `lap_ke_hoach` — thứ kế hoạch **ĐỊNH**
                      nén để trả nợ, và thứ ⛔ KHÔNG ai thi hành (`ket_xuat.
                      dung_lenh` chỉ map `master`).
    `he_so_da_ap`     `{ma: h_ap}` mà `am_master.tron_lo` **THẬT SỰ** áp, lấy từ
                      `ban_ke.he_so_co_gian` sau khi kẹp trần kỹ thuật.

    🔴 **Vì sao hàm này tồn tại (đo 28/09).** Hai đại lượng ấy từng in cạnh nhau
       trong cùng một `outputs` dưới hai cái tên nghe như MỘT:
       `he_so_toc_lon_nhat = 1,15` cạnh `master.he_so_toc_da_ap max = 1,3333`.
       Hai TẬP khác nhau, và vì `1,15 < 1,3333` nên người đọc kết luận **ngược**:
       *"trần đã giữ"*.

    ⚠️ **MẪU SỐ: chỉ các `ma` có trong `he_so_da_ap`.** Đó là các `ma` SỞ HỮU một
       tệp tiếng (`nan_thoi_luong.tep_theo_ma`); `ma` đi theo một khe đã gộp ⛔
       không có lớp riêng nên nó ⛔ không so được. ⇒ `so_doan_tang_toc_ke_hoach`
       ở đây CỐ Ý **khác** `tom_tat()["so_doan_tang_toc"]` (đếm MỌI dòng kế
       hoạch, kể cả dòng đi theo). Hai con số, hai mẫu số, hai cái tên.

    ⭐ Trả thêm `lech` = `[(ma, h_ke, h_ap)]` để người gọi nói to từng chỗ. Hàm
       này ⛔ KHÔNG log và ⛔ không ném: nó chỉ ĐO.
    """
    ke_hoach_cung_tap = {ma: float(he_so_ke_hoach.get(ma, 1.0))
                         for ma in he_so_da_ap}
    ap = {ma: float(h) for ma, h in he_so_da_ap.items()}
    lech = [(ma, ke_hoach_cung_tap[ma], ap[ma]) for ma in sorted(ap)
            if abs(ke_hoach_cung_tap[ma] - ap[ma]) > 1e-6]
    return {
        "he_so_toc_da_ap_lon_nhat": round(max(ap.values(), default=1.0), 4),
        "so_doan_tang_toc_da_ap": sum(1 for h in ap.values() if h > 1.0),
        "he_so_toc_ke_hoach_lon_nhat": round(
            max(ke_hoach_cung_tap.values(), default=1.0), 4),
        "so_doan_tang_toc_ke_hoach": sum(
            1 for h in ke_hoach_cung_tap.values() if h > 1.0),
        "so_doan_he_so_lech_ke_hoach": len(lech),
        # ⭐ TÍCH của hai máy trên CÙNG một `ma` — đại lượng mà B13 §3.4 sợ
        #    (`1,15 × 1,3333 = 1,53`). Hôm nay nó ⛔ KHÔNG được thi hành, nên ghi
        #    nó ra là cách để ngày nào nó bị thi hành thì con số **tự tố giác**,
        #    thay cho một nhánh `raise` nằm chết.
        "he_so_gop_ke_hoach_x_da_ap_lon_nhat": round(
            max((ke_hoach_cung_tap[ma] * ap[ma] for ma in ap), default=1.0), 4),
        "lech": lech,
    }


def _tang_toc_can(dai_ms: int, ngan_sach_ms: int) -> float:
    if dai_ms <= 0 or ngan_sach_ms <= 0:
        return 1.0
    return dai_ms / ngan_sach_ms


def lap_ke_hoach(muc: list[dict], thoi_luong_tieng: dict, *,
                 tong_giay: float, che_do: str = "fit_original",
                 nhom_gop: dict | None = None,
                 he_so_da_ap: dict[str, float] | None = None) -> dict:
    """Dựng kế hoạch đặt từng đoạn. Không chạm tệp nào.

    `muc`             các mục của `content.json` (có `ma`, `bat`, `ket`)
    `thoi_luong_tieng` `{ma: giây}` — độ dài THẬT của tệp tiếng đã sinh
    `tong_giay`       thời lượng video nguồn
    `nhom_gop`        `{ma đi theo: ma đứng đầu}` của các **khe đã gộp**
                      (`nan_thoi_luong`). Rỗng/None = lượt chạy không gộp gì,
                      và khi đó hàm này chạy y hệt bản trước một mili-giây.
    `he_so_da_ap`     `{ma: hệ số `atempo` SẼ ĐƯỢC ÁP}` — lấy từ
                      `ban_ke.he_so_co_gian` sau khi kẹp trần kỹ thuật
                      (`giai_doan_thoi_gian.he_so_da_ap_theo_ma`). `None` =
                      người gọi ⛔ chưa có bản kê ⇒ đường LUI, xem khối
                      *"Hệ số tốc độ"* trong thân hàm.

    ## 🔴 B13-A4 (28/09): hàm này thôi tự tăng tốc để trả nợ

    Bản trước tính `he_so_toc` riêng (`_tang_toc_can`, kẹp `TRAN_TANG_TOC`) rồi
    chừa chỗ theo `dai / he_so_toc` — trong khi **⛔ không một ai thi hành con số
    ấy**: `ket_xuat.dung_lenh` chỉ nạp bản phối. ⇒ 12 đoạn của lượt
    `asvr_47327a869a8f4597960048f09064740` được chừa chỗ hẹp hơn tệp thật.

    ⭐ Nay hàm này **đọc** hệ số sẽ được áp, nên kế hoạch và bản phối nói **cùng
       một con số**: `giai_doan_thoi_gian.doi_chieu_he_so_toc` phải đếm **0 đoạn
       lệch**, và đó là phép chứng minh A4 đã ăn (nó từng đếm 12).

    ⛔ Ba thứ A4 ⛔ KHÔNG được phá, và cả ba vẫn do đúng chỗ cũ gánh:
       1. **T2 / D-ASV-03** — `ket_cuoi_ms` ⛔ không bao giờ vượt `tong_ms`: vòng
          `while` ở đuôi hàm vẫn bỏ đoạn tràn, và `kiem()` vẫn ném.
       2. `TRAN_CHONG_LAN_MS` — `dat_tai` vẫn `max(bat_goc + troi, con_tro - 200)`.
       3. Bậc thang trả nợ (`TRAN_TROI_SO_DOAN` → bỏ đoạn) vẫn nguyên; nay nó
          gánh phần mà máy tăng tốc bịa ra từng che đi.

    ## 🔴 `nhom_gop` đổi ĐÚNG hai điều, và cả hai đều bắt buộc

    Một khe đã gộp là MỘT tệp tiếng đọc liền mạch cho 2–4 `ma`. `ban_ke.json`
    vẫn có một dòng cho **mọi** `ma` (bất biến ở `giai_doan_thoi_gian.py:88-89`
    không bị phá), với `giay` là **phần** của nó trong tệp
    (`nan_thoi_luong.chia_giay`). Vậy:

      1. **Đặt LIỀN NHAU.** `ma` đi theo đặt đúng ở mốc kết thúc của thành viên
         trước (`con_tro`), ⛔ không phải ở mốc gốc `bat` của chính nó. Lý do:
         tiếng của nó **đã phát rồi** — nó nằm ngay sau phần trước trong cùng
         một tệp. Đặt ở mốc gốc là chèn lại đúng khoảng lặng mà phép gộp vừa
         mượn, và phụ đề sẽ hiện **trễ** so với tiếng tới `TRAN_KHE_GIUA_S` mỗi
         thành viên.
      2. **MỘT hệ số cho cả nhóm.** Tệp được `atempo` **một lần**, nên hai `ma`
         cùng tệp mang hai `he_so_toc` khác nhau là hai mốc không thể cùng đúng.

    ⭐ Và phép bỏ đoạn (trần nợ) chỉ quyết ở thành viên ĐỨNG ĐẦU: không cắt được
       một phần của một tệp (đó chính là phép **cắt trả về** đã làm bot Viral
       phải tắt phép gộp — `nan_thoi_luong.gop_khe`). Bỏ đầu ⇒ bỏ cả nhóm.

    ## 🔴 `ban_do` ĐÃ RỜI KHỎI hàm này (b4 hai giai đoạn, 25/09)

    Bản trước nhận một `BanDoThoiGian` để đổi mốc NGUỒN sang mốc BẢN RA, vì cảnh
    bị cắt **biến mất khỏi bản ra**: giây 120 của nguồn có thể là giây 74 của bản
    ra — hoặc không tồn tại — và sai số đó **tích luỹ** theo từng cảnh bị cắt.

    Chủ dự án chốt 25/09 đổi **thứ tự** chứ không đổi phép đổi mốc: cắt cảnh nằm
    SAU render (`ke_cat.py`, giai đoạn 2). Nên ở đây:

        giai đoạn 1  =  MP4 tiếng Việt, TOÀN BỘ độ dài gốc, không cắt gì
        ⇒ trục kế hoạch **LÀ** trục nguồn, cho CẢ HAI preset

    ⭐ Và đó là cái được: phép đổi mốc không được *quản lý tốt hơn*, nó **không
       còn chỗ để sinh ra**. Một tham số biến mất là một lớp lỗi biến mất — chứ
       không phải một lớp lỗi được kiểm nhiều hơn.

    ⛔ Hai preset vì thế đi **y hệt** một đường ở đây, và `test_4801` ghim điều
       đó bằng máy chứ không bằng giao ước: `lap_ke_hoach` không còn một tham số
       nào để mà nhánh theo preset.

    Trả về kế hoạch: mỗi đoạn có `dat_tai_ms`, `he_so_toc`, `cat_bot_ms`, và
    `troi_sau_ms` để đọc được diễn biến của món nợ.
    """
    if not muc:
        raise ThoiGianError(_t('Không có mục nào để lập kế hoạch thời gian.'))
    if che_do not in ("fit_original", "natural"):
        raise ThoiGianError(f"che do thoi gian khong hop le: {che_do!r}")

    # ── Mốc của NGUỒN, và ở giai đoạn 1 đó cũng là mốc của bản ra ─────────
    #
    # 🔑 Không một phép đổi nào ở đây nữa. Giai đoạn 1 giao **toàn bộ độ dài
    #    gốc**, nên trục kế hoạch và trục nguồn là MỘT — xem docstring.
    #
    # ⚠️ `max(bat, ket)` vẫn ở lại: một mục có `ket < bat` là dữ liệu hỏng của
    #    thượng nguồn, và kẹp nó ở đây rẻ hơn để nó lan vào `ngan_sach_doan`.
    bat_ra = [_ms(float(m["bat"])) for m in muc]
    ket_ra = [max(b, _ms(float(m["ket"]))) for b, m in zip(bat_ra, muc, strict=True)]

    tong_ms = _ms(tong_giay)
    ke: list[dict] = []
    troi = 0                    # 🔑 nợ trôi, mang theo suốt bài
    # ══ HAI cỗ máy cắt, HAI bộ đếm (đo 28/09, B15) ════════════════════════
    #
    # 🔴 **`so_doan_bi_cat` từng GỘP hai cỗ máy khác hẳn nhau vào một số**, và
    #    điều đó làm một bản đối soát ⛔ không trả lời được *"khách mất câu vì
    #    NỢ hay vì ĐUÔI?"*:
    #
    #      `so_doan_cat_vi_no`   nợ vượt `TRAN_TROI_SO_DOAN` ⇒ bỏ hẳn tiếng
    #                            đoạn này để mua lại ngân sách của nó.
    #      `so_doan_cat_vi_duoi` vòng `while` ở đuôi hàm `pop()` đoạn tràn quá
    #                            `tong_ms` ⇒ **đây** là thứ cưỡng chế T2 /
    #                            `D-ASV-03`, ⛔ không phải trần nợ.
    #
    # ⭐ Đo được 28/09: nâng `TRAN_TROI_SO_DOAN` lên vô cực (tắt cỗ máy thứ
    #    nhất) mà `so_doan_bi_cat` **vẫn** là 1 ở `k = 1,15` — chính cỗ máy thứ
    #    hai. Một số gộp đã che mất điều đó suốt.
    so_cat_no = 0
    so_cat_duoi = 0
    con_tro = 0                 # mốc kết thúc của đoạn trước, sau khi đặt
    theo_cua = {str(k): str(v) for k, v in (nhom_gop or {}).items() if v}
    he_so_nhom: dict[str, float] = {}   # ma đứng đầu -> hệ số của CẢ tệp
    nhom_bi_cat: set[str] = set()       # ma đứng đầu đã bị bỏ ⇒ bỏ cả nhóm

    for i, m in enumerate(muc):
        ma = m["ma"]
        dai = _ms(thoi_luong_tieng.get(ma, 0.0))
        if dai <= 0:
            raise ThoiGianError(
                _t('Đoạn {ma} chưa có tiếng.').format(ma=ma))
        dung_dau = theo_cua.get(str(ma), "")   # "" = đoạn này tự sở hữu tệp

        bat_goc = bat_ra[i]
        ngan_sach = ngan_sach_doan(bat_ra, i, tong_ms)
        noi_thoai = max(0, ket_ra[i] - bat_goc)
        khoang_lang = max(0, ngan_sach - noi_thoai)

        # ── Ngân sách dùng được: thoại + PHẦN khoảng lặng được mượn ────────
        #    Chừa lại 30 % để bản lồng tiếng vẫn còn nhịp nghỉ.
        dung_duoc = noi_thoai + int(khoang_lang * TY_LE_MUON_KHOANG_LANG)

        # ── Hệ số tốc độ: ĐỌC cái SẼ ĐƯỢC ÁP, ⛔ không tự bịa (B13-A4, 28/09) ─
        #
        # 🔴 **Bản trước tự tăng tốc tới `TRAN_TANG_TOC` để trả nợ, và ⛔ KHÔNG
        #    MỘT AI thi hành con số ấy.** `ket_xuat.dung_lenh` chỉ nạp bản phối
        #    (`-i duong_master`, `-map 1:a:0`); `duong_lop` chỉ bị đếm để đối
        #    chiếu độ dài. Nên `he_so_toc` là một phép chia **chỉ có trong số
        #    học của hàm này**: nó chừa cho đoạn một chỗ hẹp hơn thực tế, và
        #    `am_master.tron_lo` rồi đặt vào đó một tệp DÀI HƠN. Đo trên
        #    `asvr_47327a869a8f4597960048f09064740`: **12 đoạn** như vậy, và
        #    `kiem()` ⛔ không bắt được vì nó kiểm chồng lấn trên `dai_ms` ĐÃ chia.
        #
        # ⭐ **Chủ dự án chốt 28/09: BỎ.** Thứ tự cứu là *"dùng khoảng lặng trước;
        #    cho tiếng dàn trong đoạn; chỉ tăng tốc như phương án cuối"* — và nấc
        #    cuối ấy ĐÃ có chủ: bậc thang nắn (`nan_cho_vua.co_gian_du_khong`,
        #    mẫu số `ngan_sach` từ B13-A2). Giữ thêm một máy tăng tốc thứ hai ở
        #    đây là nén 12 đoạn nữa, tức đi NGƯỢC lời chốt.
        #
        # 🔑 **Và vì thế nợ ⛔ không phình ra.** `ngan_sach_nan_s(khe, ngan_sach)`
        #    = `khe + 0,7 × lặng` là **CÙNG một con số** với `dung_duoc` ngay
        #    trên (`noi_thoai + 0,7 × khoang_lang`), nên một đoạn tràn `dung_duoc`
        #    đã bị bậc thang nắn nén về ĐÚNG `dung_duoc` rồi ⇒ `troi = 0`. Máy
        #    tăng tốc ở đây vốn giải **cùng một bài** bằng **sai mẫu số**.
        #
        # ⚠️ `he_so_da_ap is None` = *"người gọi ⛔ chưa có bản kê"* ⇒ đường LUI:
        #    giữ NGUYÊN luật cũ (tự tăng tốc trả nợ, kẹp `TRAN_TANG_TOC`). Đường
        #    sản phẩm (`giai_doan_thoi_gian.chay`) LUÔN truyền, nên nấc tự-tăng-
        #    tốc ⛔ không còn nằm trên đường của khách; nó chỉ còn là hợp đồng cho
        #    người gọi chưa biết hệ số nào sẽ được áp (`test_410` đi đường này).
        #
        # ⭐ Đoạn đi theo mượn hệ số của thành viên đứng đầu: MỘT tệp, `atempo`
        #    MỘT lần (xem docstring, điểm 2).
        if dung_dau:
            he_so = he_so_nhom.get(dung_dau, 1.0)
        else:
            if he_so_da_ap is None:
                he_so = 1.0
                if troi > 0 and dai > 0:
                    can = _tang_toc_can(dai + troi, dai)
                    he_so = min(max(1.0, can), TRAN_TANG_TOC)
            else:
                # ⛔ Kẹp TRÊN về trần KỸ THUẬT, ⛔ không về `TRAN_TANG_TOC`: chủ
                #    dự án chốt 26/09 rằng trần thiết kế là CẢNH BÁO. Kẹp DƯỚI về
                #    1,0 vì làm chậm lại ⛔ không nằm trong mô hình (ADR-003 D4).
                he_so = min(TRAN_KY_THUAT_ATEMPO,
                            max(1.0, float(he_so_da_ap.get(str(ma), 1.0))))
            he_so_nhom[str(ma)] = he_so
        dai_sau = int(dai / he_so) if he_so > 1.0 else dai

        # ── Đặt: sau mốc trước, không sớm hơn vị trí gốc quá nhiều ────────
        #
        # ⭐ Đoạn đi theo đặt ĐÚNG ở `con_tro`: tiếng của nó nằm ngay sau phần
        #    trước TRONG CÙNG một tệp, nên mốc gốc của nó không còn nghĩa.
        dat_tai = con_tro if dung_dau else max(bat_goc + troi,
                                               con_tro - TRAN_CHONG_LAN_MS)

        # ── Trần cứng cho nợ (ADR-003 D5) ─────────────────────────────────
        tran = sum(ngan_sach_doan(bat_ra, j, tong_ms)
                   for j in range(i, min(len(muc), i + TRAN_TROI_SO_DOAN)))
        cat = 0
        if dung_dau and dung_dau in nhom_bi_cat:
            # ⭐ Thành viên đứng đầu đã bị bỏ ⇒ cả tệp bị bỏ. ⛔ Không cắt được
            #    một phần của một tệp — xem docstring.
            cat = dai_sau
            dai_sau = 0
            so_cat_no += 1
            dat_tai = max(bat_goc, con_tro)
            ket_thuc = dat_tai
        elif not dung_dau and troi > tran:
            # Nợ đã vượt ngân sách của ba đoạn kế tiếp. Dừng tích luỹ: **bỏ hẳn
            # tiếng của đoạn này** — mất một câu, mua lại ngân sách của nó.
            #
            # 🔴 Bản đầu ở đây đặt lại `dat_tai = bat_goc` và `troi = 0`, và nó
            #    SAI theo hai cách cùng lúc:
            #
            #      * lùi thời gian về sau mốc mà tiếng đoạn trước vẫn đang chạy
            #        — phép kiểm chồng lấn bắt được ngay;
            #      * xoá sạch nợ, tức giả vờ rằng bỏ **một** đoạn đủ trả **mọi**
            #        khoản nợ. Không đúng: bỏ một đoạn chỉ mua lại đúng ngân
            #        sách của đoạn đó.
            #
            # ⇒ Mô hình đúng: không lùi thời gian, và trừ nợ đúng phần mua được.
            #    Nợ lớn thì cần nhiều lần cắt — điều đó tự giới hạn và trung thực.
            #
            # ⛔ QC phải ghi lại mỗi lần cắt (T12). Mất lời thoại là một khiếm
            #    khuyết chất lượng, không phải một chi tiết kỹ thuật.
            cat = dai_sau
            dai_sau = 0
            so_cat_no += 1
            dat_tai = max(bat_goc, con_tro)
            troi = max(0, troi - ngan_sach)
            ket_thuc = dat_tai
            # ⭐ Đoạn này có thể là thành viên ĐỨNG ĐẦU của một khe đã gộp: bỏ
            #    nó là bỏ CẢ tệp, nên các `ma` đi theo phải bị bỏ cùng.
            nhom_bi_cat.add(str(ma))
        else:
            ket_thuc = dat_tai + dai_sau

            # ── Ghi/trả nợ ────────────────────────────────────────────────
            het_ngan_sach = bat_goc + dung_duoc
            if ket_thuc > het_ngan_sach:
                troi = ket_thuc - het_ngan_sach
            else:
                # Còn dư khoảng lặng: TRẢ NỢ trước, phần còn lại mới thành im lặng.
                du = het_ngan_sach - ket_thuc
                troi = max(0, troi - du)

        ke.append({
            "ma": ma,
            "dat_tai_ms": dat_tai,
            "dai_ms": dai_sau,
            "he_so_toc": round(he_so, 4),
            "cat_bot_ms": cat,
            "troi_sau_ms": troi,
            "ngan_sach_ms": ngan_sach,
            "khoang_lang_ms": khoang_lang,
        })
        con_tro = ket_thuc

    # ── Đuôi: bản lồng tiếng không bao giờ dài hơn video ──────────────────
    #
    # 🔴 Áp dụng cho CẢ HAI chế độ, không riêng `natural`. Bản đầu chỉ cắt khi
    #    `che_do == "natural"` — và đó là đọc nhầm hợp đồng: `MVP_CONTRACT.md` §6
    #    nhắc `natural` vì đó là chế độ dễ tràn nhất, nhưng ràng buộc thật đến từ
    #    **D-ASV-03**: luồng hình được **sao chép**, nên tổng thời lượng là một
    #    con số cố định. `fit_original` tràn ít hơn, không có nghĩa là được phép.
    #
    #    Lỗ này lộ ra ở `test_ban_long_tieng_KHONG_BAO_GIO_dai_hon_video` với
    #    `fit_original` — đúng chỗ bản đầu không cắt.
    ket_cuoi = ke[-1]["dat_tai_ms"] + ke[-1]["dai_ms"]
    while ke and ke[-1]["dat_tai_ms"] + ke[-1]["dai_ms"] > tong_ms:
        bo = ke.pop()
        if bo["dai_ms"] > 0:
            so_cat_duoi += 1
    if not ke:
        raise ThoiGianError(
            _t('Bản lồng tiếng dài hơn video và không còn đoạn nào vừa.'))
    ket_cuoi = ke[-1]["dat_tai_ms"] + ke[-1]["dai_ms"]

    ke_hoach = {
        "schema": SCHEMA_KE_HOACH,
        "che_do": che_do,
        "tong_ms": tong_ms,
        # ⛔ **Trường `ban_do` ĐÃ BỊ BỎ, và bỏ chứ không để rỗng.** Một khoá
        #    `"ban_do": {}` luôn có mặt sẽ trông như một bản đồ đã được tính và
        #    ra kết quả trống — tức đúng cái bẫy "hai trạng thái một giá trị".
        #    Giai đoạn 2 (`ke_cat.KeCat.ban_do`) là chủ sở hữu duy nhất của phép
        #    đổi mốc, và nó đổi mốc trên MỘT tệp đã xong.
        "thoi_luong_nguon_ms": _ms(tong_giay),
        "ket_cuoi_ms": ket_cuoi,
        "so_doan": len(ke),
        # ⚠️ `so_doan_bi_cat` GIỮ NGUYÊN nghĩa "tổng số đoạn khách mất" — bốn
        #    chỗ hạ nguồn đọc nó (`ban_dung`, `qc`, `tom_tat`, `test_411`) và
        #    đổi nghĩa một khoá đang có là cách chắc chắn nhất để một trong bốn
        #    chỗ ấy lệch. Hai khoá MỚI **thêm vào** để nói *vì sao*.
        "so_doan_bi_cat": so_cat_no + so_cat_duoi,
        "so_doan_cat_vi_no": so_cat_no,
        "so_doan_cat_vi_duoi": so_cat_duoi,
        "troi_toi_da_ms": max((d["troi_sau_ms"] for d in ke), default=0),
        "doan": ke,
    }
    kiem(ke_hoach)
    return ke_hoach


def kiem(ke_hoach: dict) -> None:
    """Kiểm kế hoạch. Ném `ThoiGianError` kèm lý do cụ thể."""
    if int(ke_hoach.get("schema") or 0) != SCHEMA_KE_HOACH:
        raise ThoiGianError(_t('Kế hoạch thời gian thuộc phiên bản khác.'))

    doan = ke_hoach.get("doan") or []
    if not doan:
        raise ThoiGianError(_t('Kế hoạch thời gian không có đoạn nào.'))

    tong = int(ke_hoach.get("tong_ms") or 0)
    truoc_ket = None
    for d in doan:
        dat, dai = int(d["dat_tai_ms"]), int(d["dai_ms"])
        if dat < 0 or dai < 0:
            raise ThoiGianError(_t('Kế hoạch có mốc thời gian âm.'))
        if dai == 0:
            # Đoạn đã bị cắt: nó không chiếm thời gian nào, nên không thể chồng
            # lấn với gì cả. Đưa nó vào phép kiểm chồng lấn là bắt một xung đột
            # không tồn tại.
            continue
        if truoc_ket is not None and dat + TRAN_CHONG_LAN_MS < truoc_ket:
            # ⛔ Chồng lấn quá 200 ms nghe thành HAI NGƯỜI cùng nói.
            raise ThoiGianError(
                _t('Kế hoạch có hai đoạn chồng lấn quá {ms} ms.').format(
                    ms=TRAN_CHONG_LAN_MS))
        # 🔴 **Trần KỸ THUẬT, ⛔ không phải trần THIẾT KẾ (B13-A4, 28/09).**
        #
        #    Trước A4 chỗ này ném ở `TRAN_TANG_TOC` (1,15), và điều đó ĐÚNG khi
        #    `he_so_toc` là con số hàm này tự tính (nó tự kẹp về 1,15). Từ A4
        #    `he_so_toc` là hệ số **SẼ ĐƯỢC ÁP**, và chủ dự án đã chốt 26/09 rằng
        #    trần thiết kế là **CẢNH BÁO** chứ ⛔ không phải một cổng — cổng duy
        #    nhất còn cưỡng chế là trần kỹ thuật của `atempo`
        #    (`giai_doan_thoi_gian.py:~360` ghi lại quyết định ấy).
        #
        # ⛔ Giữ `TRAN_TANG_TOC` ở đây sẽ làm MỌI lượt chạy có một đoạn `CO_GIAN`
        #    chết ngay ở `kiem()` — tức dựng lại đúng cái cổng đã bị bỏ, ở một
        #    tệp khác, nơi ⛔ không ai đi tìm nó.
        # ⚠️ **Câu cho khách giữ NGUYÊN từng chữ, chỉ CON SỐ đổi — hai lý do cơ
        #    học, ⛔ không phải một sự lười:**
        #      · `test_410::test_KHONG_cham_tep_am_thanh_nao` quét bằng AST và
        #        **chuỗi thường VẪN tính** (chỉ docstring/chú thích được miễn), nên
        #        một `_t('… atempo …')` ở đây làm nó đỏ — và cái chốt ấy ĐÚNG: tệp
        #        này ra một KẾ HOẠCH, nó ⛔ không được biết tên công cụ thi hành;
        #      · sửa một chữ trong `msgid` là tạo một mục MỚI trong catalog, và
        #        `pre-commit` (`ban-dich-thieu`) đỏ cho tới khi có bản EN —
        #        `locale/` ⛔ không thuộc làn này.
        # ⭐ Câu vẫn ĐÚNG: nó báo *"kế hoạch vượt trần"* và IN ra trần ấy; từ A4
        #    trần in ra là trần KỸ THUẬT (2,0), ⛔ không còn trần thiết kế (1,15).
        if float(d["he_so_toc"]) > TRAN_KY_THUAT_ATEMPO + 1e-6:
            raise ThoiGianError(
                _t('Kế hoạch vượt trần tăng tốc {tran}.').format(
                    tran=TRAN_KY_THUAT_ATEMPO))
        truoc_ket = dat + dai

    # T2 / D-ASV-03: bản lồng tiếng KHÔNG BAO GIỜ dài hơn video nguồn.
    if tong and int(ke_hoach.get("ket_cuoi_ms") or 0) > tong:
        raise ThoiGianError(
            _t('Bản lồng tiếng dài hơn video nguồn.'))


def van_tay_ke_hoach(*, checksum_van_ban: str, ban_ke_tieng: str,
                     che_do: str) -> str:
    """Vân tay của kế hoạch.

    Bốn thành phần: bản dịch, độ dài tiếng thật đã sinh, chế độ, và phiên bản
    thuật toán. Đổi bất kỳ hằng số nào ở đầu tệp là đổi `PHIEN_BAN_THOI_GIAN`,
    và cache cũ vô hiệu (O13).
    """
    goi = json.dumps({
        "van_ban": checksum_van_ban,
        "tieng": ban_ke_tieng,
        "che_do": che_do,
        "muon": TY_LE_MUON_KHOANG_LANG,
        "tang_toc": TRAN_TANG_TOC,
        "tran_troi": TRAN_TROI_SO_DOAN,
        "chong_lan": TRAN_CHONG_LAN_MS,
        "phien_ban": PHIEN_BAN_THOI_GIAN,
        "schema": SCHEMA_KE_HOACH,
    }, sort_keys=True)
    return hashlib.sha256(goi.encode("utf-8")).hexdigest()


def tom_tat(ke_hoach: dict) -> dict:
    """Con số cho tiến độ và QC. Không có lời thoại (I16).

    ## 🔴 `so_doan_tang_toc` / `he_so_toc_lon_nhat`: SAI → ĐÚNG, ⛔ không → CHẾT

    **Cái bẫy đã có thật** (lượt `asvr_47327a869a8f4597960048f09064740`): ở đây
    `1,15` / `12 đoạn`, còn `master.he_so_toc_da_ap` `max = 1,3333` / `4 đoạn` —
    HAI TẬP khác nhau trong CÙNG một `outputs`, và vì `1,15 < 1,3333` nên người
    đọc kết luận **ngược**: *"trần đã giữ"*.

    ⭐ **A4 (28/09) xoá cái bẫy ở GỐC, ⛔ không bằng cách đổi tên.** Từ A4
       `lap_ke_hoach` ⛔ không tự bịa một `he_so_toc` nữa — nó **MIRROR** hệ số sẽ
       được áp (`ban_ke.he_so_co_gian` đã kẹp trần kỹ thuật). ⇒ Hai khoá này nay
       đo **ĐÚNG cái mà tên chúng hứa**, và chúng báo cùng một đại lượng với
       `master.he_so_toc_da_ap_lon_nhat` / `so_doan_tang_toc_da_ap`.

    ⚠️ **Một vế VẪN khác, và nó là mẫu số:** hàm này đếm theo **`ma`** — kể cả
       dòng ĐI THEO của một khe đã gộp (chúng mirror hệ số của trưởng nhóm) —
       còn `master.so_doan_tang_toc_da_ap` đếm theo **TỆP**. ⇒ Trên một lượt CÓ
       gộp, `so_doan_tang_toc` **≥** số lồng. `he_so_toc_lon_nhat` thì **bằng
       hẳn**: mirror ⇒ `max` trên tập cha bằng `max` trên tập con.
       `test_4921` chốt cả hai mệnh đề.

    ⛔ **Vì sao ⛔ KHÔNG đổi tên và ⛔ KHÔNG xoá hai khoá này:**
       - ⛔ không CHẾT: sau A4 chúng ⛔ không phải `0`/`1` vĩnh viễn — lượt đã đo
         sẽ báo `2 đoạn` / `1,1711`, tức đúng những đoạn khách nghe bị nén;
       - ⛔ không SAI TÊN nữa: `he_so_toc` nay LÀ hệ số được áp;
       - và đổi tên buộc phải sửa `asv_doi_soat.KHOA_BO_QUA_CO_Y["timing_align"]`
         (`test_408` chốt hai chiều: khoá mới chưa khai ⇒ đỏ; khoá đã khai mà ⛔
         không ai ghi ⇒ cũng đỏ), tức một tệp `tools/` mà làn này ⛔ không sở hữu.

    ⚠️ **Cái giá nếu quyết định này sai:** một người muốn *"bao nhiêu TỆP bị tăng
       tốc"* mà đọc khoá phẳng sẽ đếm **thừa** trên một lượt có gộp. Đổi lại,
       khoá lồng nằm ngay cạnh trong cùng `outputs`, và ⛔ không một sổ đăng ký
       dùng chung nào bị chạm.
    """
    doan = ke_hoach.get("doan") or []
    nhanh = [d for d in doan if float(d["he_so_toc"]) > 1.0]
    return {
        "so_doan": len(doan),
        "so_doan_bi_cat": int(ke_hoach.get("so_doan_bi_cat") or 0),
        # ⛔ **`so_doan_cat_vi_{no,duoi}` CỐ Ý ⛔ KHÔNG ở đây.** Chúng nằm trong
        #    `ke_hoach` (artifact) và được `giai_doan_thoi_gian` xuất xuống
        #    `outputs["master"]`. Lý do cơ học, ⛔ không phải thẩm mỹ: mỗi khoá
        #    PHẲNG mới của hàm này phải được khai ở
        #    `asv_doi_soat.KHOA_{CAN,BO_QUA_CO_Y}` — `test_408` chốt hai chiều —
        #    và `tools/` thuộc L3. `master` là MỘT khoá trong `KHOA_CAN` nên
        #    khoá con của nó thêm được tự do. Cùng đường đã dùng cho B13-B4.
        # ⚠️ Dem theo `ma` (ke ca dong DI THEO), ⛔ khong theo TEP — xem docstring.
        "so_doan_tang_toc": len(nhanh),
        "he_so_toc_lon_nhat": round(
            max((float(d["he_so_toc"]) for d in doan), default=1.0), 3),
        "troi_toi_da_ms": int(ke_hoach.get("troi_toi_da_ms") or 0),
        "ket_cuoi_ms": int(ke_hoach.get("ket_cuoi_ms") or 0),
        "che_do": ke_hoach.get("che_do", ""),
    }
