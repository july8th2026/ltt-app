r"""
nhap_kho_giong_cu.py — nhập kho giọng của hệ CŨ (`D:\Voiceclone_TTS`) vào kho
DÙNG CHUNG của nền tảng, đi đúng cửa HTTPS mà một khách hàng đi.

    powershell -ExecutionPolicy Bypass -File .\setup\nhap_kho_giong_cu.ps1 -Xem
    powershell -ExecutionPolicy Bypass -File .\setup\nhap_kho_giong_cu.ps1 -Nhap

## Ba việc đường nhập cũ KHÔNG làm, và cả ba đều đã trả giá

① **GHI XUẤT XỨ.** Bốn giọng nhập trước 01/09 đều có `ghi_chu` **rỗng**. Khi
   hỏi *"Ivy lấy từ clip nào của kho cũ"* thì không ai trả lời được — kể cả
   `VoiceConsent` cũng chỉ nói *có người đã đồng ý*, không nói *đồng ý cho cái
   gì*. Với mười bảy giọng nguồn tiếng Anh sắp phát cho **mọi tài khoản**, xuất
   xứ là thứ phải ghi **lúc nhập**; sau đó thì không truy lại được.

   ⭐ Nhưng bốn giọng ấy vẫn truy được, và cách truy đáng ghi lại: `VoiceRef`
      giữ `sha256` của **tệp nguồn**, còn `tmp/giong_cu/*.wav` là chính những
      tệp đã nối ra để nhập. Nên chỉ cần băm lại và so — xuất xứ **suy ra được
      từ dữ liệu** thay vì phải nhớ. Đó là lý do `--xem` chạy phép so ấy trước
      khi làm bất cứ việc gì.

② **ĐẶT LÀN.** `ngon_ngu` mặc định `"vi"`, và không ai đặt, nên hai giọng tiếng
   Anh nằm ở làn tiếng Việt suốt. Ở đây làn suy ra từ **`engine` của hệ cũ** —
   `f5tts` → `vi`, `xtts` → `en` — vì đó là cách kho cũ được xây (F5 train giọng
   Việt, XTTS train giọng Anh) và ASR xác nhận **25/25** khớp.

   ⛔ ĐỪNG đoán làn từ TÊN. Kho cũ có `hoathinh_female`, `meoquan_men`,
      `tamlyhoc_men`, `cg_huong_nam` — tên tiếng Việt rành mạch, người nói
      **tiếng Anh**. Đó là tên kênh/nhân vật, không phải tên người nói. Tôi đã
      đọc tên như dữ liệu một lần và kết luận sai.

③ **KHÔNG BỎ SÓT GIỌNG.** Kho có **25** giọng, không phải 24. `kyan_nam` có ba
   clip ở 24000/24000/**22050** Hz; bộ nối cũ từ chối cả giọng vì hai tần số
   khác nhau, in một dòng "BO:" giữa hai mươi lăm dòng, và mọi con số sau đó
   nói "24". Nay `soi_kho_giong_cu._noi_kho` chuyển tần số thay vì từ chối.

## Vì sao đi HTTPS chứ không ghi thẳng vào CSDL

Ghi thẳng sẽ **xanh kể cả khi cửa hỏng**. Ngày 31/08 mọi cửa POST của app này
chết vì `vo.ngu_canh` không phát `csrf_token`, và một kịch bản gọi thẳng
`submit_with_credit` sẽ không thấy gì cả. Đường này đọc token khỏi HTML đã
render rồi nộp kèm — nhập 21 giọng cũng là chạy thử cửa ghi danh 21 lần.

⛔ NÓ CHẠM TIỀN THẬT: mỗi lượt ghi danh giữ chỗ rồi quyết toán trong sổ credit,
   và sổ credit chỉ ghi thêm. Chỉ chạy với tài khoản đuôi `.local`.

⚠️ Chỉ ĐỌC `D:\Voiceclone_TTS`. Không sửa, không tạo, không xoá gì bên đó.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "reconfigure"):
    # ⛔ `reconfigure`, KHÔNG phải `io.TextIOWrapper(sys.stdout.buffer, ...)`.
    #    Một wrapper mới NHẬN QUYỀN SỞ HỮU buffer bên dưới; khi nó bị thu
    #    gom rác — hoặc khi một module thứ hai bọc đè lên cùng buffer ấy —
    #    nó ĐÓNG buffer thật, và cả tiến trình chết với `ValueError: I/O
    #    operation on closed file` ở dòng `print` tiếp theo, một thông
    #    điệp không nhắc gì tới mã hoá hay tới module nào gây ra.
    #    `reconfigure()` sửa tại chỗ, gọi nhiều lần vô hại.
    #    Bánh cóc: `tests/test_353_voice_sidecar_bo_do.py`.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace",
                           line_buffering=True)

UA = "ltt-nhap-kho/1.0"
DUOI_THU = ".local"
KHO_CU = r"D:\Voiceclone_TTS"
CLIP_DA_NOI = "tmp/giong_cu"

#: `engine` của hệ cũ -> làn. Đây là bản đồ **duy nhất** đáng tin cho ngôn ngữ.
LAN_THEO_ENGINE = {"f5tts": "vi", "xtts": "en"}

#: Tên hiển thị, soạn tay cho cả 25 giọng.
#:
#: ⭐ Lấy `display_name` của hệ cũ làm gốc chứ không bịa: nó là tên chủ sản phẩm
#:    đã đặt và đã quen. Chỉ chuẩn hoá ba thứ:
#:      · thêm dấu tiếng Việt (hệ cũ viết không dấu vì tên tệp);
#:      · một dấu gạch ngang em (—) ngăn TÊN với MÔ TẢ, để cột tên đọc lướt được;
#:      · mô tả viết thường, gọn, và **không lặp lại ngôn ngữ** — làn đã hiện
#:        thành một nhãn riêng ngay cạnh, nên viết "EN" vào tên là nói hai lần.
#:
#: ⛔ Tên phải DUY NHẤT trong phạm vi một chủ (`uq_voice_owner_ten`). Trùng thì
#:    cửa ghi danh trả lỗi, và với một vòng lặp 21 lượt thì nó dừng giữa chừng.
TEN = {
    # ── f5tts → làn tiếng Việt ──────────────────────────────────────────────
    "Huong_KT":                 "Hương KT — nữ, kể chuyện ngôn tình",
    "kinhte_nam":               "Kinh Tế — nam, tin tức kinh tế",
    "kyan_nam":                 "Kỳ An — nam, kể chuyện",
    "lichsu_nam":               "Lịch Sử — nam, kể chuyện lịch sử",
    "lily_nu":                  "Lily — nữ, tự nhiên",
    "nguyetnga_nu":             "Nguyệt Nga — nữ, tự nhiên",
    "ninhdon_nam":              "Ninh Đôn — nam, tự nhiên",
    "phatgiao_nu":              "Phật Giáo — nữ, kể chuyện",
    # ── xtts → làn tiếng Anh ────────────────────────────────────────────────
    "alex_male_education":      "Alex — nam, giảng bài",
    "bella_nu":                 "Bella — nữ, tự nhiên",
    "bietdoi_girl":             "Biệt Đội — nữ, hoạt hình",
    "cg_huong_nam":             "CG Hương — nam, tự nhiên",
    "giffen_male_social":       "Giffen — nam, mạng xã hội",
    "harry_male_adventure":     "Harry — nam, phiêu lưu",
    "hoathinh_female":          "Hoạt Hình — nữ, hoạt hình",
    "ht3d_men":                 "HT3D — nam, tự nhiên",
    "khanh_male_entertainment": "Khánh — nam, giải trí",
    "lam_male_storytelling":    "Lâm — nam, kể chuyện",
    "lego_nu":                  "Lego — nữ, hoạt hình",
    "meodang_men":              "Mèo Đang — nam, hoạt hình",
    "meoquan_men":              "Mèo Quàn — nam, hoạt hình",
    "qtrungg_male_narrator":    "QTrungg — nam, thuyết minh",
    "quan_male_dialogue":       "Quân — nam, hội thoại",
    "roger_male_dialogue":      "Roger — nam, hội thoại",
    "tamlyhoc_men":             "Tâm Lý Học — nam, thuyết minh",
}


class KhongLam(RuntimeError):
    """Không làm được thì VỠ, không lặng lẽ bỏ qua một giọng."""


def _ho_so_cu() -> dict:
    import yaml
    d = yaml.safe_load(open(os.path.join(KHO_CU, "configs",
                                         "voice_profiles.yaml"),
                            encoding="utf-8")).get("profiles", {})
    return {k: v for k, v in d.items() if not str(k).startswith("_")}


def _sha(duong: str) -> str:
    h = hashlib.sha256()
    with open(duong, "rb") as f:
        for k in iter(lambda: f.read(1 << 20), b""):
            h.update(k)
    return h.hexdigest()


def _da_co(db) -> dict:
    """`{sha256_nguon: (public_id, ten, ngon_ngu, ghi_chu)}` của kho chung.

    Băm tệp NGUỒN là thứ nối một hồ sơ với clip nó sinh ra — và nó là cách duy
    nhất còn lại để truy xuất xứ của bốn giọng nhập trước khi có `ghi_chu`.
    """
    from sqlalchemy import select

    from apps.ltt_voice.tables import VoiceProfile, VoiceRef
    ra = {}
    for hs in db.execute(select(VoiceProfile)).scalars():
        r = db.execute(select(VoiceRef).where(
            VoiceRef.profile_id == hs.id)).scalars().first()
        if r is not None and r.sha256:
            ra[r.sha256] = (hs.public_id, hs.ten_hien_thi, hs.ngon_ngu,
                            hs.ghi_chu or "")
    return ra


def _xuat_xu(ma: str, hs: dict, so_clip: int, sha: str) -> str:
    return json.dumps({
        "nguon": "Voiceclone_TTS",
        "ma_cu": ma,
        "engine_cu": hs.get("engine", ""),
        "lang_khai": hs.get("lang", ""),
        "gioi": hs.get("gender", ""),
        "ten_cu": hs.get("display_name", ""),
        "so_clip_goc": so_clip,
        "sha256_da_noi": sha,
    }, ensure_ascii=False)


def _ve(email: str, goc: str) -> str:
    from platform_core import users
    from platform_core.db import get_session
    from platform_core.nexus import sso

    gen = get_session()
    db = next(gen)
    try:
        u = users.tim_theo_email(db, email)
        if u is None:
            raise KhongLam(f"khong thay tai khoan {email}")
        ve = sso.tao_ve(db, u, ip="127.0.0.1")
        db.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass
    return f"{goc.rstrip('/')}/nexus-sso?ma={ve}"


def _va_xuat_xu(pid: str, ghi_chu: str) -> None:
    """Điền `ghi_chu` cho một hồ sơ ĐÃ CÓ. Chỉ ghi khi nó đang rỗng.

    ⛔ Không ghi đè một `ghi_chu` đã có nội dung. Nếu ai đó viết tay vào đó thì
       đó là thông tin ta không có, và một công cụ vá tự động không được quyền
       xoá thứ nó không hiểu.
    """
    from sqlalchemy import select

    from apps.ltt_voice.tables import VoiceProfile
    from platform_core.db import get_session

    gen = get_session()
    db = next(gen)
    try:
        hs = db.execute(select(VoiceProfile).where(
            VoiceProfile.public_id == pid)).scalar_one_or_none()
        if hs is None or (hs.ghi_chu or "").strip():
            return
        hs.ghi_chu = ghi_chu
        db.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def _dat_lan_va_chung(public_id: str, ngon_ngu: str, ghi_chu: str) -> None:
    """Đặt `ngon_ngu` + `ghi_chu` + `dung_chung` sau khi ghi danh xong.

    ⛔ Cửa HTTPS **cố ý** không đặt `dung_chung` (xem `_p_giong.py`): một giọng
       khách tự tạo mà tự vào kho chung là công khai dữ liệu sinh trắc của họ.
       Nên bước này tách riêng, và nó chỉ chạy cho đúng những giọng ta nhập.
    """
    from sqlalchemy import select

    from apps.ltt_voice.tables import VoiceProfile
    from platform_core.db import get_session

    gen = get_session()
    db = next(gen)
    try:
        hs = db.execute(select(VoiceProfile).where(
            VoiceProfile.public_id == public_id)).scalar_one_or_none()
        if hs is None:
            raise KhongLam(f"khong thay ho so {public_id}")
        if hs.trang_thai != "active":
            raise KhongLam(f"{public_id} dang `{hs.trang_thai}`, chua the "
                           f"dua vao kho chung")
        hs.ngon_ngu = ngon_ngu
        hs.ghi_chu = ghi_chu
        hs.dung_chung = True
        db.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def _cho_job(job_id, cho_giay: int):
    from platform_core.db import get_session
    from platform_core.models import JOB_CANCELLED, JOB_DONE, JOB_ERROR, Job

    t0 = time.time()
    while time.time() - t0 < cho_giay:
        gen = get_session()
        db = next(gen)
        try:
            j = db.get(Job, job_id)
            tt, res, err = j.status, j.result, j.error
        finally:
            try:
                next(gen)
            except StopIteration:
                pass
        if tt in (JOB_DONE, JOB_ERROR, JOB_CANCELLED):
            return tt, res, err, time.time() - t0
        time.sleep(5)
    return "qua_han", None, None, time.time() - t0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--email", default="thu.giongnoi@lttstudios.local")
    ap.add_argument("--goc", default="https://app.lttstudios.com")
    ap.add_argument("--clip", default=CLIP_DA_NOI)
    ap.add_argument("--nhap", action="store_true",
                    help="Thuc su nhap. Khong co co nay thi chi XEM.")
    ap.add_argument("--chi", default="", help="Chi nhap mot ma cu (de thu).")
    ap.add_argument("--cho-giay", type=int, default=600)
    ap.add_argument("--ra", default="tmp/nhap_kho_giong_cu.json")
    a = ap.parse_args(argv)

    if a.nhap and not a.email.endswith(DUOI_THU):
        print(f"TU CHOI: chi nhap voi tai khoan duoi '{DUOI_THU}'.",
              file=sys.stderr)
        return 2

    hoso = _ho_so_cu()
    thieu_ten = sorted(set(hoso) - set(TEN))
    if thieu_ten:
        # ⛔ VỠ, đừng bịa tên. Một cái tên sinh tự động sẽ đi thẳng ra danh mục
        #    khách nhìn thấy, và không ai rà lại nó.
        print(f"KHO CU CO GIONG CHUA DAT TEN: {thieu_ten}", file=sys.stderr)
        print("Them vao `TEN` trong tep nay roi chay lai.", file=sys.stderr)
        return 2

    from platform_core.db import get_session
    gen = get_session()
    db = next(gen)
    try:
        dacol = _da_co(db)
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    ke_hoach, da_co, thieu_clip = [], [], []
    for ma in sorted(hoso):
        hs = hoso[ma]
        lan = LAN_THEO_ENGINE.get(str(hs.get("engine") or ""))
        if lan is None:
            print(f"  [bo] {ma}: engine la `{hs.get('engine')}`, khong biet lan")
            continue
        duong = os.path.join(a.clip, f"{ma}.wav")
        if not os.path.isfile(duong):
            thieu_clip.append(ma)
            continue
        sha = _sha(duong)
        so_clip = len([p for p in os.listdir(
            os.path.join(KHO_CU, "speakers", ma, "reference"))
            if p.lower().endswith(".wav")])
        muc = {"ma": ma, "ten": TEN[ma], "lan": lan, "clip": duong,
               "sha256": sha,
               "ghi_chu": _xuat_xu(ma, hs, so_clip, sha)}
        (da_co if sha in dacol else ke_hoach).append(
            {**muc, "hien_co": dacol.get(sha)})

    print(f"KHO CU: {len(hoso)} giong  |  da co trong nen tang: {len(da_co)}"
          f"  |  se nhap: {len(ke_hoach)}")
    if thieu_clip:
        print(f"  ⚠️ thieu clip da noi ({len(thieu_clip)}): {thieu_clip}")
        print(f"     Chay `soi_kho_giong_cu.ps1` de sinh lai vao {a.clip}/")

    if da_co:
        print("\n── DA CO (truy xuat xu bang sha256 cua tep nguon) ───────────")
        for m in da_co:
            pid, ten, nn, gc = m["hien_co"]
            co_gc = "co" if gc.strip() else "🔴 RONG"
            dung = "OK" if nn == m["lan"] else f"🔴 SAI (dang `{nn}`)"
            print(f"  {m['ma']:26} -> {ten[:34]:34} lan={dung:22} ghi_chu={co_gc}")

    if ke_hoach:
        print("\n── SE NHAP ─────────────────────────────────────────────────")
        for m in ke_hoach:
            print(f"  [{m['lan']}] {m['ma']:26} -> {m['ten']}")

    if not a.nhap:
        print("\n(chi XEM — them `-Nhap` de thuc su nhap)")
        return 0

    if a.chi:
        ke_hoach = [m for m in ke_hoach if m["ma"] == a.chi]
        if not ke_hoach:
            print(f"KHONG CO GI DE NHAP voi --chi {a.chi}", file=sys.stderr)
            return 2

    # ── Vá xuất xứ cho giọng ĐÃ CÓ ─────────────────────────────────────────
    #
    # Bốn giọng nhập trước 01/09 có `ghi_chu` rỗng, và xuất xứ của chúng chỉ
    # truy được bằng phép so sha256 ở trên. Vá ngay ở đây, vì lần sau
    # `tmp/giong_cu/` bị dọn là mất luôn đường truy.
    va = 0
    for m in da_co:
        pid, ten, nn, gc = m["hien_co"]
        if not gc.strip():
            _va_xuat_xu(pid, m["ghi_chu"])
            va += 1
            print(f"  [va xuat xu] {ten} <- {m['ma']}")
    if va:
        print(f"Da va xuat xu cho {va} giong da co.\n")

    import requests

    s = requests.Session()
    s.headers["User-Agent"] = UA
    r = s.get(_ve(a.email, a.goc), timeout=60)
    if r.status_code != 200:
        print(f"SSO -> {r.status_code}", file=sys.stderr)
        return 2
    print(f"\n[SSO] {r.status_code}  {r.url}")

    ket = []
    for i, m in enumerate(ke_hoach, 1):
        print(f"\n[{i}/{len(ke_hoach)}] {m['ma']} -> {m['ten']}")
        rr = s.get(f"{a.goc}/ltt-voice/giong", timeout=60)
        tok = [t for t in re.findall(
            r'name="csrf_token"\s+value="([^"]*)"', rr.text) if t.strip()]
        if not tok:
            # ⛔ Dừng cả vòng lặp. Token rỗng nghĩa là MỌI cửa POST đang chết;
            #    nộp tiếp chỉ để nhận 400 và đọc nó thành "lỗi mạng".
            print("🔴 TOKEN CSRF RONG — moi cua POST dang chet. DUNG.",
                  file=sys.stderr)
            break
        with open(m["clip"], "rb") as f:
            data = f.read()
        rr = s.post(f"{a.goc}/ltt-voice/giong/tao",
                    data={"ten": m["ten"], "dong_y": "1",
                          "csrf_token": tok[0]},
                    files={"tep": (f"{m['ma']}.wav", data, "audio/wav")},
                    timeout=300)
        if rr.status_code != 200 or not (rr.json() or {}).get("ok"):
            print(f"  🔴 POST -> {rr.status_code} {rr.text[:200]}")
            ket.append({**m, "ok": False, "loi": rr.text[:200]})
            continue
        kq = rr.json()
        tt, res, err, giay = _cho_job(kq["job_id"], a.cho_giay)
        if tt != "done":
            print(f"  🔴 job {tt} sau {giay:.0f}s  {err or ''}")
            ket.append({**m, "ok": False, "loi": f"job {tt}: {err}"})
            continue
        try:
            _dat_lan_va_chung(kq["voice_id"], m["lan"], m["ghi_chu"])
        except KhongLam as e:
            print(f"  🔴 {e}")
            ket.append({**m, "ok": False, "voice_id": kq["voice_id"],
                        "loi": str(e)})
            continue
        chon = (res or {}).get("chon_doan") or {}
        print(f"  ✅ {kq['voice_id']}  lan={m['lan']}  {giay:.0f}s  "
              f"chon {chon.get('bat_dau_s')}s → {chon.get('ket_thuc_s')}s")
        ket.append({**m, "ok": True, "voice_id": kq["voice_id"],
                    "giay": round(giay, 1), "chon_doan": chon})

    ok = sum(1 for k in ket if k.get("ok"))
    print(f"\n{'=' * 70}\n  NHAP XONG: {ok}/{len(ket)} thanh cong\n{'=' * 70}")
    for k in ket:
        if not k.get("ok"):
            print(f"  🔴 {k['ma']}: {k.get('loi')}")
    os.makedirs(os.path.dirname(a.ra) or ".", exist_ok=True)
    with open(a.ra, "w", encoding="utf-8", newline="\n") as f:
        json.dump(ket, f, ensure_ascii=False, indent=2)
    print(f"Da ghi: {a.ra}")
    return 0 if ok == len(ket) else 1


if __name__ == "__main__":
    raise SystemExit(main())
