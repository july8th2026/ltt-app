r"""BỀ MẶT API CÔNG KHAI — job type nào MỞ, job type nào CỐ Ý KHÔNG MỞ.

## Vì sao tệp này tồn tại

Lượt soát 09/09/2026 (hạng mục 62) đếm được: `ltt_voice` khai **hai** job type
(`synthesize`, `enroll`) và **một** `ToolSpec`. Tức `ltt_voice.enroll` — nhân
bản giọng — có đủ giá, VRAM, trần thời gian, số lần thử, nhưng **không mở qua
`/api/v1`**.

⛔ Trạng thái ấy **đúng**, và đó chính là vấn đề: nó đúng mà **không ai ghi ra**.
   Một job type khai đủ mọi tham số vận hành trông y hệt một job type sắp được
   mở. Người đọc sau không phân biệt được *"cố ý không mở"* với *"quên viết
   ToolSpec"* — và cách sửa cho hai chẩn đoán ấy ngược nhau.

⭐ Nên tệp này **không** đòi mở gì và **không** đòi gỡ gì. Nó chốt một bản phán
   quyết: mỗi job type phải nằm ở đúng một trong hai cột, và đổi cột là một
   hành động có chủ ý mà người review nhìn thấy.

## 🔴 Vì sao `enroll` KHÔNG ĐƯỢC mở, và vì sao đây là ràng buộc CƠ HỌC

`routes/_p_giong.py` ghi một hàng `VoiceConsent` **trước khi** tạo job, và bốn
trường của hàng ấy chỉ tồn tại ở **tầng HTTP của chính người đồng ý**:

    ip=(request.client.host ...)          <- may cua NGUOI DONG Y
    user_agent=(request.headers ...)      <- trinh duyet cua NGUOI DONG Y
    phien_ban_dieu_khoan=PHIEN_BAN_...    <- ban dieu khoan HO da doc
    ref_sha256=sha                        <- rang consent vao DUNG clip do

Một lượt gọi `jobs:create` từ máy chủ của bên tích hợp mang `ip` và
`user_agent` **của bên tích hợp**, không phải của người có giọng. Mở `enroll`
qua API vì thế không sinh ra "consent yếu hơn" — nó sinh ra một **bản ghi
consent nói sai về người đã đồng ý**, trong khi trông vẫn đầy đủ.

⇒ Đây là hạng lỗi **sở hữu / pháp lý** (§36 xếp trên hiệu năng và UX), và nó
  không sửa được bằng cách thêm trường vào `params_schema`.

## ⛔ Vì sao chốt bằng phép kiểm chứ không bằng chú thích

Một chú thích *"đừng mở enroll"* không ngăn được ai thêm một `ToolSpec`; nó chỉ
trách người ấy sau khi việc đã xong. Phép kiểm dưới đây làm việc thêm ToolSpec
**đỏ gate**, nên người thêm buộc phải đọc lý do trước khi đi tiếp — và nếu lý do
ấy đã hết hiệu lực (consent được ghi ở nơi khác) thì họ sửa phép kiểm, và bản
sửa ấy hiện ra trong review.
"""
from __future__ import annotations

import ast
import pathlib

import pytest

from apps.ltt_voice.manifest import MANIFEST

GOC = pathlib.Path(__file__).resolve().parents[1]

#: `job_type` -> phán quyết bề mặt công khai.
#:
#:   "mo"        — CÓ `ToolSpec`, khách gọi được qua `/api/v1`
#:   "khong_mo"  — CỐ Ý không có `ToolSpec`; lý do ghi ở cột thứ hai
PHAN_QUYET = {
    "ltt_voice.synthesize": ("mo", ""),
    "ltt_voice.enroll": (
        "khong_mo",
        "consent lay ip/user_agent/phien_ban_dieu_khoan tu request cua CHINH "
        "nguoi dong y; mot loi goi jobs:create mang danh tinh cua ben tich hop "
        "=> ban ghi consent noi SAI ve nguoi da dong y",
    ),
}


def _job_type_cua_tool() -> set[str]:
    return {t.job_type for t in MANIFEST.tools}


def test_moi_job_type_deu_co_PHAN_QUYET():
    """Thêm job type mới mà quên quyết định ⇒ đỏ ngay.

    ⛔ Đây là nửa chặn kiểu hỏng **im lặng**: một job type mới không có
       `ToolSpec` trông y hệt `enroll` — tức trông như đã được cân nhắc. Không
       có chốt này thì "chưa quyết" và "đã quyết là không mở" đọc ra giống nhau.
    """
    khai = set(MANIFEST.job_types)
    assert khai == set(PHAN_QUYET), (
        f"thieu phan quyet: {sorted(khai - set(PHAN_QUYET))} · "
        f"thua trong bang: {sorted(set(PHAN_QUYET) - khai)}")


@pytest.mark.parametrize("jt", sorted(k for k, v in PHAN_QUYET.items()
                                      if v[0] == "mo"))
def test_job_type_khai_MO_thi_that_su_co_ToolSpec(jt):
    assert jt in _job_type_cua_tool(), (
        f"`{jt}` khai la 'mo' nhung KHONG ToolSpec nao tro toi no")


@pytest.mark.parametrize("jt", sorted(k for k, v in PHAN_QUYET.items()
                                      if v[0] == "khong_mo"))
def test_job_type_khai_KHONG_MO_thi_dung_la_khong_mo(jt):
    """⛔ ĐỐI CHỨNG NGƯỢC — nửa quan trọng hơn.

    Không có nó thì bảng chỉ chốt một chiều: ai đó thêm `ToolSpec` cho `enroll`
    và bảng vẫn ghi "khong_mo" sẽ **xanh mãi mãi**, còn bản kiểm kê thì thành
    đúng thứ nó sinh ra để thay.
    """
    ly_do = PHAN_QUYET[jt][1]
    assert jt not in _job_type_cua_tool(), (
        f"`{jt}` khai la 'khong_mo' nhung DA co ToolSpec.\n"
        f"Ly do no khong duoc mo: {ly_do}\n"
        f"Neu ly do ay da het hieu luc thi sua BANG truoc, va noi ro vi sao.")


def test_consent_VAN_duoc_ghi_o_tang_HTTP_chu_khong_o_handler():
    """🔑 Chốt chính **tiền đề** của phán quyết trên, không chỉ chốt kết luận.

    Lý do `enroll` không mở được là: consent lấy danh tính từ `request`, thứ chỉ
    có ở đường trình duyệt. Nếu ai đó dời việc ghi consent xuống `jobs.py` (nơi
    một lượt API cũng đi qua) thì **tiền đề đổi**, và lúc ấy mở `enroll` có thể
    thành hợp lệ.

    ⭐ Nên bài này đỏ khi tiền đề đổi — đó là **đúng** hành vi mong muốn: nó
       không cấm thay đổi, nó bắt người thay đổi quay lại đọc phán quyết ở trên.
    """
    cay = ast.parse((GOC / "apps/ltt_voice/routes/_p_giong.py")
                    .read_text(encoding="utf-8"))
    goi_consent = [n for n in ast.walk(cay)
                   if isinstance(n, ast.Call)
                   and isinstance(n.func, ast.Name)
                   and n.func.id == "VoiceConsent"]
    assert goi_consent, (
        "khong con noi nao trong `_p_giong.py` dung `VoiceConsent` — consent da "
        "doi cho? Neu no xuong `jobs.py` thi doc lai docstring dau tep nay")

    truong = {k.arg for g in goi_consent for k in g.keywords}
    for bat_buoc in ("ip", "user_agent", "phien_ban_dieu_khoan", "ref_sha256"):
        assert bat_buoc in truong, (
            f"`VoiceConsent` o tang HTTP khong con truyen `{bat_buoc}` — "
            f"ban ghi consent yeu di, va phan quyet 'khong_mo' cua `enroll` "
            f"dang dua tren dung truong nay")


def test_khong_ToolSpec_nao_tro_toi_mot_job_type_KHONG_khai():
    """Một `ToolSpec` trỏ tới job type không có trong `job_types` là một cửa mở
    ra chỗ không có ai — worker sẽ không bao giờ nhận nó."""
    thua = _job_type_cua_tool() - set(MANIFEST.job_types)
    assert not thua, (
        f"ToolSpec tro toi job type khong duoc khai: {sorted(thua)}")
