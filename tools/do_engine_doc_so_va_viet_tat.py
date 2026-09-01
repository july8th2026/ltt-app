r"""
do_engine_doc_so_va_viet_tat.py — engine ĐANG đọc số, tiền và viết tắt thế nào?

    powershell -ExecutionPolicy Bypass -File .\setup\do_engine_doc_so_va_viet_tat.ps1

## Câu hỏi, và vì sao nó phải hỏi TRƯỚC khi chép gì về

Chủ dự án đề nghị lấy bộ xử lý văn bản của hệ thống cũ (đọc số, đọc tiền, từ
viết tắt, từ tiếng Anh xen giữa) về dùng cho hệ mới.

⛔ Nhưng hai hệ thống dùng **hai front-end âm vị khác hẳn nhau**. Hệ cũ chạy
   F5-TTS/XTTS; hệ mới chạy VieNeu qua `sea-g2p`, và `sea-g2p` **có** phần đọc
   số tiếng Việt của riêng nó. Chép một bộ đọc số đè lên một bộ đọc số đang
   chạy không phải "nâng cấp" — đó là hai bộ cùng viết vào một chỗ, và bộ nào
   thắng thì tuỳ thứ tự gọi.

⭐ Nên việc đầu tiên không phải là chép, mà là **đo cái đang có**. Bảng kết quả
   của tệp này chia đầu vào làm ba nhóm:

     · engine đọc ĐÚNG          -> chép về là thêm một chỗ hỏng
     · engine đọc SAI           -> đây mới là chỗ đáng lấy
     · engine đánh vần / bịa    -> chắc chắn phải can thiệp

   Và chỉ nhóm hai với nhóm ba mới xứng đáng có một mục trong từ điển.

## Cách đo

Sinh tiếng bằng chính engine production (`voice_sidecar.engine`), rồi cho MÁY
NGHE LẠI bằng `do_chat_luong.do_de_hieu` — cùng bộ nhận dạng mà cổng chất lượng
V10 dùng. So chuỗi máy nghe được với **kỳ vọng viết bằng chữ**.

⚠️ Bộ nhận dạng KHÔNG hoàn hảo, và bảng này thừa nhận điều đó: nó in nguyên văn
   chuỗi ASR bên cạnh kỳ vọng để người đọc tự phán, thay vì chỉ in ĐÚNG/SAI.
   Một phép đo dùng ASR làm trọng tài tuyệt đối sẽ tính "3 phần" và "ba phần"
   là hai câu khác nhau — trong khi tai người nghe y hệt.

   Vì thế cột phán quyết dùng phép so **đã chuẩn hoá chữ số**: quy mọi chữ số
   Ả Rập trong CẢ HAI vế về chữ trước khi so. Chỉ khi vẫn lệch mới gọi là SAI.

## ⛔ Chạm GPU, không chạm tiền

Gọi thẳng engine, không qua hàng đợi job, nên **không có bút toán credit nào**.
Nhưng nó CÓ chiếm GPU của máy A — đừng chạy song song với một lô đang đo.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace",
                           line_buffering=True)

#: `(nhom, dau_vao, ky_vong_bang_chu)`.
#:
#: ⭐ Kỳ vọng viết bằng chữ THƯỜNG, không dấu câu — vì ta so sau khi chuẩn hoá.
#:    Chỗ nào có nhiều cách đọc đúng thì ghi cách PHỔ THÔNG nhất và để người đọc
#:    nhìn cột ASR mà phán; đừng cố nhồi mọi biến thể vào một chuỗi.
CA_THU = [
    # ── số trần ───────────────────────────────────────────────────────────
    ("so", "Có 15 người.", "có mười lăm người"),
    ("so", "Có 21 người.", "có hai mươi mốt người"),
    ("so", "Có 105 người.", "có một trăm lẻ năm người"),
    ("so", "Có 1500 người.", "có một nghìn năm trăm người"),
    ("so", "Có 1250000 người.", "có một triệu hai trăm năm mươi nghìn người"),
    # ── tiền (sau khi `text_pipeline` đã bỏ dấu chấm hàng nghìn) ──────────
    ("tien", "Giá 990000 đồng.", "giá chín trăm chín mươi nghìn đồng"),
    ("tien", "Giá 1250000 đồng.",
     "giá một triệu hai trăm năm mươi nghìn đồng"),
    # ── số thập phân: tiếng Việt dùng DẤU PHẨY ────────────────────────────
    ("thapphan", "Nặng 1,5 ki lô gam.", "nặng một phẩy năm ki lô gam"),
    ("thapphan", "Tăng 0,25 lần.", "tăng không phẩy hai mươi lăm lần"),
    # ── điện thoại: phải ĐÁNH VẦN từng chữ số, không đọc thành số lớn ─────
    ("dienthoai", "Gọi 0912345678 nhé.",
     "gọi không chín một hai ba bốn năm sáu bảy tám nhé"),
    # ── viết tắt hành chính: hệ mới KHÔNG có mục nào cho nhóm này ─────────
    ("viettat", "Trụ sở tại TP.HCM.", "trụ sở tại thành phố hồ chí minh"),
    ("viettat", "UBND đã duyệt.", "ủy ban nhân dân đã duyệt"),
    ("viettat", "Công ty TNHH ABC.", "công ty trách nhiệm hữu hạn a bê xê"),
    ("viettat", "Anh ấy là TS.", "anh ấy là tiến sĩ"),
    # ── viết tắt ĐÃ CÓ trong `tu_dien.VIET_TAT` — đối chứng ───────────────
    ("dicho", "Dùng AI để làm.", "dùng ây ai để làm"),
    ("dicho", "Gọi API nhé.", "gọi ây pi ai nhé"),
    # ── tiếng Anh xen giữa, KHÔNG có trong bảng ───────────────────────────
    ("tienganh", "Gửi email cho tôi.", "gửi i meo cho tôi"),
    ("tienganh", "Tải app về máy.", "tải áp về máy"),
    ("tienganh", "Xem video này.", "xem vi đê ô này"),
    # ── số thứ tự / la mã ─────────────────────────────────────────────────
    ("lama", "Chương IV bắt đầu.", "chương bốn bắt đầu"),
]

_CHU_SO = ("không", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám",
           "chín")


def _bo_dau(s: str) -> str:
    nfd = unicodedata.normalize("NFD", s)
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn")


def _chuan(s: str) -> str:
    """Hạ chữ, bỏ dấu câu, và ĐÁNH VẦN mọi chữ số còn sót.

    ⭐ Đánh vần chữ số là chỗ quan trọng: bộ nhận dạng hay viết "3 phần" khi nó
       nghe "ba phần". Không quy về một dạng thì mọi ca có số đều báo SAI, và
       bảng trở nên vô dụng đúng ở nhóm ta quan tâm nhất.
    """
    s = unicodedata.normalize("NFC", (s or "").lower())
    s = re.sub(r"[^\w\sÀ-ỹ]", " ", s)
    s = "".join(f" {_CHU_SO[int(c)]} " if c.isdigit() else c for c in s)
    return re.sub(r"\s+", " ", s).strip()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--preset", default="", help="Trong thi lay MAC_DINH.")
    ap.add_argument("--nhom", default="", help="Chi chay mot nhom.")
    ap.add_argument("--ra", default="tmp/engine_doc_so.json")
    a = ap.parse_args(argv)

    import soundfile as sf

    from apps.ltt_voice import giong_mau, text_pipeline
    from voice_sidecar import do_chat_luong, engine, tham_so

    preset = a.preset or giong_mau.MAC_DINH
    cong = engine.lay_cong()
    ca = [c for c in CA_THU if not a.nhom or c[0] == a.nhom]
    sr_mac = getattr(tham_so, "SAMPLE_RATE", 48000)

    print(f"{len(ca)} ca · preset={preset}\n")
    print(f"{'nhom':10} {'dau vao':28} {'may NGHE LAI':44} kq")
    print("-" * 96)

    ket = []
    for nhom, vao, mong in ca:
        # ⭐ Đi qua ĐÚNG đường sản phẩm: `chuan_hoa` chạy trước, nên bảng này đo
        #    engine + pipeline HIỆN CÓ, không đo engine trần.
        sau = text_pipeline.chuan_hoa(vao)
        try:
            w, _ = cong.noi(sau, preset=preset)
        except Exception as ex:                        # noqa: BLE001
            print(f"{nhom:10} {vao[:28]:28} [hong] {type(ex).__name__}: {ex}")
            ket.append({"nhom": nhom, "vao": vao, "loi": str(ex)})
            continue

        t = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        t.close()
        sf.write(t.name, w, int(sr_mac))
        try:
            dh = do_chat_luong.do_de_hieu(t.name, sau, "vi") or {}
        finally:
            try:
                os.unlink(t.name)
            except OSError:
                pass

        nghe = (dh.get("text_nghe_lai") or "").strip()
        dung = _chuan(nghe) == _chuan(mong)
        ket.append({"nhom": nhom, "vao": vao, "sau_chuan_hoa": sau,
                    "mong": mong, "nghe": nghe, "dung": dung})
        print(f"{nhom:10} {vao[:28]:28} {nghe[:44]:44} "
              f"{'DUNG' if dung else 'LECH'}")
        if not dung:
            print(f"{'':10} {'mong doi:':28} {mong[:44]}")

    print("\n" + "=" * 96)
    for nhom in dict.fromkeys(c["nhom"] for c in ket):
        cs = [c for c in ket if c["nhom"] == nhom]
        d = sum(1 for c in cs if c.get("dung"))
        print(f"  {nhom:12} {d}/{len(cs)} dung")

    lech = [c for c in ket if not c.get("dung") and "loi" not in c]
    print(f"\n  {len(lech)}/{len(ket)} ca LECH — chi nhung ca nay moi dang co")
    print("  mot muc trong tu dien. Cac ca DUNG thi engine da lo roi, va them")
    print("  mot luat de len chung la them mot cho hong.")
    print("\n  ⚠️ Doc cot 'may NGHE LAI' truoc khi tin cot ket qua: bo nhan dang")
    print("     khong hoan hao, va mot so ca LECH la loi cua NO chu khong phai")
    print("     cua engine.")

    os.makedirs(os.path.dirname(a.ra) or ".", exist_ok=True)
    with open(a.ra, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"preset": preset, "ket": ket}, f, ensure_ascii=False,
                  indent=2)
    print(f"\nDa ghi: {a.ra}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
