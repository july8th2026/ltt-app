# PHASE 01b — THIET KE THI HANH (ban cu the de sua)

Tiep theo `01_truth_rules_docs.md` (phan chan doan). Tep nay noi **sua gi, o dau,
thay bang gi** — de nguoi sau doc mot lan la thi hanh duoc.

---

## 0. Bang chung tuoi, do luc 15:0x ngay 2026-09-02

Khong doc lai tai lieu. Hoi thang may chu:

```
GET https://app.lttstudios.com/vps           -> 200   (khach AN DANH)
GET https://app.lttstudios.com/              -> 200
GET https://app.lttstudios.com/health/ready  -> {"status":"ready",
                                                 "environment":"production",
                                                 "database":"ok"}
```

⇒ Cau da sua trong `CLAUDE.md` la **dung**: `/vps` dang cong khai va dang thu
tien. Va chinh phep do nay — ba dong `curl`, muoi giay — la thu dang thay cho
280 dong chep tay.

---

## 1. Van de, phat bieu chinh xac

`CLAUDE.md` = 496 dong. §"Viec con do" = dong **196–475** = **280 dong (56%)**.

Trong 280 dong do:
- **29 dong** la hang bang;
- **207 dong** la van xuoi ke chuyen tung he con.

🔴 Va hai hang don le da phinh thanh hai khoi khong con doc duoc:

| Dong | Hang | Do dai mot O BANG |
|---:|---|---|
| 223 | Model tao anh noi bo | ~2.500 tu **trong MOT o** |
| 226 | Ban VPS | ~1.900 tu **trong MOT o** |

Mot o bang dai 2.500 tu khong phai mot bang. Do la mot bai viet bi nhet vao mot
cai o, va do la ly do khong ai doc lai duoc de phat hien no da troi.

---

## 2. Ba loai noi dung dang bi tron trong cung 280 dong do

| Loai | Vi du that trong dong 223/226 | Thuoc ve dau |
|---|---|---|
| **LUAT** (bat bien) | *"Ban ≠ hong — khi may B ban, khong goi `api_pool.danh_dau_loi()`"* · *"Cum khong chay duoc virtio: `sata0`+`e1000`"* | **ma nguon** (da co chu so huu — xem §1.4 bao cao 01) |
| **TRANG THAI** (het han) | *"4 cong con khoa"* · *"LTT_VPS=1"* · *"gia 3 credit/anh"* | **hoi may chu** |
| **LICH SU** (vi sao) | *"So mu G6b 23/08: Gemini 24 – nha 4"* · *"D-057: DUNG ke hoach dung may A"* | `docs/ANH_NOI_BO/DECISIONS.md` (**da o do roi**) |

⇒ Ca ba loai **deu da co nha rieng**. `CLAUDE.md` dang giu ban sao thu hai cua
ca ba — va mot ban sao khong co test la mot ban sao se troi.

---

## 3. Thay bang gi — khuon cu the

### 3.1 §"Viec con do" (196–475) → mot bang tro toi + mot lenh

Moi hang giu **dung bon cot**, khong hon:

```
| He con | Trang thai | Luat o dau | Lich su o dau |
|---|---|---|---|
| Ban VPS | `python tools/api_prod_canary.py --trang-thai` | `apps/vps/services/mang.py` `MO_HINH_CARD` · `apps/vps/bao_tri.py` | `docs/VPS/` |
| Model anh noi bo | (nhu tren) | `render_gateway/ngan_sach.py` · `apps/anhnoibo/gia.py` | `docs/ANH_NOI_BO/DECISIONS.md` |
```

⛔ **Cot "Trang thai" khong duoc chua mot gia tri nao.** No chua mot **lenh**.
Do la ca diem cua thay doi nay: mot o khong the troi neu no khong chua so lieu.

**Uoc luong: 280 dong → ~35 dong.** Nhung do khong phai muc tieu —
`PURIFICATION_GATES` cam dung so dong da xoa lam thuoc do. Muc tieu la **so noi
mot bat bien duoc phat bieu: tu 2 ve 1**.

### 3.2 Van xuoi lich su (H7/H22/H35/H36/H37/H38, ~207 dong)

Chuyen sang `docs/_luutru/CLAUDE_lich_su_2026-09.md`, nguyen van, co nhan:

```markdown
> ⛔ TAI LIEU LICH SU. Khong phai chi dan hien hanh.
> Chup tu `CLAUDE.md` ngay 2026-09-02. Moi con so o day noi ve luc no duoc viet.
> Muon biet HIEN GIO: `python tools/api_prod_canary.py --trang-thai`.
```

⭐ **Khong xoa mot chu nao.** Cac doan "SUA LAN HAI/BA — LAI VE PHIA NGUY HIEM"
la bang chung dat gia ve chinh che benh nay; chung phai duoc giu, chi la giu o
noi khong ai doc nham thanh luat.

### 3.3 Mo rong `tools/api_prod_canary.py`

Da co `probe` hoi `/api/v1/tools|jobs|usage`, va da co ky luat dung: *"hinh dang
la phai NOI RA"* (dong 174–186) sau khi ban cu doc `data`/`tools` trong khi API
tra `items` va in "rong — dung y muon".

Them mot lenh con `--trang-thai` in **mot man hinh**:

| Do | Nguon | Vi sao |
|---|---|---|
| tool nao dang mo | `GET /api/v1/tools` | da bat 3 lan troi |
| app nao song / cong khai | `GET /<slug>` ma khach an danh | da bat vu `/vps` |
| gia hien hanh | `GET /gia-api` | |
| `/health/ready` | | |

⚠️ **Giu nguyen ky luat cu:** hinh dang la thi **noi ra**, khong lang le thanh
rong. Chinh cho do da suyt lam con canary noi doi.

### 3.4 Bien phep do §1.3 thanh mot buoc gate

Loi thu **nam** (hai tran `1.500` cua `ltt_voice` da tach 31/08 ma `CLAUDE.md`
khong theo kip) duoc tim ra **khong phai** bang cach doc lai tai lieu, ma bang
cach doi chieu tung gia tri voi chu so huu trong ma.

⇒ Mot chot moi: moi so trong `CLAUDE.md` phai hoac (a) tro toi mot hang so
trong ma, hoac (b) khong ton tai.

⛔ **Kiem `OPERATING_CONTRACT` §8 truoc khi lam:** *"khong them luat moi de chua
luat cu"*. Chot nay **khong** vi pham, va ly do phai viet ra:

- no **khong** them viec cho nguoi — no **bo** kha nang chep tay;
- no **thay the** mot thu dang ton tai (viec "nho cap nhat", da that bai 5 lan)
  bang mot thu do duoc;
- neu §3.1 lam dung thi chot nay gan nhu khong co gi de kiem — no la **banh coc
  giu ket qua**, khong phai mot lop luat moi.

### 3.5 Di tru `docs/lttstudios-website/route-map.json`

`tools/audit_public_web.py:13` doc no lam **HOP DONG**. Chung nao no con nam
trong `docs/`, cau "docs/ la khu lich su" con sai.

⇒ Chuyen sang `tools/` (canh nguoi doc no), cap nhat mot duong dan.

---

## 4. Thu tu thi hanh, va vi sao thu tu nay

1. **§3.3 truoc** — dung nguon trang thai **truoc khi** xoa ban chep tay. Xoa
   truoc la co mot khoang thoi gian khong ai tra loi duoc "gio dang the nao".
2. **§3.2** — chuyen lich su ra, nguyen van.
3. **§3.1** — thu bang lai.
4. **§3.4** — chot, sau khi khong con gi de no bat.
5. **§3.5** — doc lap, lam luc nao cung duoc.

⛔ **Lam nguoc thu tu 1↔3 la lap lai dung loi cua nam lan truoc**: bo ban ghi cu
khi chua co ban ghi moi.

---

## 5. Cai KHONG lam o Phase 01

| Khong lam | Vi sao |
|---|---|
| Rut gon `AGENTS.md` | 697 dong nhung phan lon la **luat that**, khong phai trang thai. Khong cung mot benh |
| Viet lai `docs/KE_HOACH_TRIEN_KHAI.md` (3.668 dong) | Phase 02 se biet ban do so huu that; sua bay gio la doan |
| Xoa `docs/APP_AUDIT/` (406 tep) hay `developer_portal_mvp_ui/` (504 tep) | **HISTORICAL, khong phai DEAD.** Chi can NHAN, khong can xoa. Va hai template song dang tro toi chung |
| Dung toi `NHAT_KY.md` | no **dang** la lich su va da duoc dan nhan dung |
