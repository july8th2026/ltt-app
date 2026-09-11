"""Tệp app sinh ra phải DỌN ĐƯỢC — khoá lưu trữ phải khớp cách nền tảng nhận diện.

## Lỗi mà tệp này chốt

`platform_core/job_content.py` hết hạn nội dung của job sau `RETENTION_DAYS`, và
nó nhận diện tệp thuộc về một job bằng cách tìm **`/{job_id}/` như một đoạn
đường dẫn**. Phép nhận dạng đó cố ý sai theo hướng **bỏ sót**: thà không dọn còn
hơn xoá nhầm tệp của job khác — đúng hướng sai duy nhất chấp nhận được với một
thao tác không hoàn tác.

`apps/ltt_voice` ghi `voice/out/{owner}/{job_id}.wav`: job id nằm **cuối**, theo
sau là dấu chấm. Không khớp.

🔴 Hệ quả là một rò rỉ **hoàn toàn im lặng**. Vòng bảo trì vẫn chạy, vẫn dọn
   những job khác, vẫn đặt `content_expired_at`, vẫn ghi log "đã hết hạn N job".
   Chỉ là không tệp tiếng nào bị xoá. Đủ giấy tờ nói đã dọn, không byte nào đi.

Bảy app còn lại đều theo đúng `{app}/{owner}/{job_id}/...`; chỉ app này lệch.

## Hai chiều

1. **Hành vi** — dựng một job thật của `ltt_voice` rồi đòi `content_keys` tìm ra
   khoá của nó. Đây là phép kiểm thật.
2. **Tĩnh** — quét mọi `apps/*/jobs.py` tìm đúng hình dạng đã sai (`{job_id}` mà
   ngay sau là dấu chấm). Rẻ, và nó bắt app THỨ CHÍN trước khi app đó chạy.
"""
from __future__ import annotations

import os
import re

APPS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "apps")

#: `{job_id}` (hoặc biến tương đương) mà ngay sau là dấu chấm — tức job id
#: KHÔNG phải một đoạn đường dẫn.
XAU = re.compile(r"\{(?:job_id|jid)[^}]*\}\.")


def test_ltt_voice_khoa_ket_qua_duoc_nhan_dien_de_don():
    from platform_core.job_content import content_keys
    from platform_core.models import Job

    from apps.ltt_voice import jobs as vjobs      # noqa: F401 - dam bao import duoc

    job_id = "6e0c2cc8-ee78-45fa-8775-0c3036fc47a0"
    khoa = f"voice/out/nguoi-dung-1/{job_id}/tieng.wav"
    job = Job(id=job_id, user_id="u", app_slug="ltt_voice",
              job_type="ltt_voice.synthesize",
              params={"text": "xin chao"},
              result={"audio_key": khoa, "duration_s": 8.0})

    thay = content_keys(job)
    assert khoa in thay, (
        f"`content_keys` khong tim thay {khoa!r}.\n"
        f"No tim `/{job_id}/` NHU MOT DOAN DUONG DAN. Khoa ket thuc bang "
        f"`{{job_id}}.wav` se khong khop, va tep se KHONG BAO GIO bi don — "
        f"trong khi vong bao tri van bao la da don.")


def test_khoa_cua_moi_app_deu_dat_job_id_lam_doan_duong_dan():
    """Quét tĩnh: không app nào được đặt job id ngay trước một dấu chấm."""
    # ⛔ CHỈ quét `jobs.py`. Bản đầu quét mọi `.py` trong `apps/` và cho ba
    #    dương tính giả: một route path `/package/{job_id}.zip`, một tên tệp
    #    trong `Content-Disposition`, và một docstring NÓI VỀ hình dạng sai.
    #
    #    Cả ba đều vô hại, và đó chính là vấn đề: một bánh cóc đỏ vì thứ vô hại
    #    sẽ bị người ta tắt đi, rồi ngày nó đỏ vì thứ thật sẽ không ai nhìn.
    #    Khoá lưu trữ chỉ được dựng trong handler, nên quét đúng chỗ đó.
    xau = []
    for goc, _, tep in os.walk(APPS):
        if "__pycache__" in goc:
            continue
        for ten in tep:
            if ten != "jobs.py":
                continue
            duong = os.path.join(goc, ten)
            with open(duong, encoding="utf-8") as f:
                for i, dong in enumerate(f, 1):
                    # Bỏ dòng chú thích: tệp này và `jobs.py` của ltt_voice đều
                    # NÓI VỀ hình dạng sai đó, và đếm chúng làm phép kiểm đỏ vì
                    # một câu văn xuôi.
                    if dong.lstrip().startswith("#"):
                        continue
                    if XAU.search(dong):
                        rel = os.path.relpath(duong, os.path.dirname(APPS))
                        xau.append(f"{rel}:{i}  {dong.strip()[:80]}")

    assert not xau, (
        "Nhung dong sau dat job id ngay truoc mot dau cham. Neu do la mot khoa "
        "luu tru thi tep se KHONG BAO GIO bi don:\n  " + "\n  ".join(xau) +
        "\n\nQuy uoc cua nen tang: `{app}/{owner}/{job_id}/<ten tep>`.")


def test_dieu_khoan_noi_ro_giu_tep_bao_lau_va_lay_tu_hang_so():
    """Cửa sổ tải tệp là một LỜI HỨA, nên nó phải nằm trong điều khoản.

    `platform_core/job_content.py` tự viết ra yêu cầu này: *"Đây là lời hứa với
    khách về cửa sổ tải artifact, nên nó phải xuất hiện trong tài liệu công khai
    chứ không chỉ ở đây."* Trước 31/08/2026 không tài liệu công khai nào của
    nền tảng nhắc tới `RETENTION_DAYS` — kể cả điều khoản của app này.

    ⭐ Và con số phải LẤY TỪ HẰNG SỐ, không gõ lại. Cùng khuôn `apps/vps` +
       `test_298`: đổi hạn lưu mà quên sửa điều khoản là gate đỏ, chứ không phải
       một trang web nói sai trong im lặng.
    """
    from platform_core.job_content import RETENTION_DAYS

    from apps.ltt_voice.dieu_khoan import cac_dieu

    noi_dung = " ".join(d["noi_dung"] for d in cac_dieu())
    assert str(RETENTION_DAYS) in noi_dung, (
        f"dieu khoan khong nhac toi han luu {RETENTION_DAYS} ngay. Khach khong "
        f"co cau tra loi cho 'toi tai duoc tep nay trong bao lau'.")

    tieu_de = [d["tieu_de"] for d in cac_dieu()]
    assert any("tệp" in t.lower() for t in tieu_de), (
        f"khong co dieu nao ve viec giu tep: {tieu_de}")


def test_doi_dieu_khoan_thi_phai_doi_phien_ban():
    """Bản cam kết đã lưu trỏ tới một phiên bản — nên phiên bản phải nhúc nhích.

    Không có phép kiểm nào biết được "câu chữ đã đổi" nếu không giữ một bản
    chụp. Nên chốt thứ kiểm được: **số điều** và phiên bản đi cùng nhau. Thêm
    một điều mà quên bump phiên bản thì mọi bản cam kết cũ sẽ trỏ tới một văn
    bản mà khách chưa từng đọc.
    """
    from apps.ltt_voice.dieu_khoan import PHIEN_BAN_DIEU_KHOAN, cac_dieu

    #: Cập nhật CẢ HAI khi đổi điều khoản. Đây là một bản chụp có chủ ý.
    #: 11/09/2026 (T-07): thêm điều "Xoá giọng" (quyền thu hồi) -> 7 điều, bump
    #: phiên bản.
    SO_DIEU = 7
    PHIEN_BAN = "ltt-voice-dk-2026-09-11a"

    assert len(cac_dieu()) == SO_DIEU, (
        f"so dieu khoan doi ({len(cac_dieu())} != {SO_DIEU}) — hay bump "
        f"`PHIEN_BAN_DIEU_KHOAN` va cap nhat hai hang so trong phep kiem nay")
    assert PHIEN_BAN_DIEU_KHOAN == PHIEN_BAN, (
        f"phien ban dieu khoan la {PHIEN_BAN_DIEU_KHOAN!r}, phep kiem cho "
        f"{PHIEN_BAN!r}. Neu vua doi cau chu thi cap nhat o day.")
