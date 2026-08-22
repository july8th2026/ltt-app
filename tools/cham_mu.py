"""
cham_mu.py — bộ so mù cho H37: dựng lô so sánh, thu phiếu, tính kết quả.

    py tools/cham_mu.py tao  --a <thu_muc_A> --b <thu_muc_B> --ra <thu_muc_lo>
    py tools/cham_mu.py tinh --lo <thu_muc_lo>

⭐ VÌ SAO CÓ TỆP NÀY: từ D-010, **chất lượng là tiêu chí chọn duy nhất**. Khi một
   con số quyết định mọi thứ thì cách tạo ra con số đó phải chặt hơn mọi thứ khác.
   Luật đầy đủ ở `docs/ANH_NOI_BO/KE_HOACH_THI_HANH.md` §1.5; tệp này **thi hành**
   chúng chứ không để chúng nằm trên giấy.

Bốn luật được cưỡng chế bằng mã, không bằng trí nhớ:

 ① **Mù.** Ảnh chép sang tên mã ngẫu nhiên. Bảng đối chiếu ghi ra một tệp riêng tên
    `KHONG_MO_TRUOC_KHI_CHAM.json` — mở nó trước khi chấm là tự huỷ lô.
 ② **So từng cặp**, không chấm điểm tuyệt đối. "Ảnh này 7/10" không lặp lại được
    giữa hai ngày; "A hay B hay hoà" thì có.
 ③ **Cặp bẫy A-đấu-A.** Không phải để bắt lỗi người chấm — để **đo sàn nhiễu**.
    Xem §"sàn nhiễu" dưới.
 ④ **Đủ mẫu mới được kết luận.** Thiếu mẫu thì kết quả hợp lệ là
    **"chưa phân biệt được"**, không phải một con số nghe cho oai.

── SÀN NHIỄU: vì sao cặp bẫy quan trọng hơn vẻ ngoài ────────────────────────────
Cặp bẫy ghép hai ảnh **cùng một nguồn, khác seed**. Không có khác biệt thật nào để
tìm. Nhưng người chấm vẫn sẽ chọn — vì hai ảnh khác nhau thật, chỉ là khác do ngẫu
nhiên chứ không do model.

Tỉ lệ người chấm **dám chọn** trên cặp bẫy chính là **sàn nhiễu** `f`: mức độ quyết
đoán khi không có gì để quyết. Nếu trên cặp thật họ cũng chỉ quyết đoán ngang mức
đó (`d <= f`) thì **khác biệt giữa hai model nhỏ hơn khác biệt giữa hai lần chạy
cùng một model** — và lúc đó mọi con số thắng-thua đều vô nghĩa.

Đây là lý do không dùng cặp bẫy làm phép đậu/rớt: nó là **thước đo**, không phải
cái bẫy.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import shutil
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional, Sequence

TEN_KHOA = "KHONG_MO_TRUOC_KHI_CHAM.json"
TEN_PHIEU = "phieu.json"
TEN_ANH = "anh"
TEN_MAN = "cham.html"

#: Dưới ngưỡng này thì không kết luận. Với 30 cặp, một chênh lệch 60/40 nằm trọn
#: trong khoảng nhiễu — nhìn thì "rõ ràng" mà thật ra không nói lên gì.
SO_CAP_TOI_THIEU = 50

#: Tỉ lệ cặp bẫy mặc định. Quá ít thì sàn nhiễu đo không chuẩn; quá nhiều thì tốn
#: thời gian của người chấm vào những cặp không mang thông tin so sánh.
TY_LE_BAY = 0.10

CHON_HOP_LE = ("trai", "phai", "hoa")


# ─────────────────────────── dựng lô ────────────────────────────────────────
@dataclass
class Cap:
    ma: str
    trai: str            # tên tệp ảnh đã đổi tên mã
    phai: str
    nguon_trai: str      # "A" | "B"  — CHỈ có trong tệp khoá
    nguon_phai: str
    la_bay: bool


@dataclass
class KetQua:
    n_that: int
    thang_a: int
    thang_b: int
    hoa: int
    diem_a: float                 # (thắng + 0,5×hoà) / n — thang 0..1
    khoang_tin_thap: float
    khoang_tin_cao: float
    n_bay: int
    san_nhieu: float              # f — tỉ lệ dám chọn trên cặp bẫy
    quyet_doan_that: float        # d — tỉ lệ dám chọn trên cặp thật
    lech_vi_tri: float            # tỉ lệ chọn "trái" trên cặp bẫy; 0,5 là không lệch
    ket_luan: str
    ly_do: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return asdict(self)


def tao_lo(anh_a: Sequence[str], anh_b: Sequence[str], *,
           ty_le_bay: float = TY_LE_BAY,
           rng: Optional[random.Random] = None) -> list[Cap]:
    """Ghép cặp A↔B, chèn cặp bẫy A↔A và B↔B, rồi xáo trộn trái/phải.

    Ảnh vào là **đường dẫn**; ảnh ra trong `Cap` vẫn là đường dẫn — việc chép và
    đổi tên do `ghi_lo` làm, để hàm này thuần và test được không cần đĩa.
    """
    r = rng or random.Random()
    if not anh_a or not anh_b:
        raise ValueError("ca hai ben deu phai co it nhat mot anh")
    n = min(len(anh_a), len(anh_b))
    caps: list[Cap] = []
    for i in range(n):
        caps.append(Cap("", anh_a[i], anh_b[i], "A", "B", False))

    # Cặp bẫy: ghép hai ảnh KHÁC NHAU của CÙNG một nguồn. Cần ít nhất 2 ảnh mỗi bên.
    so_bay = int(round(n * max(0.0, ty_le_bay)))
    for i in range(so_bay):
        ben, kho = ("A", anh_a) if i % 2 == 0 else ("B", anh_b)
        if len(kho) < 2:
            continue
        x, y = r.sample(list(kho), 2)
        caps.append(Cap("", x, y, ben, ben, True))

    r.shuffle(caps)
    for i, c in enumerate(caps):
        c.ma = f"c{i + 1:03d}"
        if r.random() < 0.5:            # xáo trái/phải để không có phía nào cố định
            c.trai, c.phai = c.phai, c.trai
            c.nguon_trai, c.nguon_phai = c.nguon_phai, c.nguon_trai
    return caps


def ghi_lo(caps: Sequence[Cap], thu_muc: Path, *, nhan_a: str, nhan_b: str) -> None:
    """Chép ảnh sang tên mã, ghi phiếu trống và tệp khoá.

    ⛔ Tên tệp ảnh sau khi chép **không được mang bất kỳ dấu vết nào** của nguồn:
    không tên model, không profile, không độ phân giải. Một chữ "hidream" sót lại
    trong tên tệp là đủ để huỷ tính mù của cả lô.

    ⛔ VÀ **ĐUÔI TỆP CŨNG LÀ MỘT DẤU VẾT.** Hàm này chép nguyên si nên đuôi gốc đi
    theo. Nếu một bên toàn `.jpg` còn bên kia toàn `.png` thì người chấm chỉ cần
    nhìn tên tệp là biết nguồn — không cần mở ảnh.

    Đây không phải rủi ro lý thuyết: đo 22/08, Gemini trả **JPEG** còn phía ta trả
    **PNG**. Nên hàm này nay **từ chối** lô có hai đuôi khác nhau, thay vì lặng lẽ
    tạo ra một lô trông có vẻ mù. Chạy `tools/chuan_hoa_anh.py` trước — nó cũng
    đồng thời xử luôn chuyện hai bên khác kích thước.
    """
    duoi = {Path(getattr(c, phia)).suffix.lower()
            for c in caps for phia in ("trai", "phai")}
    if len(duoi) > 1:
        raise ValueError(
            "Lo co nhieu duoi tep khac nhau ({}): duoi tep la mot dau vet nguon, "
            "nen lo nay KHONG mu. Chay tools/chuan_hoa_anh.py truoc.".format(
                ", ".join(sorted(duoi))))

    thu_muc.mkdir(parents=True, exist_ok=True)
    (thu_muc / TEN_ANH).mkdir(exist_ok=True)
    phieu = []
    for c in caps:
        for phia in ("trai", "phai"):
            goc = Path(getattr(c, phia))
            dich_ten = f"{c.ma}_{phia}{goc.suffix.lower() or '.png'}"
            shutil.copyfile(goc, thu_muc / TEN_ANH / dich_ten)
            setattr(c, phia, dich_ten)
        phieu.append({"ma": c.ma, "chon": "", "ghi_chu": ""})

    _ghi_json(thu_muc / TEN_PHIEU, {
        "_huong_dan": [
            "Voi moi ma: mo anh <ma>_trai va <ma>_phai trong thu muc 'anh'.",
            "Dien 'chon' = trai | phai | hoa. Khong doan — thay khong khac thi ghi hoa.",
            "KHONG mo tep " + TEN_KHOA + " truoc khi cham xong.",
        ],
        "so_cap": len(caps),
        "phieu": phieu,
    })
    _ghi_json(thu_muc / TEN_KHOA, {
        "_canh_bao": "Mo tep nay truoc khi cham xong la tu huy lo. Khong co cach nao kiem chung nguoc lai.",
        "nhan": {"A": nhan_a, "B": nhan_b},
        "cap": [asdict(c) for c in caps],
    })


# ─────────────────────────── màn chấm ───────────────────────────────────────
#
# ⭐ VÌ SAO CẦN MÀN RIÊNG, KHÔNG MỞ TỆP BẰNG FILE EXPLORER:
#    ① Ảnh 2560×1440. Nhìn hai ảnh cỡ đó cạnh nhau trong trình xem ảnh của Windows
#       là không so được — và **so nhấp nháy** (bật qua bật lại tại đúng cùng vị
#       trí, cùng mức phóng) là cách duy nhất thấy được khác biệt nhỏ. Cái đó
#       trình xem ảnh không làm được.
#    ② Luật mù ở §1.5: người chấm **không được thấy đường dẫn gốc**. Mở bằng File
#       Explorer là thấy tên thư mục, mà tên thư mục nói ra nguồn.
#    ③ Chấm 33 cặp mà mất phiếu giữa chừng thì phải chấm lại từ đầu — và lần hai
#       không còn mù nữa. Nên màn tự lưu vào `localStorage` sau mỗi lượt.
#
# ⛔ Màn này chạy bằng `file://`, KHÔNG có máy chủ. Nên dữ liệu cặp phải **nhúng
#    thẳng vào HTML**: `fetch()` một tệp JSON cạnh nó sẽ bị CORS chặn.

_MAN_HTML = """<!doctype html>
<html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Cham mu</title>
<style>
:root{color-scheme:dark}
*{box-sizing:border-box}
/* Nen xam trung tinh: nen sang hay toi deu lam lech cam nhan tuong phan, va
   lech deu hai anh thi khong sao - nhung nguoi cham se doc sai do bao hoa. */
body{margin:0;background:#2b2b2b;color:#ddd;font:14px/1.5 system-ui,Segoe UI,sans-serif}
header{display:flex;gap:16px;align-items:center;padding:10px 16px;background:#222;
  position:sticky;top:0;z-index:5;border-bottom:1px solid #3a3a3a}
#ma{font:600 16px ui-monospace,Consolas,monospace;letter-spacing:1px}
#tien{flex:1;color:#9a9a9a}
button{background:#3a3a3a;color:#eee;border:1px solid #4d4d4d;border-radius:6px;
  padding:8px 14px;font:inherit;cursor:pointer}
button:hover{background:#464646}
button.chon{background:#2f5d3f;border-color:#3d7a52}
#khung{display:grid;grid-template-columns:1fr 1fr;gap:10px;padding:10px}
figure{margin:0;text-align:center}
figure img{width:100%;height:auto;max-height:74vh;object-fit:contain;
  background:#1c1c1c;border:1px solid #3a3a3a;border-radius:4px;cursor:zoom-in}
figcaption{padding:6px;color:#8f8f8f;font:600 13px ui-monospace,monospace}
#dieu{display:flex;gap:10px;justify-content:center;padding:6px 10px 16px;flex-wrap:wrap}
#ghi{width:min(560px,90vw);background:#1c1c1c;color:#ddd;border:1px solid #3a3a3a;
  border-radius:6px;padding:8px;margin:0 auto;display:block}
#zoom{position:fixed;inset:0;background:#1c1c1c;display:none;z-index:9;
  overflow:auto;cursor:zoom-out}
/* HAI anh XEP CHONG, khong doi src: doi src voi PNG 2560x1440 (~5 MB) se chop
   trang trong luc tai - dung luc mat can lien tuc nhat. Xep chong thi ca hai da
   nam san trong bo nho, bat/tat la tuc thi va tuyet doi cung vi tri. */
#zoom img{display:block;image-rendering:auto;grid-area:1/1}
#zoom{display:none;place-items:start}
#zoom.mo{display:grid}
#zoom img.an{visibility:hidden}
#nhan{position:fixed;left:50%;transform:translateX(-50%);bottom:18px;z-index:10;
  background:#000a;padding:6px 14px;border-radius:20px;font:600 13px monospace;display:none}
#xong{padding:40px;text-align:center;display:none}
kbd{background:#3a3a3a;border:1px solid #555;border-radius:4px;padding:1px 5px;
  font:12px ui-monospace,monospace}
.mach{padding:8px 16px;background:#3a2f1c;color:#e0c98a;font-size:13px}
#canhbao{position:fixed;left:0;right:0;bottom:0;z-index:20;background:#5a1f1f;
  color:#ffd7d7;padding:10px 16px;font:600 13px/1.4 system-ui,sans-serif;text-align:center}
</style></head><body>
<div class="mach">Phim tat: <kbd>1</kbd> trai &nbsp; <kbd>2</kbd> hoa &nbsp; <kbd>3</kbd> phai
 &nbsp;|&nbsp; <kbd>Z</kbd> phong to &nbsp; trong luc phong: <kbd>Space</kbd> bat qua bat lai
 (SO NHAP NHAY - cach duy nhat thay khac biet nho) &nbsp;|&nbsp;
 <kbd>&larr;</kbd> <kbd>&rarr;</kbd> doi cap</div>
<header><span id="ma"></span><span id="tien"></span>
  <button id="luu">Tai phieu ve</button></header>
<div id="than">
  <div id="khung">
    <figure><img id="imgL" alt="trai"><figcaption>TRAI</figcaption></figure>
    <figure><img id="imgR" alt="phai"><figcaption>PHAI</figcaption></figure>
  </div>
  <div id="dieu">
    <button data-c="trai">1 &nbsp;Trai tot hon</button>
    <button data-c="hoa">2 &nbsp;Hoa / khong thay khac</button>
    <button data-c="phai">3 &nbsp;Phai tot hon</button>
  </div>
  <textarea id="ghi" rows="2" placeholder="Ghi chu (khong bat buoc)"></textarea>
</div>
<div id="xong"><h2>Da cham xong</h2>
  <p>Bam <b>Tai phieu ve</b>, roi chep <code>phieu.json</code> vao thu muc lo, ghi de.</p>
  <p>Sau do tren may A chay:<br><code id="lenh"></code></p></div>
<div id="zoom"><img id="zL"><img id="zR"></div><div id="nhan"></div>
<div id="canhbao" hidden>KHONG LUU DUOC PHIEU tren may nay (trinh duyet chan localStorage voi file://). Dung tai lai trang, va bam "Tai phieu ve" truoc khi dong.</div>
<script>
const CAP = __CAP__, KHOA = "cham_mu_" + __LO__;
const $ = s => document.querySelector(s);
// ⛔ `file://` co the lam localStorage NEM (Chrome chan tuy cau hinh). Khong boc
// thi ca trang chet trang o dong dau tien - va nguoi cham khong hieu vi sao.
// Boc lai, va NOI RA khi khong luu duoc, thay vi im lang lam mat phieu.
let luuDuoc = true;
function doc() {
  try { return JSON.parse(localStorage.getItem(KHOA) || "{}"); }
  catch (e) { luuDuoc = false; return {}; }
}
function luu(d) {
  try { localStorage.setItem(KHOA, JSON.stringify(d)); }
  catch (e) { luuDuoc = false; bao(); }
}
function bao() { if (!luuDuoc) $("#canhbao").hidden = false; }
let i = 0, phieu = doc();
let zPhia = "trai";

function ve(){
  const c = CAP[i];
  $("#ma").textContent = c.ma;
  const xong = CAP.filter(x => phieu[x.ma] && phieu[x.ma].chon).length;
  $("#tien").textContent = `cap ${i+1}/${CAP.length} - da cham ${xong}`;
  $("#imgL").src = $("#zL").src = "anh/" + c.trai;
  $("#imgR").src = $("#zR").src = "anh/" + c.phai;
  const p = phieu[c.ma] || {};
  $("#ghi").value = p.ghi_chu || "";
  document.querySelectorAll("#dieu button").forEach(b =>
    b.classList.toggle("chon", b.dataset.c === p.chon));
}
function chon(v){
  const c = CAP[i];
  phieu[c.ma] = {chon: v, ghi_chu: $("#ghi").value};
  luu(phieu);
  if (i < CAP.length - 1) i++;
  ve(); ketthuc();
}
function ketthuc(){
  if (CAP.some(c => !(phieu[c.ma] || {}).chon)) return;
  $("#than").style.display = "none"; $("#xong").style.display = "block";
  $("#lenh").textContent = "py tools/cham_mu.py tinh --lo <thu_muc_lo>";
}
function moZoom(phia){
  // Ca hai anh da nam san trong DOM tu luc ve() - chi bat/tat, khong tai lai.
  zPhia = phia;
  $("#zoom").classList.add("mo");
  $("#zL").classList.toggle("an", phia !== "trai");
  $("#zR").classList.toggle("an", phia !== "phai");
  $("#nhan").style.display = "block"; $("#nhan").textContent = phia.toUpperCase();
}
function dongZoom(){
  $("#zoom").classList.remove("mo"); $("#nhan").style.display = "none";
}
function doiZoom(){
  // Khong dung toi scrollTop/scrollLeft: hai anh chung mot o luoi nen vi tri cuon
  // von da la MOT. Day moi la "cung vi tri" that, khong phai chep lai toa do.
  moZoom(zPhia === "trai" ? "phai" : "trai");
}
$("#imgL").onclick = () => moZoom("trai");
$("#imgR").onclick = () => moZoom("phai");
$("#zoom").onclick = dongZoom;
document.querySelectorAll("#dieu button").forEach(b => b.onclick = () => chon(b.dataset.c));
$("#luu").onclick = () => {
  const ra = {so_cap: CAP.length,
              phieu: CAP.map(c => ({ma: c.ma, chon: (phieu[c.ma]||{}).chon || "",
                                    ghi_chu: (phieu[c.ma]||{}).ghi_chu || ""}))};
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([JSON.stringify(ra, null, 2)],
                                        {type: "application/json"}));
  a.download = "phieu.json"; a.click();
};
addEventListener("keydown", e => {
  if (e.target.tagName === "TEXTAREA" && e.key !== "Escape") return;
  const mo = $("#zoom").classList.contains("mo");
  if (mo && (e.key === " " || e.key === "ArrowLeft" || e.key === "ArrowRight")){
    e.preventDefault(); doiZoom(); return; }
  if (e.key === "Escape"){ dongZoom(); return; }
  if (e.key === "1") chon("trai");
  else if (e.key === "2") chon("hoa");
  else if (e.key === "3") chon("phai");
  else if (e.key.toLowerCase() === "z") moZoom("trai");
  else if (e.key === "ArrowLeft" && i > 0){ i--; ve(); }
  else if (e.key === "ArrowRight" && i < CAP.length - 1){ i++; ve(); }
});
// Tai lai trang giua chung (lo cham 33 cap thi chuyen nay se xay ra) phai quay
// dung cho dang do, khong bat cham lai tu cap 1 - cham lai la het mu.
bao();
const chuaCham = CAP.findIndex(c => !(phieu[c.ma] || {}).chon);
i = chuaCham < 0 ? 0 : chuaCham;
ve(); ketthuc();
</script></body></html>
"""


def ghi_man(caps: Sequence[Cap], thu_muc: Path) -> None:
    """Sinh màn chấm cạnh lô.

    ⛔ Chỉ ghi ra `ma`, `trai`, `phai` — **tuyệt đối không** `nguon_trai`,
    `nguon_phai`, `la_bay`. Ba trường đó nằm trong tệp khoá, và nhúng chúng vào
    HTML là để nguồn lộ ra ngay trong "Xem mã nguồn trang". Test chốt điều này.
    """
    cap_cong_khai = [{"ma": c.ma, "trai": c.trai, "phai": c.phai} for c in caps]
    html = (_MAN_HTML
            .replace("__CAP__", json.dumps(cap_cong_khai, ensure_ascii=False))
            .replace("__LO__", json.dumps(thu_muc.name)))
    (thu_muc / TEN_MAN).write_text(html, encoding="utf-8")


# ─────────────────────────── tính kết quả ───────────────────────────────────
def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Khoảng tin cậy Wilson cho tỉ lệ. Dùng Wilson chứ không dùng công thức chuẩn
    vì với n nhỏ (đúng tình huống của ta) công thức chuẩn cho khoảng vượt [0,1] và
    hẹp giả tạo — nó sẽ nói "khác biệt có ý nghĩa" khi thật ra không."""
    if n <= 0:
        return 0.0, 1.0
    p = k / n
    d = 1 + z * z / n
    tam = (p + z * z / (2 * n)) / d
    nua = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / d
    return max(0.0, tam - nua), min(1.0, tam + nua)


def tinh(caps: Sequence[Cap], phieu: dict[str, str]) -> KetQua:
    """`phieu`: ma → "trai" | "phai" | "hoa". Cặp chưa chấm thì bỏ qua."""
    thang_a = thang_b = hoa = 0
    n_bay = bay_quyet = bay_trai = 0
    that_quyet = 0
    for c in caps:
        chon = (phieu.get(c.ma) or "").strip().lower()
        if chon not in CHON_HOP_LE:
            continue
        if c.la_bay:
            n_bay += 1
            if chon != "hoa":
                bay_quyet += 1
                if chon == "trai":
                    bay_trai += 1
            continue
        if chon == "hoa":
            hoa += 1
            continue
        that_quyet += 1
        nguon = c.nguon_trai if chon == "trai" else c.nguon_phai
        if nguon == "A":
            thang_a += 1
        else:
            thang_b += 1

    n_that = thang_a + thang_b + hoa
    diem = (thang_a + 0.5 * hoa) / n_that if n_that else 0.0
    # Quy về đếm nguyên để Wilson dùng được: hoà tính nửa điểm cho mỗi bên.
    thap, cao = wilson(int(round(thang_a + 0.5 * hoa)), n_that) if n_that else (0.0, 1.0)

    f = bay_quyet / n_bay if n_bay else 0.0
    d = that_quyet / n_that if n_that else 0.0
    lech = bay_trai / bay_quyet if bay_quyet else 0.5

    ly_do: list[str] = []
    ket = ""
    if n_that < SO_CAP_TOI_THIEU:
        ket = "chua phan biet duoc"
        ly_do.append(f"moi co {n_that} cap that, can >= {SO_CAP_TOI_THIEU}")
    if n_bay and d <= f:
        ket = "chua phan biet duoc"
        # ASCII thuan trong thong diep: chung duoc IN RA CONSOLE Windows, noi
        # stdout mac dinh la cp1252 va mot dau gach dai se thanh dau hoi den.
        ly_do.append(
            f"quyet doan tren cap that ({d:.0%}) khong hon san nhieu ({f:.0%}) - "
            "khac biet giua hai model nho hon khac biet giua hai lan chay cung model")
    if not ket:
        if thap <= 0.5 <= cao:
            ket = "chua phan biet duoc"
            ly_do.append(
                f"khoang tin cay diem A [{thap:.0%}, {cao:.0%}] van chua 50%")
        elif diem > 0.5:
            ket = "A thang"
        else:
            ket = "B thang"
    if bay_quyet >= 4 and not 0.3 <= lech <= 0.7:
        ly_do.append(
            f"NGHI LECH VI TRI: tren cap bay, {lech:.0%} chon ben trai - "
            "nguoi cham co the dang uu tien mot phia, khong phai mot anh")
    return KetQua(n_that, thang_a, thang_b, hoa, diem, thap, cao,
                  n_bay, f, d, lech, ket, ly_do)


# ─────────────────────────── CLI ────────────────────────────────────────────
def _ghi_json(duong: Path, obj) -> None:
    # UTF-8 KHONG BOM — quy tac 1 cua CLAUDE.md. Loi BOM da tung lam sap production.
    duong.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def _anh_trong(thu_muc: Path) -> list[str]:
    duoi = {".png", ".jpg", ".jpeg", ".webp"}
    return [str(p) for p in sorted(thu_muc.iterdir())
            if p.is_file() and p.suffix.lower() in duoi]


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="So mu cho H37")
    sub = ap.add_subparsers(dest="lenh", required=True)

    t = sub.add_parser("tao", help="dung mot lo so mu")
    t.add_argument("--a", required=True, type=Path)
    t.add_argument("--b", required=True, type=Path)
    t.add_argument("--ra", required=True, type=Path)
    t.add_argument("--nhan-a", default="A")
    t.add_argument("--nhan-b", default="B")
    t.add_argument("--bay", type=float, default=TY_LE_BAY)
    t.add_argument("--seed", type=int, default=None)

    c = sub.add_parser("tinh", help="tinh ket qua tu phieu da cham")
    c.add_argument("--lo", required=True, type=Path)

    a = ap.parse_args(argv)

    if a.lenh == "tao":
        caps = tao_lo(_anh_trong(a.a), _anh_trong(a.b), ty_le_bay=a.bay,
                      rng=random.Random(a.seed))
        ghi_lo(caps, a.ra, nhan_a=a.nhan_a, nhan_b=a.nhan_b)
        ghi_man(caps, a.ra)
        that = sum(1 for x in caps if not x.la_bay)
        print(f"Da dung {len(caps)} cap ({that} that, {len(caps) - that} bay) tai {a.ra}")
        print(f"Mo de cham: {(a.ra / TEN_MAN).resolve()}")
        if that < SO_CAP_TOI_THIEU:
            print(f"CANH BAO: chi co {that} cap that. Duoi {SO_CAP_TOI_THIEU} thi "
                  "ket qua chi duoc ghi la 'chua phan biet duoc'.")
        return 0

    khoa = json.loads((a.lo / TEN_KHOA).read_text(encoding="utf-8"))
    caps = [Cap(**x) for x in khoa["cap"]]
    phieu_raw = json.loads((a.lo / TEN_PHIEU).read_text(encoding="utf-8"))
    phieu = {x["ma"]: x.get("chon", "") for x in phieu_raw["phieu"]}
    kq = tinh(caps, phieu)
    nhan = khoa.get("nhan", {})
    print(json.dumps({"A": nhan.get("A"), "B": nhan.get("B"), **kq.as_dict()},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
