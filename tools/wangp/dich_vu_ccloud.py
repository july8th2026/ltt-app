"""Service mỏng chạy TRÊN C-CLOUD — dịch các đường HTTP của LTT sang `WanGPSession`.

⭐ Vì sao cần nó: `shared/api.py` của WanGP là API **trong tiến trình**. Gọi qua
   mạng không được. Đây là mảnh nối duy nhất, và nó **mỏng có chủ đích**:

     · KHONG chuan hoa tham so   -> WanGP da lam (apply_media_flag_defaults,
                                     apply_video_length_duration)
     · KHONG chon model          -> LTT gui profile da duyet
     · KHONG biet nguoi dung/tien -> A-CONTROL giu
     · KHONG luu tru ben          -> tep o day la TAM

⛔ Chạy sau lớp xác thực. Khoá so khớp bằng `secrets.compare_digest` để không
   rò rỉ qua thời gian so sánh.

⛔ `init()` chỉ gọi được **một lần mỗi tiến trình** (`P01-D-13`) ⇒ một tiến trình
   phục vụ **đúng một cấu hình**. Muốn hai cấu hình thì hai tiến trình.

Chạy:
    /data/env311/bin/python -m uvicorn dich_vu_ccloud:app --host 0.0.0.0 --port 8888

⛔ **8888, không phải 8188.** Cổng phải nằm trong danh sách pod ĐÃ MỞ lúc tạo;
   pod hien tai (`s6bbn2cip61wo3`) khai `ports: ['8888/http', '22/tcp']`. Nghe ở cổng
   không khai thì dịch vụ vẫn chạy, log vẫn sạch, và máy A vẫn **không gọi tới
   được** — một kiểu hỏng không để lại dấu vết ở phía máy chủ. Đường công khai
   RunPod dựng theo khuôn `https://<pod-id>-<cong>.proxy.runpod.net`.
"""
from __future__ import annotations

import contextlib
import os
import secrets
import threading
import time
from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI, Header, HTTPException, Request

KHO_WANGP = Path(os.environ.get("LTTV_WANGP_ROOT", "/data/Wan2GP"))
KHOA = (os.environ.get("LTTV_WANGP_KEY") or "").strip()
#: Hồ sơ bộ nhớ. **1** = model đang dùng trọn trong VRAM + model khác trú ở
#: RAM để luân chuyển nhanh (`HighRAM_HighVRAM` trong `mmgp`). Máy đo được
#: 85 GB VRAM + 251 GB RAM ⇒ dư cả hai cột. Xem `P01-D-15`.
PROFILE = os.environ.get("LTTV_PROFILE", "1")
ATTENTION = os.environ.get("LTTV_ATTENTION", "sage2")


@contextlib.asynccontextmanager
async def _vong_doi(_app: "FastAPI"):
    """Hâm nóng model ngay khi dịch vụ lên — xem `_ham_nong_nen`.

    Dùng `lifespan` chứ không `@app.on_event("startup")`: FastAPI đã phế bỏ
    `on_event`, và một cảnh báo phế bỏ trong mã mới là nợ sinh ra lúc viết.
    """
    threading.Thread(target=_ham_nong_nen, daemon=True).start()
    yield


app = FastAPI(title="LTT ↔ WanGP bridge", lifespan=_vong_doi)

_khoa_phien = threading.Lock()
_phien: Any = None
#: job_id -> {"job": SessionJob, "tien_do": dict, "bat_dau": float}
_JOB: dict[str, dict] = {}


#: Tên header mang khoá. Dùng header thay vì thân yêu cầu để **đường `GET`
#: cũng kiểm được** — ba đường đọc (`progress`, `result`, `tai`) trước đây
#: không đòi khoá, và cộng với `job_id` đoán được thì đó là một đường tải
#: video của người khác mà không cần khoá nào.
HEADER_KHOA = "X-LTTV-Key"


_SO_NGUYEN = frozenset({"limit", "offset"})


def _loc_tu_query(request: "Request") -> dict:
    """Doi query string thanh bo loc cho `list_model_metadata`.

    ⭐ Dat RIENG chu khong nhet vao `tra_cuu_model`: bon duong tra cuu phai
       thuan chuyen tiep de `test_739` doc AST xac nhan duoc dieu do. Phep bien
       doi nao can thiet thi dung o day, noi no NHIN THAY duoc.

    Tham so lap lai (`?inputs=image&inputs=video`) thanh danh sach — `docs_API.md`
    noi nhieu gia tri la phep HOAC.
    """
    ra: dict = {}
    for khoa in request.query_params.keys():
        gia_tri = request.query_params.getlist(khoa)
        v = gia_tri if len(gia_tri) > 1 else gia_tri[0]
        ra[khoa] = int(v) if khoa in _SO_NGUYEN and isinstance(v, str) else v
    return ra


def sinh_job_id() -> str:
    """`job_id` sinh bằng CSPRNG.

    ⛔ Bản đầu dùng `f"j{int(time.time()*1000)}{len(_JOB)}"` — đoán ra được
       trong vài lượt thử vì nó chỉ là đồng hồ cộng một bộ đếm.
    """
    return "j" + secrets.token_urlsafe(16)


def _kiem_khoa(khoa: str) -> None:
    if not KHOA:
        raise HTTPException(status_code=500, detail="server missing LTTV_WANGP_KEY")
    if not secrets.compare_digest(khoa or "", KHOA):
        raise HTTPException(status_code=401, detail="bad key")


#: Lỗi lúc hâm nóng, giữ lại để `/health` nói ra thay vì im lặng.
_loi_ham: str = ""


def _lay_phien():
    """Một `WanGPSession` ấm cho cả tiến trình. `init()` chỉ gọi được một lần."""
    global _phien
    with _khoa_phien:
        if _phien is None:
            import sys

            sys.path.insert(0, str(KHO_WANGP))
            os.chdir(KHO_WANGP)
            from shared.api import init

            cli = ["--profile", PROFILE, "--attention", ATTENTION]
            # `--compile`: co trong `run-docker-cuda-deb.sh` chinh chu cua WanGP
            # va trong vi du "Best Performance" cua `docs/CLI.md:225`.
            if os.environ.get("LTTV_COMPILE", "0") == "1":
                cli.append("--compile")
            _phien = init(root=KHO_WANGP, cli_args=cli)
        return _phien


def _ham_nong_nen() -> None:
    """Nạp model NGAY KHI dịch vụ lên, ở một luồng nền.

    🔴 Bản đầu nạp model **lười** — lần `/submit` đầu tiên gọi `_lay_phien()`.
       Nó hỏng theo ba đường cùng lúc:

         1. người dùng ĐẦU TIÊN trả toàn bộ độ trễ nạp model;
         2. proxy RunPod (Cloudflare) có trần thời gian riêng, nên nâng timeout
            phía client **không** cứu được — yêu cầu chết ở giữa đường;
         3. `/health` đã biết sự thật (`san_sang: false`) mà không ai dùng.

       Đo 06/09: `POST /submit` timeout ở 60 giây, log phía dịch vụ **không có
       dòng nào** cho `/submit` — vì uvicorn chỉ ghi khi phản hồi đã gửi.

    ⭐ Đây cũng là cách WanGP tự làm: server của nó nạp model lúc khởi động,
       không đợi lượt sinh đầu tiên.
    """
    global _loi_ham
    try:
        _lay_phien()
    except Exception as e:  # noqa: BLE001 — ghi lai, khong nuot
        _loi_ham = f"{type(e).__name__}: {e}"


@app.get("/health")
def health() -> dict:
    """Sẵn sàng chưa — và **chạy đúng bản nào**.

    Trả `wangp_sha` để A-CONTROL đối chiếu với SHA mà hồ sơ neo vào. Lệch nhau
    nghĩa là tham số đang được diễn giải bởi một engine khác bản.
    """
    import subprocess

    try:
        sha = subprocess.run(["git", "-C", str(KHO_WANGP), "rev-parse", "HEAD"],
                             capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception as e:  # noqa: BLE001
        sha = f"khong-doc-duoc:{type(e).__name__}"
    return {"ok": True, "wangp_sha": sha, "profile": PROFILE,
            "attention": ATTENTION,
            # ⛔ `runtime_san_sang` KHONG co nghia la "sinh duoc ngay". `init()`
            #    chi dung runtime; TRONG SO chi nap o `submit_task` dau tien.
            #    Do 06/09: `/health` bao san sang, roi `/submit` van mat vai
            #    phut o "Loading Model ... / Pinning data of 'transformer' to
            #    reserved RAM" — profile 1 ghim ~30 GB tu o mang vao RAM.
            #    Ten cu la `san_sang`, va no HUA nhieu hon thu no biet.
            "runtime_san_sang": _phien is not None,
            "san_sang": _phien is not None,   # giu ten cu cho ban client dang chay
            "loi_ham_nong": _loi_ham}


# 🔴 `/metadata` da GO 08/09 (HM-7). No gom `list_model_defs()` + `get_model_
#    schema()` cua MOI model roi NHET LOI cua tung model vao chinh o cua no
#    (`{"loi": ...}`). Nghe nhu phong thu, thuc ra la GIAU HONG HOC VAO TRONG DU
#    LIEU: tang tren doc o ay nhu mot nang luc, va mot model hong trong giong
#    het mot model khong co nang luc.
#
#    Bon duong tra cuu tho o tren thay no. `test_739` doc AST de cam dung kieu
#    gom ay quay lai.

# ══════════════════════════════════════════════════════════════════════════
#  BON DUONG TRA CUU — chuyen tiep THO, khong bien doi
#
#  ⛔ Khong `if`, khong `for`, khong `try/except` nuot loi trong bon ham duoi.
#     Mot phep bien doi o day nam NGOAI tam voi cua gate: gate chay tren may A,
#     cau noi chay tren may thue. Sai o day thi khong luot kiem nao thay, va no
#     chi lo ra khi co nguoi dung that. `test_739` doc AST de canh dieu do.
#
#  ⭐ Bon duong nay KHONG nhan mot ma tran nao — chung doc ban khai JSON va quet
#     he tep. Nen chung chay duoc CA KHI stack CUDA dang hong, va do la ly do
#     HM-7 khong phai cho HM-9.
# ══════════════════════════════════════════════════════════════════════════

@app.get("/model")
def tra_cuu_model(request: Request, x_lttv_key: str = Header(default="")) -> dict:
    """`list_model_metadata(**loc)` — nguyen van."""
    _kiem_khoa(x_lttv_key)
    return {"model": _lay_phien().list_model_metadata(**_loc_tu_query(request))}


@app.get("/model/{model_type}/so-do")
def tra_cuu_so_do(model_type: str, x_lttv_key: str = Header(default="")) -> dict:
    """`get_model_schema(model_type)` — nguyen van."""
    _kiem_khoa(x_lttv_key)
    return {"so_do": _lay_phien().get_model_schema(model_type)}


@app.get("/model/{model_type}/mac-dinh")
def tra_cuu_mac_dinh(model_type: str, x_lttv_key: str = Header(default="")) -> dict:
    """`get_default_settings(model_type)` — nguyen van."""
    _kiem_khoa(x_lttv_key)
    return {"mac_dinh": _lay_phien().get_default_settings(model_type)}


@app.get("/model/{model_type}/kha-dung")
def tra_cuu_kha_dung(model_type: str, x_lttv_key: str = Header(default="")) -> dict:
    """`get_model_availability(model_type)` — nguyen van."""
    _kiem_khoa(x_lttv_key)
    return {"kha_dung": _lay_phien().get_model_availability(model_type)}


@app.post("/nap_media")
async def nap_media(request: Request, x_lttv_key: str = Header(default=""),
                    duoi: str = "png") -> dict:
    """Nhận **byte** của một tệp media, ghi ra đĩa pod, trả **đường dẫn tuyệt đối**.

    ⭐ Vì sao thao tác này bắt buộc phải có, khác với `/hau_ky` đã bỏ:
       `docs/API.md` §*Accepted Input Shapes* cho biết mọi đầu vào media của
       WanGP là **đường dẫn tệp trên chính máy chạy nó**. Không có dạng URL,
       không có dạng base64. Ảnh của người dùng nằm ở R2 phía LTT, nên **không
       có đường nào khác** để nó tới được model.

    ⛔ Tệp ở đây là **TẠM**, cùng vòng đời với tệp kết quả: `/cleanup` xoá nó.
       Ổ container biến mất khi xoá pod, nên đừng coi đây là kho.
    """
    _kiem_khoa(x_lttv_key)
    du_lieu = await request.body()
    if not du_lieu:
        raise HTTPException(status_code=400, detail="empty body")
    if len(du_lieu) > 200 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="media too large")
    an_toan = "".join(c for c in (duoi or "bin") if c.isalnum())[:8] or "bin"
    thu_muc = Path("/tmp/lttv_media")
    thu_muc.mkdir(parents=True, exist_ok=True)
    tep = thu_muc / f"{secrets.token_hex(16)}.{an_toan}"
    tep.write_bytes(du_lieu)
    return {"duong": str(tep), "byte": len(du_lieu)}


@app.post("/submit")
def submit(than: dict = Body(...)) -> dict:
    _kiem_khoa(str(than.get("khoa") or ""))
    settings = than.get("settings")
    if not isinstance(settings, dict) or not settings:
        raise HTTPException(status_code=400, detail="missing settings")

    # ⛔ Chua am thi TU CHOI NGAY, dung cho. Mot yeu cau treo cho toi khi proxy
    #    cat la mot that bai KHONG PHAN BIET DUOC voi may chet — LTT khong biet
    #    nen thu lai hay bao hong. 503 noi ro: chua san sang, thu lai sau.
    if _phien is None:
        raise HTTPException(
            status_code=503,
            detail=("WanGP session is still loading" if not _loi_ham
                    else f"WanGP session failed to load: {_loi_ham}"),
            headers={"Retry-After": "60"},
        )

    s = _lay_phien()
    job = s.submit_task(settings)          # ⛔ nguyen van — khong sua gi
    jid = sinh_job_id()
    _JOB[jid] = {"job": job, "tien_do": {}, "bat_dau": time.time()}

    def _theo_doi() -> None:
        """Rút sự kiện để `/progress` có cái trả. Không diễn giải lại."""
        try:
            for ev in job.events.iter(timeout=0.5):
                if getattr(ev, "kind", "") != "progress":
                    continue
                d = getattr(ev, "data", None)
                _JOB[jid]["tien_do"] = {
                    "phase": getattr(d, "phase", None),
                    "current_step": getattr(d, "current_step", None),
                    "total_steps": getattr(d, "total_steps", None),
                }
        except Exception as e:  # noqa: BLE001
            _JOB[jid]["tien_do"] = {"loi_theo_doi": f"{type(e).__name__}: {e}"}
        finally:
            # 🔑 Vong `for` tren chi thoat khi luong su kien DONG — xem
            #    `shared/api.py:379`: `iter()` gap `None` thi kiem `_closed`,
            #    het gio thi `continue`. Nen toi day la job DA XONG.
            #
            # ⭐ Vi sao can co nay: `/progress` truoc do khong co cach nao noi
            #    "xong", nen phia LTT phai goi `/result` (chan-cho ~20 phut) de
            #    biet — va no chet vi timeout socket 30 giay. Mot co boolean o
            #    day doi mot cuoc goi 20 phut thanh mot cuoc goi vai mili-giay.
            _JOB[jid].setdefault("tien_do", {})
            _JOB[jid]["tien_do"]["xong"] = True

    threading.Thread(target=_theo_doi, daemon=True).start()
    return {"job_id": jid}


@app.get("/progress/{job_id}")
def progress(job_id: str, x_lttv_key: str = Header(default="")) -> dict:
    _kiem_khoa(x_lttv_key)
    m = _JOB.get(job_id)
    if m is None:
        raise HTTPException(status_code=404, detail="unknown job")
    ra = dict(m["tien_do"])
    ra["giay_da_chay"] = round(time.time() - m["bat_dau"], 1)
    # Nguon thu HAI cho cung mot su that: hoi thang luong su kien. Neu luong da
    # dong ma luong theo doi chua kip dat co thi ta van tra loi dung.
    try:
        if getattr(m["job"].events, "closed", False):
            ra["xong"] = True
    except Exception as e:  # noqa: BLE001
        # Hoi mot thuoc tinh khong duoc lam vo mot duong doc trang thai — nhung
        # cung KHONG duoc im. Nguon thu nhat (co trong `finally`) van dung.
        ra["loi_hoi_closed"] = f"{type(e).__name__}: {e}"
    return ra


@app.post("/cancel/{job_id}")
def cancel(job_id: str, than: dict = Body(default={})) -> dict:
    _kiem_khoa(str(than.get("khoa") or ""))
    m = _JOB.get(job_id)
    if m is None:
        raise HTTPException(status_code=404, detail="unknown job")
    m["job"].cancel()
    return {"cancelled": True}


@app.get("/result/{job_id}")
def result(job_id: str, x_lttv_key: str = Header(default="")) -> dict:
    """Chờ xong rồi trả. Huỷ trả `success=False` + một mục lỗi huỷ — đúng khuôn
    `docs/API.md`, và LTT phân biệt huỷ với hỏng bằng chính mục đó."""
    _kiem_khoa(x_lttv_key)
    m = _JOB.get(job_id)
    if m is None:
        raise HTTPException(status_code=404, detail="unknown job")
    kq = m["job"].result()
    return {
        "success": bool(getattr(kq, "success", False)),
        "generated_files": [str(x) for x in (getattr(kq, "generated_files", []) or [])],
        "errors": [str(getattr(e, "message", e)) for e in (getattr(kq, "errors", []) or [])],
        # 🔴 `huy` den tu CHINH TRUONG cua WanGP (`GenerationResult.cancelled`),
        #    khong de LTT do chuoi "cancelled" trong thong diep loi nua.
        #    Phan biet huy/hong la mot phep phan biet VE TIEN — huy thi hoan
        #    phan chua dung, hong thi khong tru. Dat no tren mot chuoi cua
        #    thuong nguon nghia la mot lan doi cach dien dat o WanGP se lang le
        #    doi cach tinh tien o day, va khong test nao thay.
        "huy": bool(getattr(kq, "cancelled", False)),
        "giay_da_chay": round(time.time() - m["bat_dau"], 1),
    }


@app.get("/tai/{job_id}/{chi_so}")
def tai_ve(job_id: str, chi_so: int, x_lttv_key: str = Header(default="")):
    """Trả byte của tệp thứ `chi_so`. LTT kéo về rồi đẩy lên R2."""
    from fastapi.responses import FileResponse

    _kiem_khoa(x_lttv_key)
    m = _JOB.get(job_id)
    if m is None:
        raise HTTPException(status_code=404, detail="unknown job")
    tep = [str(x) for x in (getattr(m["job"].result(), "generated_files", []) or [])]
    if not 0 <= chi_so < len(tep):
        raise HTTPException(status_code=404, detail="no such file")
    return FileResponse(tep[chi_so], media_type="video/mp4")


@app.post("/cleanup/{job_id}")
def cleanup(job_id: str, than: dict = Body(default={})) -> dict:
    """Xoá tệp tạm **sau khi** LTT xác nhận đã có bản trong R2."""
    _kiem_khoa(str(than.get("khoa") or ""))
    m = _JOB.pop(job_id, None)
    if m is None:
        return {"da_don": 0}
    da = 0
    try:
        for x in (getattr(m["job"].result(), "generated_files", []) or []):
            p = Path(str(x))
            if p.is_file():
                p.unlink()
                da += 1
    except Exception as e:  # noqa: BLE001
        return {"da_don": da, "loi": f"{type(e).__name__}: {e}"}
    return {"da_don": da}
