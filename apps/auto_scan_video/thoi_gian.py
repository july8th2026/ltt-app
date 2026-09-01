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
PHIEN_BAN_THOI_GIAN = 1

SCHEMA_KE_HOACH = 1


class ThoiGianError(ValueError):
    """Kế hoạch thời gian không dựng được."""


def _ms(giay: float) -> int:
    return int(round(float(giay) * 1000))


def ngan_sach_doan(muc: list[dict], i: int, tong_ms: int) -> int:
    """Ngân sách của đoạn `i`: **tới lúc đoạn sau bắt đầu**.

    Đoạn cuối lấy tới hết nguồn — phần đuôi sau câu cuối cũng là khoảng lặng dùng
    được, và bỏ nó đi là tự làm chặt chính chỗ dễ thở nhất.
    """
    bat = _ms(muc[i]["bat"])
    if i + 1 < len(muc):
        return max(0, _ms(muc[i + 1]["bat"]) - bat)
    return max(0, tong_ms - bat)


def _tang_toc_can(dai_ms: int, ngan_sach_ms: int) -> float:
    if dai_ms <= 0 or ngan_sach_ms <= 0:
        return 1.0
    return dai_ms / ngan_sach_ms


def lap_ke_hoach(muc: list[dict], thoi_luong_tieng: dict, *,
                 tong_giay: float, che_do: str = "fit_original") -> dict:
    """Dựng kế hoạch đặt từng đoạn. Không chạm tệp nào.

    `muc`             các mục của `content.json` (có `ma`, `bat`, `ket`)
    `thoi_luong_tieng` `{ma: giây}` — độ dài THẬT của tệp tiếng đã sinh
    `tong_giay`       thời lượng video nguồn

    Trả về kế hoạch: mỗi đoạn có `dat_tai_ms`, `he_so_toc`, `cat_bot_ms`, và
    `troi_sau_ms` để đọc được diễn biến của món nợ.
    """
    if not muc:
        raise ThoiGianError(_t('Không có mục nào để lập kế hoạch thời gian.'))
    if che_do not in ("fit_original", "natural"):
        raise ThoiGianError(f"che do thoi gian khong hop le: {che_do!r}")

    tong_ms = _ms(tong_giay)
    ke: list[dict] = []
    troi = 0                    # 🔑 nợ trôi, mang theo suốt bài
    so_cat = 0
    con_tro = 0                 # mốc kết thúc của đoạn trước, sau khi đặt

    for i, m in enumerate(muc):
        ma = m["ma"]
        dai = _ms(thoi_luong_tieng.get(ma, 0.0))
        if dai <= 0:
            raise ThoiGianError(
                _t('Đoạn {ma} chưa có tiếng.').format(ma=ma))

        bat_goc = _ms(m["bat"])
        ngan_sach = ngan_sach_doan(muc, i, tong_ms)
        noi_thoai = max(0, _ms(m["ket"]) - bat_goc)
        khoang_lang = max(0, ngan_sach - noi_thoai)

        # ── Ngân sách dùng được: thoại + PHẦN khoảng lặng được mượn ────────
        #    Chừa lại 30 % để bản lồng tiếng vẫn còn nhịp nghỉ.
        dung_duoc = noi_thoai + int(khoang_lang * TY_LE_MUON_KHOANG_LANG)

        # ── Tăng tốc CHỈ để trả nợ (ADR-003 D4) ───────────────────────────
        he_so = 1.0
        if troi > 0 and dai > 0:
            can = _tang_toc_can(dai + troi, dai)
            he_so = min(max(1.0, can), TRAN_TANG_TOC)
        dai_sau = int(dai / he_so) if he_so > 1.0 else dai

        # ── Đặt: sau mốc trước, không sớm hơn vị trí gốc quá nhiều ────────
        dat_tai = max(bat_goc + troi, con_tro - TRAN_CHONG_LAN_MS)

        # ── Trần cứng cho nợ (ADR-003 D5) ─────────────────────────────────
        tran = sum(ngan_sach_doan(muc, j, tong_ms)
                   for j in range(i, min(len(muc), i + TRAN_TROI_SO_DOAN)))
        cat = 0
        if troi > tran:
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
