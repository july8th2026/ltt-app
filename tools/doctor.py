"""
doctor.py — báo cáo sức khoẻ bằng một lệnh (PA-4).

⚠️ ĐỌC CÁI NÀY TRƯỚC KHI THÊM MỤC KIỂM MỚI.

Tệp này từng có **sáu** mục kiểm, và **năm** trong số đó thuộc app socialbot:
cấu hình `data/config.json`, kho token Facebook/TikTok, danh sách worker, email
service account, và kết nối Google Sheet. Chúng bị gỡ ngày 2026-08-25 cùng app
đó. Câu hỏi tệp này từng trả lời là *"bot đăng bài được chưa?"* — một câu hỏi
không còn ai hỏi.

⛔ Nên đừng đọc phần còn lại như *"doctor của nền tảng bị teo đi"*. **Chưa bao
   giờ có doctor của nền tảng.** Không có mục nào kiểm CSDL, kho R2, worker hay
   Cloudflare Tunnel — và điều đó không đổi hôm nay. Muốn có thì đó là một việc
   phải làm có chủ ý, không phải một chỗ trống cần lấp cho đầy.

⭐ Thứ **đang** trả lời cho sức khoẻ nền tảng, ở chỗ khác:
     `/health/ready`                     CSDL nối được (nssm + Cloudflare thăm dò)
     `/status/api`                       tình trạng công khai của `/api/v1`
     `/status`                           mục này + tóm tắt vận hành Nexus
     `platform_core/public_api/status.py` số liệu của khu API

Không bao giờ in ra token, bí mật hay giá trị khoá — chỉ tên, số đếm, trạng thái.

Dùng:
    python tools/doctor.py            # báo cáo cho người đọc
    python tools/doctor.py --json     # máy đọc được

Mã thoát:
    0 = không có lỗi chặn
    1 = có ít nhất một lỗi chặn
"""
from __future__ import annotations

import argparse
import json
import os
import sys

# Cho phép chạy `python tools/doctor.py` từ gốc dự án.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _force_utf8_output() -> None:
    """Làm đầu ra an toàn trên console Windows đời cũ.

    Console Windows Server mới tinh chạy bảng mã cũ (cp1252 / cp437). Báo cáo
    này có tiếng Việt và biểu tượng trạng thái, nên `print` từng ném
    UnicodeEncodeError và giết tiến trình — công cụ chẩn đoán chết đúng lúc
    người vận hành cần nó. Đặt lại UTF-8 với `errors="replace"` thì một ký tự
    không in được thành '?' thay vì làm sập cả lượt chạy.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            pass   # luồng không cấu hình lại được (pipe, pytest capture) — không sao


_force_utf8_output()

OK    = "ok"
WARN  = "warning"
BLOCK = "blocker"


class Report:
    def __init__(self) -> None:
        self.sections: list[dict] = []

    def add(self, name: str, status: str, detail: str = "", fix: str = "") -> None:
        self.sections.append(
            {"check": name, "status": status, "detail": detail, "fix": fix}
        )

    @property
    def has_blocker(self) -> bool:
        return any(s["status"] == BLOCK for s in self.sections)

    def to_text(self) -> str:
        icon = {OK: "✅", WARN: "⚠️ ", BLOCK: "❌"}
        lines = ["", "=" * 62, "  LTT STUDIOS — BÁO CÁO SỨC KHOẺ", "=" * 62]
        for s in self.sections:
            lines.append(f"{icon[s['status']]} {s['check']}")
            if s["detail"]:
                for d in s["detail"].splitlines():
                    lines.append(f"     {d}")
            if s["fix"]:
                lines.append(f"     → CÁCH SỬA: {s['fix']}")
        lines.append("-" * 62)
        blockers = [s for s in self.sections if s["status"] == BLOCK]
        if blockers:
            lines.append(f"KẾT LUẬN: CÓ {len(blockers)} LỖI CHẶN:")
            for b in blockers:
                lines.append(f"  • {b['check']}")
        else:
            warns = [s for s in self.sections if s["status"] == WARN]
            lines.append(
                f"KẾT LUẬN: Không có lỗi chặn. {len(warns)} cảnh báo."
                if warns else "KẾT LUẬN: Tất cả đều tốt."
            )
        lines.append("=" * 62)
        return "\n".join(lines)


# ─── từng mục kiểm ────────────────────────────────────────────────────────────

def check_environment(report: Report, env: dict) -> None:
    """Hồ sơ môi trường và nơi dữ liệu vận hành thật sự nằm.

    Mục này đáng giữ vì nó trả lời một câu hỏi hay bị trả lời sai bằng trí nhớ:
    *"tiến trình này đang ghi dữ liệu vào đâu?"* Trên máy chủ, đường dẫn tương
    đối rơi vào `app\\data\\` — thư mục **bị xoá và thay toàn bộ mỗi lần cập
    nhật**. In đường thật ra đây rẻ hơn nhiều so với đi tìm sau khi mất dữ liệu.
    """
    from platform_core.runtime_paths import resolve_runtime_paths
    from platform_core.settings import resolve_environment

    try:
        environment = resolve_environment(env)
    except Exception as exc:
        report.add("Môi trường", BLOCK, str(exc), "Đặt LTT_ENV hợp lệ")
        return
    paths = resolve_runtime_paths(env)
    report.add(
        "Môi trường", OK,
        f"profile={environment.value}\ndata={paths.data_dir}\nlogs={paths.logs_dir}",
    )


def run(env: dict | None = None) -> Report:
    env = os.environ if env is None else env
    report = Report()
    check_environment(report, env)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="LTT Studios health report")
    parser.add_argument("--json", action="store_true", help="Machine-readable output")
    args = parser.parse_args(argv)

    report = run()
    if args.json:
        print(json.dumps(report.sections, ensure_ascii=False, indent=2))
    else:
        print(report.to_text())
    return 1 if report.has_blocker else 0


if __name__ == "__main__":
    sys.exit(main())
