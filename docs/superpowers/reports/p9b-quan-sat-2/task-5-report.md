# P9b Task 5 - Dien tap loi §18.7 tren be mat quan sat

## ⚠️ DOC TRUOC: §18.7 la dieu kien ra cua CA PHASE, khong phai cua mot lan

17 tinh huong cua §18.7 trai khap dong co, worker, connector, trigger,
credential. Lan nay dien tap **dung tap con ma no cham**, va **khai ra** phan
con lai. Noi "da dien tap §18.7" khi moi lam 5/17 la dung hinh dang loi
"pham vi phep do hep hon loi tuyen bo".

## Bang do phu - 17 muc cua §18.7

| # | Tinh huong | Trang thai | Bang chung |
|---|---|---|---|
| 1 | **Restart web** | ✅ DA DO | trinh duyet that, xem duoi |
| 2 | Restart worker | ⬜ khong thuoc lan (worker) | - |
| 3 | Restart dong co | ⬜ khong thuoc lan (dong co) | - |
| 4 | CSDL mat ket noi 30 s | 🟡 MOT NUA | phia CLIENT do duoc (mat cua doc ⇒ lui dan + noi ra, muc 1); phia MAY CHU **chua do** |
| 5 | Provider het gio | ⬜ khong thuoc lan | - |
| 6 | **Provider mo ho** | ✅ DA DO | `test_3453::test_provider_mo_ho…` - `ABANDONED` ⇒ 409 `khong_thu_lai_duoc` |
| 7 | Webhook trung | ⬜ khong thuoc lan (trigger) | - |
| 8 | Tin hieu truoc WAITING | ⬜ khong thuoc lan (cho_doi) | - |
| 9 | **Retry** | ✅ DA DO | `test_3453::test_retry_thu_cong…` - ⛔ khong khoan giu thu hai, `attempt` tang |
| 10 | **Huy** | ✅ DA DO | `test_3453::test_huy…` (luong SSE dong NGAY, khung cuoi noi `CANCELLED`) + trinh duyet (task 3) |
| 11 | Trigger dong thoi | ⬜ khong thuoc lan | - |
| 12 | Credential het han/thu hoi | ⬜ khong thuoc lan (p6) | - |
| 13 | GPU ban | ⬜ khong thuoc lan | - |
| 14 | Connector 429 | ⬜ khong thuoc lan (p6) | - |
| 15 | **Publish version moi khi run dang chay** | ✅ DA DO | `test_3453::test_publish_ban_moi…` - run cu GHIM version cu, va cua so sanh NOI RA `khac_version` |
| 16 | Subworkflow hong | ⬜ chua do | - |
| 17 | Human het han | ⬜ chua do (`waiting_kind=HUMAN` da co tu P9) | - |

**5/17 da do tren lan nay.** ⛔ Dieu kien ra cua PHASE 13 **chua dat** - con 12
muc thuoc lan khac hoac chua do. Day la thong tin cho dieu phoi, khong phai mot
lan xin phep.

## Dong do / dong xanh + doi chung

```
4 passed, 1 warning in 9.70s     (tests/test_3453_dien_tap_18_7_quan_sat.py)
```

Bon bai nay xanh ngay lan dau - dung, vi **dien tap la dien lai hanh vi da co**,
khong phai xay moi. Nen gia tri cua chung nam o **phep tiem loi**, khong o mau
xanh. Tiem ba loi cung luc vao `runs_v3.py`:

| Tiem | Bai do |
|---|---|
| mot luot thu lai tu `credit.giu_cho` mot khoan rieng | `test_retry_thu_cong…` |
| bo cong `thu_lai.KHONG_THU_LAI` | `test_provider_mo_ho…` |
| `khac_version` luon `False` | `test_publish_ban_moi…` |

```
3 failed, 1 passed, 1 warning in 9.92s
```
⭐ Bai thu tu (**huy**) VAN XANH duoi ca ba vet tiem - no la doi chung: ba bai
kia do vi **dung cai da hong**, khong phai vi moi thu deu do.

## 🔴 DIEN TAP "RESTART WEB" TREN TRINH DUYET THAT

Chromium that (Playwright), cong **8177** co lap, sqlite vut di.
⛔ Khong dung cong 8100 (production). Kich ban: Canvas dang nghe luong SSE cua
mot run DANG TIEU TIEN ⇒ **giet may chu web** ⇒ doi ⇒ **khoi dong lai**.

```
1. TRANG THAI TRUOC KHI RESTART: QUEUED   (1 goi doc run, la /su-kien)
2. DA GIET MAY CHU WEB
3. MAN HINH CO NOI RA MAT LIEN LAC KHONG: True
   TRANG THAI VAN HIEN (khong trang ron): QUEUED
4. DA KHOI DONG LAI MAY CHU WEB
5. DONG LOI DA BIEN MAT CHUA: True
   TRANG THAI SAU KHI KHOE LAI: QUEUED
   DA TAI LAI TRANG CHUA (phai la False): False
--- LOI CONSOLE KHONG PHAI MANG (4) --- (deu la ERR_CONNECTION_* trong lúc may chu chet)
--- REQUEST HONG (5) --- (deu la /su-kien trong cua so mat dien)
--- GOI DOC RUN (3) --- 200 .../su-kien?sau=1
```

Bon dieu doc duoc:
1. Man hinh **NOI RA** khi mat lien lac - khong "thu lai vo han trong im lang".
2. No **khong noi doi**: van hien `QUEUED` (trang thai that cuoi cung biet
   duoc), khong trang ron va khong bia mot trang thai moi.
3. No **tu noi lai** va **tu xoa dong loi** - ⛔ khong can tai lai trang
   (`navigation entries == 1`).
4. **Chong-ngap con nguyen**: ~7 giay mat dien chi sinh **5** lan thu, dung
   hinh dang lui dan 1,5s -> 3s -> 6s -> 12s. Khong lui dan thi con so ay la
   hang chuc.

## Chua lam duoc
- Muc 4 (**CSDL mat ket noi 30 s**) moi do duoc PHIA CLIENT. Phia may chu -
  luong SSE dang mo ma CSDL rot - can mot cach cat ket noi CSDL that; chua lam.
- Muc 16, 17 chua do; muc 2, 3, 5, 7, 8, 11, 12, 13, 14 thuoc lan khac.
