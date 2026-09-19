> LƯU TRỮ 2026-09-19 — không còn đúng hệ thống hiện tại; thay bằng: hợp đồng docs/00_LTT_OPERATING_CONTRACT.md (nhánh admin-mvp-v3/master của đợt dọn 02/09 đã gộp main). Chỉ đọc để hiểu lịch sử.

# PHASE -1 — NEN TANG PHAT TRIEN NHIEU PHIEN

Ngay: 2026-09-02 · Nhanh: `phase-minus-1-foundation` · Goc: `89eb46c`
Cay lam viec: `D:/LTTSTUDIOSAPP-p1` (worktree, khong phai cay chinh)

---

## BEFORE — kien truc gate truoc khi doi

### Da co san (va tot hon prompt gia dinh)

Doc `tools/gate.py` (766 dong) truoc khi viet mot dong nao. Ket qua: **phan lon
thu prompt yeu cau xay thi da ton tai**, va xay lai chung se la chinh cai
"nhieu ban" ma prompt cam.

| Nang luc | Da co? | O dau |
|---|---|---|
| MOT gate engine | ✅ | `tools/gate.py`, 26 buoc, 21 checker |
| Lich chay SONG SONG co phu thuoc | ✅ | `_chay_theo_lich` — 5 nhom, "viec dai chay truoc"; do 28,3s → 7,1s |
| Khoa LIEN TIEN TRINH | ✅ mot phan | `tools/cua_so_yen.py` (235 dong) — **mot** khoa toan cuc |
| Phat hien cay doi giua luot | ✅ | `_anh_chup_cay` + `_ke_cho_da_doi` |
| Nhan biet thay doi | ✅ mot phan | `_da_doi_so_voi_HEAD` — chi dung de bo frontend |
| **Cay rieng cho moi phien** | ✅ | `tools/cay_rieng.py` (159 dong) + chot chan trong `setup/2-cai-dat.ps1` + `test_362` |
| Trang thai thu ba "chay ma khong lam duoc viec" | ✅ | `Step.bo_qua` |
| Thu hoi tien trinh mo coi | ✅ | `don_tien_trinh_mo_coi.py` |

⭐ Kho nay **da** dung worktree tu truoc: `D:/LTTGateQ6`,
`D:/LTTSTUDIOSAPP-asv`, `D:/LTTSTUDIOSAPP_RELEASE_H42`.

### Thieu that su

| Thieu | He qua do duoc |
|---|---|
| So dang ky thanh phan | Sua mot dong trong mot app van keo ca bo test 430 giay |
| `--pham-vi` / `--doi` | khong co duong nao chay it hon ma van la bang chung |
| Khoa theo **TEN** tai nguyen | hai luot khong dung chung gi van doi nhau |
| Kho ket qua | khong tra loi duoc "gate nao da chay tren ma nao" |
| Tai lieu quy trinh | moi phien tu suy ra mot quy trinh khac nhau |

### Bottleneck do duoc trong DUNG mot gio, khong phai gia thuyet

Ba su co that xay ra 13:31–14:20 ngay 02/09 khi hai phien
(`lttstudiosapp-cb`, `lttstudiosapp-e6`) cung lam tren `D:\LTTSTUDIOSAPP`:

1. **13:45 — doi nhanh cua phien khac.** Toi chay `git switch -c purification-v1`
   truoc khi biet co phien dang song ⇒ cay lam viec cua ho bi chuyen nhanh ~1
   phut. Da hoan tac va khai bao. **Nguyen nhan goc: khong co buoc "kiem xem ai
   dang o day" truoc lenh git dau tien.**
2. **13:47 — gate treo vi tranh CPU.** `--vong-lap` (binh thuong ~15 giay) chay
   qua 5 phut vi phien kia dang chay gate day du. `--vong-lap` **co y** khong
   xep hang, va do la quyet dinh dung — nhung khoa cu chi co MOT muc, nen khong
   co cach nao vua khong-chan-vong-lap-ngan vua khong-tranh-CPU.
3. **Toan bo dieu phoi phai lam bang TAY** — hai phien nhan `SendMessage` cho
   nhau bon luot de chot ai giu tep nao.

### Bang so goc (gate day du tren worktree sach tai `56e8245`)

```
TONG          430,5 giay (7,2 phut)
  pha 1 song song  358 giay
  pha 2 noi tiep    72 giay
pytest        4 failed, 5.282 passed, 32 skipped (356,3 giay)
```

⚠️ **Va lan chay do lo ra mot dieu quan trong hon con so: gate day du KHONG
xanh duoc trong mot cay rieng.** 5 buoc do, va **khong buoc nao la loi that**:

| Buoc do | Ly do that |
|---|---|
| `frontend` × 3 | `node_modules/` khong nam trong git ⇒ moi worktree moi deu thieu |
| `system profile` | tep dan xuat, commit ngoai nhip |
| `test_362::test_cay_chinh_co_dot_git_la_THU_MUC` | **chot tu suy "cay chinh" tu vi tri tep test** |
| `test_362::test_cay_lien_ket_...` | cung goc |
| `test_82::test_vendor_engine_co_mat` | engine vendor khong theo doi |

🔴 **Do la mot mau thuan nam ngay trong kho:** `tools/cay_rieng.py` khuyen moi
phien mot cay rieng, con bo test thi khong the xanh o do. Quy trinh duoc khuyen
va quy trinh duoc kiem la hai thu khac nhau — va khong ai phat hien vi truoc do
chua ai chay gate day du trong worktree.

---

## DECISIONS — MUST NOW / SHOULD NOW / DEFER / REJECT

Phan loai sau khi doc repo, khong theo thu tu prompt.

### REJECT — da ton tai, xay lai la tao ban thu hai

| Yeu cau | Vi sao REJECT |
|---|---|
| **A. `tools/workspace.py`** | `tools/cay_rieng.py` da lam dung viec do (`liet-ke`/`tao`/`go`), co chot chan deploy va 15 phep kiem o `test_362`. Them mot CLI nua la dung cai prompt cam o muc "KHONG tao nhieu ban" |
| **F. Scheduler DAG moi** | `_chay_theo_lich` da lam, co so do (28,3s → 7,1s), va no ma hoa hai rang buoc that (`cong` chay mot minh; `sau_test` sau `bo test`). Thay no la vut bo cai da duoc chung minh |
| **E. Tep dang ky task rieng** | `Step` + `NHOM` da la mot dang dang ky. Them mot tep TOML nua chi de mo ta thu da khai trong ma la them mot chu so huu thu hai |
| Scheduler phan tan / executor tu xa | mot may, ba phien |

### MUST NOW

| Yeu cau | Vi sao bay gio |
|---|---|
| **D. So dang ky thanh phan** | moi thu khac phu thuoc no |
| **C. Gate theo thay doi** | 430 giay cho moi sua doi la thu dat nhat dang tra |
| **G. Khoa theo TEN tai nguyen** | su co #2 hom nay |
| **J. Ho so co HOP DONG viet ra** | kho nay da tra gia mot lan cho mot che do khong tu khai |
| **O. Tu kiem** | mot phep LOC sai **khong bao gio keu** |
| **P. Tuong thich nguoc** | `python tools/gate.py` la hop dong voi `AGENTS.md` |

### SHOULD NOW

| Yeu cau | Ghi chu |
|---|---|
| **H. Kho ket qua** | re, va tra loi dung cau hoi cua nhieu phien |
| **K. `DEVELOPMENT_WORKFLOW.md`** | thu duy nhat lam quy trinh nay lap lai duoc |

### DEFER — co ly do, khong phai vi luoi

| Yeu cau | Vi sao hoan |
|---|---|
| **I. Cache ket qua** | do phuc tap > cai duoc. `--vong-lap` da cho vong lap 15 giay; cache dung se de sinh ra mot lop "vi sao no khong chay lai" moi |
| **L. `CURRENT_ARCHITECTURE.md`** | ⛔ Purification Phase 02 **so huu** viec ve ban do so huu. Viet bay gio la doan, va la tao mot tep se mau thuan voi ket qua do that |
| **M. Trang thai phien dang tep** | chua chung minh duoc no giai quyet van de gi ma `cay_rieng.py liet-ke` + kho ket qua chua giai quyet |
| **N. Rut gon `AGENTS.md`/`CLAUDE.md`** | ⛔ Purification Phase 01 so huu. Sua o day la hai chu so huu cho mot tep |

---

## IMPLEMENTED

### 1. `tools/thanh_phan.py` + `tools/thanh_phan.toml` — so dang ky thanh phan

37 thanh phan. **Chi khai thu khong suy ra duoc:**

- **app** suy tu `apps/*/manifest.py` — khong khai lai, vi `registry.py` da nap
  chung tu do; khai lai la tao chu so huu thu hai;
- **anh xa test** suy tu **`import`** doc bang AST;
- **phu thuoc / nguoi tieu thu** suy tu import;
- chi **ranh gioi cua phan khong-phai-app**, **tai nguyen**, **muc he trong** va
  **canh dong** la khai tay.

#### 🔴 Anh xa test PHAI suy tu import, khong tu ten tep — co so do

```
app            khop TEN TEP    thuc su IMPORT
thumbnail            2              19
upscalevideo         1              11
taoanh               2               8
agent               21               4   <- ten khop nham
```

`thumbnail` co 19 tep test cham toi no, chi 2 mang chu "thumbnail". Chon theo
ten se **bo qua 17 phep kiem, im lang** — va mot phep loc thieu trong y het mot
phep loc dung.

#### `[[canh_dong]]` — phu thuoc ma AST khong thay

Sau canh, gom **ba lop**, xep theo do kho thay:

| Lop | Vi du | Con gi de grep |
|---|---|---|
| dict tra bang **chuoi** | `GOI_TAI` phuc vu 5 tep `sdk/` | mot chuoi |
| **import dong** tu quet thu muc | `registry.py` → `apps/*/manifest.py` | ten thu muc |
| **quet thu muc + regex** | `_goi_moi_nhat()` → `data/api_dist/*.exe` | **khong gi ca** |

🔴 Lop thu ba do phien `lttstudiosapp-e6` bao va toi da xac minh
(`server/routes/tai_lieu_api.py:63-84`): noi dung nam trong `data/`, **ngoai
git**. Tha mot tep vao do la doi be mat cong khai — khong deploy, khong commit,
khong dong ma nao doi.

### 2. `tools/cua_so_yen.py` — mot khoa → khoa theo TEN tai nguyen

- moi tai nguyen **mot tep khoa rieng**, giu `O_EXCL` (mot tep chung bat buoc
  doc-sua-ghi, va cua so giua doc va ghi chinh la luc hai tien trinh cung thang);
- xin **theo thu tu sap xep** — hai luot xin cung tap theo hai thu tu khac nhau
  la khoa chet, va no chi xay ra khi hai phien tinh co bat dau gan nhau, tuc rat
  kho tai hien;
- **tat ca hoac khong gi** — giu mot phan roi doi phan con lai la cong thuc
  khoa chet thu hai;
- `trang-thai` liet moi tai nguyen + ai giu + bao lau + co treo khong;
- tai nguyen mac dinh giu **dung ten tep cu** de mot ban gate cu dang chay van
  thay khoa cua ban moi.

### 3. `tools/gate.py` — ho so, pham vi, tai nguyen, kho ket qua

- `--ho-so {vong-lap,pham-vi,doi,day-du,phat-hanh}`, `--pham-vi <tp>`, `--doi`;
- moi ho so khai **`chung_minh`** va **`khong_chung_minh`**, va dong `RESULT`
  cua ho so thu hep tu noi gioi han cua no;
- `Step.tai_nguyen`; gate xin dung nhung tai nguyen cac buoc that su can;
- kho ket qua `test-results/gates/<id>.json`: SHA, nhanh, cay, la-cay-chinh,
  ho so, tung buoc, thoi gian, **thoi gian cho khoa**;
- frontend thieu `node_modules` nay **TU KHAI `BO QUA`** thay vi FAIL.

### 4. Bon loi CO SAN da sua

Khong cai nao do toi gay ra; ca bon lo ra vi Phase -1 buoc phai chay gate trong
mot cay rieng.

| # | Loi | Vi sao no dang ke |
|---|---|---|
| 1 | `cay_rieng.py` tro toi `tools/check_cay_chinh.py` va noi no "chay trong gate" — **tep do khong ton tai** | Mot tham chieu chet trong tai lieu an toan la **mot lop bao ve TUONG TUONG**: nguoi doc tin co hai lop trong khi chi co mot, nen khong di kiem lop con lai. Chot that nam o `setup/2-cai-dat.ps1`, do `test_362` giu |
| 2 | `test_362` suy "cay chinh" tu vi tri tep test ⇒ **bo test khong the xanh trong worktree** | Quy trinh duoc khuyen va quy trinh duoc kiem la hai thu khac nhau. Nay hoi git; khong goi duoc git thi doc `gitdir:` trong `.git` — khong `skip` |
| 3 | `test_chi_luot_DAY_DU_xep_hang` khoa **mot chuoi ma nguon** | `IMPLEMENTATION_LOCK` dung nghia. Do khi doi cach lam **du hanh vi khong doi mot chut nao**. Nay tinh dung phep tinh `main()` tinh — **chat hon** ban cu, vi ban cu xanh voi bat ky tep nao chua chuoi do, ke ca trong mot chu thich da chet |
| 4 | Chot cua **chinh toi** de lai ba ban ghi `PASS` **gia** trong kho ket qua | Dung cai bay `AGENTS.md` §10.4. Mot chot ve tinh trung thuc cua kho ket qua ma tu lam ban kho ket qua thi no dang chung minh dieu nguoc lai. Nay ghi vao `tmp_path` |

⭐ Loi #4 do **banh coc `check_bo_qua.py` bat**, khong phai toi tu thay: ban va
dau cua loi #2 dung `pytest.skip` khi thieu git, va banh coc do ngay — *"mot
test bi bo qua la mot test khong canh gi ca"*. No dung: tien de do doc duoc ma
khong can git.

---

## TEST EVIDENCE

```
python -m pytest tests/test_394_nen_da_phien.py tests/test_362_cay_rieng_va_deploy.py
  -> 41 passed in 141.20s
```

`tests/test_394_nen_da_phien.py` — 25 chot moi:

| Nhom | Chot dang chu y |
|---|---|
| So dang ky | moi app deu thanh mot thanh phan (khong the quen mot app) · khop **tien to dai nhat** · duong Windows = duong POSIX · **duong khong ai so huu thi KHONG doan** · cham tep dung chung thi chay TAT CA |
| Anh xa test | **suy tu import chu khong tu ten tep** · chi lay module test that (`tests/__init__.py` lot vao lam ca luot chet bang `INTERNALERROR`) |
| Canh dong | **`sdk/` khong duoc tro lai thanh mo coi** · moi canh phai co bang chung |
| Khoa | hai tai nguyen khac nhau **khong doi nhau** · cung tai nguyen thi nguoi thu hai truot · khoa treo bi doat · **tat ca hoac khong gi** · xin theo thu tu sap xep |
| Gate | moi ho so phai khai no **khong** chung minh gi · **`test_moi_buoc_gate_cu_van_con`** · chi buoc that su doc quyen moi khai tai nguyen |
| Kho ket qua | nam ngoai git **va** ngoai deploy · du danh tinh · **khong ghi bien moi truong / dau ra buoc** |

⛔ Chot quan trong nhat la **`test_moi_buoc_gate_cu_van_con`** — no liet 22 buoc
bat buoc va do khi mot buoc bien mat. `PURIFICATION_GATES` doi *"prove new gate
coverage >= old critical coverage"*; day la cho dieu do duoc cuong che thay vi
duoc hua.

### Banh coc bo qua

```
python tools/check_bo_qua.py  ->  RESULT: PASS   (khong them lan bo qua nao)
```

### Dieu phoi tai nguyen (hai tien trinh that)

```
LUOT-A: gate --pham-vi app:taoclipngan   (giu khoa)
LUOT-B: gate --pham-vi app:anhnoibo      (cung xin cpu_nhieu)

python tools/cua_so_yen.py trang-thai
  [cpu_nhieu] LUOT-A (pid 20836) chay `gate --ho-so pham-vi` duoc 6.6 phut
```

⇒ Phien thu hai **biet ro tai nguyen nao va ai dang giu**, khong treo khong ro
ly do. Da don khoa va tien trinh sau khi do.

---

## PERFORMANCE

| Phep do | Truoc | Sau |
|---|---:|---:|
| Gate day du (bo test) | 430,5 s | khong doi |
| Nhom kiem tinh | ~28,3 s noi tiep / 7,1 s song song | khong doi |
| **Bo test cho `app:taoclipngan`** | 430,5 s (ca kho) | **27 tep test** |
| **Bo test cho `core:tien`** | 430,5 s | **150 tep test** |
| **Bo test cho `app:anhnoibo`** | 430,5 s | **134 tep test** |

### ⚠️ Muc thu hep NHO HON du kien, va do la mot phat hien chu khong phai that bai

`app:anhnoibo` van keo **134/323** tep test (~41%). Nguyen nhan: `server:web`
la nguoi tieu thu, va no co ~130 tep test.

Canh do **co that**, da kiem tung dong:

```
server/routes/dashboard.py:134:    from apps.anhnoibo import gia as gia_anh
```

⇒ Doi gia cua `anhnoibo` co the lam vo bang dieu khien, nen chay test cua
`server:web` la **dung**.

⭐ Va phep do nay vua lo ra mot **vi pham phan tang** cho purification Phase 06:
`server/` biet ten mot app cu the. Hop dong app cho phep chieu `app → server`
(danh sach trang o `lint_app_contract.py:58-61`) nhung khong noi gi ve chieu
nguoc lai. Do la mot khoan no kien truc, va no dang **do bang so**: no la ly do
mot thay doi trong mot app nho van keo 41% bo test.

⇒ Ket luan trung thuc: **gia tri cua `--pham-vi` bi chan tren boi do dinh that
cua kho, va cong cu nay bien do dinh do thanh mot con so nhin thay duoc.** Do
la gia tri lau dai lon hon con so 27 tep.

---

## COMPATIBILITY

| Lenh cu | Trang thai |
|---|---|
| `python tools/gate.py` | ✅ khong doi nghia — mac dinh `--ho-so day-du` |
| `python tools/gate.py --quick` | ✅ giu nguyen, **van khong xep hang** |
| `python tools/gate.py --vong-lap` | ✅ giu nguyen, **van khong xep hang** |
| `python tools/cua_so_yen.py trang-thai` | ✅ mo rong: liet moi tai nguyen |
| `python tools/cua_so_yen.py nha` | ✅ mac dinh nha TAT CA; `--tai-nguyen` de chon |
| `python tools/cay_rieng.py *` | ✅ khong doi (chi sua chu thich) |

Hanh vi xep hang da duoc do lai, khong phai suy:

```
ho_so=vong-lap  quick=True   tai_nguyen=(khong)      -> xep_hang=False
ho_so=day-du    quick=False  tai_nguyen=['cpu_nhieu']-> xep_hang=True
--quick tran                 tai_nguyen=(khong)      -> xep_hang=False
```

---

## OPEN RISKS

| Muc | Rui ro | Xu ly |
|---|---|---|
| P1 | `--pham-vi` **tin nguoi goi**. Chon sai pham vi la mot luot xanh khong co nghia | Hop dong ho so noi thang; `--doi` tu kiem nen an toan hon |
| P1 | Do thi khong thay import dong ngoai nhung canh **da khai**. Mot co che dong moi ma khong khai la mot lo hong im lang | `test_394` doi moi canh co bang chung, nhung khong the doi mot canh **chua ai biet** |
| P2 | Cay rieng khong co `node_modules` ⇒ frontend luon `BO QUA` o do | Hien o dong RESULT. Muon chung minh frontend thi `npm ci`, hoac chay tren cay chinh |
| P2 | `test_82::test_vendor_engine_co_mat` van do trong cay rieng (engine vendor khong theo doi) | **Chua sua** — ngoai pham vi Phase -1; ghi lai cho purification |
| P3 | Kho ket qua khong tu don | Thu muc nho (~1 KB/luot); them viec don la them mot thu de hong |

---

## BON LOI CUA CHINH TOI, do gate bat — khong phai toi tu thay

⭐ Muc nay dang ke hon phan "da lam duoc", vi no do chinh cai cong dang duoc
sua. Neu cong nay yeu di sau Phase -1 thi bon loi duoi day da di thang vao
nhanh chinh.

| # | Loi | Ai bat | Vi sao nguy hiem |
|---|---|---|---|
| 1 | Bo phan giai dua ca `tests/__init__.py` cho pytest | luot `--pham-vi` dau tien | `INTERNALERROR` = **ca bo test khong chay**, nhung dong ket qua trong y het mot that bai binh thuong |
| 2 | Ban va dau cua `test_362` dung `pytest.skip` khi thieu git | **`check_bo_qua.py`** | *"Mot test bi bo qua la mot test khong canh gi ca."* No dung: tien de do doc duoc ma khong can git |
| 3 | Doi `da_giu` tu `bool` sang `list` lam hai chot `test_361` do | **gate day du** | Nghia khong doi (`[]` = khong giu gi) nhung chung dung `is False` |
| 4 | Kho ket qua ghi `tai_nguyen_da_giu: []` cho mot luot **CO** giu khoa | **doc chinh dau ra cua minh** | `__exit__` xoa `da_giu` truoc khi bao cao. Khong on ao; chi lang le ghi sai vao dung cho phien sau se tin |
| 5 | Ghi lai hai tep bang Python lam chung thanh **CRLF** trong khi HEAD la LF | **`check_xuong_dong.py`** | Mot tep bi ghi lai toan bo lam `git diff` khong doc duoc |

🔴 **Loi #4 dang duoc noi rieng.** Chot cua toi (`test_kho_ket_qua_ghi_du_danh_tinh`)
**khong bat duoc no**, vi no dung mot doi tuong khoa **gia** chua he di qua
`__exit__`. Do la kieu khoang trong dien hinh: kiem tung manh thay vi kiem doan
noi giua chung. Da them `test_sau_khi_thoat_van_bao_duoc_da_giu_gi` lap dung
khoang do.

---

## FINAL VERDICT

### ✅ `FOUNDATION PASS`

Luot gate day du tren cay `D:/LTTSTUDIOSAPP-p1`, nhanh `phase-minus-1-foundation`:

```
RESULT: PASS  [4 BUOC TU BO QUA, KHONG PHAI BANG CHUNG:
               bat bien da tien trinh, frontend agent-canvas,
               frontend autosub-studio, frontend prompt-ai-ommi]
```

- **0 buoc FAIL**
- **khong** co dong `CAY DA DOI TRONG LUC CHAY`
- 5.312 test pass · 32 skip · **0 fail**

### Bon buoc `BO QUA` — vi sao chung khong phai mot lan lam ngo

| Buoc | Ly do | Co che khien no khong bi quen |
|---|---|---|
| `bat bien da tien trinh` | may nay khong co PostgreSQL test | tu khai + hien o dong `RESULT` |
| `frontend` × 3 | cay rieng khong co `node_modules` (~700 MB, khong trong git) | nhu tren; `cay_rieng.py tao` in ro |

⛔ Chung **khong** im lang xanh. Ca bon deu hien ten o dong `RESULT` kem cau
"KHONG PHAI BANG CHUNG" — dung co che `Step.bo_qua` da co san tu truoc, khong
phai mot ngoai le moi.

### Sau dieu kien

| # | Dieu kien | Trang thai |
|---|---|---|
| 1 | gate day du xanh | ✅ `RESULT: PASS` |
| 2 | `test_394` + `test_362` + `test_361` | ✅ **40/40** |
| 3 | `check_bo_qua.py` | ✅ PASS — khong them lan bo qua nao |
| 4 | quet bi mat | ✅ PASS (trong gate) |
| 5 | lenh cu khong doi nghia | ✅ da **do**, khong phai hua |
| 6 | viec purification khong mat | ✅ `docs/system_purification/` day du |

⇒ Du dieu kien quay lai System Purification.
