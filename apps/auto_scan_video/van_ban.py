"""Hop dong VAN BAN DA XU LY (ProcessedText) — ban dich giu nguyen lineage.

## Hai tai lieu, khong phai mot tai lieu bi sua

⛔ Prompt 11 cam sua `TranscriptDocument` tai cho, va ly do khong phai su gon
   gang. Ban ghi la **bang chung** ve thu may nghe duoc; ban dich la mot **dien
   giai** cua no. Ghi de dien giai len bang chung thi:

     * khong con doi chieu duoc ban dich voi loi goc khi khach khieu nai;
     * mot lan dich lai bat buoc phai chep loi lai, vi ban goc da mat;
     * lineage dut — `parent_keys` tro toi mot tep da khac voi luc no duoc dung.

⇒ `transcript.json` bat bien. `content.json` la mot artifact MOI tro ve no.

## Ma doan la kheo noi giua hai tai lieu

Moi muc trong `content.json` mang **dung** `ma` cua doan trong ban ghi. Khong
danh so lai, khong sap xep lai, khong gop. Bon giai doan ha nguon (VOICE,
TIMING, COMPOSE, QC) deu bam vao ma do; mot lan danh so lai o day se lam ca bon
lech mot cach im lang.

`kiem()` chot dieu do bang cach doi chieu **tap ma** cua hai tai lieu, chu khong
chi dem so luong — hai tap cung kich thuoc van co the khac nhau.
"""
from __future__ import annotations

import hashlib
import json

from platform_core.i18n import _ as _t

#: Phien ban HINH DANG cua tai lieu. Vao van tay.
SCHEMA_VAN_BAN = 1

#: Phien ban cua LOI NHAC (prompt). Doi loi nhac = doi ban dich, ke ca khi moi
#: thu khac giu nguyen — nen no phai vao van tay (Prompt 11 muc 7).
#:
#: 2 (24/09): them quy tac 5 — TEN RIENG phien am HAN-VIET. Ly do co BANG CHUNG,
#: ⛔ khong phai phong doan: ban nen doc tay 30 cau thay `光子` ra "Photon"
#: trong khi loi nhac khong he co quy tac nao ve ten rieng (`B2_DICH.md` §4.1).
#:
#: 🔴 3 (24/09, cung ngay): **vi du trong loi nhac viet KHONG DAU, va model chep
#: dung cai do.** Ban v2 sua duoc `光子` -> "Quang Tu" nhung lam `李宗盛` TUT tu
#: "Lý Tông Thành" xuong "Lý Tông Thanh" — mat dau, khop y het bon vi du ASCII
#: ta dua vao. ⇒ v3 viet vi du CO DAU day du va cam bo dau tuong minh.
#: ⭐ Bai hoc: **mot vi du trong loi nhac la mot MENH LENH ngam** — model bat
#:    chuoc hinh thuc cua vi du, khong chi noi dung cua luat. (Cung ho voi ghi
#:    chu o `dich_thuat.MODEL_CHINH`: *mot vi du trong docstring la ma ma nguoi
#:    ta chep*.)
#: ⚠️ 4 (24/09): quy tắc 5 tách làm **BA nhánh** — người/địa danh phiên Hán-Việt ·
#: người thật có lối viết quen dùng lối quen · **tổ chức/thương hiệu GIỮ NGUYÊN,
#: không phiên**.
#:
#: ⛔ **Đây là luật TẠM do điều phối THU HẸP, chưa phải chủ dự án chốt ba nhánh.**
#: Chủ dự án ra luật bằng ví dụ `张伟 → Trương Vĩ` — một **tên người**; đem nó áp
#: lên một **thương hiệu** là **ta** nới rộng. Thu về là **trả lại** lời họ nói.
#: Bằng chứng: `光子` trong phim v3 là **xưởng game** (`B2_DICH.md` §4g).
#: 🔴 5 (24/09): **dựng lại trên đúng TRỤC**, ⛔ không vá thêm một chữ.
#:
#: v4 cắt theo **loại thực thể** (người · địa danh · tổ chức) ⇒ `首尔` rơi vào
#: nhánh *"địa danh ⇒ phiên Hán-Việt"* và ra **"Sê-ôl"**, trong khi `李宗盛` được
#: sửa. Đó là lần **thứ ba** trong một ngày *"sửa một, hỏng một"*.
#:
#: ⭐ Trục thật ⛔ không phải *loại thực thể* mà là **"đã có lối viết quen hay
#:    chưa"** — *lối quen* là thuộc tính của **CÁI TÊN**, không của **người**.
#:    `首尔` (nơi chốn) và `腾讯` (tổ chức) đều có lối quen; `张伟` thì không.
#: ⇒ v5 hỏi **lối quen TRƯỚC**, loại thực thể **tụt xuống bước sau**.
#:
#: ⛔ Vẫn là luật TẠM do điều phối thu hẹp: nhánh 5.2 giữ **nguyên văn** câu chủ
#:    dự án ra (`张伟 → Trương Vĩ`), nên đây là **thu hẹp**, ⛔ không phải quyết
#:    thay họ. Đo trên tập 12 ca nguồn-tra-được: `tools/bench_b2_ten_rieng.py`.
PHIEN_BAN_LOI_NHAC = 5


class VanBanError(ValueError):
    """Van ban da xu ly khong dat hop dong."""


def _sach(s) -> str:
    return " ".join(str(s or "").split())


def dung(ban_ghi_goc: dict, ban_dich: dict, *, provider: str, model: str) -> dict:
    """Dung tai lieu tu ban ghi + bang `{ma: cau_dich}`. Nem neu khong khop.

    `ban_dich` la ket qua da gop tu cac lo. Ham nay khong goi model — no chi
    rap, va vi the no kiem duoc bang mot phep kiem khong can mang.
    """
    doan_goc = list(ban_ghi_goc.get("doan") or [])
    if not doan_goc:
        raise VanBanError(_t('Bản ghi nguồn không có đoạn nào.'))

    muc = []
    thieu = []
    for d in doan_goc:
        ma = d["ma"]
        dich = _sach(ban_dich.get(ma))
        if not dich:
            thieu.append(ma)
            continue
        muc.append({
            "ma": ma,
            "bat": float(d["bat"]),
            "ket": float(d["ket"]),
            # ⭐ Giu CA HAI: goc de doi chieu khi khach khieu nai, dich de doc.
            #    Bo ban goc di la bo kha nang tra loi cau hoi "no dich tu cai gi".
            "goc": _sach(d.get("chu")),
            "chu": dich,
        })

    if thieu:
        # ⛔ Thieu mot doan la mot PHAN HOI KHONG DAY DU, khong phai mot doan
        #    khong can dich. Chap nhan no nghia la ban long tieng se im lang o
        #    dung nhung cho do — va khong ai biet vi sao.
        raise VanBanError(
            _t('Thiếu bản dịch cho {n} đoạn.').format(n=len(thieu)))

    tai_lieu = {
        "schema": SCHEMA_VAN_BAN,
        "ngon_ngu_goc": str(ban_ghi_goc.get("ngon_ngu") or ""),
        "ngon_ngu_dich": "vi",
        "provider": str(provider or ""),
        "model": str(model or ""),
        "loi_nhac": PHIEN_BAN_LOI_NHAC,
        "muc": muc,
    }
    kiem(tai_lieu, ban_ghi_goc)
    return tai_lieu


def kiem(tai_lieu: dict, ban_ghi_goc: dict | None = None) -> None:
    """Kiem tai lieu; doi chieu ma voi ban ghi neu duoc dua vao.

    Chay ca luc tao lan luc doc lai tu kho — mot artifact hop le luc ghi van co
    the bi sua sau do, va I8 noi DONE phai keo theo mot ket qua **con dung**.
    """
    if not isinstance(tai_lieu, dict):
        raise VanBanError(_t('Văn bản đã xử lý không đúng định dạng.'))
    if int(tai_lieu.get("schema") or 0) != SCHEMA_VAN_BAN:
        raise VanBanError(_t('Văn bản đã xử lý thuộc phiên bản cấu trúc khác.'))

    muc = tai_lieu.get("muc")
    if not isinstance(muc, list) or not muc:
        raise VanBanError(_t('Văn bản đã xử lý không có mục nào.'))

    da_thay = set()
    truoc_ket = None
    for m in muc:
        ma = m.get("ma")
        if not ma or ma in da_thay:
            raise VanBanError(_t('Văn bản đã xử lý có mã đoạn trùng hoặc thiếu.'))
        da_thay.add(ma)
        if not _sach(m.get("chu")):
            raise VanBanError(_t('Văn bản đã xử lý có mục rỗng.'))
        bat, ket = float(m.get("bat", -1)), float(m.get("ket", -1))
        if bat < 0 or ket <= bat:
            raise VanBanError(_t('Văn bản đã xử lý có mốc thời gian không hợp lệ.'))
        if truoc_ket is not None and bat + 0.05 < truoc_ket:
            raise VanBanError(_t('Văn bản đã xử lý có hai mục chồng thời gian.'))
        truoc_ket = ket

    if ban_ghi_goc is not None:
        ma_goc = {d["ma"] for d in (ban_ghi_goc.get("doan") or [])}
        if da_thay != ma_goc:
            # So TAP HOP chu khong so SO LUONG: hai tap cung kich thuoc van co
            # the khac nhau, va do la dung kieu lech im lang can bat o day.
            raise VanBanError(
                _t('Mã đoạn của bản dịch không khớp với bản ghi gốc.'))


def van_tay_van_ban(*, checksum_ban_ghi: str, provider: str, model: str,
                    ngon_ngu_dich: str) -> str:
    """Van tay (Prompt 11 muc 7).

    Nam thanh phan, va ly do tung cai:
      `checksum_ban_ghi` doi loi goc      -> phai dich lai
      `PHIEN_BAN_LOI_NHAC` doi loi nhac   -> ban dich khac, du dau vao giu nguyen
      `provider` + `model`                -> **doi model la doi san pham**
      `ngon_ngu_dich`                     -> dich sang thu tieng khac
      `SCHEMA_VAN_BAN`                    -> hinh dang khac
    """
    goi = json.dumps({
        "ban_ghi": checksum_ban_ghi,
        "loi_nhac": PHIEN_BAN_LOI_NHAC,
        "provider": provider,
        "model": model,
        "ngon_ngu": ngon_ngu_dich,
        "schema": SCHEMA_VAN_BAN,
    }, sort_keys=True)
    return hashlib.sha256(goi.encode("utf-8")).hexdigest()


def tom_tat(tai_lieu: dict) -> dict:
    """Con so cho tien do va log. KHONG chua loi thoai (I16)."""
    muc = tai_lieu.get("muc") or []
    return {
        "so_muc": len(muc),
        "ngon_ngu_goc": tai_lieu.get("ngon_ngu_goc", ""),
        "ngon_ngu_dich": tai_lieu.get("ngon_ngu_dich", ""),
        "provider": tai_lieu.get("provider", ""),
        "model": tai_lieu.get("model", ""),
        "so_ky_tu": sum(len(m.get("chu") or "") for m in muc),
    }
