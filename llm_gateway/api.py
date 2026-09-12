"""
api.py — hợp đồng HTTP của cổng VLM.

    GET  /health                  phien ban · model dang mo · trong tai · thuong nguon
    GET  /v1/models               danh muc THAT SU dang mo (fail-closed)
    POST /v1/chat/completions     OpenAI Chat      — moi thu khac
    POST /v1/responses            OpenAI Responses — CODEX CLI (bat buoc giao thuc nay)
    POST /v1/messages             Anthropic        — CLAUDE CODE (ANTHROPIC_BASE_URL)

    GET  /v1/residency/trang_thai  su that do duoc cua 3090 (Dual-model 5.4b)
    POST /v1/residency/nha         nha DUNG mot model khoi VRAM
    POST /v1/residency/nap         nap lai model cu tru (chay o luong nen)

⭐ BA ĐƯỜNG `residency/*` LÀ **LỆNH**, KHÔNG PHẢI **QUYẾT ĐỊNH** (D01 B, TD-D10).
   Người quyết khi nào 3090 thuộc về LLM và khi nào thuộc về ảnh là **trọng tài
   residency ở máy A**. Cổng này thi hành và báo lại số đo. Đừng thêm một người
   quyết thứ hai ở đây — hai cơ chế cùng canh một card sẽ lệch nhau, và đó đúng
   là cặp trọng tài cũ (`don_dep` + `nhuong_card`) mà Task 5.4 vừa gỡ bỏ.

⭐ BA GIAO THỨC, MỘT ĐƯỜNG ỐNG. Codex chỉ nói Responses (từ 02/2026 nó bỏ hẳn lựa
   chọn `chat`); Claude Code chỉ nói Anthropic Messages. `llama-server` **nói được
   cả ba**, nên cổng này không dịch gì cả — nó chỉ **kiểm rồi chuyển tiếp**.

⛔ BẬN THÌ TRẢ **429**, KHÔNG PHẢI 5xx. Máy A phân biệt hai thứ này: 429 là trạng
   thái bình thường của một máy chia GPU với việc ảnh và việc video. Nếu máy A hiểu
   nhầm thành lỗi, `api_pool` sẽ cooldown rồi `disable` key `ltt_llm` sau 5
   lần — và một tối chạy video sẽ **tự tắt vĩnh viễn model nhà** (D-005).

⛔ KHÔNG TỰ ĐỔI SANG MODEL KHÁC khi bận. Cổng này chỉ biết model nhà. Việc "bận thì
   dùng đám mây" là **quyết định của máy A** (D-010), không phải của cổng.

⛔ KHÔNG PHÂN TÍCH RỒI DỰNG LẠI SSE. Xem `upstream.stream`.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable, Optional

from fastapi import Body, Depends, FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse, Response, StreamingResponse
from starlette.background import BackgroundTask

from . import __version__
from . import ngan_sach as NS
from .catalog import KhongCoModel, ModelSpec, lay, nap_catalog, ten_la
from .config import Config
from . import gpu_uuid as GPU
from . import residency as RES
from .gioi_han import GioiHan, boc_luong
from . import so_luot as SL
from .so_theo_model import SoTheoModel, token_dat_truoc
from .upstream import MA_DA_HUY, MA_HET_GIO
from .nhip_tim import boc_nhip_tim
from .dem import Dem, boc_do_ttft
from .to_tien import ToTien
from .tren_gpu import kiem as kiem_gpu
from .trong_tai import TrongTai

log = logging.getLogger("llm_gateway.api")

#: Đường thượng nguồn tương ứng mỗi đường của cổng. llama-server phơi đúng các
#: đường này, nên ánh xạ là một-đối-một.
DUONG = {
    "chat": "/v1/chat/completions",
    "responses": "/v1/responses",
    "messages": "/v1/messages",
}


def create_app(cfg: Config, upstream, *, trong_tai: Optional[TrongTai] = None,
               gioi_han: Optional[GioiHan] = None,
               so: Optional[SoTheoModel] = None,
               chay_nen: Optional[Callable[[Callable[[], None]], None]] = None,
               now=time.monotonic) -> FastAPI:
    app = FastAPI(title="LTT LLM Gateway", version=__version__)

    # Chup to tien MOT LAN o day, luc no chac chan con song. Sau khi vo boc
    # chet thi duong di len cay khong con nua -- do lai la muon. Xem bay #3
    # o `to_tien.py`.
    to_tien = ToTien()

    # So cong don theo nhom ket cuc. Chi cong don, khong giu noi dung.
    dem = Dem()

    # ── Sổ lượt đang bay: hủy được, và mỗi lượt một dòng (Dual-model 4.3) ────
    #
    # ⭐ MỘT SỔ CHO MỖI `create_app()`, không phải một biến module. Bộ test dựng
    #    nhiều app trong cùng tiến trình; một sổ dùng chung sẽ để lượt của app
    #    này hủy được bằng mã của app kia — xanh vì lý do sai.
    so_luot = SL.SoLuot()

    catalog: dict[str, ModelSpec] = nap_catalog(cfg.models_mo)
    la = ten_la(cfg.models_mo)
    if la:
        log.warning("LTT_LLM_MODELS co ten khong khop ho so nao: %s", ", ".join(la))

    # ⛔ TRỌNG TÀI NÀY KHÔNG CÒN HỎI ComfyUI, VÀ KHÔNG CÒN ĐỌC MỨC TẢI (5.4b).
    #    Cuộc tranh 3090 nay do **một** trọng tài residency ở máy A phân xử
    #    (D01 B); trong cửa sổ LLM, ComfyUI đã bị **dừng hẳn** (5.4a) nên một
    #    phép hỏi `/queue` hay một ngưỡng `utilization.gpu` ở đây chỉ còn sinh ra
    #    429 oan. Thứ còn lại là hai cái phanh thuần cơ học: RAM chủ và số tiến
    #    trình python đang tính trên card.
    tt = trong_tai if trong_tai is not None else TrongTai(
        ram_trong_toi_thieu_gb=cfg.ram_trong_toi_thieu_gb, bat=cfg.trong_tai_bat)

    # ── Sổ suất: MỘT SỔ CHO MỖI MODEL (Dual-model 4.2) ──────────────────────
    #
    # 🔴 MỘT SỔ CHUNG NÓI SAI THEO CẢ HAI CHIỀU. Hai model ở hai card: sổ chung
    #    báo "đầy" khi ba lượt đều nằm trên 3090 và 5060 Ti đang rảnh (⇒ 429 oan,
    #    và máy A đọc 429 là "bận" nên khách đi ra đám mây), rồi gộp hai bể KV
    #    khác cỡ thành một con số (⇒ 3090 nhận quá tay, KV cạn, llama.cpp huỷ
    #    **mọi** slot). Xem `so_theo_model.py`.
    #
    # ⭐ `gioi_han=` (một `GioiHan` trần) VẪN NHẬN ĐƯỢC, và nó gói thành sổ gộp.
    #    `test_258`/`test_363` tiêm nó để đo hàng rào và lưới thu hồi suất treo —
    #    những phép kiểm ấy không nói gì về hai model. Ép chúng dựng hai sổ là
    #    đổi thứ chúng đo; giữ cửa này là giữ nguyên phép đo của chúng.
    if so is not None:
        pass                                   # đã tiêm (test)
    elif gioi_han is not None:
        so = SoTheoModel.gop(gioi_han, tuple(catalog) or tuple(cfg.models_mo))
    else:
        so = SoTheoModel(
            tuple(catalog),
            max_dong_thoi=cfg.max_dong_thoi, rpm=cfg.rpm,
            # Bể mặc định của một model không khai = cửa sổ hồ sơ của nó.
            token_pool=0,
            dong_thoi_rieng=dict(cfg.dong_thoi_rieng),
            pool_rieng=dict(cfg.token_pool_rieng),
            san_vram_mb=dict(cfg.vram_trong_toi_thieu_mb),
            # lambda: `_vram_trong_cua_model` định nghĩa bên dưới, tên giải lúc
            # GỌI — cùng khuôn với `model_cua_ta_dang_chay` ở trên.
            doc_vram_trong=lambda m: _vram_trong_cua_model(m),
            now=now)

    #: Sổ kết quả của lượt `POST /v1/residency/nap` gần nhất. Một sổ cho mỗi
    #: `create_app()`, cùng lý do với `so_luot` ở trên.
    so_nap = RES.SoNap()

    def _chay_nen_that(viec: Callable[[], None]) -> None:
        threading.Thread(target=viec, name="residency-nap", daemon=True).start()

    #: Tiêm được để phép kiểm chạy thân lượt nạp **đồng bộ** — một luồng nền
    #: trong test là một cuộc đua, và một phép kiểm đua là một phép kiểm nói dối
    #: theo cả hai chiều.
    chay_nen = chay_nen or _chay_nen_that

    #: Nhớ tên hồ sơ đang nạp trong ít giây, để một phiên agent gửi liên tiếp
    #: không sinh một `/running` cho mỗi lượt.
    #:
    #: ⭐ 2 giây là đủ: thứ ta hỏi chỉ quyết định *đếm chính xác có rẻ không*.
    #:    Sai trong 2 giây thì hậu quả xấu nhất là một lần lùi về phép ước
    #:    (từ chối oan một yêu cầu lẽ ra vừa) hoặc một `/tokenize` bị llama-swap
    #:    trả lời bằng hồ sơ khác — cả hai đều không chạm tiền và không sai
    #:    chiều nguy hiểm.
    _nho_nap: dict = {"luc": None, "san": frozenset()}
    _TTL_NHO_NAP_S = 2.0
    _HET_GIO_HOI_NAP_S = 2.0

    def _ho_so_dang_nap(ten: str) -> bool:
        """Đúng **hồ sơ này** có đang nằm trong VRAM không.

        Câu hỏi ở đây là *"đếm token bằng `/tokenize` có RẺ không"*, và nó chỉ rẻ
        khi **đúng hồ sơ này** đã nạp: hỏi `/tokenize` cho một hồ sơ khác thì
        llama-swap sẽ ĐỔI model để phục vụ nó — tức đánh thức GPU, mất 2,5 phút,
        và làm đúng cái điều mà phép ước sinh ra để tránh.

        🔴 GIỮ CẢ **TẬP** HỒ SƠ SẴN SÀNG, KHÔNG PHẢI CÁI ĐẦU TIÊN. Bản cũ `break`
           ở hồ sơ `ready` đầu tiên rồi so bằng. Với **một** model điều đó đúng;
           từ Task 3.3 máy B giữ **hai** hồ sơ cùng lúc (`groups: swap:false`, đo
           12/09 L-17), nên cái thứ hai luôn bị trả lời "chưa nạp" — và mọi lượt
           của nó lặng lẽ lùi về phép ƯỚC dù `/tokenize` đang rẻ. Cùng khuôn lỗi
           L-17 §4: một phép hỏi không mang tên đối tượng chỉ đúng khi hệ thống
           có đúng một đối tượng.

        ⚠️ `timeout` 2 giây, KHÔNG phải 5. Lời gọi này nằm trên đường **từ chối**:
           nếu llama-swap chết thì bản cũ trả `413` tức thì, còn bản này sẽ chờ
           hết timeout trước khi từ chối. Năm giây cho một yêu cầu chắc chắn bị
           từ chối là một hồi quy; hai giây là cái giá tối thiểu còn đọc được.
        """
        luc = _nho_nap["luc"]
        if luc is not None and (now() - luc) < _TTL_NHO_NAP_S:
            return ten in _nho_nap["san"]
        bang = RES.models_dang_chay(upstream, timeout_s=_HET_GIO_HOI_NAP_S)
        if bang is None:
            return False
        san = frozenset(m for m, tr in bang.items() if tr == RES.SAN_SANG)
        _nho_nap["luc"] = now()
        _nho_nap["san"] = san
        return ten in san

    def _dem_token_that(ten: str, van: list) -> "int | None":
        """Số token THẬT của các đoạn văn bản, qua `/tokenize` của llama-server.

        Trả `None` khi không đếm được — hồ sơ chưa nạp, hoặc thượng nguồn không
        trả lời. `None` **không phải** 0: bên gọi phải lùi về phép ước, không
        được coi như một yêu cầu rỗng.

        ⭐ `/tokenize` KHÔNG chạy inference. Nó cần từ vựng của model đang nạp,
           không cần một lượt sinh. Đo 03/09: gọi hàng chục lần trên prompt
           130K–180K, không sinh một token nào.

        ⛔ MỘT LỜI GỌI CHO CẢ HỘI THOẠI, không phải một lời gọi mỗi đoạn. Nối
           bằng `chr(10)` rồi đếm một lần: `n` lời gọi cho `n` tin nhắn là `n`
           vòng loopback, và với một phiên agent thì `n` lên tới hàng trăm.
           Sai số của việc nối (vài token ranh giới) nhỏ hơn hai bậc so với
           chỗ `LE` đã chừa.

        🔴 ĐƯỜNG PHẢI LÀ `/upstream/<model>/tokenize`, KHÔNG PHẢI `/tokenize`.
           `llama-swap` định tuyến theo trường `model` **trong thân**; `/tokenize`
           không có trường đó nên nó trả **404**. Đo 03/09 trên máy B:

               POST /tokenize                        -> 404
               POST /upstream/qwen38-api/tokenize     -> 200 {"tokens":[...]}
               POST 127.0.0.1:8281/tokenize (thang)   -> 200

        ⛔ VÀ BẢN ĐẦU CỦA HÀM NÀY DÙNG `/tokenize`. Nó nhận 404, `ma != 200`,
           trả `None`, và cổng **lặng lẽ lùi về phép ước** — tức bản vá đã
           deploy lên production và **không làm gì cả**, không một dòng nào nói
           ra. Đúng lớp khuyết tật mà cả chương trình này đi sửa: một năng lực
           có, được nối dây, và im lặng không hoạt động.

        ⭐ Nên lần lùi bây giờ **kêu**. Phân biệt hai thứ khác hẳn nhau:
           *"chưa nạp nên không hỏi"* là đường bình thường, không log;
           *"đã hỏi mà thất bại"* là một khuyết tật, và nó phải ra log.
        """
        if not van:
            return None
        if not _ho_so_dang_nap(ten):
            return None                      # binh thuong: khong log
        ma, than = upstream.json(
            "POST", "/upstream/" + ten + "/tokenize",
            body={"content": chr(10).join(str(s) for s in van)},
            timeout=30.0)
        if ma != 200:
            log.warning("dem token that THAT BAI ma=%s model=%s - lui ve phep uoc "
                        "(neu thay dong nay lien tuc thi duong /tokenize da doi)",
                        ma, ten)
            return None
        try:
            import json as _json
            d = _json.loads(than or b"{}")
        except (ValueError, TypeError):
            return None
        toks = d.get("tokens")
        if not isinstance(toks, list):
            log.warning("dem token that: than khong co `tokens` (model=%s) - "
                        "lui ve phep uoc", ten)
            return None
        return len(toks)

    def auth(authorization: str = Header(default="")) -> None:
        if not cfg.token:
            return          # dev: chưa đặt token → không chặn (giống render_gateway)
        got = authorization.removeprefix("Bearer ").strip()
        if got != cfg.token:
            raise HTTPException(status_code=401, detail="token khong dung")

    # ── Đọc trạng thái ───────────────────────────────────────────────────────

    @app.get("/live")
    def live() -> dict:
        """Thăm dò SỐNG/CHẾT — **không cần bearer**, và cố ý không nói gì thêm.

        ⭐ VÌ SAO TÁCH KHỎI `/health`: `/health` trả danh sách model, trạng thái
           trọng tài, các trần — đó là thông tin vận hành và nó **phải** sau khoá.
           Nhưng một máy giám sát chỉ cần biết tiến trình còn thở, và bắt nó mang
           theo bí mật chỉ để hỏi câu đó là đặt bí mật vào một chỗ nữa.

        ⛔ KHÔNG thêm bất cứ thứ gì vào đây. Mỗi trường thêm vào là một thứ rò ra
           cho người chưa xác thực: model nào đang mở, máy có bận không, trần bao
           nhiêu — tất cả đều nói cho người ngoài biết hệ thống đang ở đâu.
        """
        return {"ok": True, "version": __version__}

    @app.get("/health/ready")
    def ready() -> Response:
        """SẴN SÀNG nhận lượt chưa — **fail-closed**, không cần bearer.

        🔴 KHÁC `/live` MỘT CHỮ VÀ CẢ CÔNG DỤNG. `/live` trả lời *"tiến trình còn
           thở không"*; câu đó xanh suốt sự cố 23/08 (CUDA hỏng, model bò trên
           CPU) và suốt cả ca một card rụng khỏi hệ thống. Từ 09/2026 cổng này
           phục vụ **hai** model trên **hai** card, nên "sẵn sàng" có một điều
           kiện cơ học mới: driver phải còn thấy **đủ** cả hai UUID.

        ⛔ THIẾU MỘT CARD ⇒ 503, và "không hỏi được `nvidia-smi`" cũng ⇒ 503. Hai
           thứ ấy trông giống nhau từ đây và đòi **cùng một** hành động: đừng đưa
           lượt mới vào cho tới khi có người xem. Đây là chốt **sẵn sàng** của
           dịch vụ, không phải chốt vào cửa của một yêu cầu — nó không làm lượt
           nào đang bay bị từ chối, và nó **không** giết gì cả.

        ⛔ KHÔNG thêm trường nào khác: cùng luật với `/live`, mỗi trường là một
           thứ rò ra cho người chưa xác thực. Chi tiết từng card nằm ở `/health`,
           sau khoá.
        """
        if not GPU.thay_du_hai_card():
            return JSONResponse(status_code=503,
                                content={"ok": False, "ly_do": "thieu_card"})
        return JSONResponse(status_code=200, content={"ok": True})

    #: 🔴 HAI Ô NHỚ RIÊNG, VÀ ĐÓ LÀ MỘT BẢN VÁ CHO CHÍNH BẢN ĐẦU CỦA TÔI.
    #:
    #:    Bản đầu nhớ **cả cụm** trong một ô. Hai giá trị ấy có vòng đời
    #:    khác hẳn nhau:
    #:
    #:      `swap`   bất biến khi tiến trình llama-swap còn sống
    #:      `engine` **phụ thuộc hồ sơ nào đang nằm trong VRAM**
    #:
    #: ⛔ Nên gộp chúng làm hỏng đúng ca thường gặp nhất: lượt `/health` đầu
    #:    tiên sau khi khởi động lại thì **chưa có model nào nạp** (đó là
    #:    trạng thái mặc định sau restart, và cũng là lúc máy giám sát hỏi
    #:    sớm nhất). `engine` = None được đóng băng cùng `swap`, và nó ở lại
    #:    None tới **hết đời tiến trình** — kể cả sau khi model đã nạp và
    #:    câu trả lời đã sẵn sàng.
    #:
    #: ⭐ Đúng lớp lỗi mà `to_tien.py` sinh ra để chống: một câu trả lời sai
    #:    được ghi nhớ, rồi mọi lượt hỏi sau đều nhận lại nó. Chỉ khác là
    #:    lần này tôi tự dựng lại nó trong lúc đi sửa nó.
    _nho_swap: dict = {"gia_tri": None}
    _nho_engine: dict = {"gia_tri": None}

    def _phien_ban_thuong_nguon() -> dict:
        """`llama-swap` đang chạy bản nào — và, nếu rẻ, engine build nào.

        🔴 VÌ SAO CHỐT NÀY TỒN TẠI. Ngày 09/09 tôi thử **bốn** đường độc lập để
           hỏi *"máy B đang chạy phần mềm phiên bản nào"*:

             1. `GET /health` của chính cổng    -> không có trường nào nói
             2. đọc tệp trong kho               -> không tệp nào ghi
             3. Nexus `command.run` trên máy B  -> bị chặn (đúng chính sách)
             4. Nexus `file.read` log máy B     -> bị chặn (đúng chính sách)

           Bốn đường, không đường nào trả lời. Thứ duy nhất còn lại là **bản
           thân cổng tự khai**, vì nó là tiến trình duy nhất nói chuyện được
           với llama-swap qua loopback.

        ⭐ `GET /api/version` **RẺ VÀ AN TOÀN**: nó đọc `BuildInfo` mà llama-swap
           nhồi vào lúc dựng nhị phân, không chạm model, không đánh thức GPU. Đã
           đối chiếu trên **đúng bản đang chạy** (v250, gói cài
           `llama-swap_250_windows_amd64.zip`), không phải trên `main` thượng
           nguồn — v250 trả `{"version","commit","build_date"}`.

        ⛔ BUILD CỦA ENGINE THÌ **KHÔNG** RẺ. Nó nằm ở `build_info` trong `/props`
           của `llama-server`, và đường tới đó là `/upstream/<model>/props` —
           mà llama-swap **sẽ nạp model** để phục vụ một đường `/upstream/…`
           nếu model chưa nằm trong VRAM. Tức một lượt `/health` vô hại sẽ đánh
           thức GPU 2,5 phút và đá văng bất cứ hồ sơ nào đang chạy.

           ⇒ Chỉ hỏi khi hồ sơ **đã nạp sẵn**, dùng đúng `_ho_so_dang_nap` mà
             `_dem_token_that` đã dùng cho cùng lý do. Không nạp thì trả `None`.
             Một chốt **quan sát** không bao giờ được trả giá bằng một sự cố
             hiệu năng — cùng luật đã ghi ở `_xem_gpu`.

        ⚠️ Thượng nguồn cũ không có `/api/version` (nó xuất hiện trước v250).
           Thiếu ⇒ `null` + `ly_do`, **không** làm `/health` đỏ.
        """
        if (_nho_swap["gia_tri"] is not None
                and _nho_engine["gia_tri"] is not None):
            return {"swap": _nho_swap["gia_tri"],
                    "engine": _nho_engine["gia_tri"], "ly_do": ""}

        import json as _json
        ra: dict = {"swap": None, "engine": None, "ly_do": ""}

        # `swap` bat bien khi tien trinh llama-swap con song -> hoi mot lan.
        if _nho_swap["gia_tri"] is not None:
            ra["swap"] = _nho_swap["gia_tri"]
        else:
            ma, than = upstream.json("GET", "/api/version", timeout=5.0)
            if ma != 200:
                ra["ly_do"] = ("/api/version tra " + str(ma)
                               + " (ban llama-swap cu?)")
            else:
                try:
                    d = _json.loads(than or b"{}")
                except (ValueError, TypeError):
                    ra["ly_do"] = "/api/version tra than khong doc duoc"
                else:
                    ra["swap"] = {
                        "version": str(d.get("version") or ""),
                        "commit": str(d.get("commit") or ""),
                        "build_date": str(d.get("build_date") or "")}

        # Engine: chỉ khi có hồ sơ đã nạp. Không nạp thì im lặng bỏ qua —
        # đây là đường bình thường, không phải khuyết tật.
        #
        # ⚠️ Và chỉ hỏi khi CHƯA nhớ được: build của engine cũng bất biến
        #    theo nhị phân, nhưng ta không đọc được nó cho tới khi có hồ sơ
        #    nạp — nên phải thử lại ở các lượt sau, chứ không đóng băng` None`.
        for ten in ([] if _nho_engine["gia_tri"] else sorted(catalog)):
            if not _ho_so_dang_nap(ten):
                continue
            ma2, than2 = upstream.json(
                "GET", "/upstream/" + ten + "/props", timeout=10.0)
            if ma2 != 200:
                break
            try:
                d2 = _json.loads(than2 or b"{}")
            except (ValueError, TypeError):
                break
            ra["engine"] = {"ho_so": ten, "build_info": str(d2.get("build_info") or "")}
            break

        # ⛔ Chỉ nhớ thứ ĐÃ đọc được. Hỏng lúc khởi động (llama-swap chưa kịp
        #    lên, hoặc chưa hồ sơ nào nạp) mà nhớ luôn thì `/health` sẽ nói dối
        #    tới hết đời tiến trình.
        if ra["swap"] is not None:
            _nho_swap["gia_tri"] = ra["swap"]
        if ra["engine"] is not None:
            _nho_engine["gia_tri"] = ra["engine"]
        if ra["engine"] is None and _nho_engine["gia_tri"] is not None:
            ra["engine"] = _nho_engine["gia_tri"]
        return ra

    @app.get("/health")
    def health(_: None = Depends(auth)) -> dict:
        px = tt.phan_xu()
        ma, _th = upstream.json("GET", "/v1/models", timeout=5.0)
        return {
            "version": __version__,
            "models_mo": sorted(catalog),
            "models_la": list(la),
            "thuong_nguon": {"url": cfg.upstream_url, "ma": ma,
                             "song": 200 <= ma < 300,
                             # 🔴 CHỐT DUY NHẤT NÓI ĐƯỢC "MÁY B ĐANG CHẠY BẢN
                             #    NÀO". Xem `_phien_ban_thuong_nguon`: bốn đường
                             #    khác đã thử và không đường nào trả lời.
                             "phien_ban": _phien_ban_thuong_nguon()},
            "trong_tai": {
                "bat": tt.bat,
                "ban": px.ban,
                "ly_do": px.ly_do,
                "so_python_gpu": px.so_python_gpu,
                "ram_trong_gb": round(px.ram_trong_gb, 1) if px.ram_trong_gb else None,
            },
            "tran": {
                "input_tokens": cfg.max_input_tokens,
                "output_tokens": cfg.max_output_tokens,
                "images": cfg.max_images,
            },
            # Khoi theo model + tong. `max_dong_thoi`/`rpm` la `None` khi hai
            # model khai khac nhau — mot con so gop o do se tra loi SAI dung cau
            # `test_334` hoi. Xem `SoTheoModel.trang_thai_chung`.
            "gioi_han": so.trang_thai_chung(),
            # So cong don theo nhom ket cuc — vet duy nhat cua nhung luot
            # BI TU CHOI, thu ma `/metrics` cua engine khong bao gio thay.
            "dem": dem.trang_thai(),
            "nhip_tim_giay": cfg.nhip_tim_giay,
            # 🔴 CHỐT DUY NHẤT NHÌN RA ĐƯỢC SỰ CỐ 23/08. Mọi trường khác ở trên
            #    vẫn XANH khi CUDA hỏng và model bò trên CPU. Xem `tren_gpu`.
            "gpu": _xem_gpu(),
            # 🔴 CHOT DUY NHAT NHIN RA DUOC "HEALTH XANH GIA" (do 01/09:
            #    /health tra 200 suot 99 giay trong khi Get-Service = Stopped).
            #    Moi truong khac o tren van XANH khi tien trinh nay da mo coi,
            #    vi chung noi ve suc khoe cua CHINH no -- va no that su khoe.
            #    Cau hoi dung khong phai "anh co khoe khong" ma "anh co NEN
            #    dang chay khong".
            "duoi_dich_vu": to_tien.trang_thai(),
        }

    def _vai_dang_nap() -> set:
        """Vai GPU của hồ sơ đang nằm trong VRAM. Dùng `_ho_so_dang_nap` (có nhớ
        2 giây) nên cả vòng này tốn **một** lời gọi `/running`.

        🔴 PHẢI THEO TỪNG VAI, KHÔNG PHẢI "CÓ MODEL NÀO ĐANG NẠP". Với hai card,
           `co_model_nap=True` cho **cả hai** làm chốt VRAM báo động về card đang
           trống một cách hoàn toàn đúng luật — 5060 Ti chưa nạp gì thì VRAM của
           nó thấp là **bình thường**, không phải "model bò trên CPU". Một cảnh
           báo dương tính giả mỗi lượt thăm dò thì kênh cảnh báo chết (QT-2).
        """
        ra = set()
        for ten in sorted(catalog):
            vai = GPU.vai_cua_model(ten)
            if vai and _ho_so_dang_nap(ten):
                ra.add(vai)
        return ra

    def _xem_gpu() -> dict:
        """Model có thật sự nằm trên card không — **theo từng card**.

        ⛔ Không dùng để từ chối yêu cầu — chốt **quan sát**, không phải chốt vào
           cửa. Model chạy CPU vẫn trả lời đúng, chỉ chậm; từ chối phục vụ sẽ
           biến một sự cố hiệu năng thành một sự cố ngừng dịch vụ.

        ⭐ KHỐI CŨ (`tren_gpu`/`vram_dung_mb`/`dang_lo` ở mức trên) ĐƯỢC GIỮ
           NGUYÊN TÊN, vì `platform_core` đang đọc đúng các khoá ấy để báo động
           (`ops_alerts` qua `test_277`/`test_378`) — đó là một hợp đồng đang
           chạy thật, không phải mã cũ. Nó nay mang số của **3090** (card lịch sử
           của cổng này), và `dang_lo` là **HOẶC** của hai card: một cảnh báo ở
           card nào cũng phải nổi lên, còn *card nào* thì đọc `theo_vai`.
        """
        vai_nap = _vai_dang_nap()
        theo_vai: dict = {}
        for vai in (GPU.VAI_38, GPU.VAI_35):
            try:
                uu = GPU.uuid_cua(vai)
            except (GPU.VaiKhongCo, OSError, ValueError) as e:
                theo_vai[vai] = {"ly_do": f"khong doc duoc danh tinh: {e}"}
                continue
            the = GPU.doc_the(uu)

            def _vram_the(t: Optional[dict] = the) -> Optional[int]:
                return None if t is None else int(t["vram_dung_mib"])

            px = kiem_gpu(co_model_nap=(vai in vai_nap), doc_vram=_vram_the)
            theo_vai[vai] = {
                "uuid": uu,
                "tren_gpu": px.tren_gpu,
                # ⭐ SỐ ĐO THẬT, KHÔNG PHẢI `px.vram_dung_mb`. `kiem()` cố ý trả
                #    `None` khi **chưa model nào nạp** — đó là đúng cho *phán
                #    xử* ("không kết luận gì"), nhưng sai cho *quan sát*: VRAM
                #    của một card chưa nạp model là một con số có thật và là thứ
                #    duy nhất nói được ai đang giữ card ấy.
                "vram_dung_mb": None if the is None else the["vram_dung_mib"],
                "vram_trong_mb": None if the is None else the["vram_trong_mib"],
                "util_pt": None if the is None else the["util_pt"],
                "co_model_nap": px.co_model_nap,
                "dang_lo": px.dang_lo,
                "ly_do": px.ly_do,
            }
        chinh = theo_vai.get(GPU.VAI_38) or {}
        return {"tren_gpu": chinh.get("tren_gpu"),
                "vram_dung_mb": chinh.get("vram_dung_mb"),
                "co_model_nap": chinh.get("co_model_nap", False),
                "dang_lo": any(bool(v.get("dang_lo")) for v in theo_vai.values()),
                "ly_do": chinh.get("ly_do", ""),
                "theo_vai": theo_vai}

    @app.get("/v1/models")
    def models(_: None = Depends(auth)) -> dict:
        # Rỗng là **đúng**, không phải hỏng: `LTT_LLM_MODELS` rỗng ⇒ chưa mở gì.
        return {
            "object": "list",
            "data": [
                {"id": m.ten, "object": "model", "owned_by": "ltt",
                 "context_window": m.max_context, "vision": m.co_vision,
                 "description": m.mo_ta}
                for m in sorted(catalog.values(), key=lambda x: x.ten)
            ],
        }

    # ── LỆNH RESIDENCY 3090 (Dual-model 5.4b) ────────────────────────────────
    #
    # ⭐ Ba đường dưới đây là **tay chân** của trọng tài residency ở máy A, không
    #    phải một trọng tài thứ hai (D01 B, TD-D10). Chúng chỉ làm ba việc: nói
    #    sự thật đo được, nhả đúng một model, nạp lại đúng một model.
    #
    # ⛔ MỌI TỪ CHỐI PHẢI NÊU ĐIỀU KIỆN NÀO HỎNG VÀ VỚI CON SỐ NÀO — cùng kỷ luật
    #    với `/v1/nha_comfy` của cổng render (5.4a). Một bước residency tin rằng
    #    nó đã dọn xong card trong khi chưa là đúng hỏng hóc D01 B đi chặn.

    def _vram_theo_uuid() -> dict:
        """`{uuid: MiB đang dùng}` cho **từng** card, đọc theo UUID.

        🔴 KHÔNG BAO GIỜ MỘT SỐ ĐO GỘP. Máy B có hai card và LTT-3.5 thường trú
           ~13 GB trên 5060 Ti: một `max()` của cả máy sẽ luôn nói "3090 chưa
           sạch", tức LTT-3.8 **không bao giờ** được nạp lại. Đó đúng là khuyết
           tật Task 6.1 vừa gỡ khỏi `render_gateway/busy.py`; đừng dựng lại nó ở
           đây. Máy A tra bảng này theo UUID của chính nó (`MayBResidency._vram`).

        ⚠️ Card nào không đọc được thì **vắng mặt** khỏi bảng, không mang giá trị
           0: 0 MiB là "card trống", và nói thế về một card không hỏi được là
           mời một lần nạp đè.
        """
        ra: dict = {}
        for vai in (GPU.VAI_38, GPU.VAI_35):
            try:
                uu = GPU.uuid_cua(vai)
            except (GPU.VaiKhongCo, OSError, ValueError) as e:
                log.warning("residency: khong doc duoc danh tinh vai %s: %s", vai, e)
                continue
            mib = GPU.vram_mib(uu)
            if mib is not None:
                ra[uu] = mib
        return ra

    def _model_hop_le(body: Optional[dict]) -> str:
        """Tên hồ sơ trong thân lệnh, đã kiểm. Sai ⇒ 400, **không** đoán hộ.

        ⛔ Không có mặc định "model cư trú": một lệnh nhả nhắm sai hồ sơ là một
           lượt của khách bị cắt, và im lặng đoán hộ là cách nhanh nhất tới đó.
        """
        ten = str((body or {}).get("model") or "").strip()
        if not ten:
            raise HTTPException(400, detail={"ly_do": "thieu truong `model`"})
        if ten not in so.models():
            raise HTTPException(
                400, detail={"ly_do": "khong biet ho so nay",
                             "model": ten, "co": list(so.models())})
        return ten

    @app.get("/v1/residency/trang_thai")
    def residency_trang_thai(_: None = Depends(auth)) -> dict:
        """Sự thật đo được của máy B — bốn trường, không trường nào suy diễn.

        ⚠️ `llm_da_nap = null` nghĩa là **không hỏi được llama-swap**, khác hẳn
           `false`. Máy A xử `None` theo hướng KHÔNG hành động (fail-closed,
           `QuanSat`); gộp hai thứ ấy thành `false` là bảo trọng tài rằng card
           đang trống trong lúc ta thật ra đang mù.
        """
        bang = RES.models_dang_chay(upstream)
        da_nap = None if bang is None else any(
            GPU.vai_cua_model(m) == GPU.VAI_38 and tr == RES.SAN_SANG
            for m, tr in bang.items())
        return {
            "llm_da_nap": da_nap,
            # Sổ suất của CHÍNH cổng này — thứ `lease` của máy A không thấy: một
            # lượt có thể đã nhả lease mà kết nối tới llama-server còn sống.
            "inflight": {m: so.dang_chay(m) for m in so.models()},
            "vram_mib": _vram_theo_uuid(),
            "nap_ket_qua": so_nap.doc(),
        }

    @app.post("/v1/residency/nha")
    def residency_nha(body: dict = Body(default=None), _: None = Depends(auth)):
        """Nhả **đúng một** hồ sơ khỏi VRAM.

        ⛔ CÒN SUẤT ĐANG BAY ⇒ **409**, VÀ KHÔNG MỘT LỜI GỌI NÀO XUỐNG
           llama-swap. Không "chờ một tí rồi ép", không hạn chờ leo thang: lệnh
           `unload` của llama-swap **không** drain (`fifo.go:222-270`), nên phát
           nó lúc còn in-flight là cắt ngang một lượt của khách — đúng thứ
           `GET /unload` cũ đã làm và là lý do trọng tài cũ bị gỡ (L-9, L-17).
           Việc drain là của máy A: ngừng nhận ⇒ chờ về 0 ⇒ rồi mới gọi lại. Lệnh
           này idempotent nên phát lại ở nhịp sau không tốn gì.
        """
        ten = _model_hop_le(body)
        bay = so.dang_chay(ten)
        if bay > 0:
            raise HTTPException(
                status_code=409,
                detail={"ly_do": "con luot dang chay — KHONG nha",
                        "model": ten, "inflight": bay,
                        "can": "inflight == 0"})
        kq = RES.nha(upstream, ten)
        if not kq.xong:
            log.error("residency/nha(%s) that bai: %s", ten, kq.ly_do)
            return JSONResponse(
                status_code=503,
                content={"error": {"code": "nha_that_bai", "message": kq.ly_do},
                         "model": ten, "ma_thuong_nguon": kq.ma,
                         "con_lai": list(kq.con_lai or ())})
        return {"da_nha": True, "model": ten, "inflight": 0,
                "con_lai": list(kq.con_lai or ()),
                "vram_mib": _vram_theo_uuid()}

    @app.post("/v1/residency/nap")
    def residency_nap(body: dict = Body(default=None), _: None = Depends(auth)):
        """Nạp lại hồ sơ cư trú — **chạy ở luồng nền**, kết quả đọc ở `trang_thai`.

        🔴 CHỐT VRAM ĐỨNG TRƯỚC, VÀ NÓ ĐỌC ĐÚNG CARD CỦA HỒ SƠ NÀY. Nạp 16 GB
           lên một card còn ai đó giữ thì llama.cpp **không báo lỗi**: nó tràn
           trọng số sang RAM chủ qua PCIe và chạy ở một phần tư tốc độ trong khi
           `/health` vẫn xanh (đo 22/08). Ngưỡng lấy từ `Config.vram_sach_mb`,
           cùng con số mà `ThamSoResidency.vram_sach_mib` của máy A dùng.

        ⚠️ Không đọc được VRAM ⇒ **503**, không phải "cứ nạp": "không biết" và
           "card trống" là hai thứ khác nhau, và chỉ một trong hai an toàn.
        """
        ten = _model_hop_le(body)
        vai = GPU.vai_cua_model(ten)
        try:
            uu = GPU.uuid_cua(vai) if vai else ""
        except (GPU.VaiKhongCo, OSError, ValueError) as e:
            uu = ""
            log.warning("residency/nap: khong doc duoc danh tinh %s: %s", vai, e)
        vram = GPU.vram_mib(uu) if uu else None
        if vram is None:
            return JSONResponse(
                status_code=503,
                content={"error": {
                    "code": "khong_doc_duoc_vram",
                    "message": (f"khong doc duoc VRAM cua card chay {ten!r} "
                                f"(vai {vai!r}, uuid {uu or 'khong ro'}) — "
                                f"KHONG nap khi khong biet card co sach khong. "
                                f"Kiem `nvidia-smi` va `gpu_may_b.json`.")},
                    "model": ten})
        if vram > cfg.vram_sach_mb:
            raise HTTPException(
                status_code=409,
                detail={"ly_do": "card chua sach — KHONG nap",
                        "model": ten, "uuid": uu,
                        "vram_dung_mib": vram,
                        "can": f"vram_dung_mib <= {cfg.vram_sach_mb}"})

        # ⭐ `bat_dau()` ĐẶT LẠI `nap_ket_qua` VỀ `""` ngay tại đây — trước khi
        #    luồng nền chạy dòng nào. Một `"loi"` cũ sống sót qua lệnh này làm máy
        #    A quay vòng `LOI_NAP → NAP_LLM → LOI_NAP` với thời gian lùi phồng
        #    tới trần vì một con số cũ (lo ngại số 1 của Task 5.1/5.2).
        if not so_nap.bat_dau():
            return JSONResponse(
                status_code=200,
                content={"da_bat_dau": False, "dang_chay": True, "model": ten,
                         "nap_ket_qua": so_nap.doc(),
                         "ly_do": "da co mot luot nap dang chay"})
        chay_nen(lambda: RES.chay_nap(upstream, ten, so_nap))
        return JSONResponse(
            status_code=202,
            content={"da_bat_dau": True, "dang_chay": True, "model": ten,
                     "vram_dung_mib": vram, "nap_ket_qua": so_nap.doc()})

    # ── Đường ống chung của ba giao thức ─────────────────────────────────────

    def _vram_trong_cua_model(model: str) -> "int | None":
        """VRAM còn trống trên card chạy `model`, MiB. `None` = không hỏi được.

        Ánh xạ hồ sơ → card đi qua `gpu_uuid.vai_cua_model` (theo tiền tố tên hồ
        sơ), nên một hồ sơ `qwen35-*` mới không phải khai thêm ở đây.
        """
        vai = GPU.vai_cua_model(model)
        if not vai:
            return None
        try:
            return GPU.vram_trong_mib(GPU.uuid_cua(vai))
        except (GPU.VaiKhongCo, OSError, ValueError):
            return None

    def _uuid_cua_model(model: str) -> str:
        """UUID của card chạy `model`, cho dòng sổ. `""` = không giải được.

        ⭐ Đọc `gpu_may_b.json` (Task 4.1), **không** gọi `nvidia-smi`: đây là
           đường nóng của mọi yêu cầu và câu hỏi là *"model này ở card nào"* —
           một sự thật tĩnh, không phải một phép đo.

        ⚠️ Dòng sổ mà thiếu UUID thì mọi phân tích "3.8 chậm hay 3.5 chậm" phải
           suy từ tên hồ sơ, tức suy lại đúng thứ `gpu_may_b.json` đã khai. Vẫn
           chấp nhận `""` chứ không ném: một tệp danh tính thiếu không được làm
           sập một lượt đang tính tiền.
        """
        try:
            vai = GPU.vai_cua_model(model)
            return GPU.uuid_cua(vai) if vai else ""
        except (GPU.VaiKhongCo, OSError, ValueError):
            return ""

    def _dau_ra(do, request_id: str) -> dict:
        """Header phản hồi. `X-LTT-Request-Id` chỉ dội lại khi bên gọi có gửi.

        ⭐ Dội lại chứ không tự sinh: một mã do cổng tự đặt thì máy A không có gì
           để nối vào, nên nó chỉ là một chuỗi đẹp trong log. Mã có ích là mã
           **chung**, và bên bắt đầu lượt là bên duy nhất đặt được nó.
        """
        h = {"X-LTT-Token-Vao": str(do.token_vao)}
        if request_id:
            h["X-LTT-Request-Id"] = request_id
        return h

    def _tran_ra_xin(body: dict[str, Any]) -> int:
        """Trần token SINH RA của yêu cầu này, theo cả ba giao thức.

        ⛔ Không khai ⇒ lấy trần cấu hình, **không** lấy 0. KV lớn dần theo từng
           token sinh, nên một lượt không khai `max_tokens` có thể chạy tới trần —
           đặt chỗ bằng 0 là để bể KV vỡ ở giữa lượt, và lúc bể vỡ thì llama.cpp
           huỷ **mọi** slot (`server-context.cpp:3688-3724`).
        """
        xin = body.get("max_tokens")
        if xin is None:
            xin = body.get("max_output_tokens")
        if isinstance(xin, (int, float)) and xin > 0:
            return min(int(xin), cfg.max_output_tokens)
        return cfg.max_output_tokens

    #: Lý do từ chối → nhóm bộ đếm. Ba loại 429 đòi ba hành động khác nhau của
    #: người trực, nên gộp chúng là vứt đi đúng phần trả lời được "tôi phải làm
    #: gì bây giờ" — cùng lập luận đã ghi ở `dem.NHOM`.
    def _nhom_tu_choi(ly_do: str) -> str:
        if "pool KV" in ly_do or "khong khai token" in ly_do:
            return "ban_pool"
        if "whale" in ly_do:
            return "ban_whale"
        if "VRAM trong" in ly_do:
            return "ban_vram"
        return "ban_day"

    def _chuyen_tiep(giao_thuc: str, body: dict[str, Any], *,
                     token_dat_khai: int = 0, la_whale: bool = False,
                     request_id: str = "") -> Response:
        """Mở sổ cho lượt này, chạy nó, rồi ghi **đúng một dòng**.

        🔴 MỘT DÒNG MỘT LƯỢT, VÀ MỌI ĐƯỜNG RA ĐI QUA ĐÂY. Ba đường ra: phản hồi
           thường, `HTTPException` (429/413/404), và luồng SSE. Nếu chỗ ghi sổ
           nằm cạnh chỗ trả phản hồi thì hai đường đầu sẽ có dòng và đường thứ ba
           **âm thầm không có** — mà đường thứ ba chính là đường của mọi client
           thật (Codex, Claude Code). Một sổ thiếu hẳn một cửa thì nó không phải
           sổ; nên cửa duy nhất là hàm này.

        ⚠️ Luồng SSE ghi **muộn**: lúc hàm này trả về, token còn chảy hàng chục
           giây và chưa ai biết lượt sẽ kết thúc thế nào (hủy? hết? khách ngắt?).
           Nên với `stream` thì dòng sổ và việc rút khỏi sổ lượt do
           `BackgroundTask` của luồng làm — đúng chỗ `suat.tra()` đã làm, và đúng
           lý do: nó chạy khi **phản hồi** kết thúc, kể cả khi thân chưa được đọc.
        """
        # Moc de do TTFT NHU KHACH THAY: gom ca cho suat, don card va nap
        # model — ba khoan `llama-server` khong bao gio nhin thay.
        t0 = now()
        ten = str(body.get("model") or "").strip()
        luot = SL.Luot(ma=request_id, model=ten, giao_thuc=giao_thuc, t0=t0,
                       gpu=_uuid_cua_model(ten), bam_gio=now)
        so_luot.dat(luot)
        moc = SL.SO_LUOT.set(luot)
        try:
            return _kiem_va_chay(giao_thuc, body, luot,
                                 token_dat_khai=token_dat_khai,
                                 la_whale=la_whale, request_id=request_id)
        except HTTPException as e:
            luot.ma_http = int(e.status_code)
            luot.ket_thuc = luot.ket_thuc or "tu_choi"
            raise
        except BaseException:
            luot.ket_thuc = luot.ket_thuc or "loi"
            raise
        finally:
            SL.SO_LUOT.reset(moc)
            # ⛔ `luot.stream` là câu *"có ai khác sẽ ghi dòng này không"*, và nó
            #    chỉ được đặt sau khi `StreamingResponse` đã cầm `BackgroundTask`
            #    trong tay. Đặt sớm hơn (ví dụ ngay khi thấy `body["stream"]`)
            #    thì một lượt stream bị 429 **trước** khi có luồng sẽ không ai
            #    ghi dòng cho nó cả.
            if not luot.stream:
                so_luot.xoa(luot.ma)
                SL.ghi_so(luot)

    def _kiem_va_chay(giao_thuc: str, body: dict[str, Any], luot: "SL.Luot", *,
                      token_dat_khai: int = 0, la_whale: bool = False,
                      request_id: str = "") -> Response:
        t0 = luot.t0
        ten = luot.model
        try:
            spec = lay(catalog, ten)
        except KhongCoModel:
            dem.cong("khong_co_model")
            # 404, không phải 400: model không mở là "không có ở đây", và fail-closed
            # nghĩa là ta **không** tiết lộ model nào tồn tại mà chưa mở.
            raise HTTPException(status_code=404,
                                detail={"ly_do": "model khong co hoac chua duoc mo",
                                        "model": ten, "co_the_dung": sorted(catalog)})

        try:
            do = NS.kiem_tra(
                body,
                max_input_tokens=min(cfg.max_input_tokens, spec.max_context),
                max_output_tokens=cfg.max_output_tokens,
                max_images=cfg.max_images,
                max_image_bytes=cfg.max_image_bytes,
                max_context=spec.max_context,
                co_vision=spec.co_vision,
                # ⭐ Chỉ được gọi khi phép ƯỚC đã vượt trần — xem `NS.kiem_tra`.
                #    Đường nhanh không thêm round-trip nào.
                dem_that=lambda van: _dem_token_that(ten, van),
            )
        except NS.VuotNganSach as e:
            dem.cong("qua_tran")
            # 413 chứ không phải 400: đây là "to quá", không phải "sai cú pháp".
            raise HTTPException(status_code=413, detail=e.as_dict())

        # ── Hàng rào đồng thời (V9) ──────────────────────────────────────────
        #
        # ⭐ ĐỨNG SAU NGÂN SÁCH, TRƯỚC TRỌNG TÀI VÀ VIỆC DỌN. Ba lý do, theo thứ tự:
        #
        #   1. Sau ngân sách, vì 413 phải dứt khoát (xem đoạn dưới) — một yêu cầu
        #      to quá thì to quá, dù cổng đang đầy hay rảnh.
        #   2. Trước việc dọn, vì `bao_dam_sach()` **chờ tới 18 giây**. Không chặn ở
        #      đây thì 50 yêu cầu cùng lúc là 50 lượt chờ dọn song song, mỗi lượt
        #      giữ một luồng của uvicorn. Cái phải chặn là chỗ tốn thời gian.
        #   3. Trước trọng tài, vì trọng tài đọc `nvidia-smi` và `psutil` — rẻ,
        #      nhưng không rẻ khi nhân 50.
        #
        # 🔴 CÓ SUẤT LÀ CÓ NỢ. Mọi đường ra từ đây trở xuống **phải** trả suất, kể
        #    cả đường ném HTTPException. Đó là việc của `try/finally` bên dưới, và
        #    của `boc_luong` với luồng SSE. Quên một nhánh thì cổng tự bóp
        #    cổ mình sau vài lần lỗi, và triệu chứng sẽ là "429 mãi mãi" — rất khó
        #    lần ra vì lúc đó GPU hoàn toàn rảnh.
        #
        # ⭐ SỐ TOKEN ĐẶT TRƯỚC ĐI KÈM MỖI SUẤT. Máy A khai qua `X-LTT-Token-Dat`
        #    (nó đã tính đỉnh KV để giữ lease của chính nó); không khai thì cổng
        #    dùng **số của chính mình** — `do.token_vao` (thật nếu đã `/tokenize`,
        #    không thì ước) cộng trần ra của yêu cầu. Đó không phải phỏng đoán, nó
        #    là phép đo cổng vừa làm ở bước ngân sách ngay trên.
        dat = token_dat_truoc(do.token_vao, _tran_ra_xin(body))
        if token_dat_khai > 0:
            dat = token_dat_khai
        px_gh, suat = so.cap_suat(ten, dat, la_whale)
        if suat is None:
            dem.cong(_nhom_tu_choi(px_gh.ly_do))
            raise HTTPException(
                status_code=429,
                detail={"ly_do": "cong dang day", "chi_tiet": px_gh.ly_do,
                        "model": ten},
                headers={"Retry-After": str(px_gh.thu_lai_sau_s)})
        try:
            return _chay_that(giao_thuc, body, spec, do, suat, t0, luot,
                              request_id=request_id)
        except BaseException:
            suat.tra()         # ⛔ kể cả HTTPException, kể cả Ctrl-C. Idempotent.
            raise

    def _chay_that(giao_thuc: str, body: dict[str, Any], spec: ModelSpec,
                   do, suat, t0: float, luot: "SL.Luot", *,
                   request_id: str = "") -> Response:
        """Phần tốn thời gian, đã cầm suất trong tay.

        ⚠️ Nó **không** tự trả suất khi thành công: với phản hồi thường, bên gọi
           trả ngay sau khi hàm này về; với SSE, suất còn phải giữ tới khi luồng
           hết. Xem hai nhánh cuối hàm.
        """
        ten = str(body.get("model") or "").strip()

        # ── Chốt dưới đây CHỈ nói về card 3090 ──────────────────────────────
        #
        # 🔴 VÀ ĐÓ LÀ MỘT SỬA LỖI, KHÔNG PHẢI MỘT TỐI ƯU. `trong_tai` nói về cuộc
        #    tranh trên card 24 GB, nơi ComfyUI ghim UUID 3090 (`test_1200`).
        #
        #    Từ Task 6.1, `render_gateway.busy` lọc mọi số đọc theo **UUID 3090**
        #    — đúng cho `qwen38-*` và **vô nghĩa cho `qwen35-*`**: LTT-3.5 nằm
        #    trên 5060 Ti. Áp chúng cho lượt 3.5 là từ chối một lượt vì một card
        #    **khác** đang bận (429 oan, mà máy A đọc 429 là *bận* nên khách đi ra
        #    đám mây), và bảo ComfyUI nhả VRAM để nạp một model **không dùng card
        #    của ComfyUI**.
        #
        # ⭐ Cửa của 5060 Ti là **sàn VRAM theo model** ở `so_theo_model.py`, đọc
        #    theo UUID của chính nó — đã chạy trước khi tới đây.
        vai = GPU.vai_cua_model(ten)
        card_cua_comfy = (vai == GPU.VAI_38)

        # ⛔ Trọng tài đứng SAU ngân sách có chủ ý: một yêu cầu vượt trần phải bị từ
        #    chối dứt khoát (413) kể cả khi card đang rảnh. Nếu đảo thứ tự, cùng một
        #    yêu cầu hỏng sẽ lúc trả 429 lúc trả 413 tuỳ card bận hay rảnh — và bên
        #    gọi sẽ thử lại mãi một thứ không bao giờ chạy được.
        px = tt.phan_xu() if card_cua_comfy else None
        if px is not None and px.ban:
            dem.cong("ban_trong_tai")
            raise HTTPException(
                status_code=429,
                detail={"ly_do": "may B dang ban", "chi_tiet": px.ly_do},
                headers={"Retry-After": "30"})

        # 🔴 VIỆC "DỌN CARD TRƯỚC KHI NẠP" ĐÃ RỜI KHỎI ĐÂY (5.4b) — và nó không
        #    biến mất, nó **đổi chủ**. Số đo 22/08 vẫn đúng (card bẩn 18,2 tok/s
        #    vs card sạch 63,3 tok/s, llama.cpp tràn sang RAM chủ mà `/health`
        #    vẫn xanh), nhưng người dọn nay là **trọng tài residency ở máy A**:
        #    nó phát `POST /v1/nha_comfy` **dừng hẳn** LTTComfyUI (5.4a — `/free`
        #    không nhả 223,5 MiB ngữ cảnh CUDA, L-14 §3), đợi VRAM tụt, rồi mới
        #    phát `POST /v1/residency/nap` xuống dưới đây.
        #
        # ⛔ Để lại một lối dọn thứ hai ở đường nóng là dựng lại đúng cặp trọng
        #    tài mà D01 B vừa gỡ: hai chỗ cùng quyết về một card, không khoá
        #    chung, và cái chạy sau sẽ phá việc của cái chạy trước.

        duong = DUONG[giao_thuc]
        log.info("%s model=%s token_vao~%d anh=%d", duong, ten, do.token_vao, do.so_anh)

        if bool(body.get("stream")):
            ma, ct, luong = upstream.stream(
                "POST", duong, body=body, timeout=cfg.stream_timeout_s)
            if ma >= 500:
                than = b"".join(luong)
                suat.tra()
                # ⛔ Chưa đặt `luot.stream` ⇒ dòng sổ do `_chuyen_tiep` ghi. Ở
                #    đây không có luồng nào để `BackgroundTask` bám vào.
                luot.ma_http = _ma_cho_khach(ma)
                # ⚠️ Hủy có thể đến **trước cả header** thượng nguồn. Nhánh này
                #    phải có: `MA_DA_HUY` là 597, tức nó thoả `ma >= 500` và sẽ
                #    rơi vào cửa 502 nếu không chặn — đúng cái mã mà máy A đọc
                #    thành "khoá hỏng".
                if ma == MA_DA_HUY:
                    return _da_huy(luot)
                return _loi_thuong_nguon(ma, than)
            # 🔴 SUẤT ĐƯỢC TRẢ KHI LUỒNG HẾT, KHÔNG PHẢI KHI HÀM NÀY VỀ.
            #    `StreamingResponse` trả về ngay lập tức; token còn chảy hàng chục
            #    giây sau đó. Trả suất ở đây là đo đồng thời bằng "số lần bấm nút"
            #    chứ không phải "số lượt đang chạy", và chốt thành vô nghĩa đúng
            #    lúc cần nó nhất.
            # 🔴 DON DEP KHONG DUOC PHU THUOC VAO VIEC GENERATOR CHAY.
            #
            #    `boc_luong` tra suat trong `finally`, va do la dung — nhung mot
            #    `finally` chi ton tai SAU khi generator chay dong dau tien. Neu
            #    Starlette khong bao gio lap qua no (khach da ngat truoc khi byte
            #    dau chay), khoi `try` chua tung duoc vao, `finally` khong chay,
            #    va suat bi giu VINH VIEN.
            #
            # ⛔ Do la nguyen nhan su co 31/08: mot suat treo, `max_dong_thoi=1`,
            #    cong tra 429 suot SAU GIO trong khi GPU ranh va model chua nap.
            #    89/117 luot cua mot khach hong. Ba phep kiem cua `boc_luong` deu
            #    goi `next(g)` truoc, nen khong phep nao cham trang thai nay.
            #
            # ⭐ `BackgroundTask` chay khi PHAN HOI ket thuc, ke ca khi than chua
            #    tung duoc doc — nen no phu dung khe ho ay. Day cung la khuon ma
            #    may A DA dung dung cho ve admission (`server/api/streaming.py`),
            #    chi la chua duoc mang sang day.
            #
            # `Suat.tra()` va `dong()` deu idempotent, nen lop nay CONG THEM chu
            # khong thay the `finally` — hai duong doc lap cho cung mot viec.
            dong_thuong_nguon = getattr(luong, "dong", None)
            luot.stream = True
            luot.ma_http = int(ma)

            def _don_dep() -> None:
                try:
                    suat.tra()
                finally:
                    try:
                        if dong_thuong_nguon is not None:
                            dong_thuong_nguon()
                    finally:
                        # 🔴 DÒNG SỔ Ở ĐÂY, KHÔNG Ở `_chuyen_tiep`. Lúc
                        #    `_chuyen_tiep` trả về, lượt này chưa kết thúc —
                        #    `huy` còn có thể bật lên hàng chục giây sau. Ghi sớm
                        #    là ghi `huy=false` cho một lượt sắp bị hủy, tức một
                        #    dòng sổ **đúng cú pháp và sai sự thật**.
                        #
                        # ⚠️ Rút khỏi sổ lượt cũng ở đây: rút sớm thì `/v1/huy`
                        #    không tìm thấy lượt đang chảy và trả 404, đúng lúc
                        #    nó cần trả lời "đã cắt".
                        so_luot.xoa(luot.ma)
                        SL.ghi_so(luot)

            dem.cong("ok_stream")
            # ⛔ TTFT bọc TRONG nhip_tim: nhip tim phat byte trong luc prefill,
            #    boc ngoai thi moi luot dai deu ra ~15 giay. Xem `boc_do_ttft`.
            luong = boc_do_ttft(luong, dem, t0, now, luot.ghi_ttft)
            luong = boc_nhip_tim(luong, moi_giay=cfg.nhip_tim_giay)
            return StreamingResponse(boc_luong(luong, suat), status_code=ma,
                                     media_type=ct,
                                     headers=_dau_ra(do, request_id),
                                     background=BackgroundTask(_don_dep))

        try:
            ma, thu = upstream.json("POST", duong, body=body,
                                    timeout=cfg.upstream_timeout_s)
        finally:
            suat.tra()
        luot.ma_http = _ma_cho_khach(ma)
        # TTFT của cửa đồng bộ = cả lượt: khách không thấy byte nào trước đó.
        luot.ghi_ttft(now() - t0)
        if ma == MA_DA_HUY:
            return _da_huy(luot)
        if ma >= 500:
            return _loi_thuong_nguon(ma, thu)
        # ⛔ Bóc số TRƯỚC khi trả: `thu` là thân sẽ đi ra cho khách, và đây là
        #    chỗ duy nhất còn thấy nó. Bóc chỉ đọc, không sửa một byte nào.
        luot.doc_than(thu)
        dem.cong("ok")
        return Response(content=thu, status_code=ma, media_type="application/json",
                        headers=_dau_ra(do, request_id))

    def _ma_cho_khach(ma: int) -> int:
        """Mã nội bộ của lớp vận chuyển → mã HTTP khách thật sự nhận.

        Dòng sổ phải mang mã **khách thấy**, không phải mã nội bộ: `597/598/599`
        không tồn tại ở phía khách, và một sổ ghi chúng sẽ không khớp được với
        log truy cập của Cloudflare hay của máy A — tức không nối được hai đầu
        của cùng một sự cố.
        """
        return {MA_DA_HUY: 499, MA_HET_GIO: 504}.get(ma, 502 if ma >= 500 else int(ma))

    def _da_huy(luot: "SL.Luot") -> JSONResponse:
        """499 — lượt bị hủy theo yêu cầu.

        ⛔ 499, KHÔNG 502 và KHÔNG 429. Máy A đọc 502 thành `CongVlmError` ⇒
           `api_pool.danh_dau_loi()` ⇒ năm lần là `APIKEY_ERROR`, thứ **không tự
           hồi**: khách bấm "dừng" năm lần thì model nhà tắt vĩnh viễn (D-005).
           Và 429 thì máy A sẽ **đi tiếp provider khác** — với model nội bộ
           `canonical.THU_TU_PROVIDER` chỉ có MỘT phần tử, nên "đi tiếp" là cạn
           danh sách ⇒ `KhongCoProviderNao`, một thông điệp che mất nguyên nhân
           thật. 499 ⇒ `cong_vlm.HuyError`, một lớp riêng không phải lỗi của ai.

        ⚠️ 499 không phải mã của IANA — nó là quy ước của nginx cho *"client đã
           đóng"*. Dùng nó ở đây vì đúng nghĩa và vì cả hai đầu là mã của ta.
        """
        dem.cong("huy")
        luot.ket_thuc = luot.ket_thuc or "huy"
        return JSONResponse(status_code=499,
                            content={"ly_do": "huy theo yeu cau",
                                     "ma": luot.ma or None})

    def _loi_thuong_nguon(ma: int, thu: bytes) -> JSONResponse:
        # ⛔ HẾT GIỜ ≠ HỎNG, VÀ SỰ KHÁC BIỆT ẤY TỐN TIỀN THẬT.
        #
        #    Trước 09/09 cả hai đi chung một cửa 502. Máy A đọc 502 thành
        #    `CongVlmError` ⇒ `api_pool.danh_dau_loi()` ⇒ sau 5 lần
        #    `key.status = APIKEY_ERROR` — và `APIKEY_ERROR` **KHÔNG TỰ HỒI**
        #    (`api_pool._ung_vien` chỉ tự hồi `COOLDOWN`). Tức năm lần hết giờ
        #    là model nhà tắt và **ở lại tắt** tới khi có người sửa tay.
        #
        # ⭐ Đó chính là D-005, đi vào bằng cửa **hết giờ**. Cửa 429 đã được bịt
        #    rất kỹ; cửa này thì chưa ai bịt. Một prompt 200K prefill hàng phút
        #    là hành vi **bình thường** của hệ này, không phải máy B hỏng.
        if ma == MA_HET_GIO:
            dem.cong("het_gio")
            log.warning("thuong nguon HET GIO: %s", thu[:200])
            return JSONResponse(
                status_code=504,
                content={"ly_do": "thuong nguon khong tra loi kip",
                         "ma_thuong_nguon": ma,
                         "chi_tiet": thu[:500].decode("utf-8", "replace")})
        """llama-swap/llama-server hỏng hoặc không với tới được.

        ⚠️ Trả **502**, và **không** trả 429. Đây là hỏng thật, máy A **nên** đánh
        dấu lỗi cho key ở đây — khác hẳn trường hợp bận ở trên.
        """
        dem.cong("loi_thuong_nguon")
        log.error("thuong nguon loi ma=%s: %s", ma, thu[:300])
        return JSONResponse(status_code=502,
                            content={"ly_do": "thuong nguon khong phuc vu duoc",
                                     "ma_thuong_nguon": ma,
                                     "chi_tiet": thu[:500].decode("utf-8", "replace")})

    # ── Ba giao thức, cùng ba header vào ────────────────────────────────────
    #
    # 🔑 BA HEADER, MỘT NGUỒN: máy A. Nó đã tính đỉnh KV và ngưỡng cá voi **theo
    #    từng model** (`apps/ltt_llm/ngan_sach.NGUONG_WHALE`: 33.792 cho 3.8,
    #    56.832 cho 3.5 — hai đường cong prefill khác nhau, §G4). Cổng **không
    #    tính lại**: hai chỗ cùng tính một điều thì chúng sẽ lệch, và bên lệch là
    #    bên ta tin.
    #
    #      X-LTT-Request-Id   nối log hai máy về một lượt (Task 4.3 ghi log)
    #      X-LTT-Token-Dat    token KV lượt này chiếm ở đỉnh
    #      X-LTT-Whale        lượt đủ dài để chặn prefill của người khác
    #
    # ⛔ VÀ KHÔNG CÓ HEADER NÀO ĐI LÊN THƯỢNG NGUỒN. `upstream.json/stream` nhận
    #    đúng `(method, path, body, timeout)` — không có tham số `headers`, nên
    #    `X-Conversation-Id` (máy A gắn cho hội thoại) **không có đường** lọt sang
    #    llama-server. Đó là một bảo đảm **cấu trúc**, không phải một chỗ lọc dễ
    #    quên; `test_1221` chốt đúng tính chất ấy.
    def _so_header(gt: str) -> int:
        try:
            return max(0, int((gt or "").strip() or 0))
        except ValueError:
            return 0

    def _co_header(gt: str) -> bool:
        return (gt or "").strip().lower() in ("1", "true", "yes", "co")

    def _id_sach(gt: str) -> str:
        """Mã lượt, đã lọc. Cổng **dội lại** nó để hai máy nối được log.

        ⛔ LỌC CHỨ KHÔNG DỘI THÔ. Đây là chuỗi do bên gọi đặt, và nó đi vào một
           header phản hồi: một `\\r\\n` trong đó là chèn header (response
           splitting). Chỉ giữ chữ-số-gạch, cắt 64 ký tự.
        """
        return "".join(c for c in (gt or "").strip()
                       if c.isalnum() or c in "-_.:")[:64]

    @app.post("/v1/huy")
    def huy(body: dict = Body(default=None), _: None = Depends(auth),
            x_ltt_request_id: str = Header(default="")) -> Response:
        """Hủy một lượt đang bay: đóng cửa ra mạng của nó, không giết gì cả.

        ⛔ ĐÓNG KẾT NỐI **LÀ** CƠ CHẾ HỦY, và nó là cơ chế duy nhất được dùng.
           llama.cpp nhả slot ≤1 s sau khi client rời (`server-context.cpp:39`,
           `server-queue.cpp:607-617`), nên không có lý do nào để `taskkill`, để
           gọi `/unload` của llama-swap, hay để chạm vào một slot khác. Cả ba
           việc ấy đều đánh vào **lượt của người khác**, và `/unload` thậm chí
           không mang tên model nên nó nhả cả hai card (L-17).

        ⭐ Vì sao cần đường này chứ không chỉ để máy A đóng socket A→B. Thân của
           một endpoint `def` chạy ở threadpool của uvicorn và **không** nhận tin
           khách đã đi; nó chỉ biết khi `upstream.json` trả về. Máy A đóng socket
           của nó thì lượt B→llama vẫn chạy tới hết cho một người đã đi. Lời gọi
           này là cách máy A **nói bằng lời** điều mà socket không nói được.

        404 khi không có lượt nào mang mã ấy. ⛔ Không 200: một bên hủy nhận 200
        sẽ tin là đã cắt được, trong khi mã có thể sai hoặc lượt đã xong — và
        "tưởng đã cắt" là đúng trạng thái làm người ta không kiểm lại.
        """
        ma = _id_sach(str((body or {}).get("request_id") or "")) or _id_sach(
            x_ltt_request_id)
        if not ma:
            raise HTTPException(status_code=400,
                                detail={"ly_do": "thieu request_id"})
        n = so_luot.huy(ma)
        if n is None:
            raise HTTPException(
                status_code=404,
                detail={"ly_do": "khong co luot dang chay mang ma nay", "ma": ma})
        log.warning("huy luot %s theo yeu cau — dong %s cua ra mang", ma, n)
        # ⚠️ KHÔNG ghi một dòng sổ ở đây. Sổ là "một dòng mỗi LƯỢT MODEL", và
        #    lượt bị hủy sẽ tự ghi dòng của nó (với `huy=true`) khi nó kết thúc.
        #    Ghi thêm một dòng ở đây là hai dòng cho một lượt.
        return JSONResponse(status_code=200,
                            content={"huy": True, "ma": ma, "so_cua_dong": n})

    @app.post("/v1/chat/completions")
    def chat(body: dict = Body(...), _: None = Depends(auth),
             x_ltt_token_dat: str = Header(default=""),
             x_ltt_whale: str = Header(default=""),
             x_ltt_request_id: str = Header(default="")) -> Response:
        return _chuyen_tiep("chat", body,
                            token_dat_khai=_so_header(x_ltt_token_dat),
                            la_whale=_co_header(x_ltt_whale),
                            request_id=_id_sach(x_ltt_request_id))

    @app.post("/v1/responses")
    def responses(body: dict = Body(...), _: None = Depends(auth),
                  x_ltt_token_dat: str = Header(default=""),
                  x_ltt_whale: str = Header(default=""),
                  x_ltt_request_id: str = Header(default="")) -> Response:
        return _chuyen_tiep("responses", body,
                            token_dat_khai=_so_header(x_ltt_token_dat),
                            la_whale=_co_header(x_ltt_whale),
                            request_id=_id_sach(x_ltt_request_id))

    @app.post("/v1/messages")
    def messages(body: dict = Body(...), _: None = Depends(auth),
                 x_ltt_token_dat: str = Header(default=""),
                 x_ltt_whale: str = Header(default=""),
                 x_ltt_request_id: str = Header(default="")) -> Response:
        return _chuyen_tiep("messages", body,
                            token_dat_khai=_so_header(x_ltt_token_dat),
                            la_whale=_co_header(x_ltt_whale),
                            request_id=_id_sach(x_ltt_request_id))

    return app
