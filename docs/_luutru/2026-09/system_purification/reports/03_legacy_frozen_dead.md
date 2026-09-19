> LƯU TRỮ 2026-09-19 — không còn đúng hệ thống hiện tại; thay bằng: hợp đồng docs/00_LTT_OPERATING_CONTRACT.md (nhánh admin-mvp-v3/master của đợt dọn 02/09 đã gộp main). Chỉ đọc để hiểu lịch sử.

# BAO CAO 03 — LEGACY, FROZEN & DEAD CODE

Ngay: 2026-09-02 · Cay `D:/LTTSTUDIOSAPP-p01`, nhanh `phien/p01`
Vao phase voi **0 ung vien xoa co san** (ket luan cua Phase 02).

---

## 0. Ket qua mot dong

**Xoa: 0 tep. Chuyen cho: 18 tep. Phan loai lai: 6 he con.**

Va do **khong** phai mot phase that bai. Xem §5.

---

## 1. Danh sach uu tien cua goi prompt da PHAI doi muc tieu

Prompt 03 dat `core/`, `socialbot`, `demo` o dong dau. Do voi repo that:

| Muc tieu cua prompt | Thuc te |
|---|---|
| `core/` | **khong ton tai** — 0 tep |
| `socialbot` | da go 25/08 (Q108) |
| `demo`, `kichban`, `mediatools` | da go 25/08 (Q109) |

⇒ Phase nay chay tren mot danh sach **tu tim**, khong phai danh sach thua ke.

---

## 2. Du chan cua cac app da go — **KHONG phai DEAD**

| Thu | Con lai o dau | Phan loai |
|---|---|---|
| `LTT_SOCIALBOT_ROUTES` | 3 cho, **deu la chu thich** (`server/app.py:318,321`, `apps/nexus/routes.py:64`, `tests/test_248:15`) | `HISTORICAL` |
| `apps/demo` | 4 tep, **deu la chu thich** (`registry.py:31`, `conftest.py:47,53,78,161`, `test_60:215,562`, `test_69:160`) | `HISTORICAL` |
| `kichban`, `mediatools` | **0** tham chieu trong ma song | — |

⛔ **Khong xoa cai nao.** Moi cho deu dang giai thich **vi sao ma hien tai trong
nhu the**:

- `registry.py:31` — *"Khong con app mau de copy"* ⇒ ngan nguoi sau di tim mot
  app mau khong ton tai;
- `conftest.py:47-78` — mo ta app THU thay cho `apps/demo`, **giu nguyen cong
  thuc cu** de cac phep khang dinh ve so tien con doc duoc;
- `server/app.py:321` — noi thang *"co nay khong con duoc doc o dau ca"* ⇒ ngan
  nguoi sau tuong no van co tac dung.

⭐ Xoa nhung dong nay **khong** lam kho sach hon. No lam mat cau tra loi cho cau
hoi "vi sao", va cau hoi do se duoc hoi lai — boi mot phien khong con cau tra loi.

---

## 3. Nam he con "khong ai tieu thu" — **kiem tung cai, khong cai nao DEAD**

| He con | Bang chung no SONG | Phan loai |
|---|---|---|
| `apps/nexus` | `routes.py:40` co router that; `_trang_gioi_thieu` (dong 87) phuc vu; phan web-broker nam sau `_web_broker_bat()` | `ACTIVE` (mot phan `FROZEN` sau co, dung Q101) |
| `codex_sidecar/` | khai trong **3 script cai** (`2-cai-dat.ps1`, `bat_tu_dung_day.ps1`, `nap_lai_env.ps1`); `apps/chataistudio` phu thuoc | `ACTIVE` |
| `gateway:llm`, `gateway:render` | deploy sang **may B** | `ACTIVE` (ngoai may) |
| `sidecar:voice` | dich vu NSSM `LTTStudioVoice` tren may A | `ACTIVE` |
| `agent:nexus` | co doi **da commit chua deploy** (`docs/nexus/N8_CHO_DEPLOY.md`) | `ACTIVE` |
| `frontend` | chay bang `npm`, khong bang `import` | `ACTIVE` |

⇒ "0 nguoi tieu thu" o kho nay la **trang thai binh thuong**, khong phai trieu
chung. App duoc nap **dong**; gateway deploy o may khac; frontend khong phai
Python. Doc danh sach do nhu danh sach ung vien xoa la doc nguoc.

---

## 4. `cutclipshort/` — 30.776 dong, `FROZEN` chu khong `DEAD`

Dung that boi `apps/taoclipngan`, qua **7 duong module** phan biet:

```
cutclipshort.types          .types.base       .core.config
cutclipshort.core.analysis_runner             .editorial.brain
cutclipshort.adapters.ffmpeg_hw               .render.segment_renderer
```

⛔ **Khong tia ben trong.** Day la engine **vendor**. Xoa phan "khong duoc goi"
ben trong mot thu vien vendor la lam mat kha nang dong bo voi ban goc — doi mot
khoan no nhin thay duoc lay mot khoan no khong nhin thay duoc.

⇒ `FROZEN`, bien ro: `cutclipshort/` da nam trong `BO_QUA` cua
`check_bien_dich.py` va trong `SCAN` cua cac chot khac.

---

## 5. Viec DUY NHAT da lam: don thu muc goc

**18 tep** (17 `.png` + `nuitka-crash-report.xml`, 3,5 MB) tu goc kho sang
`docs/_luutru/anh_bang_chung_2026-09/`.

### Bang chung (day du 5 co che cua SP-04 + 4 phep kiem)

| Kiem | Ket qua |
|---|---|
| `GOI_TAI` | khong co |
| `BUILT_PAGES` / `PUBLIC_LINKS` | khong co |
| `_CONTENT_TYPE` (Nexus) | khong co |
| `_goi_moi_nhat()` quet `data/api_dist/` | khong co |
| `registry.py` nap app | khong lien quan |
| `grep` toan kho `.py`/`.html`/`.ps1` | **0** |
| `dong_goi_gui.py::TAI_SAN` | chi `server/static/ltt.css` |
| `ho_so_he_thong.txt` | khong liet ke tep nao |
| `test_145` | chi quet `frontend/`, khong quet goc |

Hai "tham chieu" duy nhat la **van ban goi chung la rac**:
`docs/MVP_OPTIMIZATION_V2/00_LIVE_SYSTEM_MAP.md:530` va bao cao cua chinh
chuong trinh nay.

### Vi sao CHUYEN chu khong XOA

Chung la **bang chung**: anh chup trang thai giao dien tai mot thoi diem la thu
khong dung lai duoc. Phan loai dung la `HISTORICAL`, va hop dong noi ro
*"khong xoa lich su co gia tri"* — viec phai lam la **dat dung cho**.

`git mv` giu nguyen lich su tung tep.

**Ket qua: goc kho 38 → 20 muc duoc theo doi.**

---

## 6. Vi sao "xoa 0 tep" la ket qua DUNG chu khong phai phase that bai

`PURIFICATION_GATES` cam dung so dong da xoa lam thuoc do, va day la ly do cu the:

Kho nay **da** trai qua hai dot xoa lon co ky luat trong vong mot thang —
Q108 (socialbot: 15.046 dong `core/` + 43 route + ~1.017 test) va Q109
(3 app, danh muc 19 → 14). Ca hai deu do **truoc khi xoa**: 0 job, 0
`app_access`, khong tep token nao.

⇒ Phan de xoa **da duoc xoa roi**. Mot phase 03 tim thay nhieu thu de xoa o day
se la mot phase 03 dang doan, khong phai dang do.

⭐ Gia tri that cua phase nay la **doi dau nam ung vien tu UNKNOWN sang co ten**:
truoc phase, nam he con do la "khong ai import — co the chet"; sau phase, moi
cai co mot cau tra loi kem bang chung. Lan don dep sau se khong phai dieu tra lai.

---

## 7. Giao cho phase sau

| Muc | Phase | Vi sao chua lam o day |
|---|---|---|
| Ma chet **ben trong** `cutclipshort/` | — | ⛔ vendor; tia trong la mat duong dong bo upstream |
| 140 diem vao CLI trong `tools/` chua kiem ke | 09 | thuoc tooling, khong thuoc legacy |
| `docs/developer_portal_mvp_ui/` (504 tep, 487 PNG) | 09 | can quyet dinh ve **noi dat bang chung**, khong phai mot lan xoa |
| Hai template song tro toi `developer_portal_mvp_ui` | 06 | chu thich trong `server/templates/` |

## 8. Phan loai sau Phase 03

| Class | So | Ghi chu |
|---|---:|---|
| ACTIVE | 30 | |
| FROZEN | 1 | `cutclipshort/` (vendor, bien ro) |
| HISTORICAL | 6 | du chan chu thich + 18 tep anh da chuyen |
| COMPAT | 1 | `taovideo → upscalevideo` (khai o linter) |
| **DEAD** | **0** | ⛔ khong muc nao du bang chung |
| UNKNOWN | **0** | moi muc deu da co cau tra loi |
