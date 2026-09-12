"""soi_cong_llm.py — đối chiếu HAI nguồn sự thật về cổng LLM trên máy B.

    python tools/soi_cong_llm.py               # đọc, in bảng, trả mã thoát
    python tools/soi_cong_llm.py --im          # chỉ nói khi có gì đó lệch

## ⛔ VÌ SAO KHÔNG PHẢI "THÊM MỘT TRƯỜNG VÀO `/health`"

Đo 01/09 trên máy B. Dừng vỏ bọc `nssm.exe` của `LTTLlmGateway`:

    + 0.0s   /health=200  Get-Service=Stopped   cong8299=26528
    +62.9s   /health=200  Get-Service=Paused    cong8299=26528
    +99.0s   /health=200  Get-Service=Paused    cong8299=26528

Tiến trình con **sống sót mồ côi**, vẫn giữ cổng, vẫn trả 200 — suốt 99 giây,
trong khi dịch vụ đã chết và `FAILURE_ACTIONS` của SCM không giành lại được cổng.

🔴 Không sửa được bằng cách làm `/health` thông minh hơn. `/health` **do chính
   con mồ côi phục vụ**; một endpoint sức khoẻ được phục vụ bởi thứ cần kiểm tra
   thì vĩnh viễn không nói được *"tôi là tiến trình không nên tồn tại"*. Nó
   không nói dối — nó thành thật báo cáo về một tiến trình thật sự khoẻ, chỉ là
   tiến trình đó lẽ ra không nên đang chạy.

⇒ Lớp lỗi này chỉ lộ ra khi **hai nguồn độc lập** không khớp:

      nguồn 1  `/health`      — do TIẾN TRÌNH tự nói
      nguồn 2  `Get-Service`  — do WINDOWS nói

  Đo một nguồn thì không bao giờ thấy, dù đo kỹ đến đâu. Đây không phải chuyện
  "kiểm cho chắc"; nó là chuyện **số nguồn**.

## Đọc kết quả

| /health | Get-Service | nghĩa |
|---|---|---|
| 200 | Running | lành |
| 200 | **không Running** | 🔴 **MỒ CÔI** — health xanh giả, chờ sập |
| ✗ | Running | đang khởi động, hoặc cổng treo |
| ✗ | không Running | chết thật, và ít nhất nó *nói* là chết |

Hàng thứ hai là hàng đắt nhất: hệ thống trông khoẻ, không cảnh báo nào nổi, và
tiến trình đang phục vụ **không có ai dựng dậy** nếu nó chết.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

#: Node máy B trong LTT Nexus. Xem `Ket_noi.md` trên Desktop và CLAUDE.md.
NODE_B = "f8b24d88-6e3e-4719-8143-d5e83f68ed82"
NEXUS = f"https://192.168.2.17:9444/api/v1/nodes/{NODE_B}/proxy/api/v1/exec"

LANH, LECH, KHONG_DO_DUOC = 0, 1, 2


#: Phán xử tách khỏi phần gọi mạng, để chốt được bằng test mà không cần máy B.
#:
#: ⭐ Vì sao đáng tách: `LANH` chỉ có nghĩa nếu công cụ **có khả năng** trả
#:    `LECH`. Tối 31/08 một đồng hồ đọc sai tên trường đã cho ra một dãy số
#:    trông hoàn hảo trong khi nó không đo gì cả. Một hàm thuần thì chứng minh
#:    được cả hai chiều bằng dữ liệu tổng hợp, không cần dựng lại sự cố.
def phan_xu(health: str, gateway: str) -> tuple[int, str]:
    """(mã thoát, nhãn) từ hai nguồn. Xem bảng ở docstring đầu tệp."""
    khoe = health == "200"
    chay = gateway == "Running"
    if khoe and chay:
        return LANH, "lanh"
    if khoe and not chay:
        # Hàng đắt nhất: trông khoẻ, không cảnh báo nào nổi, và tiến trình đang
        # phục vụ không có ai dựng dậy nếu nó chết.
        return LECH, "xanh-gia"
    if not khoe and chay:
        return LECH, "dang-khoi-dong-hoac-treo"
    return LECH, "chet-that"


# ══════════════════════════════════════════════════════════════════════════
#  BÁO ĐỘNG CỦA CỔNG DUAL-MODEL (Task 6.3)
# ══════════════════════════════════════════════════════════════════════════
#
# ⭐ CÙNG KHUÔN VỚI `phan_xu` Ở TRÊN: phán xử là **hàm thuần**, phần đọc mạng
#    nằm riêng. Lý do không đổi — một báo động chỉ có nghĩa nếu nó chứng minh
#    được **cả hai chiều**: kêu khi phải kêu, và **im khi lành**. Một bộ dò kêu
#    mọi lúc và một bộ dò không bao giờ kêu đều qua được một phép kiểm một
#    chiều, và cả hai đều vô dụng — cái sau âm thầm, cái trước ồn ào tới mức
#    người ta tắt kênh cảnh báo đi, rồi lượt kêu thật rơi vào hư không.

#: Mức của một báo động. `loi` = đang hỏng hoặc sắp hỏng theo hướng mất dịch vụ;
#: `canh_bao` = lệch so với hình dạng đã đo, đáng nhìn nhưng chưa mất gì.
MUC_LOI, MUC_CANH_BAO = "loi", "canh_bao"


class BaoDong(dict):
    """Một báo động: `{ma, muc, ...chi tiết}`. `dict` để in/JSON không cần dịch."""

    def __init__(self, ma: str, muc: str = MUC_LOI, **chi_tiet):
        super().__init__(ma=ma, muc=muc, **chi_tiet)


# ── 1. VRAM trống dưới sàn, THEO UUID ────────────────────────────────────────
#
# 🔴 KHÔNG CÓ CON SỐ NÀO GÕ Ở ĐÂY. Sàn đọc từ `/health` → `gioi_han[model]
#    .san_vram_mb` (cổng lấy từ `llm_gateway.config._san_vram`; mặc định của
#    `qwen35-api` chốt ở DECISION_LOG **L-18**), và VRAM trống đọc từ `/health`
#    → `gpu.theo_vai[<vai>].vram_trong_mb`, tức số của **đúng card** —
#    `gpu_uuid.doc_the` đã lọc `nvidia-smi` theo cột `uuid`.
#
# ⛔ VÀ VÌ THẾ NÓ ĐỌC SÀN **ĐANG SỐNG TRÊN MÁY B**, không phải mặc định trong
#    kho: sàn nằm ở env theo model (`LTT_LLM_VRAM_TRONG_TOI_THIEU_MB__<model>`),
#    nên một bản sao đọc từ `llm_gateway/config.py` ở máy A sẽ nói sai ngay lần
#    đầu ai đó chỉnh env. Hỏi máy chủ, đừng đọc một bảng chép tay.

def _vai_cua(model: str) -> str:
    """`qwen38-*` → `ltt38` · `qwen35-*` → `ltt35`. Nguồn: `llm_gateway.gpu_uuid`."""
    try:
        from llm_gateway.gpu_uuid import vai_cua_model
    except ImportError:                                          # pragma: no cover
        return ""
    return vai_cua_model(model) or ""


def bao_dong_vram(health: dict) -> list:
    """VRAM trống của card phục vụ một model đã xuống dưới **sàn của model ấy**.

    Ba câu trả lời khác nhau, và chúng phải khác nhau:

      · sàn = 0 / thiếu ⇒ model này **không có sàn ở tầng cổng** — `qwen38-api`
        cố ý như vậy (3090 do trọng tài residency quản; hai cơ chế canh một card
        là hai chỗ khai một điều). Không báo động, và cũng không giả vờ đã kiểm.
      · `vram_trong_mb = None` ⇒ **không hỏi được driver**. Đó KHÔNG phải "lành":
        cái sàn đang không được canh, và điều đó phải nói ra (`canh_bao`).
      · trống < sàn ⇒ `loi`. Cổng đang trả `429 bận` cho model ấy.
    """
    ra = []
    theo_vai = ((health.get("gpu") or {}).get("theo_vai") or {})
    for model, gh in sorted((health.get("gioi_han") or {}).items()):
        if not isinstance(gh, dict):
            continue
        san = int(gh.get("san_vram_mb") or 0)
        if san <= 0:
            continue
        vai = _vai_cua(model)
        the = theo_vai.get(vai) or {}
        trong = the.get("vram_trong_mb")
        if trong is None:
            ra.append(BaoDong("vram_khong_do_duoc", MUC_CANH_BAO, model=model,
                              vai=vai, san_mb=san,
                              ly_do=str(the.get("ly_do") or "khong co so lieu card")))
            continue
        if int(trong) < san:
            ra.append(BaoDong("vram_trong_duoi_san", MUC_LOI, model=model,
                              vai=vai, uuid=str(the.get("uuid") or ""),
                              vram_trong_mb=int(trong), san_mb=san))
    return ra


# ── 2. Tràn WDDM (`Shared Usage`) ────────────────────────────────────────────
#
# 🔴 "`Shared Usage > 0`" — ĐIỀU KẾ HOẠCH VIẾT — LÀ MỘT BÁO ĐỘNG KÊU SUỐT NGÀY,
#    và §G1 của `docs/ltt_llm_dual/10_BENCHMARK_P3.md` đã bác nó bằng đối chứng:
#    chạy **đúng cấu hình đang phục vụ khách** qua cùng bộ đếm cũng cho 526–568
#    MiB. Một cấu hình đang chạy tốt không thể là "đang tràn". Bộ đếm có một
#    SÀN của engine/driver, và phần tràn thật = `Shared − sàn`.
#
# ⚠️ VÀ SÀN ẤY KHÔNG CỐ ĐỊNH: §G1b đo lại ở `-ub 256` thì nó tụt còn 348 MiB.
#    Phần lớn "sàn" là bộ đệm dàn trang theo micro-batch. ⇒ Hai con số dưới đây
#    **chỉ đúng cho micro-batch mặc định**, tức đúng cấu hình đã chốt (L-14).
#    Đổi micro-batch ở `llama-swap.yaml` là phải ĐO LẠI sàn, không suy ra.
#
# ⛔ Đây là nơi DUY NHẤT trong kho khai hai con số này. Chúng không có "nguồn
#    chân lý" nào khác để đọc: không phải cấu hình vận hành (không ai chỉnh
#    được chúng), mà là kết quả một phép đo. Sao chép chúng đi nơi khác là mở
#    lại đúng cái khe đã nói sai năm lần.
SAN_SHARED_MIB = {
    # §G1b, dòng cấu hình chốt (3 slot, mmproj trên GPU, micro-batch mặc định):
    # Shared 568, nằm đúng trong dải sàn 526–568 đo ở §G1 ⇒ **không tràn**.
    "qwen38-api": 568,
    # §G3, LTT-3.5 trên 5060 Ti ở cấu hình chốt: Shared 354, không tràn.
    "qwen35-api": 354,
}

#: Bao nhiêu MiB TRÊN sàn thì mới coi là tràn thật.
#:
#: 🔴 CON SỐ NÀY **CHƯA ĐƯỢC ĐO TRỰC TIẾP** — nó nội suy giữa hai phép đo thật,
#:    và nó phải tự khai điều đó. Hai mốc §G1b kẹp nó:
#:
#:      · dải sàn của các cấu hình LÀNH trải **42 MiB** (526–568);
#:      · lần tràn NHỎ NHẤT thật sự quan sát được là **+138 MiB** trên sàn
#:        (dòng ngữ cảnh kế tiếp: Shared 706 so với sàn 568).
#:
#:    128 nằm dưới mốc tràn nhỏ nhất và trên toàn bộ độ trải của dải lành, nên
#:    nó không thể kêu vì nhiễu của chính bộ đếm, và vẫn bắt được lần tràn nhỏ
#:    nhất từng thấy. Khoảng giữa hai mốc ấy là vùng **chưa ai đo**; chọn đầu
#:    cao của vùng ấy là chọn phía "không kêu oan", đúng yêu cầu của một kênh
#:    cảnh báo mà người ta phải còn tin.
BIEN_SHARED_MIB = 128


def bao_dong_shared(model: str, shared_mib) -> list:
    """`Shared Usage` của model vượt **sàn đã đo + biên** ⇒ tràn WDDM.

    ⚠️ Tràn WDDM là lớp hỏng của sự cố 22/08: `/health` vẫn xanh, model vẫn sinh
       chữ hợp lệ, và tốc độ chỉ sụp **khi lượt thật sự chạm vào phần đã tràn**.
       Không bộ đếm nào của `nvidia-smi` thấy nó.
    """
    if shared_mib is None:
        return [BaoDong("shared_khong_do_duoc", MUC_CANH_BAO, model=model)]
    san = SAN_SHARED_MIB.get(model)
    if san is None:
        # Model chưa đo sàn ⇒ **không kết luận**. Mượn sàn của model khác là
        # mượn số của một cấu hình khác: sàn đổi theo micro-batch và theo engine.
        return [BaoDong("shared_chua_do_san", MUC_CANH_BAO, model=model,
                        shared_mib=int(shared_mib))]
    tran = int(shared_mib) - san
    if tran > BIEN_SHARED_MIB:
        return [BaoDong("tran_wddm", MUC_LOI, model=model,
                        shared_mib=int(shared_mib), san_mib=san,
                        tran_mib=tran, bien_mib=BIEN_SHARED_MIB)]
    return []


# ── 3. `requests_deferred` của engine ────────────────────────────────────────

def bao_dong_deferred(model: str, van_ban: str) -> list:
    """`requests_deferred > 0` trong `/upstream/<model>/metrics` (khuôn Prometheus).

    ⭐ Đọc theo **hậu tố tên**, không theo tên đầy đủ: llama.cpp đặt tiền tố
       `llamacpp:` và tiền tố ấy đã đổi giữa các bản. Khớp hậu tố thì một lần
       đổi tiền tố không biến bộ dò thành một đường im lặng.

    `requests_deferred` là số lượt engine phải HOÃN vì hết slot — tức hàng đợi
    đã tràn qua khỏi phòng chờ của máy A xuống tới engine, nơi ta không còn điều
    phối được gì.
    """
    for dong in (van_ban or "").splitlines():
        d = dong.strip()
        if not d or d.startswith("#"):
            continue
        phan = d.split()
        if len(phan) < 2:
            continue
        ten = phan[0].split("{", 1)[0]
        if not ten.endswith("requests_deferred"):
            continue
        try:
            gt = float(phan[-1])
        except ValueError:
            continue
        if gt > 0:
            return [BaoDong("requests_deferred", MUC_LOI, model=model,
                            gia_tri=gt, ten_do=ten)]
    return []


# ── 4. Dòng log "Context size has been exceeded" ─────────────────────────────

#: Chuỗi llama-server in khi một lượt vượt cửa sổ ngữ cảnh của slot. Nó là chuỗi
#: của **engine**, không phải của ta — đừng "chuẩn hoá" nó.
DAU_VUOT_NGU_CANH = "Context size has been exceeded"


def bao_dong_log(cac_dong) -> list:
    """Log engine có dòng vượt ngữ cảnh không.

    ⚠️ Đây là báo động về **chốt của ta**, không phải về engine: trần vào của
       cổng (`ngan_sach.TOKEN_VAO_TRAN`) lẽ ra đã chặn trước. Thấy dòng này là
       một lượt đã lọt qua chốt ấy — thường vì một bản sao trần ở đâu đó đã trôi.
    """
    hit = [d.strip() for d in (cac_dong or []) if DAU_VUOT_NGU_CANH in d]
    if not hit:
        return []
    return [BaoDong("vuot_ngu_canh", MUC_LOI, so_dong=len(hit),
                    dong_cuoi=hit[-1][:300])]


# ── 5. Trọng tài cư trú kẹt ở `LOI_NAP` ──────────────────────────────────────

def bao_dong_residency(trang_thai: str, lan_nap_loi: int = 0) -> list:
    """Nhóm GPU đang ở trạng thái nạp lỗi.

    Tên trạng thái đọc từ `platform_core.llm.residency` — **không gõ chuỗi**:
    docstring của module ấy nói rõ các chuỗi này đi vào CSDL và vào log, nên một
    bản sao ở đây sẽ trôi cùng lúc với một lần đổi tên trạng thái.

    ⚠️ `LOI_NAP` nghĩa là LTT-3.8 **không nằm trên card** và trọng tài đang lùi
       dần để thử lại. Mọi lượt tương tác tới 3.8 đang chờ, và thời gian lùi gấp
       đôi mỗi lần — nên nó phải kêu ngay lần đầu, không đợi tới lần thứ ba.
    """
    try:
        from platform_core.llm import residency
    except ImportError:                                          # pragma: no cover
        return []
    if str(trang_thai or "") == residency.LOI_NAP:
        return [BaoDong("residency_loi_nap", MUC_LOI,
                        trang_thai=str(trang_thai),
                        lan_nap_loi=int(lan_nap_loi or 0))]
    return []


# ── 6. Tiến trình lạ trên UUID 3090 ──────────────────────────────────────────
#
# ⚠️ DANH SÁCH NÀY LÀ MỘT **TUYÊN BỐ**, KHÔNG PHẢI MỘT PHÉP ĐO, và nó nói ra
#    như vậy. Nó khai những gì ĐƯỢC PHÉP tính trên card tranh chấp: engine LLM,
#    và ComfyUI (chạy bằng python). Task 0.3 đã liệt kê cái đang có thật trên
#    card ấy: `llama-server.exe` + ComfyUI; phần desktop (explorer/dwm/…) là đồ
#    hoạ WDDM chứ không phải tiến trình **tính toán**, nên `--query-compute-apps`
#    không trả chúng và danh sách này không cần kể tới chúng.
#
# ⇒ Mức `canh_bao`, không phải `loi`: một tiến trình lạ trên 3090 là thứ **phải
#   nhìn** (nó ăn vào biên của cấu hình chốt), nhưng bản thân nó chưa làm mất
#   dịch vụ, và ta không muốn một phiên RDP của chủ dự án làm kênh báo động đỏ.
TIEN_TRINH_CHO_PHEP = ("llama-server", "python", "pythonw")


def bao_dong_tien_trinh(tien_trinh, cho_phep=TIEN_TRINH_CHO_PHEP) -> list:
    """Tiến trình đang TÍNH trên card 3090 mà không nằm trong danh sách cho phép.

    `tien_trinh` là dạng `llm_gateway.gpu_uuid.tien_trinh(uuid)` trả về:
    `[(pid, ten, mib)]`, và hàm ấy **đã lọc theo `gpu_uuid`**, nên đây là số của
    đúng một card. ⛔ Đừng truyền danh sách chưa lọc: một tiến trình trên 5060 Ti
    báo về 3090 là một con số của card sai, tệ hơn không có con số nào.
    """
    goc_cho_phep = {str(c).lower() for c in cho_phep}
    la = []
    for pid, ten, mib in (tien_trinh or ()):
        goc = str(ten or "").replace(chr(92), "/").rsplit("/", 1)[-1].lower()
        if goc.endswith(".exe"):
            goc = goc[:-4]
        if goc in goc_cho_phep:
            continue
        la.append({"pid": int(pid), "ten": str(ten), "mib": int(mib)})
    if not la:
        return []
    return [BaoDong("tien_trinh_la_tren_3090", MUC_CANH_BAO, tien_trinh=la)]


def soi_bao_dong(*, health: "dict | None" = None,
                 shared_mib: "dict | None" = None,
                 upstream_metrics: "dict | None" = None,
                 dong_log=(), residency_trang_thai: str = "",
                 residency_lan_nap_loi: int = 0,
                 tien_trinh_3090=()) -> list:
    """Gộp cả sáu bộ dò. Đầu vào nào **không có** thì bộ dò ấy không chạy.

    ⛔ "Không có dữ liệu" KHÁC "lành", và chỗ phân biệt hai thứ ấy là ở đây: hàm
       này không sinh ra một báo động "lành" nào, nên một danh sách rỗng chỉ nói
       *"không bộ dò nào kêu"*. Người gọi phải in ra mình đã **đo được gì** —
       `main()` làm việc đó — nếu không thì một lượt không đo được gì sẽ trông y
       hệt một lượt mọi thứ đều tốt.
    """
    ra: list = []
    if health:
        ra += bao_dong_vram(health)
    for model, gt in sorted((shared_mib or {}).items()):
        ra += bao_dong_shared(model, gt)
    for model, van_ban in sorted((upstream_metrics or {}).items()):
        ra += bao_dong_deferred(model, van_ban)
    ra += bao_dong_log(dong_log)
    if residency_trang_thai:
        ra += bao_dong_residency(residency_trang_thai, residency_lan_nap_loi)
    ra += bao_dong_tien_trinh(tien_trinh_3090)
    return ra


def _token_nexus() -> str:
    """Token điều khiển Nexus. Ưu tiên đường dẫn khai tường minh.

    ⛔ `Path.home()` KHÔNG DÙNG ĐƯỢC KHI CHẠY THEO LỊCH, và đó là lý do biến môi
       trường này tồn tại. Một Scheduled Task chạy bằng `SYSTEM` có
       `USERPROFILE` = `C:\\Windows\\system32\\config\\systemprofile`, nơi không
       có tệp token nào. Công cụ khi đó trả `KHONG_DO_DUOC` — **thành thật**,
       nhưng vô dụng: nó chạy mỗi 15 phút để nói rằng nó không đo được.

    ⭐ Đây chính là hình dạng của khuyết tật P08 F-07. Công cụ đã tồn tại, đã có
       `test_370` chốt phán xử của nó, và **không ai chạy nó** — không task, không
       vòng bảo trì, không caller nào ngoài phép kiểm. Một bộ dò không ai chạy
       giảm nhẹ được **0**; năng lực có mà chốt kiểm soát thì không.
    """
    from os import environ
    duong = environ.get("LTT_NEXUS_TOKEN_FILE", "").strip()
    p = Path(duong) if duong else Path.home() / ".nexus" / "claude-code.token"
    return p.read_text(encoding="utf-8").strip() if p.exists() else ""


def _tren_may_b(lenh: str, tok: str, timeout: int = 60) -> str | None:
    """Chạy một lệnh đọc trên máy B. None = không hỏi được (KHÁC với 'hỏng')."""
    than = json.dumps({"command": lenh, "shell": "powershell",
                       "reason": "soi_cong_llm: doi chieu hai nguon"}).encode()
    yc = urllib.request.Request(
        NEXUS, data=than, method="POST",
        headers={"Content-Type": "application/json",
                 "X-Nexus-Protocol": "1", "Authorization": f"Bearer {tok}",
                 "User-Agent": "ltt-soi/1.0"})
    import ssl
    # Nexus dùng chứng chỉ tự ký trong LAN; đây là kênh nội bộ đã có bearer.
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        with urllib.request.urlopen(yc, timeout=timeout, context=ctx) as r:
            d = json.loads(r.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError,
            OSError, ValueError) as e:
        print(f"  [!] khong hoi duoc may B: {type(e).__name__}: {e}")
        return None
    if d.get("error"):
        print(f"  [!] Nexus tra loi: {json.dumps(d['error'])[:200]}")
        return None
    return (d.get("data") or {}).get("stdout", "")


# ══════════════════════════════════════════════════════════════════════════
#  THU THẬP — phần CÓ chạm mạng, tách hẳn khỏi phần phán xử ở trên
# ══════════════════════════════════════════════════════════════════════════
#
# ⚠️ PHẦN NÀY CHƯA ĐƯỢC CHẠY THẬT VỚI MÁY B (phiên 6.3 bị cấm chạm máy B), nên
#    nó đi sau một cờ `--bao-dong` **tự chọn**: đường mặc định của công cụ —
#    lượt đối chiếu `/health` với `Get-Service` vốn đang chạy theo lịch — không
#    đổi một dòng nào. Lớp phán xử ở trên thì đã chốt cả hai chiều bằng test.
#
# ⛔ NHÁY ĐƠN, KHÔNG NHÁY KÉP, vì lý do ghi ở docstring của lệnh thứ nhất: chuỗi
#    đi qua BA tầng (JSON → Nexus → PowerShell) và mỗi tầng ăn một loại escape.

NGAN_HEALTH = "---HEALTH---"
NGAN_PROC = "---PROC---"
NGAN_SHARED = "---SHARED---"


def _lenh_bao_dong() -> str:
    """Lệnh PowerShell lấy `/health`, tiến trình tính theo UUID, và Shared Usage."""
    return "; ".join((
        r"$e = Get-Content C:\ProgramData\LTTLlm\gateway.env",
        r"$t = ($e | Select-String '^LTT_LLM_TOKEN=').ToString().Split('=',2)[1].Trim()",
        r"$ha = 'Authorization: Bearer ' + $t",
        r"Write-Output '" + NGAN_HEALTH + r"'",
        r"curl.exe -s --max-time 8 -H $ha -H 'User-Agent: ltt-soi/1.0' "
        r"http://127.0.0.1:8299/health",
        r"Write-Output '" + NGAN_PROC + r"'",
        r"nvidia-smi --query-compute-apps=pid,process_name,used_memory,gpu_uuid "
        r"--format=csv,noheader,nounits",
        r"Write-Output '" + NGAN_SHARED + r"'",
        # Shared Usage KHÔNG có trong nvidia-smi — bộ đếm WDDM là đường duy nhất
        # đọc được phần tràn (cùng cách `docs/.../artifacts/bench/bench.py` dùng).
        r"foreach ($pr in (Get-Process llama-server -ErrorAction SilentlyContinue)) "
        r"{ $s = Get-Counter ('" + chr(92) + r"GPU Process Memory(pid_' + "
        r"$pr.Id + '*)" + chr(92) + r"Shared Usage') -ErrorAction "
        r"SilentlyContinue; $v = 0; if ($s) { $v = ($s.CounterSamples | "
        r"Measure-Object -Property CookedValue -Sum).Sum }; "
        r"Write-Output ([string]$pr.Id + '=' + [string][int]($v / 1MB)) }",
    ))


def _cat_khuc(ra: str) -> dict:
    """Tách stdout thành ba khúc theo ba dòng ngăn. Thiếu khúc nào ⇒ khúc rỗng."""
    khuc, ten = {NGAN_HEALTH: [], NGAN_PROC: [], NGAN_SHARED: []}, ""
    for dong in (ra or "").splitlines():
        d = dong.strip()
        if d in khuc:
            ten = d
            continue
        if ten:
            khuc[ten].append(dong)
    return {k: "\n".join(v).strip() for k, v in khuc.items()}


def _doc_proc(van_ban: str) -> list:
    """`[(pid, ten, mib, uuid)]` từ đầu ra `--query-compute-apps` dạng csv.

    ⚠️ `used_memory` trả `[N/A]` trên WDDM ở nhiều driver: ghi 0 nhưng **giữ
       dòng**. Sự tồn tại của tiến trình là tin chắc chắn; chỉ dung lượng là
       không biết, và bỏ cả dòng vì thiếu một ô là biến "có việc đang chạy"
       thành "card rảnh" (cùng luật với `gpu_uuid.tien_trinh`).
    """
    ra = []
    for dong in (van_ban or "").splitlines():
        o = [x.strip() for x in dong.split(",")]
        if len(o) < 4:
            continue
        try:
            pid = int(o[0])
        except ValueError:
            continue
        try:
            mib = int(float(o[2]))
        except ValueError:
            mib = 0
        ra.append((pid, o[1], mib, o[3]))
    return ra


def _doc_shared(van_ban: str) -> dict:
    """`{pid: MiB}` từ các dòng `<pid>=<mib>`."""
    ra = {}
    for dong in (van_ban or "").splitlines():
        d = dong.strip()
        if "=" not in d:
            continue
        a, b = d.split("=", 1)
        try:
            ra[int(a)] = int(float(b))
        except ValueError:
            continue
    return ra


def gom_shared_theo_model(health: dict, proc: list, shared: dict) -> dict:
    """`{model: Shared Usage MiB}` — cộng theo **đúng card của model ấy**.

    🔴 ĐÂY LÀ CHỖ "THEO UUID" THẬT SỰ XẢY RA. Bộ đếm WDDM khoá theo **tiến
       trình**, không theo card; nên phép quy về card đi qua `nvidia-smi
       --query-compute-apps ... ,gpu_uuid`: tiến trình nào đang tính trên UUID
       nào. Không có bước đó thì một `llama-server` của 5060 Ti sẽ được cộng vào
       con số của 3090 — đúng lớp lỗi đã phải sửa ở ba tệp ngày 12/09.
    """
    theo_vai = ((health.get("gpu") or {}).get("theo_vai") or {})
    ra = {}
    for model in (health.get("gioi_han") or {}):
        vai = _vai_cua(model)
        uu = str((theo_vai.get(vai) or {}).get("uuid") or "")
        if not uu:
            ra[model] = None
            continue
        pids = [pid for pid, ten, _m, u in proc
                if u == uu and "llama-server" in str(ten).lower()]
        if not pids:
            ra[model] = None
            continue
        ra[model] = sum(int(shared.get(pid, 0)) for pid in pids)
    return ra


def doc_residency() -> tuple:
    """`(trạng thái, lần nạp lỗi)` của nhóm cư trú, từ CSDL máy A. `("", 0)` = không đọc được.

    ⛔ KHÔNG hỏi máy B. `gpu_residency` là sổ của **máy A** — trọng tài chạy ở
       đó — và hỏi sai máy ở đây sẽ trả lời một câu hoàn toàn khác.
    """
    try:
        from platform_core.db import get_session
        from platform_core.models import GpuResidency
    except ImportError:
        return "", 0
    gen = get_session()
    db = next(gen)
    try:
        row = db.query(GpuResidency).first()
        if row is None:
            return "", 0
        return str(row.trang_thai or ""), int(row.lan_nap_loi or 0)
    except Exception as e:                                       # noqa: BLE001
        print(f"  [!] khong doc duoc gpu_residency: {type(e).__name__}: {e}")
        return "", 0
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def chay_bao_dong(tok: str) -> int:
    """Một lượt báo động đầy đủ. Trả mã thoát.

    ⛔ IN RA MÌNH ĐÃ ĐO ĐƯỢC GÌ, trước khi in kết luận. Một danh sách báo động
       rỗng vì **không đo được gì** trông y hệt một danh sách rỗng vì mọi thứ
       lành — và hai thứ ấy đòi hai hành động ngược nhau.
    """
    ra = _tren_may_b(_lenh_bao_dong(), tok, timeout=90)
    if ra is None:
        print("=> KHONG KET LUAN DUOC (bao dong). Day KHONG phai 'lanh'.")
        return KHONG_DO_DUOC
    khuc = _cat_khuc(ra)
    try:
        health = json.loads(khuc[NGAN_HEALTH]) if khuc[NGAN_HEALTH] else {}
    except ValueError:
        health = {}
    proc = _doc_proc(khuc[NGAN_PROC])
    shared = _doc_shared(khuc[NGAN_SHARED])
    shared_model = gom_shared_theo_model(health, proc, shared) if health else {}
    tt, lan = doc_residency()

    uuid_38 = str((((health.get("gpu") or {}).get("theo_vai") or {})
                   .get("ltt38") or {}).get("uuid") or "")
    tren_3090 = [(pid, ten, mib) for pid, ten, mib, u in proc if u == uuid_38]

    print(f"  do duoc: health={'co' if health else 'KHONG'} "
          f"tien_trinh={len(proc)} shared_pid={len(shared)} "
          f"residency={tt or '<khong doc duoc>'}")
    canh = soi_bao_dong(health=health, shared_mib=shared_model,
                        residency_trang_thai=tt, residency_lan_nap_loi=lan,
                        tien_trinh_3090=tren_3090)
    if not canh:
        print("  KHONG BO DO NAO KEU (voi nhung gi do duoc o tren).")
        return LANH
    for c in canh:
        print(f"  [{c['muc']}] {c['ma']}: "
              + json.dumps({k: v for k, v in c.items()
                            if k not in ('ma', 'muc')}, ensure_ascii=False))
    return LECH if any(c["muc"] == MUC_LOI for c in canh) else LANH


def main() -> int:
    p = argparse.ArgumentParser(
        description="Doi chieu /health voi Get-Service tren may B.")
    p.add_argument("--im", action="store_true",
                   help="chi in khi co gi do lech (hop de chay theo lich)")
    p.add_argument("--bao-dong", action="store_true", dest="bao_dong",
                   help="chay them sau bo do cua cong dual-model (Task 6.3)")
    a = p.parse_args()

    tok = _token_nexus()
    if not tok:
        print("KHONG CO TOKEN NEXUS (~/.nexus/claude-code.token)")
        return KHONG_DO_DUOC

    # Một lượt gọi lấy CẢ HAI nguồn, để chúng nói về CÙNG một khoảnh khắc.
    # Hai lượt gọi cách nhau vài giây là hai ảnh chụp khác nhau, và đúng cái
    # lệch ta đang săn có thể lọt qua khe giữa chúng.
    # ⛔ KHÔNG dùng dấu nháy kép lồng trong chuỗi này. Nó đi qua BA tầng —
    #    JSON → Nexus → PowerShell — và mỗi tầng ăn một loại escape khác nhau.
    #    Bản đầu viết `\"Authorization: ...\"`: PowerShell thoát bằng backtick
    #    chứ không phải backslash, nên nó nhận literal `\"` và cả lệnh câm, trả
    #    stdout rỗng.
    #
    # ⇒ Chỉ nháy đơn + nối chuỗi bằng `+`. Nhàm hơn, nhưng nó qua được cả ba tầng.
    lenh = "; ".join((
        r"$e = Get-Content C:\ProgramData\LTTLlm\gateway.env",
        r"$t = ($e | Select-String '^LTT_LLM_TOKEN=').ToString().Split('=',2)[1].Trim()",
        r"$ha = 'Authorization: Bearer ' + $t",
        r"$h = (curl.exe -s -o NUL -w '%{http_code}' --max-time 5 -H $ha "
        r"-H 'User-Agent: ltt-soi/1.0' http://127.0.0.1:8299/health)",
        r"$s = (Get-Service LTTLlmGateway).Status",
        r"$l = (Get-Service LTTLlamaSwap).Status",
        r"$c = (Get-NetTCPConnection -LocalPort 8299 -State Listen "
        r"-ErrorAction SilentlyContinue).OwningProcess",
        r"$m = (Get-WmiObject Win32_Service | Where-Object Name -eq "
        r"'LTTLlmGateway').ProcessId",
        r"'health=' + $h + ';gateway=' + $s + ';llamaswap=' + $l + "
        r"';pid_cong=' + $c + ';pid_scm=' + $m",
    ))
    ra = _tren_may_b(lenh, tok)
    if ra is None:
        print("=> KHONG KET LUAN DUOC. Day KHONG phai 'lanh'.")
        return KHONG_DO_DUOC

    # Không để một stdout lạ làm vỡ công cụ bằng `IndexError`. Một công cụ giám
    # sát mà chết vì đầu vào lạ thì im lặng đúng lúc nó cần nói nhất.
    dong = [x for x in ra.strip().splitlines() if "health=" in x]
    if not dong:
        print("  [!] may B tra ve thu khong doc duoc:")
        print("      " + (repr(ra)[:400] if ra.strip() else "<stdout RONG>"))
        print("=> KHONG KET LUAN DUOC. Day KHONG phai 'lanh'.")
        return KHONG_DO_DUOC
    d = dict(x.split("=", 1) for x in dong[-1].split(";") if "=" in x)
    health = d.get("health", "")
    gateway = d.get("gateway", "")
    ma, nhan = phan_xu(health, gateway)
    lech = nhan == "xanh-gia"

    if not a.im or ma != LANH:
        print(f"  /health            : {health or '<khong tra loi>'}")
        print(f"  Get-Service gateway: {gateway}")
        print(f"  Get-Service swap   : {d.get('llamaswap')}")
        print(f"  pid giu cong 8299  : {d.get('pid_cong') or '<khong ai>'}")
        print(f"  pid SCM biet       : {d.get('pid_scm')}")

    if lech:
        print()
        print("  🔴 LECH -- HEALTH XANH GIA.")
        print(f"     /health=200 nhung dich vu = {gateway}.")
        print("     Nhieu kha nang mot tien trinh MO COI dang giu cong 8299 va")
        print("     phuc vu /health. No KHONG co ai dung day neu no chet.")
        print()
        print("     Xu ly tren may B:")
        print(f"       Stop-Process -Id {d.get('pid_cong')} -Force")
        print("       Start-Service LTTLlmGateway")
        return ma

    if ma != LANH:
        print(f"\n  Dich vu khong khoe ({nhan}), NHUNG hai nguon KHOP nhau "
              "-- do la mot hong TU BAO, khong phai xanh gia.")
        return ma

    if not a.im:
        print("\n  LANH -- hai nguon khop nhau.")
    if a.bao_dong:
        print()
        ma_bd = chay_bao_dong(tok)
        if ma_bd != LANH:
            return ma_bd
    return ma


if __name__ == "__main__":
    sys.exit(main())
