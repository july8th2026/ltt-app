"""
bradley_terry.py — xếp hạng NHIỀU model từ phiếu so từng cặp.

    from tools.bradley_terry import xep_hang
    xep_hang([("A", "B", "A"), ("B", "C", "hoa"), ...])

⭐ VÌ SAO CẦN, KHI ĐÃ CÓ `cham_mu.tinh()`

   `cham_mu.tinh()` tính **tỉ lệ thắng + khoảng Wilson**. Cái đó **đúng và đủ cho
   HAI model**. G6b có **ba đối thủ** (Klein 9B · Gemini 3 Pro Image · GPT Image 2),
   và ở đó tỉ lệ thắng theo cặp **không cộng lại thành một bảng xếp hạng nhất
   quán**: A thắng B, B thắng C, C thắng A là chuyện **bình thường** trong dữ liệu
   thật, không phải dấu hiệu ai đó chấm sai.

📖 THEO TÀI LIỆU. LMArena (Chatbot Arena) **bỏ Elo tuần tự** tháng 12/2023 và
   chuyển sang **Bradley-Terry ước lượng hợp lý cực đại**, khoảng tin cậy bằng
   **bootstrap** (bách phân vị 2,5–97,5).

   Lý do họ đổi đáng chép lại: Elo cập nhật sau **từng trận** nên **phụ thuộc thứ
   tự** — xáo lại cùng một bộ phiếu ra một bảng xếp hạng khác. Bradley-Terry khớp
   **toàn bộ phiếu cùng lúc**, nên cùng dữ liệu luôn cho cùng kết quả.

   Nguồn: <https://www.lmsys.org/blog/2023-12-07-leaderboard/> ·
   <https://github.com/lm-sys/FastChat> (Apache-2.0). Ta chép **cách làm**, không
   chép mã.

🔧 KHÁC HỌ HAI CHỖ:

   · **Không quy về thang Elo 1000–2000.** Thang đó chỉ có nghĩa khi so với một
     bảng xếp hạng cùng thang. Ta có ba model và một câu hỏi *"có đáng bán không"*,
     nên giữ nguyên **xác suất thắng** — đọc thẳng ra được.
   · **Hoà tính là nửa thắng cho mỗi bên.** Bradley-Terry gốc không mô hình hoá
     hoà; biến thể Davidson thì có. Với bộ phiếu vài trăm cặp, nửa-thắng là xấp xỉ
     tiêu chuẩn và **không giấu** hoà đi — `so_hoa` vẫn báo ra để người đọc tự
     đánh giá bộ dữ liệu.

⛔ KHÔNG THAY `cham_mu.tinh()`. Với đúng hai model, Wilson **chặt hơn** và đã có 21
   test. Tệp này là công cụ cho trường hợp ba bên trở lên.
"""
from __future__ import annotations

import math
import random
from dataclasses import asdict, dataclass, field
from typing import Iterable, Optional, Sequence

#: Số vòng bootstrap. LMArena dùng 100; 200 cho khoảng ổn định hơn mà vẫn chạy
#: trong tích tắc ở quy mô vài trăm cặp.
SO_VONG_BOOTSTRAP = 200

#: Trần vòng lặp của phép khớp. Hội tụ thật thường dưới 100 vòng; trần này chỉ để
#: một bộ dữ liệu bệnh lý không treo vô hạn.
TRAN_LAP = 500

#: Ngưỡng dừng: đổi ít hơn thế này thì coi là hội tụ.
NGUONG_HOI_TU = 1e-9


class KhongDuDuLieu(ValueError):
    """Không đủ phiếu để xếp hạng. Ném chứ không trả một bảng trông có vẻ đúng."""


@dataclass
class HangModel:
    ten: str
    suc_manh: float          # tham so Bradley-Terry, da chuan hoa ve trung binh 1
    xac_suat_thang: float    # xac suat thang mot doi thu TRUNG BINH
    ci_thap: float
    ci_cao: float
    so_tran: int
    so_thang: float          # hoa tinh 0,5


@dataclass
class KetQuaBT:
    hang: list                       # [HangModel], cao -> thap
    so_cap: int
    so_hoa: int
    so_vong_bootstrap: int
    canh_bao: list = field(default_factory=list)

    def as_dict(self) -> dict:
        return asdict(self)

    def phan_biet_duoc(self, a: str, b: str) -> bool:
        """True nếu khoảng tin cậy của hai model **không chồng nhau**.

        ⛔ Đây là câu hỏi phải trả lời trước khi tuyên bố ai hơn ai. Hai khoảng
        chồng nhau nghĩa là **chưa đủ dữ liệu để phân biệt** — không phải "hoà",
        và càng không phải "gần bằng nhau".
        """
        ma = {h.ten: h for h in self.hang}
        if a not in ma or b not in ma:
            raise KeyError(f"khong co model: {a if a not in ma else b}")
        x, y = ma[a], ma[b]
        return x.ci_thap > y.ci_cao or y.ci_thap > x.ci_cao


def _khop(tran: Sequence[tuple], ten: Sequence[str]) -> dict:
    """Khớp Bradley-Terry bằng thuật lặp MM. Trả {tên: sức mạnh}.

    Thuật MM (minorize-maximize) của Hunter 2004 — đơn giản, luôn tăng hợp lý, và
    **không cần thư viện tối ưu nào**. Với vài nghìn cặp nó hội tụ trong tích tắc.
    """
    p = {t: 1.0 for t in ten}
    # thang[i] = so tran thang cua i (hoa = 0,5); cung[i][j] = so tran giua i va j
    thang = {t: 0.0 for t in ten}
    cung: dict = {t: {} for t in ten}
    for a, b, ai_thang in tran:
        cung[a][b] = cung[a].get(b, 0) + 1
        cung[b][a] = cung[b].get(a, 0) + 1
        if ai_thang == a:
            thang[a] += 1.0
        elif ai_thang == b:
            thang[b] += 1.0
        else:
            thang[a] += 0.5
            thang[b] += 0.5

    for _ in range(TRAN_LAP):
        moi = {}
        for i in ten:
            mau = 0.0
            for j, n in cung[i].items():
                mau += n / (p[i] + p[j])
            # Thang 0 tran: suc manh tien ve 0. Kep de khong chia cho 0 o vong sau.
            moi[i] = (thang[i] / mau) if mau > 0 else 1e-12
        tb = sum(moi.values()) / len(moi)
        if tb <= 0:
            break
        moi = {k: v / tb for k, v in moi.items()}      # chuan hoa: trung binh = 1
        doi = max(abs(moi[k] - p[k]) for k in ten)
        p = moi
        if doi < NGUONG_HOI_TU:
            break
    return p


def xep_hang(phieu: Iterable[tuple], *,
             so_vong: int = SO_VONG_BOOTSTRAP,
             rng: Optional[random.Random] = None) -> KetQuaBT:
    """Xếp hạng từ danh sách `(model_a, model_b, ai_thang)`.

    `ai_thang` là tên một trong hai model, hoặc `"hoa"`.
    """
    tran = []
    so_hoa = 0
    for m in phieu:
        a, b, w = (str(x).strip() for x in m)
        if not a or not b or a == b:
            continue
        if w not in (a, b) and w.lower() != "hoa":
            raise KhongDuDuLieu(f"ket qua khong hop le: {w!r} (phai la {a}, {b} hoac 'hoa')")
        if w.lower() == "hoa":
            so_hoa += 1
            w = "hoa"
        tran.append((a, b, w))

    ten = sorted({t for m in tran for t in m[:2]})
    if len(ten) < 2:
        raise KhongDuDuLieu("can it nhat hai model")
    if not tran:
        raise KhongDuDuLieu("khong co tran nao")

    # ⛔ Đồ thị phải LIÊN THÔNG. Hai cụm model chưa từng gặp nhau thì sức mạnh của
    #    chúng không so được — thuật vẫn chạy và vẫn ra số, nhưng con số đó vô
    #    nghĩa giữa hai cụm. Đây là kiểu hỏng im lặng đắt nhất của phép so cặp.
    if not _lien_thong(tran, ten):
        raise KhongDuDuLieu(
            "do thi tran KHONG lien thong: co model chua tung gap (truc tiep hay "
            "gian tiep) nhung model con lai, nen khong xep chung vao mot bang duoc")

    p = _khop(tran, ten)
    mau = _bootstrap(tran, ten, so_vong=so_vong, rng=rng or random.Random(20260823))

    so_tran = {t: 0 for t in ten}
    so_thang = {t: 0.0 for t in ten}
    for a, b, w in tran:
        so_tran[a] += 1
        so_tran[b] += 1
        if w == "hoa":
            so_thang[a] += 0.5
            so_thang[b] += 0.5
        else:
            so_thang[w] += 1.0

    hang = []
    for t in ten:
        ds = sorted(m[t] for m in mau)
        thap = ds[max(0, int(0.025 * len(ds)))] if ds else p[t]
        cao = ds[min(len(ds) - 1, int(0.975 * len(ds)))] if ds else p[t]
        hang.append(HangModel(
            ten=t, suc_manh=p[t],
            xac_suat_thang=p[t] / (p[t] + 1.0),   # so voi doi thu suc manh trung binh
            ci_thap=thap / (thap + 1.0), ci_cao=cao / (cao + 1.0),
            so_tran=so_tran[t], so_thang=so_thang[t]))
    hang.sort(key=lambda h: -h.suc_manh)

    canh_bao = []
    if len(tran) < 50:
        canh_bao.append(f"chi co {len(tran)} cap — duoi 50 thi khong ket luan (§1.5)")
    it = [t for t in ten if so_tran[t] < 20]
    if it:
        canh_bao.append(f"model co qua it tran, khoang tin se rat rong: {', '.join(it)}")
    if so_hoa > len(tran) * 0.6:
        canh_bao.append(
            f"{so_hoa}/{len(tran)} cap la HOA — nguoi cham khong phan biet duoc, "
            "bang xep hang nay noi rat it")
    return KetQuaBT(hang=hang, so_cap=len(tran), so_hoa=so_hoa,
                    so_vong_bootstrap=so_vong, canh_bao=canh_bao)


def _lien_thong(tran: Sequence[tuple], ten: Sequence[str]) -> bool:
    ke: dict = {t: set() for t in ten}
    for a, b, _w in tran:
        ke[a].add(b)
        ke[b].add(a)
    tham = {ten[0]}
    hang_doi = [ten[0]]
    while hang_doi:
        x = hang_doi.pop()
        for y in ke[x]:
            if y not in tham:
                tham.add(y)
                hang_doi.append(y)
    return len(tham) == len(ten)


def _bootstrap(tran: Sequence[tuple], ten: Sequence[str], *, so_vong: int,
               rng: random.Random) -> list:
    """Lấy mẫu lại **có hoàn lại** rồi khớp lại mỗi vòng — cách LMArena làm.

    Vòng nào lấy ra một bộ mẫu không liên thông thì **bỏ vòng đó**, không phải bỏ
    cả phép tính: đó là biến động của việc lấy mẫu, không phải lỗi dữ liệu.
    """
    ra = []
    n = len(tran)
    for _ in range(max(0, so_vong)):
        mau = [tran[rng.randrange(n)] for _ in range(n)]
        co = sorted({t for m in mau for t in m[:2]})
        if len(co) != len(ten) or not _lien_thong(mau, co):
            continue
        ra.append(_khop(mau, ten))
    return ra


def bang_van_ban(kq: KetQuaBT) -> str:
    """Bảng cho người đọc. Số phải đọc được mà không cần giải thích thêm."""
    d = [f"{kq.so_cap} cap, {kq.so_hoa} hoa, {kq.so_vong_bootstrap} vong bootstrap", ""]
    d.append(f"{'model':<24}{'thang':>8}{'tran':>7}{'p(thang)':>11}{'khoang tin 95%':>22}")
    for h in kq.hang:
        d.append(f"{h.ten:<24}{h.so_thang:>8.1f}{h.so_tran:>7}"
                 f"{h.xac_suat_thang:>10.1%} {h.ci_thap:>10.1%} - {h.ci_cao:<8.1%}")
    for c in kq.canh_bao:
        d.append(f"  !! {c}")
    return "\n".join(d)
