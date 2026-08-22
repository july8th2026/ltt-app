"""Trang tải LTT Nexus + bản kê phiên bản (Model B, Q101: web = hướng dẫn/tải).

Công khai (không cần đăng nhập) — ai cũng tải được ứng dụng. `/nexus/version.json`
là nguồn CHUNG: trang này render từ nó, và client tự-update đọc chính nó.

Bản cài (zip/apk/dmg) được PHỤC VỤ THẲNG qua Tunnel từ `data/nexus_dist/` — thư
mục vận hành (cập nhật KHÔNG chạm), nên không cần R2 cho mấy file khiêm tốn này
(APK ~26MB, zip ~31MB — đều dưới trần 100MB của Cloudflare). Manifest trỏ URL
tương đối `/nexus/dl/<tên-file>`; đổi bản = thả file mới + sửa JSON, không deploy.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from xml.sax.saxutils import escape

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response

from platform_core.nexus import versions
from server.templating import templates

router = APIRouter(tags=["nexus-download"])

#: Chỉ cho tên file "hiền": chữ/số/dấu chấm/gạch — chặn '/', '\\', '..' tận gốc.
_SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")

#: Kiểu nội dung theo đuôi (để trình duyệt/thiết bị nhận đúng).
_CONTENT_TYPE = {
    ".apk": "application/vnd.android.package-archive",
    ".zip": "application/zip",
    ".dmg": "application/x-apple-diskimage",
    ".exe": "application/vnd.microsoft.portable-executable",
    ".sha256": "text/plain; charset=utf-8",
}


#: Định danh gói iOS — phải TRÙNG với `CFBundleIdentifier` trong IPA, không thì
#: iOS tải về rồi từ chối cài mà không nói vì sao.
IOS_BUNDLE_ID = "com.lttstudios.nexus"


def _dist_dir() -> Path:
    data = os.environ.get("LTT_DATA_DIR", "data")
    return Path(data) / "nexus_dist"


@router.get("/tai-xuong")
async def trang_tai(request: Request):
    """Trang tải: logo + 4 nền tảng (Windows/macOS/iOS/Android) + hướng dẫn."""
    m = versions.manifest()
    plats = [{"key": k, **m["platforms"][k]}
             for k in versions.PLATFORM_ORDER if k in m["platforms"]]
    return templates.TemplateResponse(
        request, "nexus_download.html",
        {"version": m.get("version", ""), "notes": m.get("notes", ""),
         "platforms": plats})


@router.get("/nexus/version.json")
async def version_json():
    """Bản kê phiên bản (JSON). Client tự-update GỌI cái này để so phiên bản.

    Cache ngắn ở biên: phải mới đủ để bản cập nhật tới người dùng nhanh, nhưng
    không cần no-store (nó là dữ liệu công khai, không nhạy cảm).
    """
    return JSONResponse(versions.manifest(),
                        headers={"Cache-Control": "public, max-age=300"})


@router.get("/nexus/ios-manifest.plist")
async def ios_manifest(request: Request):
    """Manifest cho cài-thẳng-từ-Safari (`itms-services`).

    iOS **không** cho cài file `.ipa` tải bằng Safari. Cách duy nhất cài từ web
    là giao thức `itms-services://`: Safari đọc file plist này, lấy URL của IPA
    trong đó rồi cài. Ba điều kiện của Apple, thiếu một là hỏng lặng lẽ:

    1. IPA phải **đã ký** bằng hồ sơ **Ad Hoc hoặc Enterprise** — hồ sơ
       *development* (Apple ID miễn phí) **không dùng được**;
    2. plist và IPA phải qua **HTTPS** hợp lệ (ta có sẵn, qua Cloudflare);
    3. link phải mở trong **Safari** — Chrome hay trình duyệt trong app im lặng
       không làm gì.

    404 khi manifest chưa khai `signed: true`: chưa có chữ ký phân phối thì đưa
    ra link `itms-services` chỉ tạo một nút bấm vào không có chuyện gì xảy ra.
    """
    m = versions.manifest()
    ios = m.get("platforms", {}).get("ios", {})
    if not ios.get("signed") or not ios.get("url"):
        raise HTTPException(status_code=404)

    goc = str(request.base_url).rstrip("/")
    url_ipa = ios["url"]
    if url_ipa.startswith("/"):
        url_ipa = goc + url_ipa
    plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>items</key>
  <array>
    <dict>
      <key>assets</key>
      <array>
        <dict>
          <key>kind</key><string>software-package</string>
          <key>url</key><string>{escape(url_ipa)}</string>
        </dict>
      </array>
      <key>metadata</key>
      <dict>
        <key>bundle-identifier</key><string>{escape(str(ios.get("bundle_id") or IOS_BUNDLE_ID))}</string>
        <key>bundle-version</key><string>{escape(str(m.get("version") or "1.0.0"))}</string>
        <key>kind</key><string>software</string>
        <key>title</key><string>{escape(str(ios.get("title") or "LTT Nexus"))}</string>
      </dict>
    </dict>
  </array>
</dict>
</plist>
"""
    return Response(content=plist, media_type="application/xml",
                    headers={"Cache-Control": "no-store"})


@router.api_route("/nexus/dl/{filename}", methods=["GET", "HEAD"])
async def tai_file(filename: str):
    """Phục vụ bản cài từ `data/nexus_dist/`. Tên file có version nên đặt cache
    dài + immutable (đổi bản = đổi tên = đổi URL). Chặn path traversal chặt."""
    if not _SAFE_NAME.match(filename):
        raise HTTPException(status_code=404)
    root = _dist_dir().resolve()
    target = (root / filename).resolve()
    # Phải nằm ĐÚNG trong thư mục dist (chống '..' và symlink thoát ra ngoài).
    if root not in target.parents or not target.is_file():
        raise HTTPException(status_code=404)
    ext = target.suffix.lower()
    return FileResponse(
        target,
        media_type=_CONTENT_TYPE.get(ext, "application/octet-stream"),
        filename=filename,
        headers={"Cache-Control": "public, max-age=31536000, immutable"})
