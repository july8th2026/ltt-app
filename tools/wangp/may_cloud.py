"""Client RunPod cho V2.1 — **mỏng, tiêm được, và không đi qua legacy**.

🔴 **Vì sao tệp này tồn tại.** Trước 07/09 mọi mã V2 gọi cloud đều đi qua
   `tools/video_cloud.py`, và tệp ấy `import platform_core.video_gen` — mã của
   **V3**. Hai hệ quả, cả hai đều thật:

   1. **Vi phạm luật đã khoá.** Quy tắc V2.1: *"New V2 code: import legacy =
      FORBIDDEN, call legacy = FORBIDDEN, fallback legacy = FORBIDDEN."*

   2. **Nó hỏng, và hỏng ở đúng chỗ đắt nhất.** Đo 07/09 bằng `git ls-tree`:
      `tools/video_cloud.py` và `platform_core/video_gen/` (5 tệp) chỉ có trên
      nhánh `claude/ltt-video-ai-v3-p00-3f5713`. Trên `master`, trên
      `admin-mvp-v3`, và trên chính `phien/video-v2-wangp` thì **không có tệp
      nào**. Nghĩa là `apps/lttvideo/jobs.py:_dieu_phoi_that()` — đường `B1` bật
      máy theo nhu cầu, chạy trong worker thật — ném `ModuleNotFoundError` ngay
      lượt job đầu tiên có `LTTV_POD_ID`.

   ⭐ Vì sao bộ test không thấy: `_dieu_phoi_that()` trả `None` sớm khi thiếu
      `LTTV_POD_ID`, còn phép kiểm thì tiêm `_dieu_phoi` vào. Và vì sao **tôi**
      không thấy suốt phiên: tôi chạy các script S3 từ một worktree khác, cây ấy
      đứng ở nhánh V3 nên tệp có thật ở đó. Đúng cái bẫy "đọc thứ đại diện thay
      vì đọc thứ thật".

⭐ **Bề mặt công khai, không phải `_rest`.** Bản cũ để `_rest`/`_graphql` là tên
   riêng tư rồi cho năm chỗ ngoài module gọi vào. Một tên riêng tư dùng xuyên
   ranh giới module là một hợp đồng không ai hứa — nên ở đây chúng là `rest()` và
   `graphql()`, và không có bí danh gạch dưới nào để quay lại thói cũ.

⛔ **Không có hàm nào xoá network volume.** Dừng chi tiêu không cần chạm volume,
   và đó là chỗ dễ mất dữ liệu nhất. Muốn xoá thì vào console gõ tay.

⛔ **Không giữ khoá.** Khoá ở `secrets/app.env` (`RUNPOD_API_KEY`); nơi gọi truyền
   vào hàm `goi` đã gắn sẵn header. Lớp `MayCloud` không đọc biến môi trường.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional

#: Hai bề mặt, và chúng khác nhau: số dư **không có** ở REST.
REST_GOC = "https://rest.runpod.io/v1"
GRAPHQL_GOC = "https://api.runpod.io/graphql"


class LoiMayCloud(Exception):
    """Gọi nhà cung cấp hỏng thật (mạng, 5xx, thân trả về lạ)."""


def tim_app_env(duong_dan: str | Path | None = None) -> Path:
    """Tìm `secrets/app.env` — **cây hiện tại trước, gốc kho dùng chung sau**.

    🔴 Vì sao không chỉ `Path("secrets/app.env")` như bản đầu. `secrets/` nằm
       trong `.gitignore`, mà `git worktree add` **chỉ chép thứ git theo dõi**.
       Nên mọi cây riêng đều thiếu tệp ấy, và cả bốn công cụ cloud ở đây chết
       ngay dòng đầu khi chạy từ một cây riêng — đúng cây mà việc đang làm.

    ⭐ Gốc kho dùng chung lấy từ `git rev-parse --git-common-dir`: mọi worktree
       đều trỏ về **một** `.git`, nên cha của nó là bản kiểm ra chính. Đó là câu
       trả lời của git, không phải một đường dẫn tuyệt đối gõ tay — thứ sẽ sai
       ngay khi ai đó đổi chỗ kho.

    ⛔ **Không chép `app.env` sang cây riêng để "cho tiện".** Nhân bản một tệp bí
       mật là nhân bản chỗ nó có thể rò, và bản sao ấy sẽ trôi khỏi bản gốc.
    """
    if duong_dan:
        p = Path(duong_dan)
        if not p.is_file():
            raise LoiMayCloud(f"khong thay tep env: {p}")
        return p

    da_thu = []
    gan = Path.cwd() / "secrets" / "app.env"
    da_thu.append(gan)
    if gan.is_file():
        return gan

    import subprocess  # noqa: PLC0415

    try:
        ra = subprocess.run(["git", "rev-parse", "--git-common-dir"],
                            capture_output=True, text=True, timeout=15)
        if ra.returncode == 0 and ra.stdout.strip():
            goc = Path(ra.stdout.strip()).resolve().parent / "secrets" / "app.env"
            da_thu.append(goc)
            if goc.is_file():
                return goc
    except (OSError, subprocess.SubprocessError):
        pass

    raise LoiMayCloud(
        "khong tim thay secrets/app.env. Da thu: "
        + " | ".join(str(p) for p in da_thu)
        + ". Truyen duong dan bang --env, hoac dat RUNPOD_API_KEY san.")


def nap_env(duong_dan: Path) -> None:
    """Nạp `app.env` vào `os.environ`.

    `utf-8-sig` để một BOM lỡ tay không làm hỏng dòng đầu — `CLAUDE.md` quy tắc 1
    kể chuyện BOM đã từng làm sập production ở kho này.

    Dùng `setdefault`: biến đã đặt sẵn trong môi trường **thắng** tệp, để chạy thử
    với khoá khác không phải sửa tệp bí mật.
    """
    for tho in duong_dan.read_text(encoding="utf-8-sig").splitlines():
        dong = tho.strip()
        if not dong or dong.startswith("#") or "=" not in dong:
            continue
        ten, gia_tri = dong.split("=", 1)
        os.environ.setdefault(ten.strip(), gia_tri.strip())


@dataclass
class MayCloud:
    """`goi(method, url, json=None, timeout=...) -> (status, body)` tiêm vào.

    Tiêm được là để phép kiểm chạy trên máy A **không cần mạng**, không cần tài
    khoản, không tiêu một xu.
    """

    goi: Callable[..., tuple]
    timeout_s: float = 30.0

    def rest(self, method: str, duong_dan: str,
             than: Optional[dict] = None) -> Any:
        ma, body = self._goi(method, REST_GOC + duong_dan, than)
        # 🔴 `204 No Content` la THANH CONG. RunPod tra no cho `DELETE /pods/{id}`,
        #    va ban truoc coi no la loi — nen bon lan xoa pod THANH CONG deu in ra
        #    "loi xoa". Bao thanh cong thanh that bai nguy hiem theo huong rieng
        #    cua no: no day nguoi ta di thu lai mot viec DA XONG, va voi mot thao
        #    tac destructive thi lan thu lai ay nham vao thu khac.
        if ma not in (200, 201, 202, 204):
            raise LoiMayCloud(f"{method} {duong_dan} tra {ma}: {_gon(body)}")
        return body

    def graphql(self, query: str) -> dict:
        ma, body = self._goi("POST", GRAPHQL_GOC, {"query": query})
        if ma != 200:
            raise LoiMayCloud(f"graphql tra {ma}: {_gon(body)}")
        if isinstance(body, dict) and body.get("errors"):
            raise LoiMayCloud(f"graphql loi: {_gon(body['errors'])}")
        return (body or {}).get("data") or {}

    def so_du_usd(self) -> float:
        """Số dư tài khoản. GraphQL — REST **không có** đường nào cho việc này."""
        d = self.graphql("query{myself{clientBalance}}")
        try:
            return float(d["myself"]["clientBalance"])
        except (KeyError, TypeError, ValueError) as e:
            raise LoiMayCloud(f"than clientBalance la: {_gon(d)}") from e

    def _goi(self, method: str, url: str, than: Optional[dict]) -> tuple:
        try:
            return self.goi(method, url, json=than, timeout=self.timeout_s)
        except Exception as e:  # noqa: BLE001
            # Mạng đứt, DNS hỏng, nhà cung cấp 5xx — đều là "hỏng thật", nhưng
            # KHÔNG được lọt ra dạng ngoại lệ lạ làm worker chết.
            raise LoiMayCloud(f"{method} {url}: {type(e).__name__}: {e}") from e


def _gon(than: Any) -> str:
    return str(than)[:200]


def tao_client() -> MayCloud:
    """`MayCloud` gắn sẵn khoá từ môi trường. Gọi `nap_env` trước nếu cần."""
    khoa = os.environ.get("RUNPOD_API_KEY", "").strip()
    if not khoa:
        raise LoiMayCloud(
            "Thieu RUNPOD_API_KEY. Dat bien moi truong, hoac nap secrets/app.env "
            "bang nap_env().")
    import httpx  # noqa: PLC0415

    def goi(method, url, json=None, timeout=30.0):
        r = httpx.request(
            method, url, json=json, timeout=timeout,
            headers={"Authorization": f"Bearer {khoa}",
                     "Content-Type": "application/json"},
        )
        try:
            return r.status_code, r.json()
        except ValueError:
            return r.status_code, r.text

    return MayCloud(goi=goi)
