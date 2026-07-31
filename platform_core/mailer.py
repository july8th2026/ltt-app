"""
mailer.py — tầng gửi email, tách khỏi nghiệp vụ.

Vì sao tách: gửi email đến hộp thư thật cần khoá API Resend + 3 bản ghi DNS
(Q19) — thứ chỉ chủ dự án cấu hình được. Nếu route đăng ký gọi thẳng Resend thì
không test được luồng đăng ký mà không có khoá thật, và máy phát triển không
gửi được mail.

Giải: một giao diện `Mailer` với hai hiện thực —
- `ResendMailer`: gọi API Resend thật (production);
- `ConsoleMailer`: ghi thư vào log + giữ lại trong bộ nhớ (dev + test).

Chọn hiện thực nào là do biến môi trường, không phải do code nghiệp vụ. Nhờ vậy
toàn bộ luồng đăng ký/xác thực chạy và test được **ngay bây giờ**, phần cắm khoá
Resend để lại đúng cho người có khoá.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Optional

log = logging.getLogger(__name__)

# Trần Resend gọi qua HTTP; giữ nhỏ để một lỗi không treo cả request.
_TIMEOUT_S = 10.0


@dataclass
class Email:
    to: str
    subject: str
    html: str
    text: str = ""


class MailerError(RuntimeError):
    pass


class Mailer:
    """Giao diện chung. Nghiệp vụ chỉ gọi `send()`."""

    def send(self, email: Email) -> None:
        raise NotImplementedError


@dataclass
class ConsoleMailer(Mailer):
    """Ghi thư ra log và giữ lại trong RAM. Dùng cho dev và test.

    `sent` cho test đọc lại nội dung thư (vd lấy link xác thực) mà không cần
    một hộp thư thật. KHÔNG dùng ở production — thư chỉ nằm trong log.
    """

    sent: list = field(default_factory=list)

    def send(self, email: Email) -> None:
        self.sent.append(email)
        log.info("[ConsoleMailer] gui toi %s | %s", email.to, email.subject)


@dataclass
class ResendMailer(Mailer):
    """Gọi API Resend qua HTTP.

    Dùng `httpx` (đã có sẵn) thay vì SDK `resend` để bớt một phụ thuộc — API chỉ
    là một POST. Khoá API đọc từ biến môi trường, **không bao giờ** viết cứng.
    """

    api_key: str
    from_addr: str

    def send(self, email: Email) -> None:
        import httpx

        try:
            resp = httpx.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "from": self.from_addr,
                    "to": [email.to],
                    "subject": email.subject,
                    "html": email.html,
                    **({"text": email.text} if email.text else {}),
                },
                timeout=_TIMEOUT_S,
            )
        except httpx.HTTPError as exc:
            # KHÔNG nhét khoá API vào thông báo lỗi.
            raise MailerError(f"Không gửi được email qua Resend: {type(exc).__name__}") from None
        if resp.status_code >= 400:
            raise MailerError(f"Resend từ chối gửi (HTTP {resp.status_code}).")


_mailer: Optional[Mailer] = None


def get_mailer() -> Mailer:
    """Mailer dùng chung, chọn theo biến môi trường.

    - Có `RESEND_API_KEY` + `LTT_MAIL_FROM` → ResendMailer (production).
    - Ngược lại → ConsoleMailer (dev/test), kèm cảnh báo một lần.

    Không ném lỗi khi thiếu khoá: máy phát triển vẫn phải chạy được, chỉ là thư
    nằm trong log thay vì tới hộp thư thật.
    """
    global _mailer
    if _mailer is None:
        api_key = (os.environ.get("RESEND_API_KEY") or "").strip()
        from_addr = (os.environ.get("LTT_MAIL_FROM") or "").strip()
        if api_key and from_addr:
            _mailer = ResendMailer(api_key=api_key, from_addr=from_addr)
        else:
            log.warning(
                "Chua cau hinh RESEND_API_KEY/LTT_MAIL_FROM — dung ConsoleMailer, "
                "thu chi ghi vao log. Dat hai bien do de gui mail that (Q19)."
            )
            _mailer = ConsoleMailer()
    return _mailer


def set_mailer(mailer: Optional[Mailer]) -> None:
    """Cho test thay mailer (hoặc đặt None để buộc chọn lại)."""
    global _mailer
    _mailer = mailer
