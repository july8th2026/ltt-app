"""Tài liệu API **công khai** + đường tải công cụ và SDK.

🔴 VÌ SAO MODULE NÀY TỒN TẠI — ĐO 25/08 TRÊN PRODUCTION.

   Cả 18 trang của cổng lập trình viên (`server/templates/dev_*.html`) đều nằm
   sau `require_account`, nên một người **đang cân nhắc** không đọc được một dòng
   hướng dẫn tích hợp nào trước khi tạo tài khoản:

       /developers  /developers/docs  /developers/cli  /developers/quickstart
       -> 303 ve /login

   Đó là thứ tự ngược, và dự án đã học đúng bài này một lần: trang giá cũ cũng
   nằm sau cổng đăng nhập, được tách ra thành `/gia-api` công khai. Bài học đó
   chưa được áp cho phần còn lại — module này áp nốt.

⛔ VÀ HAI THỨ HOÀN TOÀN KHÔNG LẤY ĐƯỢC:

   * `dev_docs.html` liệt kê cho khách các **đường dẫn tệp trong kho mã của ta**
     (`docs/PUBLIC_API/…`, `sdk/python/…`). Khách không có kho mã.
   * Công cụ cắm `.exe` **không được nhắc ở đâu** trên site và không có route
     nào phục vụ nó. Một công cụ không tải được thì chưa tồn tại.

⭐ RANH GIỚI CÔNG KHAI / RIÊNG TƯ, và nó rất rõ: **thứ giúp người ta quyết định
   mua thì công khai; thứ gắn với một tài khoản thì sau đăng nhập.** Trang này
   giữ ranh giới đó — không có gì ở đây đọc dữ liệu của người dùng.
"""
from __future__ import annotations

import hashlib
import os
import pathlib
import re

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse

from server.templating import templates

router = APIRouter(tags=["tai-lieu-api"])

#: Gốc kho mã đang chạy — để tìm `sdk/`. KHÔNG dùng `parents[n]` đếm tay: đổi
#: chỗ file là sai lặng lẽ (trang vẫn 200, chỉ là vỏ trống). Neo bằng một mốc
#: chắc chắn có ở gốc.
_GOC = pathlib.Path(__file__).resolve().parent.parent.parent


def _thu_muc_ban_phat() -> pathlib.Path:
    """Nơi đặt bộ cài đã dựng.

    ⭐ Nằm trong `data/` **có chủ ý**: `setup/2-cai-dat.ps1` loại trừ `build` khi
       chép, và `data/` là thư mục vận hành mà cập nhật **không chạm tới**. Nên
       phát hành một bản mới = thả tệp vào đó, **không cần deploy** — đúng cách
       `data/nexus_dist/` đã làm và đã chạy thật.
    """
    return pathlib.Path(os.environ.get("LTT_DATA_DIR", "data")) / "api_dist"


#: Tên tệp bộ cài: `LTTStudios-CamCLI-Setup-<phien ban>.exe`.
_MAU_BO_CAI = re.compile(r"^LTTStudios-CamCLI-Setup-([0-9][0-9.]*)\.exe$")
_MAU_GOI_BAT = re.compile(r"^LTTStudios-CamCLI-BAT-([0-9][0-9.]*)\.zip$")


def _goi_moi_nhat(mau: re.Pattern) -> dict | None:
    """Artifact mới nhất khớp mẫu, hoặc `None` nếu chưa phát hành.

    ⚠️ **Dò theo thư mục, không phải theo một bản kê phải sửa tay.** Một bản kê
       là một bản sao thứ hai của sự thật, và nó sẽ lệch đúng vào hôm ta quên.
       Ở đây sự thật chỉ có một chỗ: tệp nằm trong thư mục.
    """
    thu_muc = _thu_muc_ban_phat()
    if not thu_muc.is_dir():
        return None
    thay = []
    for tep in thu_muc.iterdir():
        m = mau.match(tep.name)
        if m and tep.is_file():
            thay.append((tuple(int(x) for x in m.group(1).split(".") if x.isdigit()),
                         m.group(1), tep))
    if not thay:
        return None
    _, phien_ban, tep = max(thay)
    return {"ten": tep.name, "phien_ban": phien_ban,
            "kich_thuoc_mb": round(tep.stat().st_size / (1024 * 1024), 1),
            "sha256": _bam(tep), "duong": tep}


def bo_cai_moi_nhat() -> dict | None:
    return _goi_moi_nhat(_MAU_BO_CAI)


def goi_bat_moi_nhat() -> dict | None:
    return _goi_moi_nhat(_MAU_GOI_BAT)


#: Băm đã tính, theo (đường dẫn, kích thước, thời điểm sửa). Băm một tệp 25 MB
#: mỗi lần tải trang là lãng phí; băm **một bản kê chép tay** thì sai khi tệp đổi.
_BAM_DA_TINH: dict = {}


def _bam(tep: pathlib.Path) -> str:
    """SHA-256 của chính tệp đang phục vụ.

    ⭐ Tính từ tệp chứ không chép từ đâu cả. Không ký số thì đây là **thứ duy
       nhất** khách dùng để kiểm tệp tải về đúng là của ta — nên nó tuyệt đối
       không được là một chuỗi gõ tay ở chỗ khác.
    """
    st = tep.stat()
    khoa = (str(tep), st.st_size, st.st_mtime_ns)
    if khoa not in _BAM_DA_TINH:
        h = hashlib.sha256()
        with tep.open("rb") as f:
            for khoi in iter(lambda: f.read(1024 * 1024), b""):
                h.update(khoi)
        _BAM_DA_TINH.clear()          # chỉ giữ bản mới nhất, không nuôi bộ nhớ
        _BAM_DA_TINH[khoa] = h.hexdigest()
    return _BAM_DA_TINH[khoa]


#: Những thứ khách được tải, khai **tường minh**.
#:
#: ⛔ Danh sách trắng chứ không phải ghép đường dẫn từ tham số. Một `..` lọt vào
#:    là đọc được cả máy chủ; danh sách trắng làm điều đó **không thể**, chứ
#:    không phải "khó".
GOI_TAI: dict = {
    "ltt_public_api.py": (
        "sdk/python/ltt_public_api.py", "text/x-python; charset=utf-8",
        "SDK Python — mot tep, khong phu thuoc ngoai"),
    "ltt-public-api.ts": (
        "sdk/typescript/ltt-public-api.ts", "text/plain; charset=utf-8",
        "SDK TypeScript — mot tep, khong phu thuoc ngoai"),
    "ltt_cai_dat_cli.py": (
        "sdk/ltt_cai_dat_cli.py", "text/x-python; charset=utf-8",
        "Script cai dat cau hinh CLI (chay tren Windows, macOS, Linux)"),
    "ltt-public-api.postman_collection.json": (
        "sdk/postman/ltt-public-api.postman_collection.json", "application/json",
        "Postman collection — SINH tu OpenAPI"),
    "ltt-public-api.postman_environment.json": (
        "sdk/postman/ltt-public-api.postman_environment.json", "application/json",
        "Postman environment"),
}


def _boi_canh_cam(request: Request) -> dict:
    """Biến cho `_cam_chon.html`. **Cùng nguồn** với `/developers/cli`.

    ⚠️ Đừng gõ lại giá trị nào ở đây. Mọi đoạn cấu hình đến từ `examples.py` —
       cùng module mà công cụ `.exe` và trang trong bảng điều khiển dùng. Ba nơi
       cùng một nguồn là ba nơi không thể lệch nhau.
    """
    from platform_core.public_api import examples

    goc = str(request.base_url).rstrip("/")
    return {
        "base_url": goc,
        "codex_config": examples.codex_config(goc),
        "codex_profile": examples.codex_profile(),
        "claude_env": examples.claude_code_env(goc),
        "claude_settings": examples.claude_code_settings(goc),
        "desktop": examples.claude_desktop_steps(goc),
        "vscode_claude": examples.vscode_claude_settings(goc),
        "vscode_codex": examples.vscode_codex_config(goc),
        "vscode_bay": examples.VSCODE_BAY,
        "desktop_reg": examples.claude_desktop_registry(goc),
        # Ho so tung be mat — thu o chon dung de ve lai ca trang.
        "be_mat": examples.be_mat_cam(goc),
        "bay": examples.CLI_BAY,
        "model": examples.CLI_MODEL,
        "model_desktop": examples.DESKTOP_MODEL,
        "env_key": examples.ENV_API_KEY,
        # Ba cua cua `text.chat`. CONG KHAI co chu y — xem `examples.BA_CUA`.
        "ba_cua": examples.BA_CUA,
    }


@router.get("/huong-dan", response_class=HTMLResponse)
def trang_huong_dan(request: Request):
    """Hướng dẫn cắm — **công khai**, không cần đăng nhập."""
    from platform_core.public_api import examples

    ctx = _boi_canh_cam(request)
    ctx["curl_chat"] = examples.curl_chat()
    # Mục tạo ảnh — cùng nguồn `examples.py` như mọi đoạn khác, nên nó không thể
    # lệch khỏi thứ máy chủ nhận.
    ctx["curl_anh"] = examples.curl_anh_ba_buoc()
    ctx["anh_che_do"] = examples.ANH_CHE_DO_MA
    ctx["bo_cai"] = bo_cai_moi_nhat()
    ctx["goi_bat"] = goi_bat_moi_nhat()
    ctx["goi_tai"] = [{"ten": t, "mo_ta": v[2]} for t, v in GOI_TAI.items()]
    return templates.TemplateResponse(request, "huong_dan.html", ctx)


@router.get("/huong-dan/cong-cu", response_class=HTMLResponse)
def trang_cong_cu(request: Request):
    """Trang công cụ cắm: nó làm gì, chạm vào đâu, gỡ ra thế nào, tải ở đâu."""
    from platform_core.public_api import examples

    bo_cai = bo_cai_moi_nhat()
    goi_bat = goi_bat_moi_nhat()
    return templates.TemplateResponse(
        request, "huong_dan_cong_cu.html",
        {"bo_cai": bo_cai, "goi_bat": goi_bat,
         "model": examples.CLI_MODEL,
         "model_desktop": examples.DESKTOP_MODEL,
         "base_url": str(request.base_url).rstrip("/")})


@router.get("/tai/cong-cu-cam")
def tai_cong_cu():
    """Bộ cài công cụ cắm. Một đường dẫn **cố định**, tệp bên dưới đổi theo bản.

    ⭐ URL không mang số phiên bản **có chủ ý**: tài liệu, ảnh chụp màn hình và
       tin nhắn hỗ trợ đều trỏ vào đây, và chúng không nên hỏng mỗi lần phát hành.
    """
    bo_cai = bo_cai_moi_nhat()
    if bo_cai is None:
        # 503 chứ không phải 404: đường dẫn này ĐÚNG, chỉ là chưa có bản nào
        # được thả vào thư mục phát hành. Hai chuyện đó cần phân biệt được từ log.
        raise HTTPException(status_code=503,
                            detail="Chua co ban cai nao duoc phat hanh.")
    return FileResponse(
        bo_cai["duong"], filename=bo_cai["ten"],
        media_type="application/vnd.microsoft.portable-executable",
        headers={"Cache-Control": "public, max-age=300"})


@router.get("/tai/cong-cu-cam-bat")
def tai_cong_cu_bat():
    """Gói ZIP console + BAT, không GUI; launcher tự xin Administrator."""
    goi = goi_bat_moi_nhat()
    if goi is None:
        raise HTTPException(status_code=503,
                            detail="Chua co goi BAT nao duoc phat hanh.")
    return FileResponse(
        goi["duong"], filename=goi["ten"], media_type="application/zip",
        headers={"Cache-Control": "public, max-age=300"})


@router.get("/tai/{ten}")
def tai_goi(ten: str):
    """SDK và script — phục vụ thẳng từ kho mã đang chạy."""
    muc = GOI_TAI.get(ten)
    if muc is None:
        raise HTTPException(status_code=404, detail="Khong co goi nay.")
    duong = _GOC / muc[0]
    if not duong.is_file():
        raise HTTPException(status_code=404, detail="Khong co goi nay.")
    return FileResponse(duong, filename=ten, media_type=muc[1],
                        headers={"Cache-Control": "public, max-age=300"})
