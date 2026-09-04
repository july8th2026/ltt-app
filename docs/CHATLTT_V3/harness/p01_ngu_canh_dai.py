"""
p01_ngu_canh_dai.py — tool-calling ở ngữ cảnh SÂU. Đây là chỗ [U] cảnh báo hỏng.

`llama.cpp/docs/function-calling.md:332` (khối `[!CAUTION]`):
    "Beware of extreme KV quantizations (e.g. `-ctk q4_0`), they can
     substantially degrade the model's tool calling performance."

Production chạy **đúng `q4_0`** trên cả hai hồ sơ, và quyết định giữ 200K ngữ
cảnh (chủ dự án, 04/09) đã **khoá** nó lại — không đổi được. Nên lô này không
hỏi *"có nên dùng q4_0 không"*; nó hỏi **cái giá là bao nhiêu**.

## Vì sao lô chính không đủ để trả lời

Lô chính chạy prompt ~2K token và đạt ~100 %. Suy giảm do KV lượng hoá lộ ra
khi **KV lớn**, không khi prompt ngắn — nên một PASS ở 2K **không nói gì** về
130K. Đó chính là lý do lô này tồn tại như một hạng mục riêng.

## Thiết kế: "kim trong đống cỏ" nhưng kim là một LỜI GỌI TOOL

Đống cỏ = một tài liệu dài do người dùng dán vào (đúng cách khách dùng ChatLTT
thật). Kim = một dữ kiện chôn ở **đầu / giữa / cuối** tài liệu, và câu hỏi cuối
**bắt buộc** phải lấy dữ kiện đó rồi đưa vào đối số của tool.

⭐ Chôn kim ở ba vị trí là có chủ ý: KV lượng hoá thường hỏng phần **giữa**
trước (hiệu ứng "lost in the middle"), nên một phép đo chỉ đặt kim ở cuối sẽ
cho điểm cao rồi kết luận sai.

⛔ Và phép chấm phải đòi **đúng con số của kim** trong đối số. Chỉ đòi "có gọi
   tool" là bỏ lọt đúng dạng hỏng đáng sợ nhất: gọi đúng tool với **đối số bịa**.
"""
from __future__ import annotations

import argparse
import base64
import json
import pathlib
import random
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import nexus_may_b as N                                          # noqa: E402
import p01_tools as T                                            # noqa: E402

CONG = 8280
MODEL = "qwen38-api"

CHU_DE = ["hệ thống phân tán", "bộ nhớ đệm", "hàng đợi công việc", "cân bằng tải",
          "sao lưu dữ liệu", "giám sát hạ tầng", "bảo mật ứng dụng", "tối ưu truy vấn",
          "kiểm thử tự động", "triển khai liên tục", "quản lý cấu hình", "ghi nhật ký"]
MENH_DE = [
    "Thành phần này chịu trách nhiệm điều phối các yêu cầu đến và phân bổ chúng theo trọng số.",
    "Khi tải tăng đột biến, hàng đợi sẽ giữ lại yêu cầu thay vì từ chối ngay lập tức.",
    "Mọi thao tác ghi đều đi qua một lớp kiểm tra quyền trước khi chạm vào kho dữ liệu.",
    "Bản ghi nhật ký được xoay vòng theo ngày và giữ lại trong ba mươi ngày.",
    "Nếu một nút không gửi tín hiệu trong chín mươi giây, nó bị coi là ngoại tuyến.",
    "Cấu hình được nạp một lần lúc khởi động và không đọc lại cho tới khi khởi động lại.",
    "Kết quả trung gian được lưu tạm để tránh tính lại phần đã tính.",
    "Mỗi yêu cầu mang một mã tương quan đi xuyên suốt các tầng để ghép lại được.",
]


def _doan(rnd: random.Random, i: int) -> str:
    ct = rnd.choice(CHU_DE)
    cau = " ".join(rnd.sample(MENH_DE, k=rnd.randint(3, 5)))
    return f"### Mục {i} — {ct}\n\n{cau}\n"


def dung_tai_lieu(rnd: random.Random, so_doan: int, kim: str, vi_tri: str) -> str:
    doan = [_doan(rnd, i) for i in range(1, so_doan + 1)]
    idx = {"dau": 1, "giua": len(doan) // 2, "cuoi": len(doan) - 1}[vi_tri]
    doan.insert(idx, f"### Mục đặc biệt — thông số vận hành\n\n{kim}\n")
    return "\n".join(doan)


def tokenize(noi: str, *, timeout: float = 120) -> int | None:
    return _post("/tokenize", {"content": noi}, timeout=timeout, cong=8281,
                 rut=lambda o: len(json.loads(o).get("tokens", [])))


#: Tran an toan cho duong base64-trong-dong-lenh. Windows cat dong lenh o
#: ~32K ky tu, va mot tai lieu 50K token vuot xa moc do.
TRAN_DONG_LENH = 20000
TEP_TREN_B = "C:/Users/Public/h44_than.json"


def _post(duong, than, *, timeout, cong, rut):
    """Gui mot yeu cau toi may B. Than LON di bang duong khac han.

    🔴 Lo dau tien hong het 12/12 trong 0,6 s — qua nhanh cho prefill 50K, tuc
       yeu cau khong bao gio toi model. Nguyen nhan: base64 cua mot tai lieu
       50K token la ~270 KB, con dong lenh Windows cat o ~32K. Lenh bi cat giua
       chung roi chay, va `curl` doc mot tep JSON cut.

    ⛔ Va no hong IM LANG: exit code van la cua curl, khong phai cua cho bi cat.
       Neu chi nhin "12/12 that bai" ma khong nhin **0,6 giay**, rat de ket luan
       nham rang model hong o ngu canh dai — dung cai ket luan lo nay sinh ra de
       kiem chung.
    """
    than_json = json.dumps(than, ensure_ascii=False)
    b64 = base64.b64encode(than_json.encode()).decode()
    if len(b64) > TRAN_DONG_LENH:
        # Ghi thang tep len may B qua File API roi bao curl doc tep do.
        ma, _ = N.goi("files/write",
                      {"path": TEP_TREN_B, "content": than_json,
                       "reason": "H44 P01: than yeu cau ngu canh dai"},
                      method="POST", timeout=180)
        if ma not in (200, 201):
            return None
        # Than lon => prefill lau => co the vuot tran 120s cua Nexus.
        return _chay_tach_roi(duong, timeout)
    else:
        ps = (f"$b='{b64}'; $p=Join-Path $env:TEMP 'h44_nc.json'; "
              f"[IO.File]::WriteAllBytes($p,[Convert]::FromBase64String($b)); "
              f"curl.exe -sS --max-time {int(timeout)} "
              f"-H 'Content-Type: application/json' -d \"@$p\" http://127.0.0.1:{cong}{duong}")
    ma, tra = N.goi("exec", {"command": ps, "args": [], "cwd": "C:/Users",
                             "reason": "H44 P01: do tool-calling o ngu canh sau"},
                    method="POST", timeout=timeout + 40)
    if ma not in (200, 201):
        return None
    d = (json.loads(tra).get("data") or {})
    if d.get("exit_code") != 0:
        return None
    try:
        return rut(d.get("stdout") or "")
    except (ValueError, KeyError, TypeError):
        return None


#: Tran cua Nexus: controller bo cuoc neu node khong tra loi trong 120 giay.
#: Do 04/09 — mot prefill 156K mat ~150-200s, tuc VUOT tran. Con so 120,2s cua
#: lan hong dau tien khop chinh xac voi tran nay, khong phai voi model.
TRAN_NEXUS_S = 110
TEP_RA = "C:/Users/Public/h44_out.json"
TEN_TAC_VU = "H44Long"


def _chay_tach_roi(duong_cong: str, timeout: float) -> dict | None:
    """Chay mot yeu cau DAI qua Scheduled Task roi hoi ket qua theo nhip.

    🔴 BA CACH DEU HONG TRUOC KHI TOI CACH NAY, va ca ba deu hong IM LANG:

       1. exec dong bo          -> Nexus cat o 120s (loi TIMEOUT cua controller)
       2. Start-Process -NoNewWindow -PassThru
                                -> tien trinh chet ngay khi exec tra ve; tep ra
                                   0 byte, tep loi 0 byte, khong con curl.exe nao
       3. (khong thu) Start-Job -> cung buoc vao phien PowerShell da chet

    ⭐ Ghi nho van hanh cua du an da noi truoc dieu nay: *"lo do dai tren may B
       phai dung Scheduled Task; ssh va Start-Process deu chet theo phien"*.
       Toi doc no tu dau phien va van di lai ca hai duong sai — vi luc do toi
       tuong no chi noi ve ssh.
    """
    B = chr(92); PUB = "C:" + B + "Users" + B + "Public" + B
    cmd = ("@echo off" + chr(13) + chr(10) +
           'curl.exe -sS --max-time ' + str(int(timeout)) +
           ' -H "Content-Type: application/json" -d "@' + PUB + 'h44_than.json" '
           'http://127.0.0.1:' + str(CONG) + duong_cong +
           ' > ' + PUB + 'h44_out.json 2> ' + PUB + 'h44_err.txt' + chr(13) + chr(10))
    # Xoa ket qua cu TRUOC khi chay — doc nham ket qua luot truoc la mot dang
    # hong khong bao gio bao loi.
    N.goi("files/write", {"path": TEP_RA, "content": "",
                          "reason": "H44 P01: xoa ket qua luot truoc"},
          method="POST", timeout=60)
    N.goi("files/write", {"path": "C:/Users/Public/h44_run.cmd", "content": cmd,
                          "reason": "H44 P01: script cho Scheduled Task"},
          method="POST", timeout=60)
    ma, _ = N.goi("exec", {"command": ("schtasks /Create /TN " + TEN_TAC_VU + " /TR " +
                                      PUB + "h44_run.cmd /SC ONCE /ST 00:00 "
                                      "/RL HIGHEST /RU SYSTEM /F 2>&1; "
                                      "schtasks /Run /TN " + TEN_TAC_VU + " 2>&1"),
                           "args": [], "cwd": "C:/Users",
                           "reason": "H44 P01: chay lo ngu canh dai qua Scheduled Task"},
                  method="POST", timeout=100)
    if ma not in (200, 201):
        return None
    het = time.monotonic() + timeout
    while time.monotonic() < het:
        time.sleep(8)
        ma, tra = N.goi("files/read?path=" + TEP_RA, timeout=60)
        if ma != 200:
            continue
        noi = (json.loads(tra).get("data") or {}).get("content") or ""
        if not noi.strip():
            continue
        try:
            return json.loads(noi)
        except ValueError:
            continue
    return None


#: (ma, kim, cau hoi, tool mong doi, chuoi PHAI co trong doi so)
KICH_BAN = [
    ("K1", "Mã định danh cụm sản xuất là 8123, và hệ số nhân tải là 4471.",
     "Dựa vào tài liệu trên, hãy tính tích của mã định danh cụm và hệ số nhân tải.",
     "calculator", ["8123", "4471"]),
    ("K2", "Trung tâm dữ liệu chính đặt tại thành phố Đà Nẵng.",
     "Dựa vào tài liệu trên, cho tôi biết thời tiết hiện tại ở nơi đặt trung tâm dữ liệu chính.",
     "weather_fake", ["nang", "da nang"]),
    ("K3", "Mã ảnh chuẩn dùng cho tài liệu này là img_5591.",
     "Dựa vào tài liệu trên, hãy sửa ảnh chuẩn của tài liệu: tăng độ tương phản.",
     "image_edit_fake", ["img_5591"]),
    ("K4", "Câu khẩu hiệu chính thức của hệ thống là: Vận hành bền bỉ mỗi ngày.",
     "Dựa vào tài liệu trên, hãy đọc câu khẩu hiệu chính thức thành tiếng.",
     "speech_fake", ["ben bi"]),
]


def main() -> int:
    p = argparse.ArgumentParser()
    goc = pathlib.Path(__file__).parent.parent
    p.add_argument("--out", default=str(goc / "artifacts" / "01_ngu_canh_dai.json"))
    p.add_argument("--sau", default="50000,130000,180000")
    p.add_argument("--lap", type=int, default=2)
    p.add_argument("--timeout", type=float, default=600.0)
    a = p.parse_args()

    do_sau = [int(x) for x in a.sau.split(",")]
    rnd = random.Random(20260904)

    # Do mot lan de biet moi doan ~bao nhieu token, roi suy so doan can dung.
    mau = "\n".join(_doan(random.Random(1), i) for i in range(1, 21))
    tk = tokenize(mau)
    if not tk:
        print("Khong dem duoc token — dung.", file=sys.stderr)
        return 1
    moi_doan = tk / 20
    print(f"Moi doan ~{moi_doan:.1f} token\n")

    ra = pathlib.Path(a.out); ra.parent.mkdir(parents=True, exist_ok=True)
    ket: list = []
    for sau in do_sau:
        so_doan = max(1, int(sau / moi_doan))
        for vi_tri in ("dau", "giua", "cuoi"):
            for ma, kim, hoi, ten, phai in KICH_BAN:
                for r in range(a.lap):
                    tl = dung_tai_lieu(rnd, so_doan, kim, vi_tri)
                    than = {"model": MODEL, "max_tokens": 512, "tools": T.TAT_CA,
                            "messages": [
                                {"role": "system", "content": T.HE_THONG},
                                {"role": "user",
                                 "content": f"Tài liệu:\n\n{tl}\n\n---\n\n{hoi}"}]}
                    t0 = time.monotonic()
                    goi_tra = _post("/v1/chat/completions", than,
                                    timeout=a.timeout, cong=CONG,
                                    rut=lambda o: json.loads(o))
                    giay = round(time.monotonic() - t0, 1)
                    if goi_tra is None:
                        m = {"ma": f"{ma}-{sau}-{vi_tri}-r{r}", "sau": sau,
                             "vi_tri": vi_tri, "loi": "khong goi duoc", "giay": giay}
                    else:
                        ch = (goi_tra.get("choices") or [{}])[0]
                        tin = ch.get("message") or {}
                        tcs = tin.get("tool_calls") or []
                        ten_goi = [((t.get("function") or {}).get("name") or "?") for t in tcs]
                        ds = json.dumps([(t.get("function") or {}).get("arguments")
                                         for t in tcs], ensure_ascii=False).lower()
                        import unicodedata
                        ds_kd = "".join(c for c in unicodedata.normalize("NFD", ds)
                                        if unicodedata.category(c) != "Mn").replace("đ", "d")
                        m = {"ma": f"{ma}-{sau}-{vi_tri}-r{r}", "sau": sau,
                             "vi_tri": vi_tri, "giay": giay,
                             "token_vao": (goi_tra.get("usage") or {}).get("prompt_tokens"),
                             "ten_goi": ten_goi,
                             "goi_dung": bool(ten_goi) and ten_goi[0] == ten,
                             "kim_trong_doi_so": all(x in ds_kd for x in phai),
                             "doi_so": ds[:200],
                             "content": (tin.get("content") or "")[:200]}
                    ket.append(m)
                    ra.write_text(json.dumps({"ket_qua": ket}, ensure_ascii=False,
                                             indent=2) + "\n", encoding="utf-8")
                    tv = m.get("token_vao") or "?"
                    print(f"  {m['ma']:<26} {giay:6.1f}s  vao={tv:<7} "
                          f"goi_dung={m.get('goi_dung')} kim={m.get('kim_trong_doi_so')}")

    print(f"\n{'do sau':>8} {'vi tri':>7} {'goi dung':>10} {'kim trong doi so':>18}")
    print("-" * 48)
    for sau in do_sau:
        for vi_tri in ("dau", "giua", "cuoi"):
            g = [k for k in ket if k.get("sau") == sau and k.get("vi_tri") == vi_tri
                 and "loi" not in k]
            if not g:
                continue
            a1 = sum(k["goi_dung"] for k in g)
            a2 = sum(k["kim_trong_doi_so"] for k in g)
            print(f"{sau:>8} {vi_tri:>7} {a1:>6}/{len(g)} {a2:>15}/{len(g)}")
    ra.write_text(json.dumps({"ket_qua": ket}, ensure_ascii=False, indent=2) + "\n",
                  encoding="utf-8")
    print(f"\nGhi: {ra}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
