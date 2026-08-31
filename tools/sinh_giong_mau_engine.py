"""
sinh_giong_mau_engine.py — chụp lại danh sách preset của engine vào kho.

    py tools\\sinh_giong_mau_engine.py

🔴 VÌ SAO CẦN MỘT ẢNH CHỤP TRONG KHO, KHI ĐÃ CÓ TỆP GỐC TRÊN ĐĨA.

   `tests/test_345_ltt_voice_giong_mau.py` đối chiếu `apps/ltt_voice/giong_mau.py`
   với danh sách thật của engine. Bản đầu đọc thẳng
   `…\\vieneu-venv\\…\\assets\\voices_v3_turbo.json` bằng đường dẫn tuyệt đối, và
   **bỏ qua** phép kiểm khi không thấy tệp.

   Chạy tay thì nó thấy tệp và xanh. Chạy dưới `tools/gate.py` thì **không** —
   venv của engine nằm ngoài kho, ngoài tầm với của lượt chạy. Nên bốn phép kiểm
   quan trọng nhất của tệp đó âm thầm không chạy, và `check_bo_qua_im_lang` bắt
   được đúng điều ấy: *"một test bị bỏ qua là một test KHÔNG canh gì cả."*

⭐ Ảnh chụp sửa việc đó: nó nằm trong git, nên phép kiểm **luôn chạy**, ở mọi
   máy, kể cả nơi không cài engine.

⛔ NHƯNG ẢNH CHỤP KHÔNG THAY ĐƯỢC VIỆC HỎI ENGINE. Nó chốt "`giong_mau.py` khớp
   thứ ta đã chụp"; nó **không** chốt "thứ ta đã chụp còn đúng". Hai câu đó tách
   nhau đúng vào ngày nâng model — và đó là ngày duy nhất chúng có thể sai.

   ⇒ Nâng engine thì **chạy lại tệp này**, và commit phần diff. Nếu diff rỗng
     thì danh sách không đổi; nếu không rỗng thì `giong_mau.py` phải sửa theo, và
     `test_345` sẽ nói chính xác chỗ nào.

⚠️ Ảnh chụp **không** chứa `speaker_emb` lẫn `codes`. Chỉ tên, giới tính, mô tả —
   đủ để đối chiếu, và không kéo 140 KB dữ liệu mô hình vào kho.
"""
from __future__ import annotations

import json
import pathlib
import sys

#: Hai đường vì venv engine nằm **ngoài** `app\` (ổ C: chật — xem `CLAUDE.md`
#: hàng LTT VOICE), và máy chủ có thể đặt nó ở một trong hai.
NGUON = (
    pathlib.Path(r"D:\LTTPlatform-runtime\vieneu-venv\Lib\site-packages"
                 r"\vieneu\assets\voices_v3_turbo.json"),
    pathlib.Path(r"C:\LTTPlatform\vieneu-venv\Lib\site-packages"
                 r"\vieneu\assets\voices_v3_turbo.json"),
)

GOC = pathlib.Path(__file__).resolve().parent.parent
DICH = GOC / "apps" / "ltt_voice" / "giong_mau_engine.json"

GHI_CHU = ("Anh chup danh sach preset cua engine. SINH RA, dung sua tay. "
           "Sinh lai bang tools/sinh_giong_mau_engine.py khi nang engine.")


#: Mẩu GIỮA của `description` là vùng miền: `"Nam · Bắc · Phong cách tin tức"`.
_VUNG = {"Bắc": "bac", "Trung": "trung", "Nam": "nam"}


def _vung_tu_mo_ta(mo_ta: str) -> str | None:
    """Đọc vùng miền ra khỏi mô tả. Trả `None` khi không đọc được.

    ⛔ `None` chứ không phải `""`: hai thứ đó khác nhau ở chỗ quan trọng nhất —
       `""` là "giọng này không có vùng", `None` là "ta không biết". Chỉ cái
       thứ hai đáng làm dừng việc sinh ảnh chụp.
    """
    phan = [p.strip() for p in str(mo_ta or "").split("·")]
    if len(phan) < 2:
        return None
    return _VUNG.get(phan[1])


def doc_nguon() -> dict | None:
    for p in NGUON:
        try:
            if p.is_file():
                return json.loads(p.read_text(encoding="utf-8"))
        except OSError:
            continue
    return None


def main(argv=None) -> int:
    d = doc_nguon()
    if d is None:
        print("KHONG thay voices_v3_turbo.json. Duong da thu:")
        for p in NGUON:
            print(f"  {p}")
        print("\nChay tep nay tren may CO cai engine (may A).")
        return 1

    presets = {}
    hong = []
    for n, v in sorted(d.get("presets", {}).items()):
        mo_ta = str(v.get("description") or "")
        vung = _vung_tu_mo_ta(mo_ta)
        if vung is None:
            hong.append(f"  {n!r}: khong doc duoc vung tu {mo_ta!r}")
        presets[n] = {
            "gender": v.get("gender", ""),
            # `style` là cột THẬT của engine (`tin_tuc`/`tu_nhien`/`doc_truyen`).
            # Lấy thẳng nó, đừng đoán từ `description` — mô tả upstream không
            # nhất quán ("Phong cách kể chuyện" và "Phong cách đọc truyện" cùng
            # là `doc_truyen`).
            "style": v.get("style", ""),
            "description": mo_ta,
            "vung": vung or "",
        }

    if hong:
        # 🔴 HỎNG TO TIẾNG, đừng ghi một ảnh chụp khuyết.
        #
        #    Vùng miền chỉ có trong chuỗi `description` (`"Nam · Bắc · …"`) —
        #    không có cột riêng, nên nó phải được đọc ra. Ngày upstream đổi khuôn
        #    mô tả, phép đọc đó sẽ hỏng; nếu ta lặng lẽ ghi `vung: ""` thì bộ lọc
        #    vùng miền trên giao diện **im lặng rỗng** và không ai biết vì sao.
        print("KHONG doc duoc vung mien cua mot so giong:")
        print("\n".join(hong))
        print("\nKhuon mo ta cua upstream co the da doi. Sua `_vung_tu_mo_ta`.")
        return 1

    ra = {
        "_ghi_chu": GHI_CHU,
        "default_voice": d.get("default_voice"),
        "presets": presets,
    }
    moi = json.dumps(ra, ensure_ascii=False, indent=2) + "\n"
    cu = DICH.read_text(encoding="utf-8") if DICH.is_file() else ""
    if moi == cu:
        print(f"{DICH.name}: khong doi ({len(ra['presets'])} preset)")
        return 0

    # LF, khong CRLF: tep JSON nay la LF trong git.
    DICH.write_text(moi, encoding="utf-8", newline="\n")
    print(f"{DICH.name}: DA GHI ({len(ra['presets'])} preset)")
    # ⛔ stdout cua mot cong cu phai la ASCII thuan. Mot emoji o day da tung
    #    lam gate do tren may nay (CLAUDE.md muc 4) — console Windows mac
    #    dinh la cp1252 va `print` NEM chu khong xuong dong.
    print("CANH BAO: danh sach preset DA DOI. Kiem `apps/ltt_voice/giong_mau.py`, "
          "roi chay `pytest tests/test_345_ltt_voice_giong_mau.py`.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
