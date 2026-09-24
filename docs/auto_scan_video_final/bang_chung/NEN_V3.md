# NEN_V3 — nghiem thu dau-cuoi tren PHIM KHACH THAT (v3, tieng Trung)

SHA `859b3361` · nhanh `phien/asv-final-nghiem-thu` · 23/09/2026 01:44–02:27 (UTC+7)
Nguon: `深度解析…#和平精英夏日探险.mp4` — 106,833 s · h264 836×576 · aac · tieng Trung + hardsub Trung.

## Lenh (khong co bi mat)

```
python C:\Users\...\.claude\ltt\chay_nang.py --phien asv-final-nghiem-thu -- ^
  python <scratch>\nt\chay.py <preset[,preset]> NEN_V3_CHE_DO_GIONG=... NEN_V3_GIONG_ID=...
```

`chay.py` = khuon cua `setup/nghiem_thu_asv.ps1`: doc `C:\LTTPlatform\secrets\app.env` vao
env cua TIEN TRINH CON (khong in mot gia tri nao), dat `LTT_ASV_MODEL_THAT=1` +
`LTT_ASV_POOL_URL=$LTT_DATABASE_URL` + `LTT_ASV_GIONG_THAT=1` + `LTT_TEST_NANG=1` +
`LTT_TEST_DATABASE_URL=…/lttplatform_test`, giu khoa `cua_so_yen` (`postgres_test`,
`may_tao_tieng`; fail-closed) roi chay mot bai pytest scratch dung lai `_mot_luot` cua
`tests/test_448_asv_v4_e2e_nghiem_thu.py`. Khac `test_448` hai diem: nop form voi
`ngon_ngu_nguon=zh` + `ngon_ngu_dich=vi` **tuong minh**, va GHI bao cao ca khi do.

## Do trung thuc cua luot chay

`model_that=true` (1 khoa `ltt_llm` chep tu pool that → may B) · `giong_that=true`
(LTT Voice sidecar :8120 that) · `thay_the=[]` — **khong mot cua nao bi thay**.
`qc_ai` TAT (mac dinh van hanh). Whisper chay CPU/int8.

## Ket qua

| Luot | Che do giong | Chuoi | Loi | Tep ra |
|---|---|---|---|---|
| A · `localize_preserve_picture` | AUTO_MATCH | dung o `content_process` | `ChuaRangError` | khong co |
| B · `localize_preserve_picture` | USER_SELECTED `Minh Đức` | 9/11 giai doan xanh, `qc` do | QC **T3** | `nen_v3_us_localize_preserve_picture.mp4` |
| C · `smart_localize` | USER_SELECTED `Minh Đức` | 9/11 giai doan xanh, `qc` do | QC **T5** | `nen_v3_us_smart_localize.mp4` |

Gio tung giai doan (giay) — B / C:
`media_prepare` 0,3/0,3 · `audio_prepare` 72,2/66,5 · `transcribe` 35,5/27,1 ·
`edit_plan` 0,0/**163,8** · `content_process` 100,0/84,1 · `voice_synthesis`
**937,1/942,7** · `timing_align` 9,4/11,0 · `compose` 0,2/0,4 · `render` 3,3/4,9 ·
`qc` 4,3/4,6. Tong 1191 s / 1333 s cho mot phim 107 s.

ASR: `ngon_ngu="zh"`, 6 doan, van ban Trung that. Ban long tieng: 6 muc **tieng Viet that**
("Nếu nhảy chậm thì đánh kiểu gì? …"). So ke khop doi soat (`khop=true`, 24 don vi).
Tai ve: chu 200, nguoi khac 404. ffprobe ban ra: B 22 962 103 B · C 22 501 763 B, ca hai
106,833 s · h264 836×576 · aac. Am: B LUFS −14,25 / dinh −1,69 · C LUFS −14,20 / dinh −0,33.

## Loi, xep theo muc nghiem trong

1. **AUTO_MATCH la duong CHET tu dau den cuoi** — `apps/auto_scan_video/rang_giong.py:133`
   (`ma_giong` nem `ChuaRangError`) qua `giai_doan_noi_dung.py:117-118`. Nguyen nhan:
   khong giai doan nao sinh `HoSoNoiDung`, nen `dac_diem_giong` luon rong
   (`rang_giong.py:219` tra `CHUA_RANG`; `dich_vu_tao.py:53` va `gia.py:133` da ghi nhan
   "chua cua nao sinh ra no"). Khach chon "tu khop" ⇒ `content_process failed_terminal`,
   sau khi da ton 133 s demucs + ASR.
2. **`voice_synthesis` 937–943 s cho 107 s phim** (6 doan) — ~9× thoi luong, chiem 70–79 %
   ca lan chay. Kem `rut_ngan_cho_vua` 11 lan / 50 653 token (`su_dung.so_ke`): ban dich
   Viet dai hon thoai Trung nen phai nan nhieu vong. Tran `max_runtime_s` cua job va
   tran 100 giay cua Cloudflare deu nam gan day (xem `docs/auto_scan_video_v6/CHAN_DOAN_TEST_448.md` §10).
3. **QC T3 do o preset GIU HINH** (`apps/auto_scan_video/qc.py:275`): `cach_render="sao_chep"`
   nhung MD5 luong hinh ban ra ≠ nguon (`acd497e1825e…` vs `70e57a0ec644…`). Gia thuyet:
   ban duoc bam la ban DA chuan hoa cua `media_prepare`/ban dung chu khong phai tep nguon
   goc, hoac `compose` co ghi lai bitstream du khai `copy` — can doi chieu
   `giai_doan_qc.py:136` (`duong_nguon` tro vao dau).
4. **QC T5 do o preset CAT** (`qc.py:288`): dinh that −0,33 dBTP > tran −1,5. Chuan am o
   `tach_tieng` dat LUFS dung (−14,2) nhung khong ghim dinh sau khi ma hoa lai.
5. **VLM doc canh hong 4/12 lan tren anh that** — `giai_doan_ban_bien_tap.py:219`:
   `canh_0002` `LuocDoSai` ×2, `canh_0003` `HieuCanhError` ×2 (model that tra JSON sai
   luoc do). Hau qua: `so_cat=0/6` ⇒ preset `smart_localize` **khong cat canh nao**, chi
   ma hoa lai — tuc khac biet san pham giua hai preset bien mat tren phim nay.
6. (Bo do) **Harness `tests/fixtures/asv_e2e.py:840-842`**: `subprocess.run(..., text=True)`
   khong dat encoding ⇒ `UnicodeDecodeError: 'charmap'` ngay khi duong dan phim co ky tu
   Trung; ca hai preset do truoc khi cham san pham. Ban san pham
   (`apps/auto_scan_video/nhap_media.py`) giai `utf-8` dung, nen day la loi cua BO DO.
   Luot nay vong qua bang mot `monkeypatch` trong bai scratch.

## Tang vat

`<scratch>/nt/ra/` — `nen_v3_us_localize_preserve_picture.{json,mp4}`,
`nen_v3_us_smart_localize.{json,mp4}`, `nen_v3_localize_preserve_picture.json` (luot AUTO_MATCH).
JSON kem: trang thai tung giai doan, nhat ky job, van ban ASR + ban dich, so ke, QC tung muc.
