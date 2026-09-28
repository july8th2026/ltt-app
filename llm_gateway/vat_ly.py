"""
vat_ly.py — rào VẬT LÝ của cổng máy B, đọc thẳng từ `llama-swap.yaml`. (phương án C, bước 3)

⭐ MÁY A LÀ NGƯỜI QUYẾT ĐỊNH DUY NHẤT (`docs/ltt_llm_dual/KE_HOACH_PHUONG_AN_C.md`
   §3). Cổng này không có luật công bằng, không có nhịp, không có trần riêng: nó
   chỉ giữ ba bất biến mà engine **không tự giữ được**:

     1. số chuỗi đang chạy        ≤ `-np`  của hồ sơ
     2. Σ token đặt chỗ           ≤ `-c`   của hồ sơ   (`-kvu`: một bể cho mọi slot)
     3. token vào của một lượt    ≤ `-c` − max_out − DEM_UOC   (cùng công thức với A)

   Vượt 1/2 ⇒ 429 (A xếp hàng lại). Vượt 3 ⇒ 413 (cùng trần A đã kiểm trước 200).

🔴 VÌ SAO ĐỌC YAML THAY VÌ GÕ SỐ. Trước bước này `-c`/`-np` sống ở **ba** chỗ trên
   máy B — `catalog.max_context`, env nay ĐÃ GỠ `LTT_LLM_MAX_DONG_THOI[__m]`,
   `LTT_LLM_TOKEN_POOL[__m]` — cộng `LTT_LLM_MAX_INPUT_TOKENS` ép **186.368 cho cả
   hai model** (O-02: sai cho 3.5). Tệp yaml là thứ **khởi động tiến trình**; mọi
   bản sao khác chỉ là lời kể về nó.

⛔ KHÔNG PHỤ THUỘC PyYAML. venv máy B chỉ cài `fastapi uvicorn httpx psutil`
   (`deploy/deploy.ps1` bước 4, bỏ qua được bằng `-BoQuaVenv`). Một import thiếu ở
   đây là cổng **không khởi động** — nên bộ đọc là một bộ đọc HẸP cho đúng hình
   dạng tệp của ta, và `tests/test_1223_phuong_an_c_rao_vat_ly_b.py` buộc nó cho
   cùng kết quả với `yaml.safe_load` trên tệp thật.

⛔ FAIL-CLOSED. Không tìm thấy tệp, hoặc một hồ sơ thiếu `-c`/`-np` ⇒ ném
   `YamlHong`. Cổng không đoán sức chứa của một card.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

#: Biến môi trường chỉ đường tệp — **đường dẫn, không phải con số**. Chỉ dùng khi
#: bố cục chuẩn không áp dụng (chẩn đoán, máy thử). Đặt mà tệp không tồn tại ⇒
#: `YamlHong`, không lặng lẽ lùi về tệp khác.
BIEN_DUONG_YAML = "LTT_LLM_SWAP_YAML"

TEN_TEP = "llama-swap.yaml"


class YamlHong(RuntimeError):
    """Không dựng được rào vật lý từ `llama-swap.yaml`."""


@dataclass(frozen=True)
class VatLy:
    """Sức chứa vật lý của MỘT hồ sơ, đúng như llama-server được khởi động."""

    #: `-c` / `--ctx-size`. Với `-kvu` đây là bể KV **chung** mọi slot.
    ctx: int
    #: `-np` / `--parallel`: số chuỗi engine chạy cùng lúc.
    np: int
    #: `--reasoning-budget` (None khi không khai). Chỉ để công bố/đối chiếu: suy
    #: nghĩ nằm TRONG `n_predict`, không cộng thêm vào đặt chỗ (kế hoạch §3.1, R-1).
    reasoning_budget: Optional[int] = None
    #: Cờ `-kvu` / `--kv-unified` có mặt.
    kvu: bool = False
    #: `--image-min-tokens` / `--image-max-tokens` — sàn và trần token của MỘT ảnh.
    #:
    #: ⭐ Đây là hai con số duy nhất quyết định chi phí ngữ cảnh của một ảnh, và
    #:    trước 28/09/2026 chúng **ngầm** (không hồ sơ nào truyền cờ) nên không ai
    #:    tính được chi phí ấy trước khi đặt chỗ KV. Xem
    #:    `docs/superpowers/specs/2026-09-28-vision-plan-lock.md`.
    #:
    #: ⛔ KHÔNG `bat_buoc=True`, và đó là một quyết định về **kiểu hỏng**: một
    #:    yaml cũ (chưa kịp deploy) sẽ làm cổng **không khởi động được** — tức
    #:    một lỗi ảnh biến thành một sự cố toàn phần cho cả khách chỉ gửi chữ.
    #:    Vắng ⇒ `None` ⇒ người tính ngân sách ảnh từ chối ĐÚNG ảnh, với lỗi rõ
    #:    ràng, còn đường chữ chạy nguyên. `tests/test_4204_*` canh để tệp yaml
    #:    của ta không bao giờ thiếu chúng một cách lặng lẽ.
    token_anh_toi_thieu: Optional[int] = None
    token_anh_toi_da: Optional[int] = None


# ── Tìm tệp ────────────────────────────────────────────────────────────────────

def _thu_muc_goi() -> Path:
    """Thư mục gói `llm_gateway`, neo bằng TÊN chứ không đếm cấp (`AGENTS.md`)."""
    p = Path(__file__).resolve().parent
    if p.name != "llm_gateway":
        raise YamlHong(f"vat_ly.py khong nam trong goi `llm_gateway` ({p})")
    return p


def cac_duong_ung_vien() -> tuple[Path, ...]:
    """Thứ tự dò, rẻ tới đắt:

    1. `<gốc cài>/llama-swap.yaml` — cạnh gói `llm_gateway`. Trên máy B đó là
       `H:\\LTT_LLM\\gateway\\llama-swap.yaml`: **đúng tệp** `LTTLlamaSwap` đọc
       (`deploy/cai_dat_dich_vu.ps1`: `--config $Goc\\gateway\\llama-swap.yaml`).
    2. `llm_gateway/deploy/llama-swap.yaml` — bản trong kho (máy A, bộ test).
       Trên máy B nó cũng có mặt (`scp -r` cả gói) và giống hệt (1) ngay sau
       deploy — nhưng (1) mới là tệp tiến trình chạy, nên (1) thắng.
    """
    goi = _thu_muc_goi()
    return (goi.parent / TEN_TEP, goi / "deploy" / TEN_TEP)


def tim_yaml() -> Path:
    chi_dinh = (os.environ.get(BIEN_DUONG_YAML) or "").strip()
    if chi_dinh:
        p = Path(chi_dinh)
        if not p.is_file():
            raise YamlHong(f"{BIEN_DUONG_YAML}={chi_dinh} khong phai tep ton tai")
        return p
    for p in cac_duong_ung_vien():
        if p.is_file():
            return p
    raise YamlHong("khong tim thay llama-swap.yaml o: "
                   + ", ".join(str(p) for p in cac_duong_ung_vien()))


# ── Đọc tệp (bộ đọc HẸP, không PyYAML) ─────────────────────────────────────────

_KHOA = re.compile(r"^(?P<thut>\s*)(?P<khoa>[A-Za-z0-9_.-]+):(?:\s+(?P<gt>.*))?$")
_KHOI = ("|", "|-", "|+", ">", ">-", ">+")


def _bo_chu_thich(gt: str) -> str:
    """Bỏ `  # ...` cuối một scalar KHÔNG ngoặc (YAML: `#` sau khoảng trắng)."""
    m = re.search(r"\s#", gt)
    return gt[:m.start()] if m else gt


def _scalar(gt: str) -> str:
    gt = gt.strip()
    if len(gt) >= 2 and gt[0] == gt[-1] and gt[0] in "\"'":
        return gt[1:-1]
    return _bo_chu_thich(gt).strip()


def _thut(dong: str) -> int:
    return len(dong) - len(dong.lstrip(" "))


def _doc_khoi(dong: list[str], i: int, thut_cha: int) -> tuple[str, int]:
    """Đọc một block scalar bắt đầu ở dòng `i`. Trả `(văn bản, chỉ số dòng kế)`.

    Block kết thúc ở dòng không trống đầu tiên thụt **không sâu hơn** khoá cha.
    Ta chỉ tách token bằng khoảng trắng nên gập (`>`) hay giữ dòng (`|`) như nhau.
    """
    phan: list[str] = []
    while i < len(dong):
        d = dong[i]
        if d.strip() and _thut(d) <= thut_cha:
            break
        phan.append(d.strip())
        i += 1
    return "\n".join(phan).strip(), i


def _doc_bang(van: str) -> tuple[dict[str, str], dict[str, str]]:
    """`(macros, {hồ sơ: cmd})` từ văn bản yaml."""
    dong = van.replace("\r\n", "\n").split("\n")
    macros: dict[str, str] = {}
    cmd: dict[str, str] = {}
    muc = ""            # khoá cấp 0 đang đứng trong
    ho_so = ""          # hồ sơ cấp 2 đang đứng trong (dưới `models:`)
    i = 0
    while i < len(dong):
        d = dong[i]
        tron = d.strip()
        if not tron or tron.startswith("#"):
            i += 1
            continue
        m = _KHOA.match(d)
        if not m:
            i += 1
            continue
        thut, khoa, gt = _thut(d), m.group("khoa"), (m.group("gt") or "").strip()
        if thut == 0:
            muc, ho_so = khoa, ""
            i += 1
            continue
        khoi = _bo_chu_thich(gt).strip() in _KHOI
        if muc == "macros" and thut == 2:
            if khoi:
                macros[khoa], i = _doc_khoi(dong, i + 1, thut)
                continue
            macros[khoa] = _scalar(gt)
        elif muc == "models" and thut == 2:
            ho_so = khoa
        elif muc == "models" and thut == 4 and ho_so and khoa == "cmd":
            if khoi:
                cmd[ho_so], i = _doc_khoi(dong, i + 1, thut)
                continue
            cmd[ho_so] = _scalar(gt)
        i += 1
    return macros, cmd


def _mo_macro(s: str, macros: dict[str, str]) -> str:
    for _ in range(8):          # macro lồng macro: vài vòng là đủ, chặn vòng lặp
        moi = re.sub(r"\$\{([A-Za-z0-9_]+)\}",
                     lambda m: macros.get(m.group(1), m.group(0)), s)
        if moi == s:
            return s
        s = moi
    return s


def _so_sau(tach: list[str], ten: tuple[str, ...], ho_so: str,
            bat_buoc: bool) -> Optional[int]:
    vi_tri = [k for k, t in enumerate(tach) if t in ten]
    if not vi_tri:
        if bat_buoc:
            raise YamlHong(f"ho so {ho_so} khong khai {'/'.join(ten)}")
        return None
    k = vi_tri[-1]              # llama.cpp: co khai sau thang
    try:
        so = int(tach[k + 1])
    except (IndexError, ValueError):
        raise YamlHong(f"ho so {ho_so}: {tach[k]} khong theo sau boi so nguyen") from None
    if bat_buoc and so <= 0:
        raise YamlHong(f"ho so {ho_so}: {tach[k]} {so} khong duong")
    return so


def doc_van_ban(van: str) -> dict[str, VatLy]:
    """`{hồ sơ: VatLy}` từ nội dung `llama-swap.yaml`. Ném `YamlHong` khi thiếu."""
    macros, cmd = _doc_bang(van)
    if not cmd:
        raise YamlHong("llama-swap.yaml khong co ho so nao co `cmd`")
    ra: dict[str, VatLy] = {}
    for ho_so, lenh in cmd.items():
        tach = _mo_macro(lenh, macros).split()
        ra[ho_so] = VatLy(
            ctx=int(_so_sau(tach, ("-c", "--ctx-size"), ho_so, True) or 0),
            np=int(_so_sau(tach, ("-np", "--parallel"), ho_so, True) or 0),
            reasoning_budget=_so_sau(tach, ("--reasoning-budget",), ho_so, False),
            kvu=("-kvu" in tach or "--kv-unified" in tach),
            token_anh_toi_thieu=_so_sau(tach, ("--image-min-tokens",), ho_so, False),
            token_anh_toi_da=_so_sau(tach, ("--image-max-tokens",), ho_so, False),
        )
    return ra


def doc_tep(p: Path) -> dict[str, VatLy]:
    try:
        van = p.read_text(encoding="utf-8")
    except OSError as e:
        raise YamlHong(f"khong doc duoc {p}: {e}") from None
    return doc_van_ban(van)


# ── Hai phép tính dùng chung với máy A ─────────────────────────────────────────

def tran_vao(v: VatLy, max_out: int, dem_uoc: int) -> int:
    """Trần token vào của một lượt = `-c − max_out − DEM_UOC`.

    CÙNG công thức với `apps/ltt_llm/ngan_sach.tran_vao_cua(m)` — hai đầu cùng
    công thức thì một lượt A nhận không bao giờ bị B trả 413 sau 200 (O-02).
    """
    return max(0, int(v.ctx) - int(max_out) - int(dem_uoc))


def token_giu(*, token_vao: int, xin_ra: int, v: VatLy, dem_uoc: int,
              token_khai: int = 0) -> int:
    """Token KV lượt này giữ trong bể của hồ sơ.

    ⭐ CÓ HEADER `X-LTT-Token-Dat` ⇒ DÙNG ĐÚNG SỐ CỦA MÁY A. Máy A đã giữ lease
       bằng chính số ấy; hai sổ đếm cùng một số thì "A nhận" ⇒ "B nhận" (A ⊆ B,
       kế hoạch §3.1 bất biến 4). Bản trước lấy `max(B tự ước, header)`: B ước
       `max_tokens` không kẹp theo chỗ còn nên có thể CAO hơn A ⇒ 429 sau 200.

    ⛔ Nhưng không dưới **token vào** B vừa đo: một header thấp hơn chính đầu vào
       là header hỏng (bản A cũ, nối dây sai). Sàn này là phép đo vật lý, không
       phải chính sách — thiếu nó thì một header `1` biến bể KV thành vô hạn.

    VẮNG HEADER (công cụ nội bộ gọi thẳng `:8299`) ⇒ cùng công thức với
    `platform_core/llm/tham_so_da_luot.luat_cho`:
    `vào + min(xin_ra, -c − vào − DEM_UOC) + DEM_UOC` (ảnh đã nằm trong `vào`).
    """
    vao = max(0, int(token_vao))
    if int(token_khai) > 0:
        return max(int(token_khai), vao, 1)
    ra = max(0, min(int(xin_ra), int(v.ctx) - vao - int(dem_uoc)))
    return max(1, vao + ra + int(dem_uoc))
