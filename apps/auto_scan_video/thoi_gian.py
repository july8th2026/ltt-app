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
#:    ⇒ Nâng số này chỉ để "cho chắc" là ném đi mọi cache đúng **và** làm đỏ
#:    `test_448` (nghiệm thu E2E chốt phiên bản engine của mỗi giai đoạn) — tức
#:    đòi một lượt ASV thật cho một thay đổi không đổi một byte đầu ra nào.
PHIEN_BAN_THOI_GIAN = 1

SCHEMA_KE_HOACH = 1


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


def _tang_toc_can(dai_ms: int, ngan_sach_ms: int) -> float:
    if dai_ms <= 0 or ngan_sach_ms <= 0:
        return 1.0
    return dai_ms / ngan_sach_ms


def lap_ke_hoach(muc: list[dict], thoi_luong_tieng: dict, *,
                 tong_giay: float, che_do: str = "fit_original",
                 ban_do=None, nhom_gop: dict | None = None) -> dict:
    """Dựng kế hoạch đặt từng đoạn. Không chạm tệp nào.

    `muc`             các mục của `content.json` (có `ma`, `bat`, `ket`)
    `thoi_luong_tieng` `{ma: giây}` — độ dài THẬT của tệp tiếng đã sinh
    `tong_giay`       thời lượng video nguồn
    `ban_do`          `BanDoThoiGian` — đổi mốc NGUỒN sang mốc BẢN RA
    `nhom_gop`        `{ma đi theo: ma đứng đầu}` của các **khe đã gộp**
                      (`nan_thoi_luong`). Rỗng/None = lượt chạy không gộp gì,
                      và khi đó hàm này chạy y hệt bản trước một mili-giây.

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

    🔴 **`ban_do` là thứ pha 16 thêm vào, và thiếu nó thì preset cắt sai âm
       thầm.** Trước đó hàm này lập kế hoạch trên trục thời gian của **nguồn**:
       đoạn bắt đầu ở giây 120 thì đặt quanh giây 120. Đúng cho preset giữ hình,
       nơi luồng hình được sao chép nguyên vẹn.

       Với `smart_localize` thì cảnh bị cắt **biến mất khỏi bản ra**, nên giây
       120 của nguồn có thể là giây 74 của bản ra — hoặc không tồn tại. Sai số
       đó **tích luỹ** theo từng cảnh bị cắt.

    ⭐ `ban_do=None` giữ nguyên hành vi cũ (bản đồ đồng nhất), nên preset giữ
       hình không đổi một mili giây nào.

    Trả về kế hoạch: mỗi đoạn có `dat_tai_ms`, `he_so_toc`, `cat_bot_ms`, và
    `troi_sau_ms` để đọc được diễn biến của món nợ.
    """
    if not muc:
        raise ThoiGianError(_t('Không có mục nào để lập kế hoạch thời gian.'))
    if che_do not in ("fit_original", "natural"):
        raise ThoiGianError(f"che do thoi gian khong hop le: {che_do!r}")

    # ⭐ Không có bản đồ = bản đồ đồng nhất. Viết ra một lần thay vì rải
    #    `if ban_do` khắp thân hàm: một nhánh điều kiện lặp lại là một nhánh sẽ
    #    bị quên ở một chỗ.
    if ban_do is None:
        from .ban_do_thoi_gian import BanDoThoiGian

        ban_do = BanDoThoiGian.giu_nguyen(tong_giay)

    # ── Đổi mốc sang trục BẢN RA, MỘT lần, ở MỘT chỗ ──────────────────────
    #
    # ⛔ `ra()` chứ không `ra_gan_nhat()` cho mốc **bắt đầu**: một câu thoại
    #    thuộc cảnh đã cắt phải **biến mất**, không được trôi sang cảnh khác. Ép
    #    nó về mốc gần nhất là đổi một mất mát NHÌN THẤY được thành một lỗi KHÓ
    #    TÌM — nghe thấy một câu trả lời cho một câu hỏi không còn.
    bat_ra: list[int] = []
    ket_ra: list[int] = []
    for m in muc:
        rb = ban_do.ra(float(m["bat"]))
        if rb is None:
            raise ThoiGianError(
                _t('Đoạn {ma} thuộc phần đã cắt nhưng vẫn có tiếng.')
                .format(ma=m.get("ma")))
        rk = ban_do.ra(float(m["ket"]))
        if rk is None:
            # Đoạn bắt đầu trong phần giữ và kết thúc trong phần cắt: khe của nó
            # kết thúc ở chỗ nối. Ở đây `ra_gan_nhat` là đúng — ta đang cắt ngắn
            # một khe, không phải di dời một câu.
            rk = ban_do.ra_gan_nhat(float(m["ket"]))
        bat_ra.append(_ms(rb))
        ket_ra.append(_ms(max(rb, rk)))

    # Tổng thời lượng của **BẢN RA**, không phải của nguồn.
    tong_ms = _ms(ban_do.thoi_luong_ra)
    ke: list[dict] = []
    troi = 0                    # 🔑 nợ trôi, mang theo suốt bài
    so_cat = 0
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

        # ── Tăng tốc CHỈ để trả nợ (ADR-003 D4) ───────────────────────────
        #
        # ⭐ Đoạn đi theo mượn hệ số của thành viên đứng đầu: MỘT tệp, `atempo`
        #    MỘT lần (xem docstring, điểm 2).
        if dung_dau:
            he_so = he_so_nhom.get(dung_dau, 1.0)
        else:
            he_so = 1.0
            if troi > 0 and dai > 0:
                can = _tang_toc_can(dai + troi, dai)
                he_so = min(max(1.0, can), TRAN_TANG_TOC)
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
            so_cat += 1
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
            so_cat += 1
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
            so_cat += 1
    if not ke:
        raise ThoiGianError(
            _t('Bản lồng tiếng dài hơn video và không còn đoạn nào vừa.'))
    ket_cuoi = ke[-1]["dat_tai_ms"] + ke[-1]["dai_ms"]

    ke_hoach = {
        "schema": SCHEMA_KE_HOACH,
        "che_do": che_do,
        "tong_ms": tong_ms,
        # 🔑 Bản đồ đi **cùng** kế hoạch, không nằm rời: một kế hoạch đặt đoạn ở
        #    giây 74 vô nghĩa nếu không biết giây 74 của bản ra ứng với đâu
        #    trong nguồn. Hai nửa tách rời là hai nửa sẽ lệch phiên bản.
        "ban_do": ban_do.sang_dict(),
        "thoi_luong_nguon_ms": _ms(tong_giay),
        "ket_cuoi_ms": ket_cuoi,
        "so_doan": len(ke),
        "so_doan_bi_cat": so_cat,
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
        if float(d["he_so_toc"]) > TRAN_TANG_TOC + 1e-6:
            raise ThoiGianError(
                _t('Kế hoạch vượt trần tăng tốc {tran}.').format(
                    tran=TRAN_TANG_TOC))
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
    """Con số cho tiến độ và QC. Không có lời thoại (I16)."""
    doan = ke_hoach.get("doan") or []
    nhanh = [d for d in doan if float(d["he_so_toc"]) > 1.0]
    return {
        "so_doan": len(doan),
        "so_doan_bi_cat": int(ke_hoach.get("so_doan_bi_cat") or 0),
        "so_doan_tang_toc": len(nhanh),
        "he_so_toc_lon_nhat": round(
            max((float(d["he_so_toc"]) for d in doan), default=1.0), 3),
        "troi_toi_da_ms": int(ke_hoach.get("troi_toi_da_ms") or 0),
        "ket_cuoi_ms": int(ke_hoach.get("ket_cuoi_ms") or 0),
        "che_do": ke_hoach.get("che_do", ""),
    }
