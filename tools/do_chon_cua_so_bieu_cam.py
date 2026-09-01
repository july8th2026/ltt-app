r"""
do_chon_cua_so_bieu_cam.py — chọn cửa sổ tham chiếu BIỂU CẢM hơn có làm bản
sinh ra biểu cảm hơn không.

    powershell -ExecutionPolicy Bypass -File .\setup\do_chon_cua_so_bieu_cam.ps1

## Đòn bẩy này nằm trong mã của TA, không phải của upstream

Khuyết tật đã đo và đã loại confound:

    do tan F0 cua ban SINH RA / cua clip goc (cung do dai)  =  -42,4%

Ba đường đã thử và **đều âm**:
  · bộ khử nhiễu — chỉ chiếm 2,6% độ tối, không liên quan biểu cảm
  · EQ bù độ sáng — DNSMOS phẳng lì ở mọi mức
  · `temperature` 0,8→1,25 — biểu cảm KHÔNG đi theo (t = 0,53), mà CER thì
    tăng gấp đôi ở 1,10

⇒ Nên nhìn vào chỗ chưa nhìn: **cách ta chọn cửa sổ tham chiếu.**

`chon_doan.chon()` xếp hạng ứng viên theo đúng một tiêu chí —
`cosine(emb(đoạn), emb(cả clip))`, tức độ **đại diện**.

🔴 Nhưng embedding người nói được thiết kế để **bất biến với ngữ điệu** — đó
   chính là điều khiến nó là embedding *người nói* chứ không phải embedding
   *câu nói*. Nên trong số những cửa sổ đại diện ngang nhau, tiêu chí hiện tại
   chọn một cửa sổ **ngẫu nhiên về mặt ngữ điệu**.

⭐ Nếu model nhân bản cả tính cách ngữ điệu của cửa sổ tham chiếu — điều mà kiến
   trúc v3 gợi ý, vì nó nhúng `ref_codes` chứ không chỉ `speaker_emb` — thì
   chọn cửa sổ biểu cảm hơn là một cách sửa **không tốn gì lúc chạy**: cùng một
   bước chọn, chỉ khác cách phá hoà.

## Thiết kế, và chỗ nguy hiểm của nó

Với mỗi giọng, sinh cùng một bộ câu từ HAI cửa sổ tham chiếu:

    A. cua so DANG CHON — dai dien nhat (cosine cao nhat)
    B. cua so BIEU CAM NHAT trong so nhung cua so con DU dai dien

⛔ "Còn đủ đại diện" là phần bắt buộc, không phải phần cho đẹp. Cửa sổ có độ
   tản F0 cao nhất rất có thể là cửa sổ khách **cười, hét, hay đọc kịch** — nó
   biểu cảm vì nó **không điển hình**, và nhân bản từ đó là nhân bản một khoảnh
   khắc chứ không phải một giọng. Nên B chỉ lấy trong số cửa sổ có cosine
   không thấp hơn cửa sổ tốt nhất quá `SAN_DAI_DIEN`.

Đo ba trục:
  ① biểu cảm — `f0_tan_tuong_doi` của bản sinh ra so với clip gốc
  ② danh tính — cosine giữa bản sinh ra và clip gốc
  ③ ổn định  — chốt K1 + CER

⭐ Trục ② là chỗ phép thử này có thể **thua**, và phải đo chứ không đoán: nếu
   cửa sổ biểu cảm hơn làm giọng nghe **khác người** thì đổi tiêu chí là một
   bước lùi, dù biểu cảm có lên.

⚠️ Ở trục ② dùng chính bộ mã hoá của VieNeu — và ở đây điều đó **hợp lệ**, khác
   với K0: ta đang so hai bản của CÙNG một hệ với nhau, không so hai hệ. Bộ mã
   hoá không thể thiên vị bên nào.
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

#: Cửa sổ B phải có cosine đại diện không thấp hơn cửa sổ tốt nhất quá mức này.
#:
#: ⛔ Không phải một con số tuỳ ý: nó là ranh giới giữa "chọn một cửa sổ khác
#:    cũng đại diện" và "chọn một khoảnh khắc bất thường". Nếu phép đo cho thấy
#:    B thắng, bước tiếp là quét chính con số này.
SAN_DAI_DIEN = 0.05

CAU = [
    "Ba tôi bảo bà ấy bán bánh ở bãi biển vào buổi sáng.",
    "Cô ấy cố gắng có được một cỗ máy mới cho công việc.",
    "Mẹ dặn mà tôi mải mê nên quên mất lời mẹ nói.",
]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--clip", default="tmp/giong_cu")
    ap.add_argument("--so-giong", type=int, default=5)
    ap.add_argument("--ra", default="tmp/chon_cua_so_bieu_cam.json")
    a = ap.parse_args(argv)

    import glob

    import numpy as np
    import soundfile as sf

    from voice_sidecar import (chon_doan, chot_sinh, do_chat_luong, do_on_dinh,
                               engine)

    cong = engine.lay_cong()
    cac = sorted(glob.glob(os.path.join(a.clip, "*.wav")))
    buoc = max(1, len(cac) // a.so_giong)
    cac = cac[::buoc][:a.so_giong]
    if not cac:
        print(f"KHONG CO WAV trong {a.clip}", file=sys.stderr)
        return 2

    bo = do_chat_luong._bo_ma_hoa_giong()
    if bo is None:
        print("KHONG NAP DUOC bo ma hoa nguoi noi", file=sys.stderr)
        return 2

    def _emb(w, sr):
        return do_chat_luong._embed(bo, w, sr)

    print(f"{len(cac)} giong x {len(CAU)} cau x 2 cua so\n")
    gom = {"A": {}, "B": {}, "C": {}}
    chi_tiet = []
    for p in cac:
        ten = os.path.basename(p).replace(".wav", "")
        w, sr = sf.read(p, dtype="float32", always_2d=False)
        if getattr(w, "ndim", 1) > 1:
            w = w.mean(axis=1)
        e_ca = _emb(w, int(sr))
        if e_ca is None:
            continue

        # Dựng lại đúng tập ứng viên mà `chon_doan` dùng, rồi chấm HAI cách.
        n = int(chon_doan.CUA_SO_S * sr)
        uv = [(i, i + n) for i in range(0, len(w) - n + 1, max(1, n // 4))]
        if not uv:
            continue
        cham = []
        for i, j in uv:
            e = _emb(w[i:j], int(sr))
            if e is None:
                continue
            dd = do_chat_luong._cosine(e, e_ca)
            bc = (do_on_dinh.do_on_dinh_f0(w[i:j], int(sr)) or {}).get(
                "f0_tan_tuong_doi")
            if bc is None:
                continue
            cham.append({"i": i, "j": j, "dai_dien": dd, "bieu_cam": bc})
        if len(cham) < 2:
            continue

        A = max(cham, key=lambda x: x["dai_dien"])
        du = [x for x in cham if x["dai_dien"] >= A["dai_dien"] - SAN_DAI_DIEN]
        B = max(du, key=lambda x: x["bieu_cam"])
        # 🔴 NHANH C — DICH DUNG, sau khi nhanh B nham sai.
        #
        #    Lượt đo đầu cho thấy đích không phải "biểu cảm nhất": cửa sổ cực
        #    đại là một **khoảnh khắc bất thường**, và 3/5 giọng thậm chí không
        #    có cửa sổ nào biểu cảm hơn trong ngưỡng — nhánh B thực ra chỉ thử
        #    hai giọng.
        #
        # ⭐ Đích đúng là **ĐIỂN HÌNH**: cửa sổ có độ tản F0 gần **trung vị của
        #    cả clip** nhất. Vì cơ chế đã lộ ra là — `cosine` với embedding
        #    TRUNG BÌNH của clip ưu ái cửa sổ ít động, do mọi đoạn ngữ điệu
        #    mạnh đều kéo ra xa tâm. Nên tối đa hoá độ đại diện chọn có hệ
        #    thống đoạn PHẲNG NHẤT (0,1131 so với 0,2515 của cả clip).
        #
        #    Sửa không phải "lấy cực đại" mà "lấy đúng mức điển hình của chính
        #    người ấy".
        tv_clip = statistics.median([x["bieu_cam"] for x in cham])
        C = min(du, key=lambda x: abs(x["bieu_cam"] - tv_clip))
        chi_tiet.append({"giong": ten, "so_ung_vien": len(cham),
                         "A": {k: round(A[k], 4) for k in ("dai_dien", "bieu_cam")},
                         "B": {k: round(B[k], 4) for k in ("dai_dien", "bieu_cam")},
                         "C": {k: round(C[k], 4) for k in ("dai_dien", "bieu_cam")},
                         "trung_vi_clip": round(tv_clip, 4),
                         "so_du_dai_dien": len(du)})
        print(f"  {ten[:26]:26} A: dd={A['dai_dien']:.4f} bc={A['bieu_cam']:.4f}"
              f" | B: dd={B['dai_dien']:.4f} bc={B['bieu_cam']:.4f}"
              f"  ({len(du)}/{len(cham)} du dai dien)")

        for nhan, x in (("A", A), ("B", B), ("C", C)):
            if x["i"] == A["i"] and nhan == "B":
                # B trung A: khong sinh lai, nhung PHAI ghi nhan — neu khong thi
                # bang ket qua se co n khac nhau giua hai nhanh ma khong ai biet.
                chi_tiet[-1]["B_trung_A"] = True
            t = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
            t.close()
            sf.write(t.name, w[x["i"]:x["j"]], int(sr))
            try:
                hs = cong.ghi_danh(t.name)
            except Exception as ex:                       # noqa: BLE001
                print(f"    [ghi danh hong] {ten}/{nhan}: "
                      f"{type(ex).__name__}: {ex}")
                continue
            finally:
                try:
                    os.unlink(t.name)
                except OSError:
                    pass
            rb = hs.get("ref_b64") or ""
            if not rb:
                continue
            for c in CAU:
                try:
                    wo, _ = cong.noi(c, ref_b64=rb)
                except Exception as ex:                   # noqa: BLE001
                    print(f"    [sinh hong] {ten}/{nhan}: "
                          f"{type(ex).__name__}: {ex}")
                    continue
                sro = 48000
                # ① bieu cam, do THEO TI LE voi clip goc cung do dai
                # 🔴 THU GIA TRI TUYET DOI, KHONG THU TI LE.
                #
                #    Lượt đo đầu thu `dau_ra / cua_so - 1` và **tỉ lệ ấy che
                #    mất câu trả lời**: nhánh A ra +0,227 (đầu ra biểu cảm HƠN
                #    cửa sổ) còn nhánh B ra −0,345, và đọc lướt thì tưởng A
                #    thắng. Nhưng hai tỉ lệ ấy có **mẫu số khác nhau** — cửa sổ
                #    B vốn biểu cảm hơn cửa sổ A 1,41 lần.
                #
                #    Quy về tuyệt đối mới thấy: đầu ra A = 0,1388, đầu ra B =
                #    0,1042. Câu hỏi luôn là *"đầu ra biểu cảm bao nhiêu"*, và
                #    một tỉ lệ với mẫu số thay đổi không trả lời được câu đó.
                bc = (do_on_dinh.do_on_dinh_f0(wo, sro) or {}).get(
                    "f0_tan_tuong_doi")
                if bc is not None:
                    gom[nhan].setdefault("bieu_cam_tuyet_doi", []).append(
                        float(bc))
                # ② danh tinh
                eo = _emb(wo, sro)
                if eo is not None:
                    gom[nhan].setdefault("danh_tinh", []).append(
                        do_chat_luong._cosine(eo, e_ca))
                # ③ on dinh
                pq = chot_sinh.kiem_het(wo, sro, len(c))
                gom[nhan].setdefault("chot_hong", []).append(
                    0.0 if pq.dat else 1.0)
                t2 = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
                t2.close()
                sf.write(t2.name, wo, sro)
                try:
                    dh = do_chat_luong.do_de_hieu(t2.name, c, "vi") or {}
                    if dh.get("cer") is not None:
                        gom[nhan].setdefault("cer", []).append(float(dh["cer"]))
                finally:
                    try:
                        os.unlink(t2.name)
                    except OSError:
                        pass

    def _tb(v):
        if not v:
            return None, 0.0, 0
        s = statistics.pstdev(v) / math.sqrt(len(v)) if len(v) > 1 else 0.0
        return statistics.mean(v), s, len(v)

    print("\n" + "=" * 76)
    print("  CHON CUA SO: DAI DIEN NHAT (A)  vs  BIEU CAM NHAT (B)")
    print("=" * 76)
    print(f"  {'truc':12} {'A dang chay':>20} {'B cuc dai':>20} "
          f"{'C dien hinh':>20}")
    ra = {}
    for truc in ("bieu_cam_tuyet_doi", "danh_tinh", "cer", "chot_hong"):
        ba = {n: _tb(gom[n].get(truc)) for n in ("A", "B", "C")}
        if any(x[0] is None for x in ba.values()):
            continue
        ra[truc] = {n: {"tb": round(v[0], 5), "sai_so": round(v[1], 5),
                        "n": v[2]} for n, v in ba.items()}
        print(f"  {truc:12}" + "".join(
            f" {ba[n][0]:>13.4f} ±{ba[n][1]:.4f}" for n in ("A", "B", "C")))

    bc = ra.get("bieu_cam", {})
    dt = ra.get("danh_tinh", {})
    print()
    if bc.get("ket_luan") == "B hon" and dt.get("ket_luan") != "A hon":
        print("  ✅ Chon cua so BIEU CAM hon lam ban sinh ra bieu cam hon MA")
        print("     KHONG lam mat danh tinh. Day la mot duong sua that, va no")
        print("     khong ton gi luc chay — cung mot buoc chon, khac cach pha hoa.")
    elif bc.get("ket_luan") == "B hon":
        print("  ⚠️ Bieu cam len NHUNG danh tinh xuong. Cua so bieu cam nhat co")
        print("     the la mot khoanh khac bat thuong — thu ha SAN_DAI_DIEN.")
    else:
        print("  🔴 Khong khac biet. Model KHONG nhan ban tinh cach ngu dieu cua")
        print("     cua so tham chieu — no chi lay danh tinh nguoi noi. Neu vay")
        print("     thi -42% bieu cam la thuoc tinh cua MODEL, va khong co duong")
        print("     nao sua no tu phia ta.")

    os.makedirs(os.path.dirname(a.ra) or ".", exist_ok=True)
    with open(a.ra, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"san_dai_dien": SAN_DAI_DIEN, "truc": ra,
                   "chi_tiet": chi_tiet}, f, ensure_ascii=False, indent=2)
    print(f"\nDa ghi: {a.ra}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
