"""Nạp `LTT_LLM_BASE_URL` + `LTT_LLM_TOKEN` của cổng LLM máy B cho một lượt gate.

🔴 VÌ SAO CÓ. `tests/test_1259_tran_anh_cong_bo_dung.py::test_BAN_SAO_khop_may_B`
   đối chiếu trần ảnh CÔNG BỐ với trần máy B ĐANG CƯỠNG CHẾ — cố ý ĐỎ khi không
   hỏi được máy B (không bao giờ bỏ qua, không xanh giả). Nhưng gate chưa từng
   cấp hai biến đó, nên L3 16/09, 17/09, 18/09 (lượt khép) và 19/09 đều đỏ đúng
   phép này, rồi được "khép" bằng một script tay đọc token qua SSH. Script tay
   làm đúng việc — chỉ là nó nằm ngoài kho, nên mỗi phiên viết lại một bản.

⭐ Đây là đúng script đó, đưa vào kho: cùng đường vào máy B của RUNBOOK §1
   (`ssh -i ~/.ssh/nexus_b lengo@192.168.2.66`, như `tools/canh_bao_ttft_b.py`,
   `tools/them_key_ltt_llm.py`), CHỈ ĐỌC một dòng của `gateway.env`.

⛔ TOKEN LÀ BÍ MẬT: chỉ nằm trong bộ nhớ, trong môi trường tiến trình con của
   gate. Không in, không ghi đĩa, không nằm trong chuỗi trạng thái trả về.
⛔ Không có khoá SSH / máy B không trả lời ⇒ KHÔNG đặt gì, trả lý do. Phép kiểm
   vẫn đỏ như trước — hàm này cấp môi trường, không nới phép kiểm.
⚠️ Biến đã đặt sẵn (người gọi tự cấp) thì giữ nguyên, không hỏi máy B.
"""
from __future__ import annotations

import pathlib
import subprocess
from collections.abc import Callable, MutableMapping

MAY_B = "lengo@192.168.2.66"
URL_CONG_LLM_B = "http://192.168.2.66:8299"
TEP_ENV_B = r"C:\ProgramData\LTTLlm\gateway.env"


def nap_env_may_b(env: MutableMapping[str, str], *,
                  chay: Callable[..., subprocess.CompletedProcess] = subprocess.run,
                  khoa: pathlib.Path | None = None) -> str:
    """Đặt hai biến vào `env` nếu thiếu. Trả MỘT dòng trạng thái ASCII, không chứa token."""
    if (env.get("LTT_LLM_BASE_URL") or "").strip() and (env.get("LTT_LLM_TOKEN") or "").strip():
        return "da co san LTT_LLM_BASE_URL + LTT_LLM_TOKEN"
    khoa = khoa or pathlib.Path.home() / ".ssh" / "nexus_b"
    if not khoa.is_file():
        return f"khong co khoa SSH {khoa.name} -> test_1259 se DO"
    try:
        r = chay(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10",
                  "-i", str(khoa), MAY_B, f"findstr /B LTT_LLM_TOKEN= {TEP_ENV_B}"],
                 capture_output=True, text=True, encoding="utf-8",
                 errors="replace", timeout=30)
    except (OSError, subprocess.SubprocessError) as loi:
        return f"ssh may B loi {type(loi).__name__} -> test_1259 se DO"
    dong = [d for d in (r.stdout or "").splitlines() if d.startswith("LTT_LLM_TOKEN=")]
    token = dong[0].split("=", 1)[1].strip().strip('"') if dong else ""
    if r.returncode != 0 or not token:
        return f"may B khong tra token (ma {r.returncode}) -> test_1259 se DO"
    if not (env.get("LTT_LLM_TOKEN") or "").strip():
        env["LTT_LLM_TOKEN"] = token
    if not (env.get("LTT_LLM_BASE_URL") or "").strip():
        env["LTT_LLM_BASE_URL"] = URL_CONG_LLM_B
    return f"da nap token cong LLM may B ({env['LTT_LLM_BASE_URL']}), khong in"
