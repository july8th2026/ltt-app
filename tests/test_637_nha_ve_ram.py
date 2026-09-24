"""
Nhả model về RAM, không nhả hẳn về đĩa — chốt một tính chất đang ĐÚNG TÌNH CỜ.

🔴 VÌ SAO TỆP NÀY TỒN TẠI. LLM và ảnh tranh nhau **RTX 3090** của máy B (card duy
   nhất đủ 19–24 GB), nên model phải nhả ra vào liên tục giữa hai bên. Chi phí
   của mỗi lần nhả nằm ở lần **nạp lại**:

   ⚠️ Bản cũ của đoạn này viết *"máy B có một card"* — đúng trước 11/09/2026. Máy
   B nay có **hai** card; card 5060 Ti thường trú `ltt-3.5` và không tham gia
   cuộc tranh này. Vai trò hai máy: `docs/HAI_MAY_A_VA_B.md`.

     nạp từ page cache (RAM)  ->  vài giây
     nạp từ đĩa lạnh          ->  lâu hơn nhiều

   `llama-swap` nhả bằng cách **tắt tiến trình** `llama-server`. Model không nằm
   lại trong RAM của tiến trình nào cả — nhưng tệp GGUF thì **vẫn nằm trong page
   cache của hệ điều hành**, vì `llama.cpp` mở nó bằng `mmap` mặc định. Đo
   04/09: máy B có 192 GB RAM, trống 82 GB, GGUF 15,33 GiB — thừa chỗ.

⛔ NHƯNG KHÔNG AI ĐANG CANH ĐIỀU ĐÓ. Thêm một cờ `--no-mmap` vào `cmd`, hoặc một
   dịch vụ khác ăn hết RAM, là mỗi lần nhả trở thành một lần đọc đĩa 15 GiB —
   **và không có gì kêu**. Cùng đúng hình dạng với sự cố "tràn trọng số sang RAM
   chủ" đo ngày 22/08: `/health` xanh, nội dung đúng, chỉ tốc độ lặng lẽ mất đi
   một phần.

⭐ Nên tệp này biến một tính chất **tình cờ** thành một tính chất **được canh**.
"""
from __future__ import annotations

import pathlib
import re

import pytest
import yaml

YAML = pathlib.Path(__file__).resolve().parents[1] / "llm_gateway" / "deploy" / "llama-swap.yaml"

#: Gia tri `--load-mode` GIU duoc kho am. ⛔ Danh sach TRANG, khong phai danh
#: sach den: `arg.cpp:2687` da doi mot lan (b10875 go `--no-mmap`) va se doi nua.
#: Mot gia tri MOI khong ai biet phai lam phep kiem DO, khong phai lam no im.
#:
#:   auto        mmap neu duoc → page cache giu tep      ✅
#:   mmap        buoc mmap                                ✅
#:   mlock       mmap + VirtualLock                       ✅ (khoa RAM, van am)
#:   mmap+mlock  ca hai                                   ✅
#:   none        doc thang vao RAM tien trinh             ⛔ moi lan nap = doc lai
#:   dio         direct I/O, BO QUA cache he dieu hanh    ⛔ va con xoa cache
LOAD_MODE_GIU_AM = frozenset({"auto", "mmap", "mlock", "mmap+mlock"})

#: Ngu canh cho cac ca "hop le" — mot ho so toi thieu de tiem mot khuyet tat vao.
#: ⛔ Khong ghi vao cay: moi doi chung dung mot chuoi trong bo nho.


def _no_macro(van: str) -> str:
    """Thay `${TEN}` bang gia tri o khoi `macros:`.

    🔴 KHONG CO BUOC NAY THI MOI PHEP QUET DUOI DAY DEU MU. Ho so Task 3.3
       dua gan het co vao MOT macro:

           macros: {CHUNG: "--jinja --reasoning-format deepseek -fa 1 ..."}
           cmd: |
             ${BIN}/llama-server.exe -m ${GGUF38} ${CHUNG} -c 221184 ...

       `_cac_dong_cmd` doc duoc 19 dong va khong dong nao chua co that. Mot
       `--load-mode dio` (hay `--no-mmap`) nhet vao `CHUNG` se di qua CA SAU
       phep kiem cua tep nay ma khong ai keu — va do dung la hinh dang khuyet
       tat ma tep nay sinh ra de canh: "`/health` xanh, noi dung dung, chi toc
       do lang le mat di mot phan".
    """
    mac = (yaml.safe_load(van) or {}).get("macros") or {}
    ra = van
    for _ in range(5):                       # macro long nhau toi da 5 tang
        truoc = ra
        for ten, gia in mac.items():
            ra = ra.replace("${%s}" % ten, str(gia))
        if ra == truoc:
            break
    return ra


@pytest.fixture(scope="module")
def van() -> str:
    """Van ban ho so, **da no macro**. Moi phep quet theo co dung cai nay."""
    assert YAML.is_file(), f"khong thay {YAML}"
    return _no_macro(YAML.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def cau_hinh() -> dict:
    """Ho so da phan tich — cho cac cau hoi ve CAU TRUC (nhom, ttl, env).

    ⚠️ Regex du cho cau hoi "co chuoi nay khong"; no khong du cho "thanh vien
       cua nhom nay nam tren card nao". Cau thu hai la cau ve quan he giua hai
       khoa, va tra loi nó bang regex la cach mot phep kiem tu tuyen bo rong hon
       thu no do.
    """
    return yaml.safe_load(YAML.read_text(encoding="utf-8")) or {}


def _uuid_cua(ho_so: dict) -> str:
    """UUID card ma mot ho so ghim, doc tu `env: CUDA_VISIBLE_DEVICES=...`."""
    for dong in (ho_so.get("env") or []):
        if str(dong).startswith("CUDA_VISIBLE_DEVICES="):
            return str(dong).split("=", 1)[1].strip()
    return ""


def _cac_dong_cmd(van: str) -> list:
    """Các dòng nằm trong khối `cmd:` của mọi hồ sơ model."""
    ra, trong_cmd = [], False
    for dong in van.splitlines():
        if re.match(r"^\s*cmd:\s*\|", dong):
            trong_cmd = True
            continue
        if trong_cmd:
            # Khối `cmd` kết thúc khi gặp một khoá cùng cấp (vd `proxy:`).
            if dong.strip() and not dong.startswith((" " * 6, "\t")):
                trong_cmd = False
                continue
            if dong.strip():
                ra.append(dong.strip())
    return ra


def test_khong_ho_so_nao_dung_no_mmap(van):
    """⛔ `--no-mmap` biến mỗi lần nhả thành một lần đọc đĩa 15 GiB.

    Với `mmap` (mặc định), trọng số được ánh xạ từ **page cache**, nên tắt tiến
    trình rồi bật lại chỉ tốn vài giây. Với `--no-mmap`, mỗi lần nạp là một lần
    đọc thật từ ổ đĩa.

    ⭐ Trên một máy phải swap model liên tục, đó là khác biệt giữa "nhả về RAM"
       và "nhả hẳn về đĩa" — đúng thứ chủ dự án yêu cầu giữ.
    """
    xau = [d for d in _cac_dong_cmd(van) if "--no-mmap" in d]
    assert not xau, (
        "co ho so dung `--no-mmap`, nen moi lan nha model se phai doc lai 15 GiB "
        f"tu dia: {xau}")


def test_mmap_khong_bi_tat_o_bat_ky_dau(van):
    """Chặn cả các biến thể: `--no-mmap`, `--mmap 0`, `--mmap false`."""
    for mau in (r"--no-mmap", r"--mmap\s+0\b", r"--mmap\s+false\b"):
        assert not re.search(mau, van, re.IGNORECASE), f"tat mmap qua `{mau}`"


def test_han_cho_nap_du_cho_TRUONG_HOP_XAU_NHAT(van):
    """`healthCheckTimeout` phải đủ cho một lần nạp **từ đĩa lạnh**.

    ⛔ Không đặt theo trường hợp thường (page cache, vài giây). Page cache là thứ
       **có thể mất** — sau khởi động lại máy, hoặc khi một tiến trình khác ăn
       hết RAM. Đặt hạn theo trường hợp thường nghĩa là lần nạp lạnh đầu tiên sau
       mỗi lần reboot sẽ bị coi là **hỏng**.
    """
    m = re.search(r"^healthCheckTimeout:\s*(\d+)", van, re.MULTILINE)
    assert m, "khong khai `healthCheckTimeout`"
    assert int(m.group(1)) >= 300, (
        f"healthCheckTimeout={m.group(1)}s co the khong du cho mot lan nap "
        "15 GiB tu dia lanh")


def test_ttl_khong_bao_gio_NGAN_ma_khac_khong(cau_hinh):
    """TTL quá ngắn thì mỗi lượt khách là một lần nạp lại — đắt và chậm.

    ⚠️ Chốt về **hướng**, không về một con số: nó chỉ kêu khi ai đó hạ TTL
       xuống mức làm việc nhả/nạp thành chuyện xảy ra giữa hai câu hỏi liên
       tiếp của cùng một khách.

    🔴 BẢN TRƯỚC ĐÒI `min(ttl) >= 300` VÀ NÓ ĐỎGI CHÍNH CÁI NÓ MUỐN (12/09).
       Hồ sơ hai model (Task 3.3) đặt `ttl: 0`, và trong llama-swap `0` là **TẮT
       đồng hồ nhả**, không phải "nhả ngay" — tức nó là dạng **mạnh nhất** của
       điều phép kiểm này đòi. Một phép kiểm đỏ trước cấu hình **tốt hơn** của
       cùng một mục tiêu là một phép kiểm đã ghìm sai đại lượng: nó ghìm *con số*
       chứ không ghìm *tính chất*.

    ⭐ Tính chất thật: khoảng **(0, 300)** là vùng cấm. `0` ở ngoài nó vì nó
       không bao giờ nhả; `≥ 300` ở ngoài nó vì một khách đang hỏi liên tiếp
       không đợi đủ 5 phút giữa hai câu.
    """
    # 🔴 DOC GIA TRI DA PHAN TICH, KHONG QUET VAN BAN — sua 13/09/2026.
    #
    #    Ban truoc dung `re.findall(r"^\s*ttl:\s*(\d+)", van)`. Ngay 13/09 ho so
    #    doi sang YAML anchor de mot cho dinh nghia va cac cho sau tham chieu:
    #
    #        ttl: &ttl_nha 1800     <- `\d+` khong khop, co `&ttl_nha` chen giua
    #        ttl: *ttl_nha          <- khong co chu so nao ca
    #
    #    Regex tra ve **rong**, va phep kiem do voi "khong ho so nao khai `ttl`"
    #    trong khi CA HAI ho so deu khai 1800. Mot phep kiem doc VAN BAN mu truoc
    #    moi cu phap YAML hop le ma no khong luong truoc — anchor, trich dan,
    #    dong gap. Thu no muon biet la **gia tri**, nen phai hoi bo phan tich.
    ttl = [int(h["ttl"]) for h in (cau_hinh.get("models") or {}).values()
           if h.get("ttl") is not None]
    assert ttl, "khong ho so nao khai `ttl`"
    xau = [t for t in ttl if 0 < t < 300]
    assert not xau, (
        f"ttl nam trong vung cam (0, 300): {xau} — moi luot khach se la mot lan "
        f"nap lai. Dung 0 (tat dong ho) hoac >= 300")


def test_DOI_CHUNG_ttl_ngan_van_bi_BAT(tmp_path):
    """Đối chứng: nịi lỏng "0 cũng được" không được làm bị mù với `ttl: 60`.

    ⛔ Không có ca này thì cách sửa "cho `0` hợp lệ" dễ nhất — bỏ hẳn phép
       kiểm — cũng xanh.
    """
    gia = "models:\n  x:\n    ttl: 60\n    unloadTimeout: 30\n"
    ttl = [int(x) for x in re.findall(r"^\s*ttl:\s*(\d+)", gia, re.MULTILINE)]
    assert [t for t in ttl if 0 < t < 300] == [60]


def test_moi_ho_so_deu_co_unloadTimeout(cau_hinh):
    """Nhả phải có hạn: một tiến trình không chịu chết là card không bao giờ về.

    ⛔ Dem tren CAU TRUC, khong dem dong van ban — cung ly do voi
       `test_ttl_khong_bao_gio_NGAN_ma_khac_khong`: ban regex cu dem
       mot mau regex tren dong `ttl:` va ra **0 ho so** sau khi ho so doi sang
       YAML anchor,
       nen phep so `2 == 0` do trong khi ca hai ho so deu khai du.
    """
    ho_so = cau_hinh.get("models") or {}
    thieu = [ten for ten, h in ho_so.items() if not h.get("unloadTimeout")]
    assert ho_so, "khong doc duoc ho so nao"
    assert not thieu, (
        f"{len(ho_so)} ho so nhung {thieu} khong khai `unloadTimeout`")


def _nhom_sai(cau_hinh: dict) -> list:
    """Nhom `swap: false` nao co hai thanh vien tren CUNG mot card (hay thieu ghim)."""
    models = cau_hinh.get("models") or {}
    xau = []
    for ten, nhom in (cau_hinh.get("groups") or {}).items():
        if (nhom or {}).get("swap") is not False:
            continue                      # nhom con doi cho nhau: khong phai ca nay
        theo_card: dict = {}
        for tv in (nhom.get("members") or []):
            uuid = _uuid_cua(models.get(tv) or {})
            if not uuid:
                xau.append(f"{ten}/{tv}: khong ghim CUDA_VISIBLE_DEVICES")
                continue
            theo_card.setdefault(uuid, []).append(tv)
        for uuid, tv in theo_card.items():
            if len(tv) > 1:
                xau.append(f"{ten}: {tv} cung tren {uuid}")
    return xau


def test_group_KHONG_SWAP_thi_moi_thanh_vien_o_MOT_CARD_RIENG(cau_hinh):
    """`groups` được dùng — nhưng chỉ khi các thành viên **không chung card**.

    🔴 BẢN TRƯỚC CẤM `groups:` HẲN, và lýc ấy nó đúng: hai hồ sơ khi đó là
       hai bản của **cùng một trọng số 27B** (`qwen38-api` + `qwen38-vision`),
       cộng lại ~43 GB trên một card 24,5 GB — cho chúng cùng sống là một lần
       OOM. Câu lệnh cấm đã **giữ đúng điều nó cần giữ** trong cả một pha.

    ⚠️ Từ Task 3.3 đây là **hai model khác nhau trên hai card khác nhau**, và
       `groups` với `swap: false` **chính là** cơ chế làm được điều đó
       (`05_COMMUNITY_EVIDENCE.md` §1, dòng "llama-swap hai model tren hai GPU
       cung luc": llama-swap v250 có `groups` `swap:false` + `env` theo model +
       `hooks.on_startup.preload`). Cấm nó lúc này là cấm đúng kiến trúc đã chốt.

    ⭐ Nên mối nguy cũ được phát biểu lại đúng như nó là — **hai hồ sơ cùng
       sống trên CÙNG MỘT card** — thay vì bằng cái bóng của nó ("có chữ
       `groups`"). Bản trước cấm cả hình dạng an toàn lẫn hình dạng nguy hiểm vì
       nó không phân biệt được hai cái.
    """
    assert _nhom_sai(cau_hinh) == [], (
        f"nhom `swap: false` co thanh vien chung card (hay thieu ghim UUID): "
        f"{_nhom_sai(cau_hinh)}")


def test_DOI_CHUNG_hai_ho_so_CUNG_card_trong_mot_nhom_thi_DO():
    """Đối chứng: đúng mối nguy cũ (hai hồ sơ một card) phải vẫn bị bắt.

    ⛔ Không có ca này thì "nới lỏng cho hai card" và "bỏ hẳn lần gác" trông
       giống nhau từ phía phép kiểm — và đó là cách một lần OOM quay lại.

    Ba hình dạng: cùng card ⇒ đỏ; thiếu ghim ⇒ đỏ; hai card ⇒ xanh.
    """
    mot_card = {
        "models": {"a": {"env": ["CUDA_VISIBLE_DEVICES=GPU-1"]},
                   "b": {"env": ["CUDA_VISIBLE_DEVICES=GPU-1"]}},
        "groups": {"g": {"swap": False, "members": ["a", "b"]}},
    }
    assert _nhom_sai(mot_card), "hai ho so CUNG card ma khong bi bat"

    thieu_ghim = {
        "models": {"a": {"env": ["CUDA_VISIBLE_DEVICES=GPU-1"]}, "b": {}},
        "groups": {"g": {"swap": False, "members": ["a", "b"]}},
    }
    assert _nhom_sai(thieu_ghim), "ho so khong ghim UUID ma khong bi bat"

    hai_card = {
        "models": {"a": {"env": ["CUDA_VISIBLE_DEVICES=GPU-1"]},
                   "b": {"env": ["CUDA_VISIBLE_DEVICES=GPU-2"]}},
        "groups": {"g": {"swap": False, "members": ["a", "b"]}},
    }
    assert _nhom_sai(hai_card) == [], "hai card khac nhau ma bi bao xau"


# ══════════════════════════════════════════════════════════════════════════════
#  `--load-mode` — cờ THAY THẾ `--no-mmap`, và bộ dò cũ mù với nó
# ══════════════════════════════════════════════════════════════════════════════

def _khai_load_mode(van: str) -> list:
    """Mọi giá trị `load-mode` khai trong hồ sơ, ở **mọi** cách khai được.

    Ba lối vào, và một hồ sơ chỉ cần một lối:

        --load-mode dio          cờ dài
        -lm dio                  dạng ngắn (nếu bản binary nhận)
        LLAMA_ARG_LOAD_MODE=dio  biến môi trường (`env:` theo model, hay dịch vụ)

    ⛔ Đọc **văn bản đã nở macro**: `${CHUNG}` là đúng chỗ một cờ như thế sẽ nằm.
    """
    ra = []
    for mau in (r"--load-mode[\s=]+([A-Za-z+]+)",
                r"(?<![\w-])-lm[\s=]+([A-Za-z+]+)",
                r"LLAMA_ARG_LOAD_MODE[\s=:]+\"?([A-Za-z+]+)"):
        ra += [x.lower() for x in re.findall(mau, van)]
    return ra


def test_moi_khai_load_mode_deu_GIU_KHO_AM(van):
    """⛔ `--load-mode none|dio` là `--no-mmap` dưới một cái tên mới.

    🔴 BỘ DÒ CŨ CANH MỘT CÁI TÊN KHÔNG CÒN TỒN TẠI. `llama.cpp` b10875 (#28334)
       **gỡ** `--no-mmap`/`--mlock` và thay bằng
       `--load-mode {auto,none,mmap,mlock,mmap+mlock,dio}` (`arg.cpp:2687`).
       Hai phép kiểm đầu tệp này vẫn quét `--no-mmap` — nên từ b10875 chúng canh
       một cánh cửa đã bị tháo, và cánh cửa mới thì không ai canh.

       `docs/ltt_llm_dual/05_COMMUNITY_EVIDENCE.md` §1 gọi tên đúng lỗ này:
       *"`tests/test_637` chỉ chặn tên cũ ⇒ **mù** với `--load-mode none/dio`"*.
       Đây là lần bịt nó (Task 6.2).

    ⚠️ Hai giá trị, hai cách hỏng khác nhau — và `dio` tệ hơn:

         none   đọc thẳng vào RAM tiến trình ⇒ mỗi lần nạp là một lần đọc thật.
         dio    direct I/O: **bỏ qua** page cache, và vì thế cũng không **để
                lại** gì trong đó ⇒ lần nạp sau cũng lạnh. Nó làm hỏng luôn cái
                kho ấm mà tệp này tồn tại để giữ.

    ⭐ Chốt bằng **danh sách trắng**: một giá trị mới mà chưa ai đo phải làm phép
       kiểm ĐỎ. Đo ở đây rẻ (một lần), còn đoán thì đắt (chậm âm thầm, không cờ
       nào kêu).
    """
    xau = [g for g in _khai_load_mode(van) if g not in LOAD_MODE_GIU_AM]
    assert not xau, (
        f"khai `load-mode` khong giu duoc kho am: {xau} "
        f"(chi nhan {sorted(LOAD_MODE_GIU_AM)})")


@pytest.mark.parametrize("tiem", [
    "cmd: |\n      llama-server.exe --load-mode none -c 1024\n",
    "cmd: |\n      llama-server.exe --load-mode dio -c 1024\n",
    "cmd: |\n      llama-server.exe -lm dio -c 1024\n",
    "    env:\n      - LLAMA_ARG_LOAD_MODE=none\n",
    "    env:\n      - LLAMA_ARG_LOAD_MODE=dio\n",
])
def test_DOI_CHUNG_bo_do_load_mode_THAY_tung_loi_vao(tiem):
    """Đối chứng cho phép kiểm trên — năm lối vào, **đo từng lối một**.

    🔴 Vì sao không gộp: bản đầu của `test_434` trong repo này ghi lại đúng bài
       học ấy (*"một cửa chỉ khoá một cánh là một cửa không khoá"*) — nó chặn
       `from x import y` và bỏ sót `from x import y as z`, và phép kiểm vẫn xanh.
       Một đối chứng gộp năm mẫu vào một chuỗi cũng xanh khi bốn mẫu chết.

    ⛔ Và đối chứng phải chạy trên **chuỗi trong bộ nhớ**, không ghi vào cây:
       `llama-swap.yaml` là tệp máy B thật đọc.
    """
    xau = [g for g in _khai_load_mode(tiem) if g not in LOAD_MODE_GIU_AM]
    assert xau, f"bo do khong thay khuyet tat trong: {tiem!r}"


def test_DOI_CHUNG_gia_tri_LANH_MANH_khong_bi_bao_xau():
    """Chiều còn lại: `--load-mode mmap` (hay `mlock`) **không** được báo xấu.

    ⛔ Không có ca này thì `return ["xau"]` vô điều kiện cũng làm mọi ca trên
       xanh — "đo sự vắng mặt thì xoá cũng xanh", ở dạng ngược.
    """
    for tot in ("--load-mode auto", "--load-mode mmap", "-lm mlock",
                "LLAMA_ARG_LOAD_MODE=mmap+mlock"):
        assert [g for g in _khai_load_mode(tot)
                if g not in LOAD_MODE_GIU_AM] == [], tot


def test_bo_do_NO_MACRO_that_su_nhin_thay_co_trong_macro():
    """Đối chứng cho `_no_macro`: cờ nằm trong macro phải bị thấy.

    🔴 Đây là ca giữ cho cả tệp khỏi thành trang trí. Hồ sơ Task 3.3 để gần hết
       cờ trong `macros.CHUNG`; nếu bước nở macro chết thì **sáu** phép kiểm phía
       trên vẫn xanh trong khi không phép nào còn đọc một cờ thật.
    """
    gia = ('macros:\n  CHUNG: "--jinja --load-mode dio -fa 1"\n'
           'models:\n  x:\n    cmd: |\n      llama-server.exe ${CHUNG} -c 8\n')
    assert "dio" not in gia.split("cmd:")[1], "chuoi mau khong con do duoc gi"
    no = _no_macro(gia)
    assert [g for g in _khai_load_mode(no) if g not in LOAD_MODE_GIU_AM] == ["dio", "dio"]
