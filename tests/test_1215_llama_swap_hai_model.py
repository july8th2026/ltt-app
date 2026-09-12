"""Task 3.3 — `llama-swap.yaml` phải mở HAI model trên HAI card, CÙNG LÚC.

🔴 VÌ SAO TỆP NÀY TỒN TẠI

`llama-swap.yaml` là tệp của **máy B**: không một phép kiểm nào trên máy A chạy
nó, và mọi thứ trong nó chỉ sai **sau khi deploy**, thường là im lặng. Ba lớp lỗi
đã đo được của chính tệp này:

1. **Model thứ hai TẮT model thứ nhất, không một lời báo.** Model không khai
   nhóm nằm trong nhóm ẩn `(default)` của llama-swap với `swap: true`. Nạp cái
   thứ hai thì cái thứ nhất bị tắt; `/running` chỉ còn một model và lượt đang
   chạy nhận `ConnectionReset` (đo 03/09). `swap: false` là cờ **duy nhất** đổi
   điều đó — nên nó phải được canh, không phải được nhớ.
2. **`--presence-penalty` ăn 11 % tốc độ mà không mua gì** (L-16: 56,61 so với
   63,01 tok/s; 56,61 nằm **dưới** ngưỡng 60,0 của cổng nghiệm thu B, chất lượng
   không đổi). Nó là một cờ *trông có lý* — chính vì thế L-15 đã chốt nó một lần
   và phải sửa ở L-16. Sự vắng mặt của nó phải là một phép kiểm, không phải một
   ghi chép.
3. **Hai model thường trú là an toàn CHỈ VÌ chúng ở hai card khác nhau.** Gỡ một
   dòng `CUDA_VISIBLE_DEVICES` mà để nguyên `swap: false` là mời hai model
   (~16,5 GiB + ~7,3 GiB trọng số) lên cùng một card 24,5 GiB.

⭐ Nên tệp này đọc **cấu hình đã khai triển macro** — thứ thật sự thành dòng lệnh
   `llama-server` — chứ không đọc văn bản thô. Một cờ nằm trong `${CHUNG}` và một
   cờ gõ thẳng vào `cmd` là **cùng một điều** với engine, nên phép kiểm không
   được phân biệt chúng.

⚠️ Và nó KHÔNG quét chuỗi trong chú thích. `llama-swap.yaml` có một khối đính
   chính giải thích *vì sao* `qwen38-vision` biến mất; một phép kiểm
   `"qwen38-vision" not in van` sẽ **trừng phạt việc giải thích** và ép người sau
   xoá lịch sử đo được để làm cho phép kiểm xanh. Ở đây hồ sơ được đọc bằng
   `yaml.safe_load`, tức đúng cái llama-swap đọc.

Nguồn số: `docs/ltt_llm_dual/10_BENCHMARK_P3.md` (G1b, G2, G3, G3b, G5),
`docs/ltt_llm_dual/DECISION_LOG.md` (L-14, L-15, L-16).
"""
from __future__ import annotations

import json
import pathlib
import re

import pytest
import yaml

GOC = pathlib.Path(__file__).resolve().parents[1]
YAML = GOC / "llm_gateway" / "deploy" / "llama-swap.yaml"
GPU_JSON = GOC / "llm_gateway" / "deploy" / "gpu_may_b.json"

#: Hai hồ sơ dual-model, và ánh xạ sang **vai** GPU trong `gpu_may_b.json`.
#: Không hard-code UUID ở đây: một lần đo lại card chỉ được sửa MỘT tệp (Task 0.2).
VAI_CUA_HO_SO = {"qwen38-api": "ltt38", "qwen35-api": "ltt35"}

#: Bộ cờ chốt ở **L-16 phương án B**. `--reasoning-budget` là cờ server-global
#: (không gửi được per-request) nên nó là thuộc tính của hồ sơ; tham số lấy mẫu
#: đặt ở server vì cache CUDA graph khoá theo bộ tham số.
CO_L16 = (
    ("--reasoning-budget", "512"),
    ("--temp", "0.6"),
    ("--top-p", "0.95"),
    ("--top-k", "20"),
    ("--min-p", "0"),
)

#: ⛔ Cờ bị L-16 **gỡ bỏ** sau khi L-15 đã chốt nó. Xem docstring đầu tệp.
CO_BI_CAM = "--presence-penalty"


def _doc_yaml(duong: pathlib.Path = YAML) -> dict:
    return yaml.safe_load(duong.read_text(encoding="utf-8"))


def _khai_trien(cfg: dict, ten: str) -> list[str]:
    """Dòng lệnh **thật** của một hồ sơ: `cmd` sau khi thay mọi macro.

    Đây là điều duy nhất `llama-server` nhìn thấy. Một cờ trong `${CHUNG}` và một
    cờ gõ thẳng vào `cmd` là cùng một điều với nó.
    """
    cmd = str(cfg["models"][ten]["cmd"])
    for khoa, gt in (cfg.get("macros") or {}).items():
        cmd = cmd.replace("${%s}" % khoa, str(gt))
    return cmd.split()


def _uuid_ghim(cfg: dict, ten: str) -> str | None:
    for x in cfg["models"][ten].get("env") or []:
        if str(x).startswith("CUDA_VISIBLE_DEVICES="):
            return str(x).split("=", 1)[1]
    return None


def _tham_so(dong_lenh: list[str], co: str) -> str | None:
    """Giá trị đi ngay sau `co`, hoặc `None` nếu không có cờ đó."""
    if co not in dong_lenh:
        return None
    i = dong_lenh.index(co)
    return dong_lenh[i + 1] if i + 1 < len(dong_lenh) else ""


def _ho_so_vi_pham_presence_penalty(cfg: dict) -> list[str]:
    """Hàm phán xử của phép kiểm L-16 — **dùng lại được** cho đối chứng.

    ⭐ Đối chứng phải gọi ĐÚNG hàm mà phép kiểm gọi. Viết lại logic trong phần
       đối chứng là đối chứng cho một bản sao, không cho phép kiểm thật.
    """
    return [ten for ten in cfg.get("models") or {}
            if CO_BI_CAM in _khai_trien(cfg, ten)]


@pytest.fixture(scope="module")
def cfg() -> dict:
    return _doc_yaml()


@pytest.fixture(scope="module")
def gpu_map() -> dict[str, dict]:
    return {x["vai"]: x for x in json.loads(GPU_JSON.read_text(encoding="utf-8"))}


# ── Hai hồ sơ, và chỉ hai ──────────────────────────────────────────────────

def test_dung_hai_ho_so_khong_con_ho_so_vision_rieng(cfg):
    """`qwen38-vision` biến mất (D02, L-14 hệ quả 4), và không lẻn lại được.

    Lý do nó biến mất không phải gọn gàng: hai hồ sơ **cùng một model** mở ra cho
    khách là một nguồn `ConnectionReset` ngẫu nhiên — llama-swap **giết lượt đang
    chạy** để nạp hồ sơ khác (đo 03/09). Nay mmproj nằm trong `qwen38-api`, đổi
    bằng ~40.000 token ngữ cảnh (mmproj trên GPU tốn ~1.136 MiB — G1b).
    """
    assert set(cfg["models"]) == set(VAI_CUA_HO_SO), (
        f"ho so trong llama-swap.yaml: {sorted(cfg['models'])}")
    assert not [t for t in cfg["models"] if "vision" in t], (
        "mot ho so vision rieng da len lai vao llama-swap.yaml")


# ── Cùng lúc: group, ttl, preload ──────────────────────────────────────────

def test_hai_ho_so_trong_MOT_nhom_cho_phep_cung_thuong_tru(cfg):
    """⭐ ĐÂY LÀ PHÉP KIỂM TRUNG TÂM CỦA TASK 3.3.

    `swap: false` là cờ **duy nhất** cho hai thành viên cùng nằm trong VRAM. Thiếu
    nó thì `ttl: 0` và `preload` đều vô nghĩa: preload nạp `qwen38-api` rồi nạp
    `qwen35-api`, và bước thứ hai **tắt** bước thứ nhất — `/running` chỉ còn một
    model, không một lỗi nào.

    Và cả hai hồ sơ phải nằm **trong** nhóm: một hồ sơ bỏ ngoài rơi về nhóm ẩn
    `(default)` (`swap: true`), tức nó vẫn đẩy model kia ra.
    """
    nhom = cfg.get("groups") or {}
    assert nhom, "khong khai `groups` => ca hai ho so nam trong nhom an (default) swap:true"
    chua_ca_hai = [ten for ten, g in nhom.items()
                   if set(g.get("members") or []) >= set(VAI_CUA_HO_SO)]
    assert len(chua_ca_hai) == 1, (
        f"can DUNG mot nhom chua ca hai ho so, dang co: "
        f"{ {t: (g.get('members') or []) for t, g in nhom.items()} }")
    g = nhom[chua_ca_hai[0]]
    assert g.get("swap") is False, (
        f"nhom {chua_ca_hai[0]} co swap={g.get('swap')!r}; phai la False, neu "
        "khong thi model thu hai TAT model thu nhat khi nap")


def test_swap_false_chi_an_toan_khi_moi_thanh_vien_o_MOT_card_rieng(cfg):
    """⛔ An toàn của `swap: false` KHÔNG đến từ `swap: false`.

    Nó đến từ hai dòng `CUDA_VISIBLE_DEVICES` ghim hai UUID **khác nhau**. Gỡ một
    dòng ghim rồi để nguyên nhóm là mời ~16,5 GiB + ~7,3 GiB trọng số lên cùng
    một card 24,5 GiB — đúng lần OOM mà chú thích cũ của tệp cảnh báo.
    """
    for ten_nhom, g in (cfg.get("groups") or {}).items():
        if g.get("swap") is not False:
            continue
        theo_uuid: dict[str, list[str]] = {}
        for ten in g.get("members") or []:
            u = _uuid_ghim(cfg, ten)
            assert u and u.startswith("GPU-"), (
                f"{ten} nam trong nhom swap:false ma khong ghim UUID: {u!r}")
            theo_uuid.setdefault(u, []).append(ten)
        trung = {u: ts for u, ts in theo_uuid.items() if len(ts) > 1}
        assert not trung, (
            f"nhom {ten_nhom} (swap:false) dat nhieu ho so len CUNG mot card: {trung}")


def test_moi_ho_so_ghim_dung_UUID_THEO_VAI(cfg, gpu_map):
    """Đúng card, không chỉ *khác* card: 27B trên 3090, 9B trên 5060 Ti (D-09a).

    Hai UUID hoán vị cho nhau vẫn thoả phép kiểm "khác nhau" ở trên, mà lúc đó
    model 27B (~16,5 GiB) sẽ nằm trên card 16 GiB và không nạp nổi.
    """
    for ten, vai in VAI_CUA_HO_SO.items():
        assert _uuid_ghim(cfg, ten) == gpu_map[vai]["uuid"], (
            f"{ten} phai ghim UUID vai {vai} ({gpu_map[vai]['ten']})")


def test_preload_liet_ke_CA_HAI_ho_so(cfg):
    """`hooks.on_startup.preload` phải nạp sẵn cả hai, không chỉ model mặc định.

    Nạp từ kho ấm 15,23 s (3.8) / 10,12 s (3.5); từ kho lạnh ước ≤ 16,9 / 10,9 s
    (G5). Một khách chờ 15 giây chỉ vì họ là người đầu tiên gọi sau một khoảng
    lặng là một lần hỏng **tránh được**, và preload trả cái giá đó một lần.
    """
    preload = (((cfg.get("hooks") or {}).get("on_startup") or {}).get("preload") or [])
    assert set(preload) == set(VAI_CUA_HO_SO), (
        f"preload dang la {preload}; phai co ca hai ho so")


#: Đồng hồ nhả, giây. Chủ sản phẩm chốt 13/09/2026: *"cơ chế nhả model sau 30p
#: không hoạt động vẫn giữ, nó sẽ nhả lại về RAM"*.
TTL_NHA_GIAY = 1800


def test_moi_ho_so_deu_TU_NHA_sau_30_phut(cfg):
    """🔴 ĐỔI 13/09/2026: `ttl: 0` → `ttl: 1800`, và lý do là một SỰ CỐ THẬT.

    Bản trước ghim `ttl == 0` (tắt đồng hồ nhả) với lập luận: *"một khách phải
    chờ 15 giây chỉ vì họ là người đầu tiên gọi sau một khoảng lặng là một lần
    hỏng TRÁNH ĐƯỢC"*. Lập luận ấy đúng — nhưng nó chỉ cân một phía.

    Phía kia đo được ngày 13/09, khi `qwen35-api` **ngừng phục vụ hoàn toàn**:

        VRAM trong 536 MiB < san 600 MiB cua card chay qwen35-api
        => cong tu choi moi luot moi; `ltt-3.5` tra 503 ba lan lien tiep

    5060 Ti nuôi cả desktop Windows (L-12 dồn đồ hoạ sang đó để 3090 chỉ chạy
    AI), và biên 1.002 MiB sau MTP không đủ cho desktop + mmproj cùng lúc. Với
    `ttl: 0` model **không bao giờ** nhả, nên card không có đường tự thoát.

    ⇒ `ttl: 0` đổi *"không ai phải chờ 15 giây"* lấy *"card không bao giờ hồi
      phục được"*. 15 giây là một lần chờ; card kẹt là **mất hẳn một model** cho
      tới khi có người vào tay.

    📏 Giá thật của mỗi lần nhả, đo 13/09 bằng đồng hồ (không lấy từ G5):

        qwen35-api  nạp ấm 12,76 s - đã sẵn 2,23 s = ~10,5 s
        qwen38-api  nạp ấm 20,35 s - đã sẵn 0,97 s = ~19,4 s

    ⭐ `preload` **vẫn giữ** — hai cờ trả lời hai câu khác nhau: `preload` lo lúc
       khởi động dịch vụ, `ttl` lo sau một khoảng rảnh. Xem
       `test_preload_liet_ke_CA_HAI_ho_so`.
    """
    for ten in VAI_CUA_HO_SO:
        ttl = cfg["models"][ten]["ttl"]
        assert isinstance(ttl, int), (
            f"{ten}: ttl={ttl!r} không phải số nguyên — nếu nó là chuỗi "
            f"'${{...}}' thì macro đã KHÔNG được thay, và llama-swap sẽ đọc "
            f"một giá trị vô nghĩa. Dùng YAML anchor (`&ttl_nha` / `*ttl_nha`), "
            f"thứ YAML giải trước khi engine nhìn thấy.")
        assert ttl == TTL_NHA_GIAY, (
            f"{ten} có ttl={ttl}; chính sách là {TTL_NHA_GIAY}s (30 phút)")
        assert cfg["models"][ten]["unloadTimeout"] >= 1, (
            f"{ten} thieu unloadTimeout: nha PHAI co han, mot tien trinh khong "
            "chiu chet la card khong bao gio ve cho trong tai residency")


def test_ttl_la_MOT_nguon_cho_moi_ho_so(cfg):
    """⛔ ĐỐI CHỨNG: mọi hồ sơ phải mang **cùng một** giá trị, và nó phải tới từ
    một chỗ.

    Ngày 12/09 hai hồ sơ mang `ttl: 0` gõ tay ở hai dòng khác nhau. Một chính
    sách gõ tay ở N chỗ là một chính sách sẽ lệch ở lần sửa thứ N+1 — và chiều
    lệch nguy hiểm là chiều **quên**: hồ sơ bị quên giữ `ttl: 0`, tức đúng cái
    hỏng vừa sửa quay lại ở một model duy nhất, lặng lẽ.

    Phép kiểm này bất biến với **số lượng** hồ sơ: thêm model thứ ba, thứ tư thì
    nó vẫn đúng mà không phải sửa một dòng nào.
    """
    ttl = {ten: ho["ttl"] for ten, ho in cfg["models"].items()}
    assert len(set(ttl.values())) == 1, (
        f"các hồ sơ khai ttl khác nhau: {ttl}. Dùng YAML anchor để một chỗ "
        f"định nghĩa, các chỗ sau tham chiếu.")
    assert set(ttl.values()) == {TTL_NHA_GIAY}, ttl

    # Và anchor phải THẬT SỰ có trong văn bản — một phép kiểm chỉ đọc giá trị
    # sau khi YAML giải thì không phân biệt được "một nguồn" với "hai chỗ gõ
    # trùng nhau", mà chính cái thứ hai mới là thứ sẽ lệch.
    van = YAML.read_text(encoding="utf-8")
    assert "&ttl_nha" in van and "*ttl_nha" in van, (
        "không thấy YAML anchor cho ttl: hai hồ sơ đang gõ tay cùng một số, và "
        "lần sửa sau sẽ lệch")


# ── Số suất: llama-swap không được giữ hàng đợi của engine ─────────────────

def test_concurrencyLimit_it_nhat_HAI_LAN_so_slot(cfg):
    """`concurrencyLimit` ≥ 2 × `-np`, và `-np` = `SO_SLOT_MAY_B`.

    llama-swap đếm ở `concurrencyLimit` số request nó **chuyển vào**; `-np` là số
    slot engine có. Để bằng nhau thì request thứ 4 bị llama-swap giữ lại và máy A
    không bao giờ thấy hàng đợi của engine. Để gấp đôi trở lên thì hàng đợi nằm
    TRONG llama.cpp — nơi `/metrics` đếm được (`requests_deferred`).
    """
    from apps.ltt_llm import ngan_sach

    for ten in VAI_CUA_HO_SO:
        dong_lenh = _khai_trien(cfg, ten)
        np = _tham_so(dong_lenh, "-np") or _tham_so(dong_lenh, "--parallel")
        assert np is not None, f"{ten} khong khai `-np`"
        assert int(np) == ngan_sach.SO_SLOT_MAY_B, (
            f"{ten} chay -np {np} nhung ngan_sach khai {ngan_sach.SO_SLOT_MAY_B}")
        gioi_han = cfg["models"][ten]["concurrencyLimit"]
        assert gioi_han >= 2 * int(np), (
            f"{ten} concurrencyLimit={gioi_han} < 2 x {np} => llama-swap se giu "
            "hang doi thay vi de engine giu, va `requests_deferred` khong thay gi")


# ── Bộ cờ L-16 ─────────────────────────────────────────────────────────────

def test_bo_co_L16_co_tren_CA_HAI_ho_so(cfg):
    """Không có bộ cờ này thì LTT-3.5 trả `content` **rỗng 6/6** lượt tiếng Việt,
    mỗi lượt đốt đúng `max_tokens` (G3c). Và chỉ `--reasoning-budget` một mình thì
    2/10 lượt trả lời **sai** kèm khối nghĩ rò ra `content` — kiểu hỏng TỆ HƠN
    rỗng, vì khách không phát hiện được (L-16 §2).
    """
    for ten in VAI_CUA_HO_SO:
        dong_lenh = _khai_trien(cfg, ten)
        for co, gt in CO_L16:
            thuc = _tham_so(dong_lenh, co)
            assert thuc == gt, (
                f"{ten}: {co} = {thuc!r}, cho L-16 phuong an B phai la {gt!r}")


def test_KHONG_ho_so_nao_dung_presence_penalty(cfg):
    """⛔ L-15 đã chốt `--presence-penalty 1.5`; L-16 **gỡ** nó sau khi đo xen kẽ.

    Bỏ nó: 56,61 → 63,01 tok/s (**+11 %**) với chất lượng **không đổi** (59/60,
    tiếng Việt 100 %). Và 56,61 nằm **dưới** ngưỡng 60,0 của cổng nghiệm thu B —
    hai dải không chồng nhau nên đó là hiệu ứng thật. Cơ chế hợp lý: nó là một
    phanh chạy ở **mỗi bước giải mã**, còn `temp/top-p/top-k/min-p` gần như miễn
    phí.
    """
    assert not _ho_so_vi_pham_presence_penalty(cfg), (
        f"ho so dung {CO_BI_CAM} (L-16 da go): "
        f"{_ho_so_vi_pham_presence_penalty(cfg)}")


def test_doi_chung_tiem_presence_penalty_thi_DO(tmp_path, cfg):
    """⭐ ĐỐI CHỨNG: một phép kiểm đo **sự vắng mặt** thì xoá hồ sơ đi nó cũng
    xanh. Nên phải chứng minh nó ĐỎ được — kể cả khi cờ lẻn vào qua **macro**,
    tức không xuất hiện trong `cmd` của bất kỳ hồ sơ nào.

    Hai chiều, trên một BẢN SAO trong `tmp_path` (không đụng cây thật).
    """
    goc = _doc_yaml()
    assert not _ho_so_vi_pham_presence_penalty(goc)

    # Chieu 1: tiem thang vao `cmd` cua mot ho so.
    hong = _doc_yaml()
    hong["models"]["qwen38-api"]["cmd"] += "\n--presence-penalty 1.5\n"
    assert _ho_so_vi_pham_presence_penalty(hong) == ["qwen38-api"]

    # Chieu 2: tiem vao macro CHUNG - ca hai ho so phai bi bat.
    hong2 = _doc_yaml()
    hong2["macros"]["CHUNG"] = str(hong2["macros"]["CHUNG"]) + " --presence-penalty 1.5"
    tep = tmp_path / "llama-swap-hong.yaml"
    tep.write_text(yaml.safe_dump(hong2), encoding="utf-8")
    assert sorted(_ho_so_vi_pham_presence_penalty(_doc_yaml(tep))) == sorted(VAI_CUA_HO_SO), (
        "co len qua macro ma phep kiem khong bat duoc => no dang doc van ban tho, "
        "khong doc dong lenh thuc")


# ── Tệp: byte, không phải lời hứa ──────────────────────────────────────────

def test_yaml_thuan_ascii_khong_BOM():
    """Bản trước của `llama-swap.yaml` **tuyên bố** "THUAN ASCII" ngay dòng 3 và
    mang 6 byte em-dash UTF-8. Lời văn không cưỡng chế được một byte.

    Tệp này đi cùng đường ống với các `.ps1` (PowerShell 5.1 đọc theo ANSI khi
    không BOM) và bị `scp` sang máy B; một BOM ở đầu tệp cấu hình là đúng lớp lỗi
    đã làm `/health/ready` trả 503 trong khi dịch vụ vẫn chạy.
    """
    raw = YAML.read_bytes()
    khong_ascii = [(i, b) for i, b in enumerate(raw) if b > 0x7E]
    assert not khong_ascii, (
        f"llama-swap.yaml co {len(khong_ascii)} byte khong-ASCII, dau tien o "
        f"offset {khong_ascii[0][0]}")
    assert not raw.startswith(b"\xef\xbb\xbf"), "llama-swap.yaml co BOM"
    assert b"\r\n" not in raw, "llama-swap.yaml dung CRLF"


def test_chu_thich_van_giu_bang_chung_do_duoc():
    """🔴 Ba con số này là **lý do** của ba quyết định trong tệp, và chúng đã bị
    xoá/viết sai một lần rồi (hai khối `DINH CHINH` trong tệp là dấu vết).

    ⛔ Phép kiểm này KHÔNG bắt tệp phải dài. Nó bắt: nếu ai đó rút gọn khối chú
       thích thì họ phải rút gọn **bằng cách dẫn nguồn**, không bằng cách bỏ số.
    """
    van = YAML.read_text(encoding="ascii")
    for so, y_nghia in (
        ("18,2", "toc do khi card BAN - ly do cua hang rao don dep GPU"),
        ("223,5", "ComfyUI giu ngu canh CUDA sau /free - rang buoc cung cua P5"),
        ("445", "bien VRAM cua ho so 221K tren 3090"),
        ("1.002", "bien VRAM cua ho so 262K tren 5060 Ti sau MTP"),
    ):
        assert so in van, f"chu thich mat con so {so} ({y_nghia})"
    assert re.search(r"10_BENCHMARK_P3", van), "chu thich khong con dan nguon so do"
