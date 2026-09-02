# BAO CAO 01 — TRUTH, RULES & DOCUMENTATION PURIFICATION

Ngay: 2026-09-02 · Phase truoc: `00_baseline_census.md`
Trang thai: **PHAN TICH XONG · THI HANH DANG CHO CAY RANH**

---

## 1. Chan doan — do duoc, khong phai cam tinh

### 1.1 `CLAUDE.md`: 56% khong phai luat

| Phan | Dong | Ty le | Ban chat |
|---|---|---:|---|
| §1–§"Gioi han Cloudflare" (1–195) | 195 | 39% | **LUAT** — bat bien, khong het han |
| §**"Viec con do"** (196–475) | **280** | **56%** | **TRANG THAI + LICH SU** |
| §"Khong bao gio commit" + §"Tai lieu" (476–496) | 21 | 4% | LUAT + chi muc |

⇒ Hon mot nua tep chi dan chinh cua du an la **anh chup mot thoi diem**, duoc
chep tay, khong ai kiem chung.

### 1.2 Va no da troi **bon lan**, ca bon deu ve phia nguy hiem

`CLAUDE.md` **tu ghi nhan**:

| Dong | Tu thu nhan |
|---:|---|
| 226 | VPS: *"DANG SONG VA CONG KHAI — SUA 2026-08-26, TRUOC DO HANG NAY NOI SAI VE PHIA NGUY HIEM"* (truoc do viet *"App van TAT"*, trong khi `/vps` tra 200 cho khach an danh va **dang thu credit that**) |
| 296 | Public API: *"SUA 2026-08-26 — DOAN NAY TRUOC DO NOI SAI, VA NOI SAI VE PHIA NGUY HIEM"* |
| 317 | *"SUA LAN HAI 2026-08-30 — LAI LECH, LAI VE PHIA NGUY HIEM"* |
| 382 | *"SUA LAN BA 2026-09-01 — VA DAY LA LAN THU BA CUNG MOT HANG"* |

Ba lan cung mot hang. Va lan thu ba **khong** duoc phat hien bang cach doc lai
tai lieu — no lo ra vi mot canary di hoi may chu.

### 1.3 🔴 PHAT HIEN MOI — cai thu NAM, tim duoc bang phep do

Chua ai ghi nhan cai nay. `CLAUDE.md` dong 458 viet:

> *"Tran 1.500 ky tu/luot la tran CHAT LUONG (#168 bao troi giong tu ~3.000),
> khong phai tran ky thuat"*

Doc ma that (`apps/ltt_voice/tham_so_cong_khai.py`):

```python
TRAN_MOI_LUOT_SINH   = 1500   # dong 23 — model doc lien duoc bao nhieu
TRAN_KY_TU_CONG_KHAI = 1500   # dong 59 — khach gui duoc bao nhieu MOT LAN
```

Chu thich ngay trong tep noi ro:

> *"🔴 HAI TRAN NAY LA HAI THU KHAC NHAU, va truoc 31/08/2026 chung la mot con so."*

⇒ Ngay 31/08 hai tran **da duoc tach**, co ly do, co test khoa quan he giua chung
(`tests/test_342_ltt_voice_noi_dai.py:44` — `TRAN_KY_TU_CONG_KHAI >= TRAN_MOI_LUOT_SINH`).
**`CLAUDE.md` khong theo kip** — no van mo ta mot tran duy nhat.

Hien tai vo hai vi hai so bang nhau. Nhung khoanh khac ai do noi
`TRAN_KY_TU_CONG_KHAI` len 3.000 (dung con duong da xay san), `CLAUDE.md` se noi
sai — va lan nay se **noi sai theo huong "khach gui duoc it hon thuc te"**.

⭐ Dieu dang noi khong phai loi nay. La **cach tim ra no**: khong ai doc lai tai
lieu ca — no lo ra khi doi chieu **tung gia tri** trong tai lieu voi **chu so
huu trong ma**. Do la phep do co the lap lai, va do la thu nen thay cho viec
"nho cap nhat".

### 1.4 Luat bi chon trong bang trang thai — **tat ca deu la BAN SAO**

Gia thuyet ban dau: xoa §"Viec con do" se lam mat ~30 luat that nam lan trong do.
Da kiem tung cai. **Gia thuyet sai** — moi luat do da co chu so huu trong ma:

| Luat trong `CLAUDE.md` | Chu so huu that | Test khoa |
|---|---|---|
| tran token render **11.412** | `render_gateway/ngan_sach.py:57` | ✅ `test_245:1237` |
| cua so model **131.072** / ra **32.768** / le **2.048** | `apps/ltt_llm/ngan_sach.py:43,71,75` | ✅ `test_334` |
| token vao **96.256** | **DAN XUAT** `ngan_sach.py:84` (khong go tay) | ✅ |
| tran voice **1.500** | `apps/ltt_voice/tham_so_cong_khai.py:23,59` | ✅ `test_342`, `test_338` |
| `sata0`+`e1000` (khong virtio) | `apps/vps/services/mang.py` `MO_HINH_CARD` | |
| "Ban ≠ hong" — khong `danh_dau_loi()` | `apps/anhnoibo/http_cong.py` + 3 app | |
| viec nen sau **lease** | `platform_core/leases.py`, `apps/vps/services/billing.py` | ✅ `test_214` |
| `AppManifest.bao_tri` | `apps/vps/bao_tri.py`, `manifest.py` | |
| fail-closed `LTT_PUBLIC_API_TOOLS` | `apps/*/manifest.py` | |
| gia 3 credit/anh | `apps/anhnoibo/gia.py` | ✅ `test_298` kieu |

⇒ **`CLAUDE.md` khong so huu mot bat bien nao ca. No chep lai chung.**
Do la ly do no troi duoc ma khong ai biet: mot ban sao khong co test.

### 1.5 Mot vi du LAM DUNG, dang lam khuon

`apps/ltt_voice/tham_so_cong_khai.py` la doi lap cua `CLAUDE.md`:
- hai hang so, moi cai **mot cau tra loi duy nhat**;
- chu thich ghi **vi sao tach**, va **cai gia cua viec gop** (van ban 3.000 ky tu
  bi tu choi trong khi thong diep loi lai chi sang mot con duong chua ai xay);
- co **test khoa quan he**, khong chi khoa gia tri;
- ghi ro dieu kien noi (`V10`), va **tu chan** cach doc sai:
  *"⛔ DUNG doc dieu do thanh 'noi duoc roi'... mot phep do khong thay duoc mot cong"*.

⇒ Khuon cho Phase 01: **gia tri song trong ma, kem ly do va dieu kien doi; tai
lieu tro toi, khong chep lai.**

---

## 2. `docs/` — 1.297 tep, ranh gioi chua duoc ve

### 2.1 Ba phan tram ba loai, tron lan

| Loai | Tep | Vi du |
|---|---:|---|
| **Bang chung lich su** | ~979 (75%) | `developer_portal_mvp_ui/` (504, trong do **487 PNG**), `APP_AUDIT/` (406), `_luutru/` (33) |
| **Luat dang hieu luc** | ~50 | `QUYET_DINH_NEN_TANG.md`, `03_THEM_APP_MOI.md`, `BAY_TRONG_CONG_CHAT_LUONG.md` |
| **DU LIEU HOP DONG** ⚠️ | vai tep | `lttstudios-website/route-map.json` |

### 2.2 🔴 `docs/` dang chua du lieu duoc DOC LUC CHAY KIEM

| Tu | Toi | Ban chat |
|---|---|---|
| `tools/audit_public_web.py:13` | `docs/lttstudios-website/route-map.json` | **CONTRACT** |
| `tools/vps_kiem_cau_hinh.py:203-204` | `docs/lttstudios-website/legal/vps-terms.html` | duong tep |
| `server/templates/developers_base.html:24` | `docs/developer_portal_mvp_ui/03_*.md` | chu thich bang chung |
| `server/templates/dev_keys.html:14` | `docs/developer_portal_mvp_ui/02_*.md` | chu thich bang chung |
| `apps/vps/dieu_khoan.py:5` | `docs/lttstudios-website/` | ghi chu lich su |

⇒ **Khong the** tuyen bo `docs/` la khu lich su roi cach ly no. Phai di tru
`route-map.json` **truoc**. Day chinh la
*"archived docs referenced as normal guidance"* ma Prompt 01 goi ten.

### 2.3 Ma chay duoc nam trong `docs/`

6 script `.py` co `if __name__ == "__main__"`:
`docs/audit_ltt_llm/artifacts/` (4) · `docs/lttstudios-website/` (1) · `docs/_luutru/verify-deploy.py` (1).

---

## 3. Thiet ke — kien truc su-that-hien-tai nho nhat

⛔ Rang buoc tu `OPERATING_CONTRACT` §8: **khong duoc them luat moi de chua luat
cu**. Nen thiet ke duoi day **khong** them quy tac; no **bo** mot lop chep tay.

### 3.1 Ba tang, mot cau hoi moi tang

| Tang | Tra loi cau hoi | Nguon | Troi duoc khong |
|---|---|---|---|
| **LUAT** | "toi duoc lam gi / khong duoc lam gi" | `CLAUDE.md` + `AGENTS.md` | ❌ bat bien |
| **TRANG THAI** | "hien gio cai gi dang bat / gia bao nhieu" | **hoi may chu** | ✅ nhung tu sua |
| **LICH SU** | "vi sao thanh ra the nay" | `docs/_luutru/`, `NHAT_KY.md`, `APP_AUDIT/` | ✅ va khong sao |

### 3.2 Thay doi cu the

**① `CLAUDE.md` §"Viec con do" (280 dong) → mot bang tro toi + mot lenh.**

Khong xoa thong tin — **doi cho no**. Moi hang trong bang hien tai tro thanh:
- neu la **LUAT**: mot dong tro toi chu so huu trong ma (khong chep gia tri);
- neu la **TRANG THAI**: bo, thay bang lenh hoi may chu;
- neu la **LICH SU**: chuyen sang `docs/_luutru/`.

**② Mo rong `tools/api_prod_canary.py` thanh cong cu trang thai duy nhat.**

No da lam dung viec nay cho `/api/v1/tools` (va da bat duoc lan troi thu ba).
Them: app nao song, co nao bat, gia hien tai. Mot lenh, muoi giay, khong troi.

⭐ Va no **da tung suyt noi doi**: doc `data`/`tools` trong khi API tra `items`
nen in *"rong — dung y muon"*. Da sua de hinh dang la **phai noi ra**. Ky luat do
phai giu khi mo rong.

**③ Doi chieu gia tri thanh phep kiem tu dong.**

Chinh phep do da tim ra §1.3 phai tro thanh mot buoc: moi con so trong `CLAUDE.md`
phai hoac (a) tro toi mot hang so trong ma, hoac (b) khong ton tai.

⚠️ Day **khong** vi pham §8: no khong them luat cho nguoi, no **bo** kha nang
chep tay. Va no thay the mot thu dang ton tai (viec nho cap nhat) bang mot thu
do duoc.

**④ Di tru `route-map.json` ra khoi `docs/`.**

---

## 4. Trang thai thi hanh

| Viec | Trang thai |
|---|---|
| Phan loai luat/trang thai/lich su | ✅ xong |
| Do ty le 56/39/4 | ✅ xong |
| Doi chieu tung gia tri voi chu so huu | ✅ xong — 10/10 deu la ban sao |
| Tim lech moi | ✅ **1 cai moi** (§1.3) |
| Ve ranh gioi `docs/` | ✅ xong — 5 tham chieu tu ma song |
| **Sua `CLAUDE.md`** | ⏳ **cho** — tep dung chung, phien kia dang commit |
| **Sua `AGENTS.md`** | ⏳ cho |
| Mo rong canary | ⏳ |
| Di tru `route-map.json` | ⏳ |

⛔ `CLAUDE.md` va `AGENTS.md` la **tep dung chung** (`AGENTS.md` §10.2②):
chi `Edit` khop chuoi chinh xac, **khong bao gio** `Write` de.

---

## 5. Ket luan tam

`CLAUDE.md` khong so huu mot bat bien nao — no chep lai chung tu ma. Do la ly do
no troi **bon lan da biet + mot lan moi tim ra**, va deu ve phia nguy hiem.

⇒ Sua bang cach **viet lai cho dung** se that bai lan thu sau. Sua dung la **bo
lop chep tay**: gia tri song trong ma (da vay roi), tai lieu tro toi, trang thai
hoi may chu.

---

## 6. DA THI HANH (2026-09-02, cay `D:/LTTSTUDIOSAPP-p01`, nhanh `phien/p01`)

### 6.1 Ba viec da lam, dung thu tu thiet ke

| # | Viec | Ket qua do duoc |
|---|---|---|
| 1 | **Dung nguon trang thai TRUOC** — `api_prod_canary.py trang-thai` | chay duoc, khong can khoa production |
| 2 | Chuyen 280 dong §"Viec con do" sang `docs/_luutru/CLAUDE_lich_su_2026-09.md` | **nguyen van, 0 chu bi xoa** |
| 3 | Thay bang mot bang **con tro** + mot lenh | `CLAUDE.md` **496 -> 263 dong** |

⛔ Thu tu 1 truoc 3 la bat buoc: bo ban ghi cu khi chua co ban ghi moi la lap
lai dung loi cua sau lan truoc.

### 6.2 Vi sao lenh `trang-thai` **khong doi khoa production**

Neu no doi khoa thi mot phien khong co khoa se quay ve doc tai lieu — va tai
lieu thi troi. Nen phan cong khai hoi duoc bang tay khong:

```
/health/ready    dich vu                      200  MO cho khach an danh
/                trang chu                    200  MO cho khach an danh
/vps             khu VPS (ban may chu ao)     200  MO cho khach an danh
/gia-api         bang gia API                 200  MO cho khach an danh
/developers      khu lap trinh vien           303  doi dang nhap
```

⇒ Xac nhan **doc lap** cau da sua trong `CLAUDE.md`: `/vps` dang cong khai va
dang thu tien that.

### 6.3 Hai bay Windows da dinh khi lam viec nay

Ca hai deu bi **chinh cong chat luong** bat, khong phai tu thay:

| Bay | Trieu chung | Cong cu bat |
|---|---|---|
| `write_text` tren Windows mac dinh **CRLF** | 2 tep doi kieu xuong dong, `git diff` khong doc duoc | `check_xuong_dong.py` |
| **Heredoc bash nuot dau gach nguoc** - trong heredoc, hai dau gach nguoc bi rut con MOT, nen Python doc `\a` = **BEL** | mot ky tu dieu khien 0x07 lot vao `CLAUDE.md` | `check_ky_tu_dieu_khien.py` |

⭐ Bay thu hai da nam san trong bo nho du an (`heredoc-bash-nuot-backslash`) va
toi van dinh. Do la ly do **banh coc dang gia hon mot ghi chu**: ghi chu doi
nguoi ta nho, banh coc thi khong.

### 6.4 🔴 LAN TROI THU SAU — va no som hon ca nam lan tep tu ghi

Khi quet tham chieu toi muc vua chuyen, tim thay:

```
docs/AUDIT_MVP_2026-07-31.md:106
  | Do chinh xac tai lieu | 62 | ... **CLAUDE.md "Viec con do" sai nang**
    (ghi PostgreSQL/job/credit ❌ du da xong) ...
docs/NHAT_KY.md:14532
  - **W0.7 CLAUDE.md drift** — bang "Viec con do" sua lai ...
```

⇒ Cung mot bang, cung mot benh, **da duoc ghi nhan tu 31/07** — hon MOT THANG
truoc lan dau tien tep tu thu nhan. Va lan do cung duoc "sua" bang cach viet
lai bang.

⭐ Do la bang chung manh nhat cho chan doan: **sau lan sua bang cach viet lai,
sau lan troi lai.** Mot bang chep tay khong the tu biet no da cu, va so lan sua
no khong doi duoc dieu do.

