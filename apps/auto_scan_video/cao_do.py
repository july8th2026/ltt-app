"""CAO DO — do F0 cua GIONG GOC tren stem `vocals`, de `AUTO_MATCH` co mot cu.

## Vi sao tep nay ton tai

`AUTO_MATCH` chi chot duoc giong khi co it nhat MOT mat rang buoc
(`rang_giong.DacDiemMongMuon.co_du_de_khop`). Ba mat cua catalog la `gioi`,
`vung`, `phong_cach`. Trong ba mat do:

  * `vung`      la giong vung mien TIENG VIET — mot phim tieng Trung khong noi
                gi ve no;
  * `phong_cach` la **nhan mo ta giong**, khong phai nut van (`giong_mau` ghi ro:
                *"Style is deprecated on v3 Turbo"*) — doan no tu van ban la
                doan;
  * `gioi`      thi **do duoc**, va do duoc tu thu khach DA tra tien de tach:
                stem `vocals` cua demucs.

⇒ Nen mat duy nhat ta di DO thay vi di HOI la `gioi`. Hai mat kia de cho mot lan
  goi model van ban re (`ho_so_noi_dung.py`), va chung duoc phep rong.

## Do o DAU — va vi sao khong phai o worker

Phep do nay chay trong **tien trinh con demucs** (`demucs_runner.main`), ngay
sau khi tach xong, khi stem `vocals` con tren dia tam va `torch` da nam san
trong bo nho tien trinh do.

⛔ Goi no tu worker se keo `torch` + `torchaudio` vao tien trinh worker — dung
   thu ma ca kien truc "demucs chay o tien trinh con" dung de tranh. Va
   `giai_doan_am_thanh` **xoa** `vocals` ngay khi tien trinh con ket thuc
   (no la giong goc cua khach, ta khong hua se giu), nen sau do khong con gi de do.

⇒ Ket qua di len bang MOT con so trong JSON cua runner: `f0_trung_vi`. Mot con
  so thay cho mot tep tieng — day cung la ly do rieng tu de thich no.

## Nguong, va vung xam

Khoang F0 noi cua nguoi lon la kien thuc pho thong cua nganh ngu am: nam ~85–180
Hz, nu ~165–255 Hz (Baken & Orlikoff, *Clinical Measurement of Speech and Voice*,
2e, bang F0 theo gioi va tuoi). Hai khoang **chong nhau** o quanh 165–180 Hz.

⛔ Nen ta KHONG phan dinh trong vung chong nhau. `gioi_tu_f0` tra ve `""` o do —
   va `""` o `rang_giong` nghia la *khong rang buoc mat nay*, khong phai "nam".
   Mot nguong don o giua se khai gioi sai cho dung nhung giong kho nhat, va hau
   qua la mot lan chay doc bang giong nguoc gioi ma khong ai bam nut nao.

⚠️ Va day la mot phep do tren giong NGUOI NOI GOC, khong phai mot phan doan ve
   noi dung. Ta ghi ro dieu do o `ho_so_noi_dung.NGUON_GIOI_DO` de man ho tro va
   hoa don noi duoc "vi sao giong nay".

## ⚠️ Gioi han da biet, viet ra de khong ai tuong no khong co

1. **Loi quang tam.** Bo do la mot ho tu tuong quan; tren mot am **khong phai
   tieng noi** no co the bat vao mot chu ky boi — do 23/09: mot sin thuan
   440 Hz + hoa am cho ra ~219 Hz, tuc roi thang vao khoang "nu". Cai chan no
   trong duong that khong phai phep do ma la **dau vao**: thu di vao day la
   stem `vocals` cua demucs, nen mot video khong co giong nguoi cho ra mot stem
   gan nhu im lang, va cua nang luong duoi day tra ve `0.0`.
2. **Mot con so cho CA video.** Video hai nguoi noi cho ra mot trung vi o giua.
   Hop dong san pham chot 22/09 la **mot giong thuyet minh moi lan chay**
   (khong phan vai), nen mot con so la dung don vi — nhung no khong tra loi
   duoc "ai noi cau nao", va khong duoc dung nhu the.
3. **Khoang nam/nu chong nhau** — xem vung xam duoi day.
"""
from __future__ import annotations

#: Tran duoi/tren cua F0 tieng noi nguoi lon. Ngoai khoang nay la nham —
#: nhac nen con sot, tieng dong, hoac mot quang tam thanh cua may.
#:
#: ⭐ `85.0` KHONG phai mot con so tron: no la dung `freq_low` mac dinh cua
#:    `torchaudio.functional.detect_pitch_frequency`. Dat san duoi thap hon dai
#:    tim cua chinh bo do la khai mot khoang ta khong the do; dat cao hon la vut
#:    di ket qua bo do da tim duoc. Mot giong tram hon the ra `0.0` — tuc
#:    "khong khai gioi", huong an toan.
F0_THAP_HZ = 85.0
F0_CAO_HZ = 400.0

#: Ranh giua hai khoang gioi. Xem docstring dau tep.
NGUONG_GIOI_HZ = 165.0
#: Nua do rong cua VUNG XAM quanh ranh — trong do khong khai gioi.
BIEN_XAM_HZ = 15.0

#: Tan so phan tich. Ha xuong 16 kHz truoc khi do: F0 tieng noi < 400 Hz nen
#: 44,1 kHz khong them mot thong tin nao, chi them 2,75 lan cong viec.
TAN_SO_DO = 16000
#: Tran thoi luong dem vao phep do. Mot phim 120 phut khong can do het de biet
#: nguoi ke chuyen la nam hay nu; cat o day giu phep do o hang GIAY.
TOI_DA_GIAY = 180.0

#: Cua nang luong: khung co RMS duoi ty le nay so voi RMS o phan vi 95 duoc coi
#: la IM LANG va bi bo. Khong co cua nay thi trung vi bi keo ve F0 rac cua cac
#: khung im — `detect_pitch_frequency` van tra mot con so cho moi khung.
TY_LE_CUA_NANG_LUONG = 0.15
#: Duoi nguong nay thi khong du bang chung de noi gi ca (0,5 giay tieng noi).
KHUNG_TOI_THIEU = 50


def gioi_tu_f0(f0: float) -> str:
    """`"nam"` | `"nu"` | `""` (khong khai). Xem vung xam o docstring dau tep.

    ⛔ Tra ve `""` chu khong bao gio doan bua: `rang_giong` doc `""` la *khong
       rang buoc mat nay*, va do dung la dieu ta muon noi khi phep do khong du
       tach bach.
    """
    try:
        hz = float(f0)
    except (TypeError, ValueError):
        return ""
    if not (F0_THAP_HZ <= hz <= F0_CAO_HZ):
        return ""
    if hz < NGUONG_GIOI_HZ - BIEN_XAM_HZ:
        return "nam"
    if hz > NGUONG_GIOI_HZ + BIEN_XAM_HZ:
        return "nu"
    return ""


def f0_trung_vi(duong_wav: str, *, toi_da_giay: float = TOI_DA_GIAY) -> float:
    """Trung vi F0 cua cac khung CO TIENG trong mot WAV PCM 16-bit. `0.0` = khong do duoc.

    🔑 Phep do la `torchaudio.functional.detect_pitch_frequency` — ban cai san
       cua thu vien (NCCF, Mauch & Dixon mo ta cung ho phuong phap). ⛔ Khong tu
       viet mot bo do cao do: mot bo tu che o day la dung loai "diem heuristic tu
       nghi" ma bo do cua lan nay cam.

    ⚠️ **Fail-soft co chu dinh.** Thieu `torchaudio`, tep hong, tep im lang: tra
       ve `0.0`. `AUTO_MATCH` con duong thu hai (`ho_so_noi_dung`), nen mot phep
       do khong chay duoc khong duoc phep lam hong ca giai doan `audio_prepare`
       — giai doan dat nhat cua chuoi.
    """
    try:
        return _do(duong_wav, toi_da_giay=toi_da_giay)
    except Exception:                                      # noqa: BLE001
        # Xem ghi chu fail-soft o tren. Nguoi goi la `demucs_runner.main`, va
        # mot ngoai le o day se giet mot lan tach da chay xong.
        return 0.0


def _do(duong_wav: str, *, toi_da_giay: float) -> float:
    import wave

    import torch
    import torchaudio

    with wave.open(str(duong_wav), "rb") as f:
        if f.getsampwidth() != 2:
            return 0.0
        tan_so = f.getframerate()
        so_kenh = f.getnchannels()
        so_khung = min(f.getnframes(), int(max(1.0, toi_da_giay) * tan_so))
        thoi = f.readframes(so_khung)
    if not thoi or tan_so <= 0:
        return 0.0

    x = torch.frombuffer(bytearray(thoi), dtype=torch.int16).float() / 32768.0
    if so_kenh > 1:
        # ⭐ Gop ve mot kenh TRUOC khi do: `detect_pitch_frequency` do tung kenh
        #    roi ta lai phai gop hai day so — gop tieng mot lan re hon.
        du = x.numel() % so_kenh
        if du:
            x = x[:x.numel() - du]
        x = x.view(-1, so_kenh).mean(dim=1)
    if x.numel() < tan_so // 2:
        return 0.0

    if tan_so != TAN_SO_DO:
        x = torchaudio.functional.resample(x, tan_so, TAN_SO_DO)
    if x.numel() < TAN_SO_DO // 2:
        return 0.0

    # 🔴 **DAI TIM giu nguyen mac dinh cua thu vien (85–3400 Hz), va do la mot
    #    phep do chu khong phai mot so thich.**
    #
    #    Bop dai tim ve dung khoang tieng noi nghe hop ly, nhung do 23/09 cho
    #    ket qua NGUOC LAI: ha tran tren xuong 400 Hz hay ha san duoi xuong
    #    60 Hz deu buoc bo do chon mot chu ky BOI con nam trong dai — 240 Hz ra
    #    sai, 440 Hz ra 147 Hz (chia ba), 500 Hz ra mot con so trong khoang
    #    nguoi. Voi mac dinh thi 105/140/200/240 deu dung va 500 bi loai.
    #
    # ⭐ Nen dai tim de rong, va khoang nguoi duoc ep o **buoc LOC ket qua** ben
    #    duoi. Loc sau thi mot gia tri ngoai khoang bi BO; bop truoc thi no bi
    #    **doi** thanh mot gia tri trong khoang — va cai thu hai khong keu len.
    f0 = torchaudio.functional.detect_pitch_frequency(
        x.unsqueeze(0), TAN_SO_DO).squeeze(0)
    if f0.numel() == 0:
        return 0.0

    # ── Cua nang luong ──────────────────────────────────────────────────────
    #
    # 🔑 `detect_pitch_frequency` tra ve MOT con so cho MOI khung, ke ca khung im
    #    lang — con so do la rac. Khong loc chung ra thi trung vi do chinh rac.
    #    Cua o day la nang luong khung so voi phan vi 95 cua chinh ban ghi, tuc
    #    tu chuan theo muc thu am chu khong theo mot dBFS go cung.
    buoc = max(1, x.numel() // int(f0.numel()))
    khung = x[:buoc * int(f0.numel())].view(int(f0.numel()), buoc)
    rms = khung.pow(2).mean(dim=1).sqrt()
    if float(rms.max()) <= 0.0:
        return 0.0
    nguong = float(torch.quantile(rms, 0.95)) * TY_LE_CUA_NANG_LUONG

    chon = f0[(rms >= nguong) & (f0 >= F0_THAP_HZ) & (f0 <= F0_CAO_HZ)]
    if chon.numel() < KHUNG_TOI_THIEU:
        return 0.0
    return round(float(chon.median()), 2)
