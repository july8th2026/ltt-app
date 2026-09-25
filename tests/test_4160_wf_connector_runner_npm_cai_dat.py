"""N3 (plan `2026-09-25-wf-v2-VAN-HANH.md`, làn wfn): chặn tái diễn khiếm
khuyết đo được 25/09/2026 — `connector_runner/package.json` khai 5 phụ thuộc
`@activepieces/piece-*` nhưng KHÔNG bước nào trong `setup/2-cai-dat.ps1` cài
chúng (`git ls-files connector_runner/node_modules` rỗng — Git không theo
dõi). Hậu quả: mọi node `piece.*` (Slack/GitHub/Telegram/Google Sheets) CHẾT
trên production với `Cannot find module '.../package.json'`
(`connector_runner/src/piece_nap.js` <- `runner.js`).

N2 đã thêm bước `npm ci` cho connector_runner vào `2-cai-dat.ps1`, ĐẶT TRƯỚC
`Stop-Service` đầu tiên (không phải trước "Khởi động") — lý do: `npm ci` gọi
mạng (npm registry) và có thể thất bại; một phép kiểm/bước có thể hỏng đặt
SAU điểm không quay lại (ở đây là Stop-Service: dịch vụ cũ đã dừng, `app`
cũ đã bị `Move-Item` sang `app.previous`) không còn là một cổng — nó chỉ còn
là một cáo phó (Plan §6 nợ số 4, và cùng tính chất với
`tests/test_45_deploy_scripts.py::test_viec_dai_khong_nam_trong_cua_so_ngung_dich_vu`).

Bộ ba phép kiểm dưới đây đọc TĨNH cả hai tệp — KHÔNG chạy `.ps1`, không cần
Node/npm cài trên máy chạy test.
"""
from __future__ import annotations

import json
import os
import re

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEP_PACKAGE_JSON = os.path.join(GOC, "connector_runner", "package.json")
TEP_PS1 = os.path.join(GOC, "setup", "2-cai-dat.ps1")


def _doc_dependencies() -> dict:
    with open(TEP_PACKAGE_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    ten = {}
    for nhom in ("dependencies", "devDependencies"):
        ten.update(data.get(nhom, {}))
    assert ten, (
        "connector_runner/package.json không khai dependency nào — phép "
        "kiểm này hết nghĩa (đo nhầm tệp?)")
    return ten


def _doc_ps1() -> str:
    with open(TEP_PS1, "r", encoding="utf-8") as f:
        return f.read()


def _dong_ps1() -> list:
    return _doc_ps1().splitlines()


def _la_dong_ma(dong: str) -> bool:
    """Bỏ dòng CHÚ THÍCH (`#...`) và dòng trắng — tệp này nói VỀ npm/Stop-Service
    ở nhiều chú thích, đếm cả chú thích sẽ làm phép kiểm vỡ vì một câu văn
    xuôi chứ không phải vì mã thật đổi."""
    t = dong.strip()
    return bool(t) and not t.startswith("#")


def test_moi_dependency_trong_package_json_duoc_mot_buoc_cai_bao_phu():
    """Tính chất cốt lõi task N3 đòi: package.json khai một piece mà trình
    cài KHÔNG có bước cài nó ⇒ ĐỎ.

    Cơ chế hiện tại (N2) là MỘT lệnh `npm ci` chung cho cả thư mục
    connector_runner — không liệt kê từng gói. Nên điều kiện đúng ở đây có
    hai nhánh, chọn theo THỰC TẾ đang có trong tệp (không giả định trước):

    - Nếu ai đó đổi sang cài THỦ CÔNG từng gói (`npm install <ten>@<ban>`),
      MỌI dependency phải có mặt riêng — một danh sách thủ công dễ lệch
      ngay khi có người thêm một piece mới mà quên sửa danh sách.
    - Ngược lại (cơ chế hiện tại): phải có một bước `npm ci`/`npm install`
      KHÔNG ĐIỀU KIỆN (là mã thật, không phải chú thích) và tệp phải nhắc
      tới đúng thư mục `connector_runner` gần đó — nếu không, lệnh cài có
      thể đang nhắm nhầm thư mục khác.
    """
    ten_phu_thuoc = _doc_dependencies()
    text = _doc_ps1()

    goi_thu_cong = set(re.findall(r"npm\s+(?:install|i)\s+(@?[\w\-./]+)@", text))
    if goi_thu_cong:
        thieu = sorted(t for t in ten_phu_thuoc if t not in goi_thu_cong)
        assert not thieu, (
            f"2-cai-dat.ps1 cài THỦ CÔNG từng gói npm, nhưng thiếu {thieu} — "
            f"package.json khai các gói này mà không có lệnh `npm install "
            f"<ten>@<ban>` riêng cho chúng")
        return

    dong = _dong_ps1()
    dong_npm = [d for d in dong if re.search(r"\bnpm\s+ci\b|\bnpm\s+install\b", d)
                and _la_dong_ma(d)]
    assert dong_npm, (
        "không tìm thấy dòng MÃ THẬT nào chạy `npm ci`/`npm install` trong "
        f"2-cai-dat.ps1 — connector_runner/package.json khai "
        f"{sorted(ten_phu_thuoc)} nhưng không có gì cài chúng trên production")

    assert "connector_runner" in text, (
        "có bước `npm ci`/`npm install` nhưng tệp không nhắc 'connector_runner' "
        "ở đâu cả — lệnh cài có thể đang nhắm nhầm thư mục")


def test_buoc_cai_npm_dat_truoc_Stop_Service_dau_tien():
    """`npm ci` gọi mạng và CÓ THỂ THẤT BẠI — thất bại phải xảy ra TRƯỚC khi
    dịch vụ bị dừng, không phải sau, để một lỗi mạng lúc cài không biến
    thành một lần downtime không cần thiết. Cùng tính chất với
    `test_45_deploy_scripts.py::test_viec_dai_khong_nam_trong_cua_so_ngung_dich_vu`,
    chốt riêng ở đây vì tệp kia chỉ quét `install-*-sidecar.ps1`, không quét
    `npm ci`.
    """
    dong = _dong_ps1()

    dong_stop = [i for i, d in enumerate(dong) if "Stop-Service" in d and _la_dong_ma(d)]
    assert dong_stop, "2-cai-dat.ps1 không còn Stop-Service — phép kiểm này hết nghĩa"

    dong_npm = [i for i, d in enumerate(dong)
                if re.search(r"\bnpm\s+ci\b|\bnpm\s+install\b", d) and _la_dong_ma(d)]
    assert dong_npm, "không tìm thấy dòng MÃ THẬT nào chạy npm ci/install"

    sau = [i for i in dong_npm if i > min(dong_stop)]
    assert not sau, (
        f"bước npm cài connector_runner ở dòng {[i + 1 for i in sau]} nằm SAU "
        f"Stop-Service đầu tiên (dòng {min(dong_stop) + 1}). Một lỗi mạng lúc "
        f"cài npm giữa cửa sổ dịch vụ đã dừng biến một cảnh báo vô hại thành "
        f"một lần downtime — chuyển lên TRƯỚC `Head 'Copy ma nguon'`.")


def test_buoc_cai_npm_khong_nham_vao_app_dir():
    """`robocopy` ở 'Head Copy ma nguon' loại `node_modules` BẰNG TÊN ở MỌI
    cấp (`/XD ... node_modules ...`) để không chép node_modules build-time
    của frontend/*. Nếu bước `npm ci` của connector_runner lại cài THẲNG vào
    `$appDir` (thư mục bị `robocopy`/`Move-Item` thay TOÀN BỘ mỗi lần
    deploy), `node_modules` vừa cài sẽ bị chính robocopy đó xoá ở lần deploy
    kế tiếp — im lặng, không báo lỗi gì. Cắm cờ để một lần "dọn mã" vô tình
    đổi đích cài về `$appDir` bị bắt ngay, không phải đợi lộ ra trên production.
    """
    dong = _dong_ps1()
    dong_npm_ma = [d for d in dong
                   if re.search(r"\bnpm\s+ci\b|\bnpm\s+install\b", d) and _la_dong_ma(d)]
    assert dong_npm_ma, "không tìm thấy dòng MÃ THẬT nào chạy npm ci/install"
    for d in dong_npm_ma:
        assert "$appDir" not in d, (
            f"dòng `{d.strip()}` chạy npm cài THẲNG nhắm `$appDir` — thư mục "
            f"này bị `robocopy`/`Move-Item` thay TOÀN BỘ mỗi lần deploy, nên "
            f"node_modules vừa cài sẽ mất ở lần deploy kế tiếp")
