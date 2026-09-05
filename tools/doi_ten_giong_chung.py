r"""
doi_ten_giong_chung.py — đổi TÊN HIỂN THỊ của các giọng trong kho chung.

    powershell -File .\setup\doi_ten_giong_chung.ps1 -Xem
    powershell -File .\setup\doi_ten_giong_chung.ps1 -Ap

## Vì sao đổi, và vì sao là một công cụ chứ không phải một nút

25 giọng trong kho chung mang tên do chủ sản phẩm đặt theo **kênh** (`kinhte`,
`lichsu`, `phatgiao`, `tamlyhoc`, `hoathinh`, `bietdoi`, `lego`) hoặc theo **tên
nhân viên** (`Khánh`, `Lâm`, `Quân`, `Hương KT`, `Ninh Đôn`, `Nguyệt Nga`).

⛔ Cả hai đều không nên nằm trên một sản phẩm bán cho công chúng:

  · tên kênh **rò danh mục kinh doanh** — khách đọc được nó từ bộ chọn giọng;
  · tên nhân viên gắn với **dữ liệu sinh trắc của chính người đó**. Tên sản phẩm
    phải là một **bí danh**, không phải một cách nhận dạng người thật.

⭐ VÀ VÌ SAO ĐỔI TÊN Ở ĐÂY LÀ AN TOÀN — trả lời một lần cho mọi lần sau:

    `VoiceProfile.public_id`   (`vc_<32 hex>`)  <- hop dong API, KHONG dung toi
    `VoiceProfile.ten_hien_thi`                 <- chi thu nay doi

  Hai cột ấy tách nhau từ ngày bảng được dựng. Nên đổi tên hiển thị **không đổi
  một chữ nào** của hợp đồng API: khách đang gọi `voice_id="vc_…"` không thấy gì
  khác ngoài cái nhãn.

  ⚠️ Đây KHÔNG đúng với **giọng mẫu** (`giong_mau.py`), nơi `ma` vừa là khoá
     engine, vừa là `public_id`, vừa là tên hiển thị. Đừng dùng công cụ này để
     nghĩ rằng đổi tên preset cũng rẻ như vậy — nó không.

## ⛔ RÀNG BUỘC DUY NHẤT PHẢI CANH: `uq_voice_owner_ten`

Tên hiển thị **duy nhất trong phạm vi một chủ**. Cả 25 giọng kho chung cùng một
chủ, nên hai tên mới trùng nhau là một lượt đổi **dừng giữa chừng** — vài giọng
đã đổi, vài giọng chưa, và không có bút toán nào nói cái nào đã xong.

⇒ Công cụ này kiểm TOÀN BỘ trước khi ghi dòng đầu tiên (xem `_kiem_truoc`), và
  ghi trong **một** transaction. Hoặc cả 25 đổi, hoặc không cái nào.

⚠️ Kiểm cả trùng với 20 tên **giọng mẫu**: chúng không nằm trong ràng buộc CSDL
   (giọng mẫu không có hàng nào trong `voice_profile`), nhưng chúng đứng cạnh
   nhau trong cùng một bộ chọn. Hai giọng cùng tên ở đó là khách chọn nhầm.
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

#: `ma_cu` (khoá kho cũ) → (tên hiện đang chờ, tên mới).
#: Căn cứ: `docs/LTT_VOICE/KHO_GIONG/01_DE_XUAT_TEN.md`.
#:
#: 🔴 KHOÁ LÀ `ma_cu`, KHÔNG PHẢI TÊN HIỂN THỊ — và bản đầu của tệp này khoá
#:    theo tên, với một lý do nghe rất hợp lý: *"tên hiển thị là thứ đọc được
#:    trực tiếp từ hàng, nên nó khớp hay không khớp một cách nhìn thấy được."*
#:
#: ⛔ Lý do ấy sai vì một dữ kiện tôi chưa kiểm khi viết nó: lượt nhập 01/09
#:    (`nhap_kho_giong_cu.py`) chỉ **vá xuất xứ** cho bốn giọng đã có từ trước —
#:    nó **KHÔNG đổi tên** chúng. Nên bốn giọng ấy vẫn mang tên do đợt nhập đầu
#:    đặt, và bảng khoá-theo-tên sẽ trượt đúng bốn dòng đó.
#:
#: ⭐ `ma_cu` thì không trôi: nó là khoá của kho cũ, ghi vào `ghi_chu` lúc nhập
#:    và vá lại cho cả bốn giọng cũ bằng phép so `sha256` của tệp nguồn.
#:
#: ⚠️ Nhưng bỏ hẳn tên đi thì mất một lớp kiểm. Nên mỗi mục giữ **cả hai**: tên
#:    đang chờ dùng làm ĐỐI CHỨNG. Lệch thì công cụ NÓI RA rồi vẫn đổi — vì
#:    `ma_cu` mới là danh tính, còn tên chỉ là thứ ta tưởng nó đang mang.
#:
#: ⚠️ Làn VI dùng tên Việt, làn EN dùng tên quốc tế — làn đã hiện thành một chip
#:    riêng cạnh tên, nên tên HỢP với làn thì khách đọc một lần là hiểu.
#:
#: ⛔ KHÔNG có vùng miền trong tên. Kho cũ **không có** trường vùng miền nào
#:    (12 trường trong `voice_profiles.yaml`, không trường nào nói về vùng), và
#:    17/25 giọng thuộc làn EN nơi khái niệm ấy không có nghĩa. Bịa vùng vào tên
#:    là dựng một bộ lọc lọc sai mà khách sẽ tin.
DOI_TEN = {
    # ── làn VI — tên Việt ───────────────────────────────────────────────────
    "Huong_KT": ("Hương KT — nữ, kể chuyện ngôn tình", "Diễm Chi — nữ, kể chuyện ngôn tình"),
    "kinhte_nam": ("Kinh Tế — nam, tin tức kinh tế", "Gia Huy — nam, bản tin kinh tế"),
    "kyan_nam": ("Kỳ An — nam, kể chuyện", "Bảo Lâm — nam, kể chuyện"),
    "lichsu_nam": ("Lịch Sử — nam, kể chuyện lịch sử", "Trọng Nghĩa — nam, kể chuyện lịch sử"),
    "lily_nu": ("Lily — nữ, tự nhiên", "Hạ Vy — nữ, tự nhiên"),
    "nguyetnga_nu": ("Nguyệt Nga — nữ, tự nhiên", "Thanh Nhã — nữ, tự nhiên"),
    "ninhdon_nam": ("Ninh Đôn — nam, tự nhiên", "Duy Khang — nam, tự nhiên"),
    "phatgiao_nu": ("Phật Giáo — nữ, kể chuyện", "An Nhiên — nữ, kể chuyện thiền"),
    # ── làn EN — tên quốc tế ────────────────────────────────────────────────
    "alex_male_education": ("Alex — nam, giảng bài", "Ethan — nam, giảng bài"),
    "bella_nu": ("Bella — nữ, tự nhiên", "Clara — nữ, thuyết minh"),
    "bietdoi_girl": ("Biệt Đội — nữ, hoạt hình", "Nova — nữ, hoạt hình"),
    "cg_huong_nam": ("CG Hương — nam, tự nhiên", "Simon — nam, trang nghiêm"),
    "giffen_male_social": ("Giffen — nam, mạng xã hội", "Miles — nam, mạng xã hội"),
    "harry_male_adventure": ("Harry — nam, phiêu lưu", "Aaron — nam, phiêu lưu"),
    "hoathinh_female": ("Hoạt Hình — nữ, hoạt hình", "Lulu — nữ, hoạt hình"),
    "ht3d_men": ("HT3D — nam, tự nhiên", "Victor — nam, kể chuyện"),
    # 🔴 KHÔNG CÓ CHỮ GIỚI, và đó là kết luận CÓ ĐO, không phải né tránh.
    #
    #    Nhãn kho cũ ghi `male`; F0 trung vị đo được 220,2 Hz — giữa dải nữ.
    #    Tôi nghi phép đo của mình sai (tự tương quan nhảy quãng tám ở giọng
    #    dải rộng). Đo lại có đối chứng thì **giả thuyết ấy bị bác**:
    #
    #      giong                     khung nghi nhay quang tam   khung < 170 Hz
    #      khanh_male_entertainment            2,8%                  24,1%
    #      lego_nu        (nu chac)            7,3%                   0,3%
    #      hoathinh_female(nu chac)            4,6%                   1,5%
    #      tamlyhoc_men   (nam chac)           0,1%                  92,8%
    #
    # ⭐ Nhảy quãng tám ở giọng này THẤP HƠN cả hai giọng nữ chắc chắn, nên
    #    220 Hz không phải lỗi đo. Nhưng 24,1% số khung vẫn nằm trong dải nam
    #    (nữ thật: 0,3% và 1,5%) — nên nó cũng không phải một giọng nữ.
    #
    # ⇒ Đây là **giọng diễn, biến hoá qua cả hai dải** — khớp đúng với
    #   `entertainment` trong tên cũ, và giải thích luôn DNSMOS thấp nhất kho
    #   (âm thanh biểu cảm/xử lý nhiều thì chấm thấp). Gán "nam" hay "nữ" đều
    #   là bỏ đi chính đặc điểm khiến giọng này đáng có mặt trong danh mục.
    "khanh_male_entertainment": ("Khánh — nam, giải trí",
                                 "Robin — giải trí, biến hoá giọng"),
    "lam_male_storytelling": ("Lâm — nam, kể chuyện", "Owen — nam, kể chuyện"),
    "lego_nu": ("Lego — nữ, tự nhiên", "Ivy — nữ, thuyết minh"),
    # ⚠️ Hai dòng dưới đổi THỂ LOẠI, không chỉ đổi tên: tên cũ ghi "hoạt hình"
    #    theo tên kênh (`meodang`/`meoquan`), nhưng `description` của kho cũ ghi
    #    thẳng "EN male narrator". Thể loại đi theo MÔ TẢ, không theo tên kênh.
    "meodang_men": ("Mèo Đang — nam, hoạt hình", "Marcus — nam, thuyết minh"),
    "meoquan_men": ("Mèo Quàn — nam, hoạt hình", "Julian — nam, thuyết minh"),
    "qtrungg_male_narrator": ("QTrungg — nam, thuyết minh", "Douglas — nam, thuyết minh"),
    "quan_male_dialogue": ("Quân — nam, hội thoại", "Nathan — nam, hội thoại"),
    "roger_male_dialogue": ("Roger — nam, hội thoại", "Peter — nam, hội thoại"),
    "tamlyhoc_men": ("Tâm Lý Học — nam, thuyết minh", "Adrian — nam, thuyết minh"),
}


def _ma_cu(ghi_chu: str) -> str:
    """`ma_cu` trong `ghi_chu` (JSON), hoặc `""` nếu không đọc được.

    ⛔ Trả `""` chứ không ném: một hàng có `ghi_chu` rỗng hay hỏng là chuyện
       **có thật** — bốn giọng nhập đợt đầu từng như thế, và chúng chỉ được vá
       ở lượt nhập 01/09 bằng phép so `sha256`. Một hàng như thế phải hiện ra
       trong bảng thành một dòng "KHONG CO ma_cu" để người chạy nhìn thấy, chứ
       không làm chết cả lượt xem.
    """
    import json
    try:
        d = json.loads(ghi_chu or "")
    except (TypeError, ValueError):
        return ""
    return str(d.get("ma_cu") or "") if isinstance(d, dict) else ""


class KhongAp(RuntimeError):
    """Không áp được thì VỠ trước khi ghi, không sửa được nửa kho."""


def _kiem_truoc(hien_co: dict) -> list[str]:
    """Mọi lý do KHÔNG được ghi, gom hết trong một lượt.

    ⭐ Trả về **danh sách** chứ không ném ở lỗi đầu tiên: người chạy muốn thấy
       cả năm vấn đề trong một lượt, không phải sửa một rồi chạy lại để gặp cái
       thứ hai. Một công cụ ném sớm biến một lượt sửa thành năm lượt.
    """
    loi = []

    moi = [v[1] for v in DOI_TEN.values()]
    trung = sorted({t for t in moi if moi.count(t) > 1})
    if trung:
        loi.append(f"ten moi TRUNG NHAU: {trung}")

    thieu = [ma for ma in DOI_TEN if ma not in hien_co]
    if thieu:
        loi.append(f"khong thay `ma_cu` trong kho chung ({len(thieu)}): {thieu}")

    # Trùng với giọng mẫu của engine — không nằm trong ràng buộc CSDL, nhưng
    # chúng đứng cạnh nhau trong CÙNG một bộ chọn.
    try:
        from apps.ltt_voice import giong_mau
        preset = {g.ma for g in giong_mau.DANH_SACH}
        cham = sorted(set(moi) & preset)
        if cham:
            loi.append(f"ten moi trung GIONG MAU cua engine: {cham}")
    except Exception as e:                    # noqa: BLE001
        loi.append(f"khong doc duoc danh sach giong mau: {type(e).__name__}: {e}")

    # Trùng với một giọng dùng chung KHÔNG nằm trong bảng đổi.
    giu = {h.ten_hien_thi for ma, h in hien_co.items() if ma not in DOI_TEN}
    cham2 = sorted(set(moi) & giu)
    if cham2:
        loi.append(f"ten moi trung mot giong dung chung khong doi: {cham2}")

    return loi


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--xem", action="store_true",
                    help="Chi in bang doi, KHONG ghi gi.")
    ap.add_argument("--ap", action="store_true", help="Ghi that.")
    a = ap.parse_args(argv)

    from sqlalchemy import select

    from apps.ltt_voice.tables import VoiceProfile
    from platform_core.db import get_session

    gen = get_session()
    db = next(gen)
    try:
        ds = list(db.execute(select(VoiceProfile).where(
            VoiceProfile.dung_chung.is_(True))
            .order_by(VoiceProfile.ten_hien_thi)).scalars())
        hien_co, khong_ro = {}, []
        for h in ds:
            ma = _ma_cu(h.ghi_chu)
            if ma:
                hien_co[ma] = h
            else:
                khong_ro.append(h.ten_hien_thi)
        print(f"KHO CHUNG — {len(ds)} giong; bang doi co {len(DOI_TEN)} muc\n")

        loi = _kiem_truoc(hien_co)
        lech = []
        for h in ds:
            ma = _ma_cu(h.ghi_chu)
            muc = DOI_TEN.get(ma)
            print(f"  [{h.ngon_ngu:>2}] {h.ten_hien_thi}"
                  + (f"   ({ma})" if ma else "   (KHONG CO ma_cu)"))
            if muc:
                cho, moi = muc
                print(f"       -> {moi}")
                # ⚠️ ĐỐI CHỨNG, không phải điều kiện. `ma_cu` là danh tính; tên
                #    chỉ là thứ ta TƯỞNG nó đang mang. Lệch thì nói ra rồi vẫn
                #    đổi — im lặng ở đây là bỏ mất tín hiệu duy nhất báo rằng
                #    một giọng đã bị ai đó ngoài công cụ này đổi tên.
                if h.ten_hien_thi != cho:
                    lech.append(f"{ma}: dang la {h.ten_hien_thi!r}, "
                                f"bang doi cho {cho!r}")

        if khong_ro:
            print(f"\nKHONG CO `ma_cu` trong ghi_chu ({len(khong_ro)}): {khong_ro}")

        thua = [h.ten_hien_thi for ma, h in hien_co.items() if ma not in DOI_TEN]
        if thua:
            print(f"\nKHONG doi ({len(thua)}): {thua}")

        if lech:
            print(f"\n[!] TEN DANG CHO LECH voi bang doi ({len(lech)}) — "
                  "van doi, vi `ma_cu` moi la danh tinh:")
            for x in lech:
                print(f"  - {x}")

        if loi:
            print("\nKHONG AP DUOC:")
            for x in loi:
                print(f"  - {x}")
            return 2

        if not a.ap:
            print("\n[--xem] Khong ghi gi. Chay lai voi --ap de ghi that.")
            return 0

        # ⛔ MỘT transaction cho cả 25. Ghi từng cái rồi commit từng cái thì một
        #    lỗi ở giọng thứ 12 để lại một kho **nửa cũ nửa mới**, và không có
        #    gì nói cái nào đã đổi.
        for ma, (_cho, moi) in DOI_TEN.items():
            hien_co[ma].ten_hien_thi = moi
        db.commit()
        print(f"\nDA DOI {len(DOI_TEN)} ten.")
        return 0
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
