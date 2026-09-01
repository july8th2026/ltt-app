r"""
do_quet_temperature.py — đánh đổi BIỂU CẢM ↔ ỔN ĐỊNH theo `temperature`.

    powershell -ExecutionPolicy Bypass -File .\setup\do_quet_temperature.ps1

## Vì sao có tệp này

Baseline K4 đo được một khuyết tật lớn hơn cả độ tối:

    delta_f0_tan_tuong_doi_ti_le  =  -0,4556

Nghĩa là bản nhân bản **chỉ giữ 54% biến thiên cao độ** của clip gốc, ở mọi bản
khoẻ mạnh. Nói bằng lời khách hàng: **giọng nhân bản đều đều hơn giọng thật**.

Và tài liệu upstream gọi tên đúng cái núm điều khiển nó:

    "A temperature around 0.8 gives the most stable result for v3 Turbo.
     Higher values add expressiveness but can be less stable."

Ta đang chạy `TEMPERATURE = 0.8` — tức đầu **ổn định** của đánh đổi. Và chú
thích ngay tại `tham_so.py:35` viết: *"Mặc định của SDK. Giữ nguyên cho tới khi
có số đo nói khác."*

⇒ Nay đã có số đo nói khác. Tệp này đo **cả hai đầu** của đánh đổi để biết còn
  chỗ nào đổi được không, thay vì đổi rồi hy vọng.

## Đo ổn định bằng chính bộ chốt K1, không bằng cảm nhận

K1 đã dựng bốn chốt để bắt đúng những kiểu mất ổn định của model tự hồi quy:
toàn vẹn · gần im · lặp đuôi · thời lượng. Chúng đã hiệu chuẩn trên tiếng thật
(0/16 báo động giả, 6/6 bắt được hỏng hóc tiêm vào).

⭐ Nên câu hỏi *"temperature cao có kém ổn định hơn không"* **đã có sẵn một
   thước đo**, và không cần ai nghe. Nếu chốt K1 bắt đầu nổ khi temperature
   lên thì đó là bằng chứng trực tiếp, không phải một ấn tượng.

## Ba trục, và chúng phải đọc CÙNG LÚC

  ① **biểu cảm** — `delta_f0_tan_tuong_doi_ti_le`, càng gần 0 càng giống gốc
  ② **ổn định**  — tỉ lệ chốt K1 nổ + CER
  ③ **chất lượng** — DNSMOS

⛔ Một mức temperature làm ① đẹp lên trong khi ② xấu đi là **không dùng được**,
   và đó là kết cục nhiều khả năng nhất. Mục tiêu không phải "tìm mức tốt nhất"
   mà là **tìm xem có mức nào cải thiện ① mà KHÔNG động tới ②** — nếu không có
   thì câu trả lời là giữ nguyên 0,8, và ta biết vì sao chứ không chỉ đoán.

## ⚠️ Hai điều về chi phí

  · **Cache CUDA graph khoá theo `(B, temperature, top_k, top_p)`.** Mỗi mức
    trong phép quét là một khoá mới, tức một lần dựng lại cache. Đó là chi phí
    của phép ĐO, không phải của việc chạy thật — chạy thật chỉ có một mức.
  · **Đổi `TEMPERATURE` là đổi `PHIEN_BAN_THAM_SO`**, và baseline cổng V10 khoá
    theo đó (`test_376`). Nên một quyết định đổi kèm theo một lượt ghim lại
    baseline. Đó là thiết kế, không phải phiền toái: nó ngăn việc đổi tham số
    rồi so với một mốc đo bằng tham số cũ.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace",
                           line_buffering=True)

#: Mức quét. 0,8 là ĐỐI CHỨNG — cấu hình đang chạy.
MUC = (0.8, 0.95, 1.1, 1.25)

CAU = [
    "Ba tôi bảo bà ấy bán bánh ở bãi biển vào buổi sáng.",
    "Cô ấy cố gắng có được một cỗ máy mới cho công việc.",
    "Mẹ dặn mà tôi mải mê nên quên mất lời mẹ nói.",
    "Tôi thấy thầy giáo đứng ở cửa lớp từ sáng sớm.",
]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", default="tmp/ref_kho_chung.json")
    ap.add_argument("--clip-ref", default="tmp/giong_cu")
    ap.add_argument("--so-giong", type=int, default=4)
    ap.add_argument("--ra", default="tmp/quet_temperature.json")
    a = ap.parse_args(argv)

    if not os.path.isfile(a.ref):
        print(f"THIEU {a.ref} — chay `xuat_ref_kho_chung.ps1` truoc.",
              file=sys.stderr)
        return 2

    import soundfile as sf

    from voice_sidecar import (chot_sinh, dnsmos, do_chat_luong, engine,
                               lech_tham_chieu, tham_so)

    # ⛔ GỌI THẲNG ENGINE, KHÔNG QUA HTTP. Cửa `/v1/speech` **cố ý** không nhận
    #    `temperature`: CLAUDE.md cấm đưa nó ra hợp đồng công khai, vì cache
    #    CUDA graph khoá theo `(B, temp, top_k, top_p)` nên một tích hợp tự
    #    chỉnh nó sẽ dựng lại cache ở mỗi lượt gọi.
    #
    # ⭐ Nên phép quét đổi `tham_so.TEMPERATURE` **trong tiến trình đo**, và cửa
    #    công khai không mọc thêm một núm nào. Một phép đo không được để lại
    #    một bề mặt mới trên sản phẩm.
    cong = engine.lay_cong()
    temp_goc = tham_so.TEMPERATURE

    kho = json.load(open(a.ref, encoding="utf-8"))
    viec = []
    for g in kho:
        try:
            ma = (json.loads(g.get("ghi_chu") or "{}") or {}).get("ma_cu")
        except ValueError:
            ma = None
        if not ma:
            continue
        d = os.path.join(a.clip_ref, f"{ma}.wav")
        if os.path.isfile(d):
            viec.append({**g, "ma_cu": ma, "clip_ref": d})
    viec.sort(key=lambda x: x["public_id"])
    buoc = max(1, len(viec) // a.so_giong)
    viec = viec[::buoc][:a.so_giong]
    if not viec:
        print("KHONG GHEP DUOC GIONG NAO VOI CLIP THAM CHIEU", file=sys.stderr)
        return 2

    print(f"{len(viec)} giong x {len(CAU)} cau x {len(MUC)} muc temperature\n")
    gom = {m: {} for m in MUC}
    for m in MUC:
        for g in viec:
            wr, srr = sf.read(g["clip_ref"], dtype="float32", always_2d=False)
            if getattr(wr, "ndim", 1) > 1:
                wr = wr.mean(axis=1)
            for c in CAU:
                tham_so.TEMPERATURE = m
                try:
                    w, _ = cong.noi(c, ref_b64=g["ref_b64"])
                except Exception as ex:                   # noqa: BLE001
                    print(f"  [hong] t={m} {g['ten'][:20]}: "
                          f"{type(ex).__name__}: {ex}")
                    continue
                finally:
                    tham_so.TEMPERATURE = temp_goc
                sr = tham_so.SAMPLE_RATE if hasattr(tham_so, "SAMPLE_RATE") else 48000

                # ① bieu cam
                lc = lech_tham_chieu.do_lech(w, int(sr), wr, int(srr))
                v = lc.get("delta_f0_tan_tuong_doi_ti_le")
                if v is not None:
                    gom[m].setdefault("bieu_cam", []).append(float(v))
                # ② on dinh — CHINH bo chot K1
                pq = chot_sinh.kiem_het(w, int(sr), len(c))
                gom[m].setdefault("chot_hong", []).append(0.0 if pq.dat else 1.0)
                # ③ chat luong + de hieu
                d = dnsmos.cham(w, int(sr)) or {}
                if d.get("ovrl") is not None:
                    gom[m].setdefault("dnsmos", []).append(float(d["ovrl"]))
                t = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
                t.close()
                sf.write(t.name, w, int(sr))
                try:
                    dh = do_chat_luong.do_de_hieu(t.name, c, "vi") or {}
                    if dh.get("cer") is not None:
                        gom[m].setdefault("cer", []).append(float(dh["cer"]))
                finally:
                    try:
                        os.unlink(t.name)
                    except OSError:
                        pass
            print(f"  t={m:.2f}  {g['ten'][:34]}")

    def _tb(v):
        if not v:
            return None, 0.0, 0
        s = statistics.pstdev(v) / math.sqrt(len(v)) if len(v) > 1 else 0.0
        return statistics.mean(v), s, len(v)

    print("\n" + "=" * 78)
    print("  DANH DOI BIEU CAM <-> ON DINH THEO temperature")
    print("=" * 78)
    print(f"  {'temp':>6} {'bieu cam (gan 0 la tot)':>26} {'chot K1 hong':>14} "
          f"{'CER':>16} {'DNSMOS':>9}")
    ra = {}
    for m in MUC:
        bc, sbc, n = _tb(gom[m].get("bieu_cam"))
        ch, _, _ = _tb(gom[m].get("chot_hong"))
        ce, sce, _ = _tb(gom[m].get("cer"))
        dn, _, _ = _tb(gom[m].get("dnsmos"))
        ra[str(m)] = {"bieu_cam": bc, "sai_so_bieu_cam": sbc,
                      "ty_le_chot_hong": ch, "cer": ce, "dnsmos": dn, "n": n}
        print(f"  {m:>6.2f} {(bc if bc is not None else 0):>17.4f} "
              f"±{sbc:.4f} {(ch or 0) * 100:>12.0f}% "
              f"{(ce if ce is not None else -1):>10.4f} ±{sce:.4f} "
              f"{(dn or 0):>9.4f}")

    nen = ra[str(MUC[0])]
    print(f"\n  Doi chung t={MUC[0]}: bieu cam {nen['bieu_cam']:+.4f}  "
          f"chot hong {(nen['ty_le_chot_hong'] or 0) * 100:.0f}%  "
          f"CER {nen['cer']:.4f}")

    # ⛔ CHI nhan mot muc khi no cai thien ① MA KHONG lam xau ②.
    tot = None
    for m in MUC[1:]:
        r = ra[str(m)]
        if r["bieu_cam"] is None:
            continue
        hon_bc = r["bieu_cam"] - nen["bieu_cam"] > 1.96 * math.hypot(
            r["sai_so_bieu_cam"], nen["sai_so_bieu_cam"])
        khong_te = ((r["ty_le_chot_hong"] or 0) <= (nen["ty_le_chot_hong"] or 0)
                    and (r["cer"] or 9) <= (nen["cer"] or 0) + 0.01)
        if hon_bc and khong_te:
            tot = m
    if tot is None:
        print("\n  🔴 KHONG muc nao cai thien bieu cam MA KHONG dong toi on dinh.")
        print("     => GIU t=0,8. Danh doi la that, va 0,8 dang o dung phia")
        print("        ma san pham can: mot ban doc deu deu con dung duoc, mot")
        print("        ban doc lap hay cut thi khong.")
    else:
        print(f"\n  ✅ t={tot} cai thien bieu cam ma khong dong toi on dinh.")
        print("     ⚠️ Doi TEMPERATURE thi PHAI bump `PHIEN_BAN_THAM_SO` va ghim")
        print("        lai baseline cong V10 — `test_376` chot dieu do.")

    os.makedirs(os.path.dirname(a.ra) or ".", exist_ok=True)
    with open(a.ra, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"muc": ra, "tot_nhat": tot}, f, ensure_ascii=False, indent=2)
    print(f"\nDa ghi: {a.ra}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
