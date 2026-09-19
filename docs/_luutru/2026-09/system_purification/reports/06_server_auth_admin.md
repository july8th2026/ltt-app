> LƯU TRỮ 2026-09-19 — không còn đúng hệ thống hiện tại; thay bằng: hợp đồng docs/00_LTT_OPERATING_CONTRACT.md (nhánh admin-mvp-v3/master của đợt dọn 02/09 đã gộp main). Chỉ đọc để hiểu lịch sử.

# BAO CAO 06 — SERVER, API, AUTH & ADMIN

Ngay: 2026-09-02 · 62 tep / 14.001 dong · nhanh `phien/p01`

---

## 0. Ket qua

**Phase dau tien DOI KIEN TRUC, khong chi ghi nhan.** Hai cạnh `server → app`
da go bang cach **bo sung hop dong**, khong bang cach bo loi goi. Va mot banh
coc da duoc lam cho noi that ve pham vi cua no.

---

## 1. Ban do kich thuoc

| Tep | Dong | Ghi chu |
|---|---:|---|
| `admin.py` | **1.622** | tep lon nhat; **da phinh +234** so voi moc 1.388 |
| `api/streaming.py` | 1.015 | |
| `admin_api.py` | **859** | ⭐ **da tu 1.897 xuong** — no giam that |
| `api/jobs.py` · `templating.py` · `app.py` | 479 · 474 · 438 | |

---

## 2. ✅ DA SUA — hai cạnh `server → app` cua trang gia

### Van de

`server/routes/dashboard.py` import thang `apps.anhnoibo.gia` va
`apps.ltt_voice.gia`. Hop dong app khai chieu `app → server`
(`SERVER_APP_CO_THE_DUNG`) va ca chieu `app → app` (`APP_DUOC_DUNG_APP`), nhung
**bo trong chieu `server → app`** — nen nen tang biet ten hai app cu the, dung
thu `registry.py` mo dau bang cau cam:

> *"Nen tang KHONG duoc biet app nao ton tai. No quet `apps/*/manifest.py`."*

### ⛔ Nhung loi goi cu KHONG cau tha — va doc nham cho nay se sua sai

No **co y** goi `bang_gia()` de tranh go lai so vao template. Chinh chu thich
ben canh no da viet:

> *"KHONG dung them mot danh sach vi du o day… them mot danh sach thu hai o tang
> route la tao dung cai 'bang gia thu hai' ma ca ham ay lan dau ham nay canh bao."*

⇒ Bo loi goi = tao mot bang gia thu hai. **Cach sua dung la bo sung vao hop dong
thu no dang thieu** — dung luat cua `CLAUDE.md`:

> *"Neu thay buoc phai sua nen tang thi dung lai va noi ro vi sao — do la dau
> hieu hop dong app con thieu, phai bo sung vao hop dong chu khong di vong."*

### Da lam

| Thay doi | Ghi chu |
|---|---|
| `AppManifest.bang_gia: Optional[Callable[[], dict]]` | theo **dung tien le** `bao_tri`/`credit_cost` da co |
| `registry.bang_gia_cong_khai()` | thu thap tu app **dang bat**; mot app hong bang gia **khong** lam sap trang gia cua app khac |
| `dashboard.py` doc qua registry | khong con biet ten app nao |
| Vi du gia anh chuyen tu route **ve app** | `ltt_voice` da lam dung tu dau; `anhnoibo` thi route giu **danh sach vi du** con app giu **phep tinh** |

### Bang chung

```
GET /gia-api -> 200, 22.584 ky tu
so xuat hien: 3 · 12 · 9   = dung ba vi du (1 anh, 4 anh, 1 anh tham chieu 3x3)
tests/test_274_gia_cong_khai + test_261_khong_ban_duoi_gia_von: 20 passed
grep "from apps\." server/  -> chi con 3 cho o streaming.py
```

### Ba cạnh con lai — **giu, va khai thanh no CO TEN**

```
server/api/streaming.py:48,509,980 -> apps.ltt_llm  (ngan sach token, alias model)
```

Khac moi quan tam (khong phai gia), va chua co hinh dang hop dong ro. Khai vao
`SERVER_BIET_APP_DUOC_PHEP` trong `tests/test_147_layering.py`, va chot moi kiem
**ca hai chieu**: cạnh moi chua khai thi do, **khai thua cung do** — mot danh
sach khai thua la mot loi noi doi ve hien trang.

---

## 3. ✅ DA SUA — banh coc kich thuoc route chi GHI con so, khong CUONG CHE

### Phat hien

`check_server_routes.py` chi so **tap hop tep** (`set(hien) - set(moc)`).
`dong`/`handler` duoc ghi vao moc va **duoc IN RA moi lan chay** — nhung khong
bao gio duoc so.

He qua do duoc: **`server/admin.py` di tu 1.388 → 1.622 dong (+234)** trong khi
chot bao PASS suot doan duong do.

⛔ Vi sao te hon mot con so sai: cong cu **IN con so ra**, nen nguoi doc co ly do
tin rang no dang duoc canh. Mot chot ghi lai thu no khong cuong che la mot chot
**noi doi ve chinh pham vi cua no**.

### Va chieu nguoc: no giam that ma khong ai ghi nhan

`admin_api.py` **1.897 → 859**. Moc van giu 1.897, tuc cho phep mot tep khong
con ton tai o kich thuoc do. Da `--update`: moc 2 tep → **1 tep**.

⚠️ Do la **ha moc sau khi no that su giam** — dung luat `OPERATING_CONTRACT` §9,
khong phai nang moc cho gate xanh.

### Sua

Them phep so gia tri. ⚠️ **Khong phai luat moi** (§8): luat cu van la "no chi
duoc giam"; phan con thieu la **mot nua phep so**. Moc vua ghi lai theo thuc te
nen hom nay khong tep nao do.

---

## 4. 🔴 BA LOI CUA CHINH TOI o phase nay — cung mot chot, ba lan

Dang ghi vi ca ba deu do **cong chat luong** bat, khong phai toi tu thay.

| Lan | Loi | Ai bat |
|---|---|---|
| 1 | Khai `GUARD_DOI_DANG_NHAP` **trong ham** nen khong import duoc | chinh chot do |
| 2 | Khoi phuc bang `write_text(newline="\\n")` — tep von **CRLF** ⇒ moi luot chay lam ban them | `check_xuong_dong` |
| 3 | **Ghi vao cay** giua luot gate | gate: `CAY DA DOI TRONG LUC CHAY` + buoc tinh doc song song thi do |

### Lan 3 dang noi nhat

Kho **da co** `gate.TEP_KHONG_DUOC_DOC_SONG_SONG` — danh sach ba tep ma bo test
ghi con buoc tinh doc, ton tai vi chung tung gay `OSError [Errno 22]` va lam hai
phien mat gan tron mot ngay.

Chot cua toi vua tao **tep thu tu** nhu the. Va cach sua **khong phai** them no
vao danh sach — do chi la mo rong mot ngoai le. Cach dung: **dung ghi vao cay**.
Va `MOC` sang `tmp_path` roi goi thang `main()` trong tien trinh. Khong tien
trinh con, khong dua voi ai, va nhanh hon.

⚠️ Nho va ca `sys.argv`: `main()` goi `parse_args()` khong tham so, nen duoi
pytest no doc dong lenh cua pytest va thoat voi ma 2.

### ⭐ Va banh coc moi bat duoc nan nhan dau tien: chinh toi

Moc co luc giu `1612` — dung bang `1622 - 10`, tuc **gia tri gia lap** trong chot
cua toi da lot vao tep that o mot luot truoc khi toi sua no thoi ghi vao cay.

Truoc Phase 06, mot gia tri sai nhu the se **nam im vinh vien**: banh coc cu chi
so tap hop, nen `1612` hay `1622` deu khong doi dong RESULT. Nay no do ngay.

---

## 5. Auth — khong dong toi, va do la quyet dinh

Prompt 06 noi ro *"Do not casually alter semantics"* cho auth. Da **doc** va
khong sua gi:

| Do | Ket qua |
|---|---|
| `require_operator` (`server/deps.py:99-106`) | goi `require_login` roi them 403 — **manh hon**, khong phai duong vong |
| Duong admin-tu-bien-moi-truong | da vo hieu o production (Q29); ma con lai co ly do tuong thich, chua do bang chung de xoa |
| `qualitylab` "thieu require_login" | **duong tinh gia** — da sua o Phase 04 |

---

## 6. Con no

| Muc | Vi sao chua lam |
|---|---|
| `admin.py` 1.622 dong | Prompt 06: *"Large file alone ≠ reason to split"*. Nay **da co banh coc chan phinh them** — do la buoc dung truoc khi tach |
| 3 cạnh `streaming.py → ltt_llm` | can mot hinh dang hop dong cho "ngan sach token cua app", chua ro |
| `server:web` phu thuoc 15 thanh phan | ⭐ da giam 2 (bo `app:anhnoibo`, `app:ltt_voice`) trong phase nay |
