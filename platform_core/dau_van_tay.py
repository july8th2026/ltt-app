"""
dau_van_tay.py — bản đang CHẠY là bản nào.

## Vì sao tệp này tồn tại

Ngày 05/09/2026 một phiên mất gần trọn buổi cho một câu hỏi lẽ ra trả lời được
trong mười giây: *"kho của tôi ghi 100.000, sao trang web hiện 1.500?"*

Câu trả lời hoá ra rất đơn giản — `C:\\LTTPlatform\\app\\` đang giữ một bản chép
từ thời `master`, còn nhánh làm việc đã đi trước **94 lượt commit**. Không có
cache nào dính dáng. Nhưng để biết điều đó phải so `md5sum` của
`/static/voice.js` với hai bản trên đĩa, vì **không có chỗ nào hỏi được máy chủ
đang chạy mã nào**.

⭐ Và đó là lớp lỗi mà `CLAUDE.md` đã ghi cho khu API: *"đừng đọc con số trong
   tài liệu, hỏi máy chủ"*. Chỗ ấy có `tools/api_prod_canary.py` để hỏi. Phần
   còn lại của nền tảng thì không có gì cả.

## ⛔ VÌ SAO ĐỌC MỘT TỆP CHỨ KHÔNG GỌI `git`

Bản deploy **không phải một kho git** — `setup/2-cai-dat.ps1` loại `.git` khỏi
robocopy có chủ ý (nó là ~1 GB lịch sử mà production không dùng tới). Nên một
`git rev-parse` ở máy chủ sẽ ném, và bản vá hiển nhiên là bọc `try/except` rồi
trả `"unknown"` — tức đúng lúc cần nhất thì nó im lặng.

⇒ Bên deploy **ghi ra** dấu vân tay; bên chạy chỉ **đọc**. Ở cây nguồn (nơi
  `.git` có thật) thì hỏi git, vì ở đó tệp marker không tồn tại và git là câu
  trả lời đúng hơn: nó đổi theo từng lượt `checkout`, một tệp thì không.

## ⚠️ CÁI GÌ ĐƯỢC PHÉP LỘ RA

`/health/*` **không có xác thực** — chính docstring của nó nói thế, và reverse
proxy dựa vào điều đó. Nên chỗ này chỉ khai những thứ ĐÃ công khai ở nơi khác:

    · `asset_ver`  — đã nằm trong mọi thẻ `<link>`/`<script>` của mọi trang
    · trần ký tự   — đã in trên màn Studio và màn API cho mọi khách đọc
    · commit ngắn  — 12 ký tự hex của một kho RIÊNG TƯ; nó định danh một bản
                     build, nó không mở được gì

⛔ ĐỪNG thêm đường dẫn tuyệt đối, tên máy, biến môi trường hay tên nhánh nội bộ
   vào đây. Nhánh thì cám dỗ — nó hữu ích khi gỡ lỗi — nhưng tên nhánh của công
   ty rò ra là rò một phần kế hoạch sản phẩm, và commit ngắn đã đủ để đối chiếu
   với `git log` ở phía trong.
"""
from __future__ import annotations

import functools
import json
import pathlib
import subprocess

#: Tên tệp mà `setup/2-cai-dat.ps1` ghi vào ngay sau lượt robocopy.
TEN_TEP = "dau_van_tay.json"

#: Gốc cây đang chạy. `parents[1]` vì tệp này ở `platform_core/`.
#:
#: ⛔ Đây là MỘT trong hai chỗ hiếm hoi mà `parents[n]` chấp nhận được, và lý do
#:    là tệp này **không bao giờ được đổi chỗ**: nó phải nằm cạnh marker để trả
#:    lời được câu hỏi của chính mình. `AGENTS.md` cấm neo đường dẫn kiểu này vì
#:    nó hỏng im lặng khi tệp di chuyển — ở đây nếu nó hỏng thì `doc()` trả
#:    `nguon="khong-ro"`, tức nó hỏng **thành tiếng**.
GOC = pathlib.Path(__file__).resolve().parents[1]


def _tu_marker() -> dict | None:
    """Đọc marker do deploy ghi. `None` nếu không có hoặc không đọc được."""
    tep = GOC / TEN_TEP
    if not tep.is_file():
        return None
    try:
        d = json.loads(tep.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(d, dict) or not d.get("commit"):
        return None
    return {"commit": str(d["commit"])[:12],
            "luc": str(d.get("luc") or ""),
            "nguon": "marker"}


def _tu_git() -> dict | None:
    """Hỏi git. Chỉ chạy được ở cây nguồn — bản deploy không có `.git`."""
    if not (GOC / ".git").exists():
        return None
    try:
        ra = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(GOC),
                            capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return None
    if ra.returncode != 0 or not ra.stdout.strip():
        return None
    return {"commit": ra.stdout.strip()[:12], "luc": "", "nguon": "git"}


def doc() -> dict:
    """`{commit, luc, nguon}` của bản đang chạy.

    `nguon` nói câu trả lời **đến từ đâu**, và nó không phải trang trí: một
    máy chủ trả `nguon="git"` là một máy chủ đang chạy thẳng từ cây nguồn chứ
    không phải từ bản deploy — thông tin ấy thay đổi hẳn cách đọc mọi con số
    còn lại. `"khong-ro"` nghĩa là cả hai đường đều câm, và đó là trạng thái
    phải sửa chứ không phải trạng thái bình thường.
    """
    return (_tu_marker() or _tu_git()
            or {"commit": "", "luc": "", "nguon": "khong-ro"})


@functools.lru_cache(maxsize=1)
def doc_da_cache() -> tuple:
    """`doc()` nhưng chỉ tính MỘT LẦN cho cả đời tiến trình.

    🔴 VÌ SAO PHẢI CACHE, VÀ ĐÂY LÀ MỘT LỖ TÔI TỰ MỞ RA RỒI TỰ ĐÓNG.

       `/health/version` **không có xác thực** — đó là thiết kế, reverse proxy
       dựa vào nó. Mà `_tu_git()` chạy `subprocess.run(["git", ...])`. Ghép hai
       điều đó lại: bất kỳ ai cũng gọi được một endpoint **fork một tiến trình
       con mỗi lượt**. Trên máy chủ thật `.git` không có nên nhánh ấy không
       chạy — nhưng "an toàn vì tình cờ không có tệp" không phải an toàn, và
       một cây nguồn chạy production là một cấu hình có thật.

    ⭐ VÀ CACHE Ở ĐÂY KHÔNG PHẢI ĐÁNH ĐỔI ĐỘ CHÍNH XÁC — nó LÀM TĂNG độ chính
       xác. Mã mà tiến trình đang chạy được nạp lúc import và **không đổi** cho
       tới khi restart; deploy thì luôn restart dịch vụ. Nên một giá trị đọc
       lại giữa chừng chỉ có thể mô tả một thứ **khác** với mã đang chạy — tức
       đúng kiểu nói dối mà tệp này sinh ra để chặn.

    ⚠️ Trả `tuple` chứ không `dict`: `lru_cache` trả về **chính** đối tượng đã
       nhớ, nên một `dict` sẽ để người gọi sửa được bộ nhớ đệm dùng chung. Một
       lỗi như thế hỏng im lặng và chỉ hiện ra ở lượt gọi sau.

    ⛔ `doc()` cố ý KHÔNG cache: nó là hàm thuần, và test cần gọi nó nhiều lần
       với `GOC` khác nhau.
    """
    return tuple(sorted(doc().items()))
