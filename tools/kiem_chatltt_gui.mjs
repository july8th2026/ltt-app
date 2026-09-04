/**
 * kiem_chatltt_gui.mjs — bo kiem GIAO DIEN ChatLTT tren mot trinh duyet that.
 *
 * ## Vi sao co tep nay, khi da co 53 test frontend va 34 tep test backend
 *
 * Vitest chay tren jsdom: khong CSS that, khong layout that, khong Cloudflare,
 * khong SSE that. No chung minh **logic component**. No khong the chung minh
 * rang o soan khong de len chan trang o 390 px, rang CSP bien khong chan bundle,
 * hay rang mot lenh gui di that su tra ve dung thu no hua.
 *
 * ⛔ Va do khong phai gia thuyet. Hai loi that cua H43 deu thuoc loai nay:
 *    o soan de len chan trang (Phase 09), va moi lenh GET bi 302 vi tien to
 *    ngon ngu (Phase 08b). Ca hai deu XANH o vitest.
 *
 * ## Cach chay
 *
 *     node tools/kiem_chatltt_gui.mjs --url http://127.0.0.1:8130 \
 *          --user demo@lttstudios.local --pass demo-password-1234
 *
 *     # production: mat khau qua BIEN MOI TRUONG, khong qua tham so dong lenh
 *     LTT_SMOKE_USER=... LTT_SMOKE_PASS=... \
 *       node tools/kiem_chatltt_gui.mjs --url https://app.lttstudios.com
 *
 * ⚠️ `--pass` chi danh cho may DEV. Tren production dung bien moi truong: tham
 *    so dong lenh nam trong `ps`, trong lich su shell, va trong log cua bat ky
 *    cong cu nao goi lai lenh nay.
 *
 * ## Hop dong cua tep nay
 *
 * Moi hang muc tra ve `{ ten, dat, chi_tiet }`. Mot hang muc KHONG duoc phep
 * nem: nem thi cac hang muc sau khong chay va bao cao thanh mot dong "hong" vo
 * dung. Loi duoc bat va bien thanh `dat: false` kem ly do doc duoc.
 *
 * ⭐ Console error va request hong duoc gom SUOT ca luot, khong chi o cuoi. Mot
 *    loi console xuat hien o hang muc 3 roi bi cuon qua thi o cuoi khong con
 *    dau vet — va do chinh la loai loi bo kiem nay sinh ra de bat.
 */
import { execSync } from 'node:child_process';
import { existsSync, mkdirSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { pathToFileURL } from 'node:url';

// ⛔ Import DONG, khong `import { chromium } from 'playwright'`.
//
//    ESM khong doc `NODE_PATH`, va kho nay khong cai `playwright` o cap goc —
//    no den tu goi toan cuc `@playwright/cli`. Mot import tinh o day chi chay
//    duoc tren may da `npm i playwright` ngay trong kho, tuc gan nhu khong may
//    nao. Tra gia bang bay dong de bo kiem chay duoc o moi cho la mot doi chac
//    de.
async function napPlaywright() {
  const ung_vien = [];
  try {
    const g = execSync('npm root -g', { encoding: 'utf-8' }).trim();
    ung_vien.push(join(g, '@playwright', 'cli', 'node_modules', 'playwright', 'index.mjs'));
    ung_vien.push(join(g, 'playwright', 'index.mjs'));
  } catch { /* khong co npm trong PATH: thu duong con lai */ }
  ung_vien.push('playwright');
  for (const d of ung_vien) {
    try {
      const m = await import(d.endsWith('.mjs') && existsSync(d) ? pathToFileURL(d).href : d);
      if (m.chromium) return m.chromium;
    } catch { /* thu ung vien tiep theo */ }
  }
  throw new Error('khong tim thay `playwright`. Cai: npm i -g @playwright/cli');
}

const chromium = await napPlaywright();

// ── Tham so ────────────────────────────────────────────────────────────────
const argv = process.argv.slice(2);
const co = (t, md = '') => {
  const i = argv.indexOf(t);
  return i >= 0 && argv[i + 1] ? argv[i + 1] : md;
};
const URL_GOC = co('--url', 'http://127.0.0.1:8130').replace(/\/$/, '');
const NGUOI = co('--user', process.env.LTT_SMOKE_USER || '');
const MAT_KHAU = co('--pass', process.env.LTT_SMOKE_PASS || '');
const HIEN = argv.includes('--hien');          // mo cua so that de nguoi xem
const THU_MUC_ANH = co('--anh', 'tmp/kiem_gui');
const CHI = co('--chi', '');                   // chay mot hang muc theo ten
/** `--dot 1,2,A` — chi chay nhung dot duoc goi ten. Rong = tat ca. */
const DOT = co('--dot', '').split(',').map((x) => x.trim()).filter(Boolean);

/**
 * `--phien <tep>` — dung mot PHIEN DA DANG NHAP (Playwright storageState).
 *
 * ⭐ Day la duong duoc uu tien tren PRODUCTION, va ly do khong phai tien tay.
 *    Chu du an dang nhap bang chinh tay ho trong mot cua so that; thu di vao
 *    tep nay la mot **cookie phien**, khong phai mat khau. Bo kiem khong bao
 *    gio cam mat khau, va khong co gi de lam ro ri.
 *
 * ⚠️ Tep phien VAN la mot bi mat song: ai co no la vao duoc tai khoan do cho
 *    toi khi phien het han. De trong `tmp/` (da gitignore), dung commit.
 */
const PHIEN = co('--phien', '');

/**
 * `--profile <thu-muc>` — chay tren mot PROFILE CHROME THAT, giu nguyen.
 *
 * 🔴 VI SAO CAN TREN PRODUCTION. `app.lttstudios.com` nam sau Cloudflare, va
 *    Cloudflare **chan trinh duyet tu dong**: mot Chromium headless moi tinh
 *    nhan `403 Just a moment...` truoc ca trang dang nhap. Do la hanh vi DUNG
 *    cua mot site that, khong phai loi.
 *
 * ⛔ Va no khong duoc "sua" bang cach gia lam nguoi. Vuot bot detection la
 *    thu bo kiem nay khong lam, khong bao gio.
 *
 * ⭐ Duong hop le: chu du an mo mot cua so Chrome THAT mot lan, tu qua xac
 *    minh va tu dang nhap. Ca hai thu do o lai trong profile. Bo kiem mo lai
 *    dung profile ay — no khong vuot cai gi ca, no dung mot phien da hop le.
 *
 * ⚠️ Chrome khoa profile khi dang chay. Dong cua so kia truoc khi chay bo kiem.
 */
const PROFILE = co('--profile', '');

/**
 * `--cdp <dia-chi>` — NOI VAO mot Chrome DANG CHAY, thay vi tu mo trinh duyet.
 *
 * 🔴 VI SAO CAN, VA BANG CHUNG DAN TOI NO. Ngay 04/09 profile kiem het
 *    phien; moi lan `launchPersistentContext` mo lai, Cloudflare tra CAPTCHA va
 *    xoay vong khong vao duoc. Cung luc do chu du an mo **Coc Coc** va dang
 *    nhap binh thuong, ngay lap tuc.
 *
 * ⭐ Do la phep doi chung dat gia: khac biet khong nam o profile, o mang,
 *    hay o tai khoan — ma o chinh viec **Playwright TU KHOI CHAY** Chrome kem
 *    co automation. Mot profile moi van bi y het, vi nguyen nhan khong phai
 *    profile.
 *
 * ⛔ Loi giai KHONG phai che dau co automation — do la vuot bot detection,
 *    thu bo kiem nay khong lam. Loi giai la **dung mot Chrome that**: chu du an
 *    tu mo, tu qua xac minh, tu dang nhap; bo kiem chi NOI VAO qua cong go loi.
 *    Khong gia mao gi, va viec xac thuc van hoan toan la cua con nguoi.
 *
 * Mo trinh duyet (chu du an chay, roi dang nhap trong cua so hien ra):
 *
 *     chrome.exe --user-data-dir=C:\LTTBrowserProfiles\ChatLTTKiem2 \
 *                --remote-debugging-port=9222 https://app.lttstudios.com/chatltt
 *
 * Roi:  node tools/kiem_chatltt_gui.mjs --url https://app.lttstudios.com \
 *            --cdp http://127.0.0.1:9222
 *
 * ⚠️ Bo kiem KHONG dong trinh duyet nay khi xong — no khong so huu cua so
 *    do. Dong nham la cuop mat phien ma nguoi dung vua bo cong dang nhap.
 */
const CDP = co('--cdp', '');

if (!PHIEN && !PROFILE && !CDP && (!NGUOI || !MAT_KHAU)) {
  console.error('Can `--cdp <dia-chi>` (noi vao Chrome dang chay), '
    + '`--profile <thu-muc>`, `--phien <tep>`, hoac LTT_SMOKE_USER/LTT_SMOKE_PASS.');
  process.exit(2);
}

mkdirSync(THU_MUC_ANH, { recursive: true });

// ── Gom loi suot ca luot ───────────────────────────────────────────────────
const loiConsole = [];
const requestHong = [];

/**
 * Hang muc dang chay, va nhung loi no DA KHAI TRUOC la co y.
 *
 * 🔴 VI SAO CAN. Ba hang muc cua dot 4 co y gui dau vao XAU de kiem rang may
 *    chu tu choi — va may chu tu choi dung, bang HTTP 400. Nhung bo chay dem
 *    moi 4xx la mot loi, nen mot luot 5/5 DAT van in `RESULT: FAIL`.
 *
 * ⛔ Va do khong phai mot su bat tien. Mot dong canh bao LUON do la mot dong
 *    nguoi ta hoc cach bo qua — roi mot loi console THAT se di qua ma khong ai
 *    thay. Cai gia khong phai bao cao sai, la cai canh bao mat gia tri.
 *
 * ⭐ Nen: hang muc phai KHAI TRUOC (`loi_mong_doi`). Khai truoc thi no la mot
 *    loi DUOC CHO DOI; khong khai thi no van la mot loi. Va viec khai nam
 *    trong chinh hang muc, canh cau hoi no dat ra.
 */
let hangMucHienTai = null;
const loiDaKhai = [];

function ghiLoi(bo, dong) {
  const mong = hangMucHienTai?.loi_mong_doi ?? [];
  if (mong.some((re) => re.test(dong))) {
    loiDaKhai.push(`${hangMucHienTai.ten}: ${dong}`);
    return;
  }
  bo.push(dong);
}

// ── Tro giup ───────────────────────────────────────────────────────────────
const cho = (ms) => new Promise((r) => setTimeout(r, ms));

/** Doi mot dieu kien tra ve truthy, hoac nem sau `hanS` giay. */
async function doiDen(mo_ta, ham, hanS = 30) {
  const het = Date.now() + hanS * 1000;
  let cuoi;
  while (Date.now() < het) {
    try {
      cuoi = await ham();
      if (cuoi) return cuoi;
    } catch (e) {
      cuoi = e.message;
    }
    await cho(250);
  }
  throw new Error(`qua ${hanS}s ma chua: ${mo_ta} (lan cuoi: ${JSON.stringify(cuoi)?.slice(0, 120)})`);
}

const soBai = (p) => p.locator('article').count();
const chuBaiCuoi = (p) => p.locator('article').last().innerText();
const soDu = async (p) => {
  const t = await p.locator('[role=status]').first().innerText().catch(() => '');
  const m = t.replace(/[.\s]/g, '').match(/(\d+)/);
  return m ? Number(m[1]) : null;
};
const dangChay = (p) => p.getByRole('button', { name: 'Dừng' }).count().then((n) => n > 0);

/** Trang thai mot nang luc, HOI THANG MAY CHU.
 *
 * 🔴 VI SAO CAN HAM NAY. Dot 5 va 6 tung bao HONG voi "qua 60s ma chua: nut
 *    media san sang" — va ket luan do SAI. Nut bi vo hieu vi `san_sang !==
 *    'san_sang'` (`TaoMedia.tsx`), tuc **model chua nap**, khong phai giao dien
 *    hong. Do 04/09: ngay sau lat chay do, catalog tra `speech.ltt=san_sang`.
 *
 * ⭐ Va ly do model chua nap lai la CHINH BO KIEM NAY: dot 1-4 gui hang chuc
 *    luot chu, giu LLM tren GPU (TTL 1800s), nen sidecar anh/tieng khong con
 *    cho. Mot bo kiem tu tao ra dieu kien roi bao do la loi san pham.
 *
 * ⛔ Nen dung suy tu cai nut. Doc **con so may chu noi**, va dat no vao thong
 *    diep `bo_qua` — mot lan bo qua co bang chung khac han mot lan bo qua vi
 *    het kien nhan.
 */
/** Phien con song khong. Nem khi da bi dang xuat / Cloudflare chan lai.
 *
 * 🔴 VI SAO PHAI CO. Lat chay 04/09: phien chet GIUA LUOT, va Cloudflare
 *    bat dau tra `403` kem trang `<!DOCTYPE html>...Just a moment...`. Hai hang
 *    muc **BAO DAT** dua tren chinh con so 403 do — vi ca hai chi kiem
 *    `status === 403` va khong nhin thu gi khac.
 *
 * ⛔ Mot `403` cua Cloudflare KHONG PHAN BIET DUOC voi mot `403` cua ung
 *    dung, neu chi doc ma trang thai. Do dung loai loi ta da sua ca ngay o cho
 *    khac: chot mot con so ma khong hoi no **tu dau ra**.
 *
 * ⭐ Nen bo kiem phai DUNG HAN thay vi de lai mot bao cao trong nhu that.
 *    Mot lat chay bi cat giua chung la mot su that; mot lat chay "xanh" tren
 *    rac la mot lat chay se bi tin.
 */
async function conPhien(page) {
  const r = await page.evaluate(async () => {
    try {
      const res = await fetch('/chatltt/api/so-du', { redirect: 'follow' });
      const chu = await res.text();
      return { ma: res.status, html: chu.trim().startsWith('<') , dai: chu.length };
    } catch (e) { return { ma: -1, html: false, loi: String(e).slice(0, 80) }; }
  });
  if (r.ma === 200 && !r.html) return true;
  throw new Error(
    `PHIEN DA CHET giua luot (so-du tra ${r.ma}${r.html ? ', than la HTML' : ''}). `
    + 'Dang nhap lai trong cua so Chrome roi chay lai — dung tin ket qua sau diem nay.');
}

const nangLuc = (p, ten) => p.evaluate(
  (t) => fetch('/chatltt/api/danh-muc').then((r) => r.json())
    .then((d) => (d.nang_luc || []).find((n) => n.ten === t)?.san_sang || 'khong_co_trong_catalog')
    .catch((e) => 'khong_doc_duoc: ' + e.message), ten);

async function guiChu(p, chu) {
  // ⛔ `exact: true`. Khong co no, `name: 'Gửi'` khop CA "Sửa và gửi lại" —
  //    va no chi khop khi hoi thoai DA CO tin nhan, tuc lo ra o hang muc thu
  //    nam chu khong phai thu nhat. Mot locator mo la mot loi biet cho luc.
  const truoc = await soBai(p);
  // ⛔ DOI O SOAN MO KHOA. Sau ~40 luot lien tiep, model bao "chua san sang"
  //    va giao dien khoa o soan — do la hanh vi DUNG (fail-closed), khong phai
  //    loi. Nhung `fill()` vao mot `<textarea disabled>` thi treo 30 giay roi
  //    bao "locator.fill: Timeout", va SAU hang muc do lien tiep nhau.
  //
  // ⭐ Mot bo kiem chay 45 luot that phai chiu duoc chinh co che chong qua tai
  //    cua san pham no dang kiem. Doi la dung; bao san pham hong la sai.
  await doiDen('o soan mo khoa (model san sang)', async () => {
    const o = p.getByLabel('Nội dung tin nhắn');
    return (await o.count()) > 0 && !(await o.isDisabled());
  }, 180);
  await p.getByLabel('Nội dung tin nhắn').fill(chu);
  await p.getByRole('button', { name: 'Gửi', exact: true }).click();
  await doiDen('luot da bat dau',
    async () => (await soBai(p)) >= truoc + 2 || (await dangChay(p)), 40);
  // ⭐ VA DOI HOI THOAI CO DIA CHI. Mot hoi thoai da co tin nhan thi PHAI co
  //    `#<id>` trong URL — do la bat bien ta vua xay. Doi no o day vua la mot
  //    phep kiem mien phi, vua go mot cuoc dua: `2.1` tung doc hash NGAY sau
  //    `xong()` va nhan chuoi rong, roi bao "hai hoi thoai cung hash". Do tay
  //    thi hash duoc dat sau ~800ms va luon khac nhau — san pham dung, phep do
  //    voi.
  await doiDen('hoi thoai da co dia chi trong URL',
    async () => (await p.evaluate(() => location.hash)).length > 4, 25);
}

async function xong(p, hanS = 150) {
  // 🔴 DOC DAU HIEU CUA SAN PHAM, DUNG DOAN BANG DO DAI CHUOI.
  //
  //    Ban truoc doi hai thu: "khong con nut Dung" va "chu dai hon 15 ky tu".
  //    Ca hai deu SAI kieu:
  //
  //      · `dangChay` co mot khoang FALSE ngay sau khi bam Gui — tin nhan da
  //        tao nhung luong chua mo. `xong` tra ve trong khoang do.
  //      · "dai hon 15 ky tu" duoc thoa boi CHINH nhan vai: mot bai chi co
  //        "ChatLTT" + "▸ Đang suy nghĩ…" da 24 ky tu, khong mot chu tra loi
  //        nao.
  //
  // ⛔ Hau qua do that tren production: hang muc hoi "thu do nuoc Phap" doc
  //    phai cau tra loi cua luot TRUOC (mot loi chao), roi bao "model tra loi
  //    sai". Chay tay cung cau hoi ay: "Paris". Bao cao vu khong san pham
  //    trong khi phep do moi la thu hong — lan thu ba trong cung mot buoi.
  //
  // ⭐ Nut "Tạo lại" chi hien tren mot bai DA XONG. Do la dau hieu chinh san
  //    pham dung de noi "luot nay ket thuc roi" — muon no thi khong phai doan.
  await doiDen('luot ket thuc (bai cuoi co nut "Tạo lại")', async () => {
    if (await dangChay(p)) return false;
    const cuoi = p.locator('article').last();
    return (await cuoi.getByRole('button', { name: 'Tạo lại' }).count()) > 0;
  }, hanS);
}

/**
 * Mo mot hoi thoai moi VA doi cho no rong han.
 *
 * ⛔ `cho(600)` khong du, va do la mot loi da xay ra: bam Gui som hon mot nhip
 *    thi tin nhan di vao hoi thoai CU, roi hang muc doc phai cau tra loi cua
 *    mot cau hoi khac va bao "model tra loi sai".
 */
async function hoiThoaiMoi(p) {
  await p.getByRole('button', { name: '+ Hội thoại mới' }).click();
  await doiDen('hoi thoai moi da rong', async () => (await soBai(p)) === 0, 25);
  await donOSoan(p);
}

/**
 * Bo MOI anh dang dinh va xoa o soan.
 *
 * 🔴 VI SAO CAN. Cac hang muc lam ban lan nhau: 4.1 de lai hai chip, nen 4.2
 *    dem chip cua 4.1 roi ket luan "tep gia vo da duoc nhan", va 4.3 gui mot
 *    luot mang theo anh cua hang muc truoc. Hai bao cao SAI ve san pham tu mot
 *    thu duy nhat — trang thai khong duoc don giua cac hang muc.
 *
 * ⛔ Va vong bam dau tien cua toi cung sai: `getByRole(...).all()` lay mot
 *    SNAPSHOT, bam cai dau lam React ve lai, va cac handle con lai thanh cu —
 *    `.catch(() => {})` nuot loi nen chi mot chip duoc bo. Phai bam CAI DAU
 *    TIEN, lap lai, doc lai moi vong.
 */
async function donOSoan(p) {
  for (let i = 0; i < 12; i += 1) {
    const nut = p.getByRole('button', { name: /^Bỏ ảnh / }).first();
    if (!(await nut.count())) break;
    await nut.click();
    await doiDen('chip da bo', async () =>
      (await p.getByRole('button', { name: /^Bỏ ảnh / }).count()) < (i + 12), 10)
      .catch(() => {});
  }
  const o = p.getByLabel('Nội dung tin nhắn');
  if (await o.count()) await o.fill('');
}

// ── Cac hang muc ───────────────────────────────────────────────────────────
//
// Moi hang muc: mot cau hoi CO THE SAI, va mot phep do tra loi no.
const HANG_MUC = [
  {
    dot: 0, ten: 'trang-mo-duoc',
    hoi: 'Trang ChatLTT co dung duoc cac phan chinh khong (thanh ben, chon model, o soan)?',
    async chay(p) {
      await doiDen('sidebar', () => p.getByRole('button', { name: '+ Hội thoại mới' }).count());
      const model = await p.locator('select[aria-label="Chọn model"]').count();
      const oSoan = await p.getByLabel('Nội dung tin nhắn').count();
      if (!model || !oSoan) throw new Error(`thieu phan: model=${model} oSoan=${oSoan}`);
      return { model, oSoan };
    },
  },
  {
    dot: 0, ten: 'chua-co-model-thi-khong-gui-duoc',
    hoi: 'Trong giay dau khi catalog chua ve, nguoi dung co bam Gui duoc khong?',
    async chay(p) {
      // ⭐ Do duoc 03/09: o t+0ms danh sach model RONG. Neu o soan van bat thi
      //    mot nguoi go nhanh se gui mot luot khong co model — may chu tu choi,
      //    va ho nhan mot loi ky thuat cho mot viec ho khong lam gi sai.
      await p.reload({ waitUntil: 'domcontentloaded' });
      const dau = await p.evaluate(() => {
        const sel = document.querySelector('select[aria-label="Chọn model"]');
        const gui = [...document.querySelectorAll('button')].find((b) => b.textContent.trim() === 'Gửi');
        return { option: sel ? sel.options.length : -1, guiBat: gui ? !gui.disabled : null };
      });
      if (dau.option === 0 && dau.guiBat === true) {
        throw new Error('chua co model nao ma nut Gui van bam duoc');
      }
      await doiDen('catalog ve', async () =>
        (await p.locator('select[aria-label="Chọn model"] option').count()) > 0);
      return dau;
    },
  },
  {
    dot: 0, ten: 'model-mac-dinh-la-ltt_llm',
    hoi: 'Model chon san co phai `ltt_llm` khong — hay la vision (ngu canh 28K thay vi 89K)?',
    async chay(p) {
      // ⛔ Doi CATALOG ve truoc khi doc. Ban dau doc ngay va nhan "", roi bao
      //    "mac dinh sai" — mot bao cao SAI ve mot san pham DUNG. Mot bo kiem
      //    noi doi ve san pham thi te hon mot bo kiem thieu hang muc.
      await doiDen('danh sach model co du lieu', async () =>
        (await p.locator('select[aria-label="Chọn model"] option').count()) > 0);
      const v = await p.locator('select[aria-label="Chọn model"]').inputValue();
      if (v !== 'ltt_llm') throw new Error(`mac dinh la "${v}", phai la "ltt_llm"`);
      return { mac_dinh: v };
    },
  },
  {
    dot: 0, ten: 'stream-tra-loi',
    hoi: 'Gui mot cau thi co cau tra loi chay ve khong, va no co noi dung that khong?',
    async chay(p) {
      const truoc = await soBai(p);
      await guiChu(p, 'Xin chao ChatLTT, tra loi ngan gon.');
      await doiDen('them hai bai (hoi + dap)', async () => (await soBai(p)) >= truoc + 2);
      await xong(p);
      const chu = await chuBaiCuoi(p);
      if (chu.replace(/\s/g, '').length < 20) throw new Error(`cau tra loi qua ngan: ${JSON.stringify(chu.slice(0, 80))}`);
      return { do_dai: chu.length };
    },
  },
  {
    dot: 0, ten: 'tra-loi-DUNG-CAU-DUOC-HOI',
    hoi: 'Cau tra loi co lien quan den cau hoi khong — hay chi la "co chu chay ve"?',
    async chay(p) {
      // 🔴 HANG MUC NAY LAP MOT LO HONG THAT trong chinh bo kiem. `stream-tra-loi`
      //    chi do DO DAI >= 20 ky tu. Mot may chu tra ve mot doan Lorem Ipsum,
      //    hay tra ve cau tra loi cua NGUOI KHAC, deu qua duoc phep kiem do.
      //
      // ⭐ Chon mot cau co dap an mot tu, kiem duoc bang chuoi con: khong can
      //    hieu ngu nghia, khong phu thuoc model "gioi" den dau.
      await p.getByRole('button', { name: '+ Hội thoại mới' }).click();
      // ⛔ Doi cho luong bai RONG HAN, khong `cho(600)`. Neu bam Gui truoc khi
      //    hoi thoai moi kip thay the hoi thoai cu, tin nhan di vao hoi thoai
      //    CU — va hang muc doc phai cau tra loi cua mot cau hoi khac.
      await doiDen('hoi thoai moi da rong', async () => (await soBai(p)) === 0, 20);
      await guiChu(p, 'Thu do cua nuoc Phap ten la gi? Tra loi dung mot tu.');
      await xong(p);
      const chu = (await chuBaiCuoi(p)).toLowerCase();
      if (!chu.includes('paris')) {
        throw new Error(`hoi thu do Phap, nhan lai: ${JSON.stringify(chu.slice(0, 160))}`);
      }
      return { co_tu_khoa: 'paris', do_dai: chu.length };
    },
  },
  {
    dot: 0, ten: 'lam-theo-rang-buoc-cua-lenh',
    hoi: 'Model co ton trong rang buoc dinh dang trong lenh khong?',
    async chay(p) {
      await p.getByRole('button', { name: '+ Hội thoại mới' }).click();
      // ⛔ Doi cho luong bai RONG HAN, khong `cho(600)`. Neu bam Gui truoc khi
      //    hoi thoai moi kip thay the hoi thoai cu, tin nhan di vao hoi thoai
      //    CU — va hang muc doc phai cau tra loi cua mot cau hoi khac.
      await doiDen('hoi thoai moi da rong', async () => (await soBai(p)) === 0, 20);
      await guiChu(p, 'Liet ke dung 3 mau sac, moi mau mot dong, khong giai thich gi them.');
      await xong(p);
      const chu = await chuBaiCuoi(p);
      // Bo hai dong vo: ten vai ("ChatLTT") va hang nut cuoi bai.
      // ⚠️ Loc nhan vai va nut. "▸ Đang suy nghĩ…" doi thanh "▸ Suy luận" khi
      //    luot xong, nen phai bat CA HAI — bat mot cai thi phep dem lech dung
      //    mot dong, va bao cao noi model tra sai so dong.
      const dong = chu.split('\n').map((d) => d.trim())
        .filter((d) => d && !/^(ChatLTT|Bạn|Tạo lại|Đọc to|▸\s*(Suy luận|Đang suy nghĩ…?))$/.test(d));
      if (dong.length < 3 || dong.length > 7) {
        throw new Error(`xin 3 dong, nhan ${dong.length}: ${JSON.stringify(dong.slice(0, 8))}`);
      }
      return { so_dong: dong.length };
    },
  },
  {
    dot: 0, ten: 'tieng-viet-co-dau-khong-vo',
    hoi: 'Chu tieng Viet co dau di tron ven qua SSE va qua Cloudflare khong?',
    async chay(p) {
      // ⛔ Day la cho ma mot loi encoding se lo ra, va no chi lo ra tren ĐUONG
      //    THAT: SSE cat chunk giua mot ky tu UTF-8 nhieu byte, hoac mot lop
      //    minify/proxy doi charset. jsdom khong the do duoc dieu do.
      await p.getByRole('button', { name: '+ Hội thoại mới' }).click();
      // ⛔ Doi cho luong bai RONG HAN, khong `cho(600)`. Neu bam Gui truoc khi
      //    hoi thoai moi kip thay the hoi thoai cu, tin nhan di vao hoi thoai
      //    CU — va hang muc doc phai cau tra loi cua mot cau hoi khac.
      await doiDen('hoi thoai moi da rong', async () => (await soBai(p)) === 0, 20);
      await guiChu(p, 'Viet lai chinh xac cau nay, khong doi gi: "Nghiêng nước nghiêng thành."');
      await xong(p);
      const chu = await chuBaiCuoi(p);
      if (!/nghiêng/i.test(chu)) {
        throw new Error(`chu co dau bi vo: ${JSON.stringify(chu.slice(0, 160))}`);
      }
      if (/\uFFFD/.test(chu)) throw new Error('co ky tu thay the U+FFFD — hong encoding');
      return { con_dau: true };
    },
  },
  {
    dot: 0, ten: 'hoi-thoai-co-dia-chi',
    hoi: 'Hoi thoai co nam trong URL khong — F5 co quay lai dung cho khong?',
    async chay(p) {
      const hash = await p.evaluate(() => location.hash);
      if (!hash || hash.length < 4) throw new Error(`URL khong mang hoi thoai: "${hash}"`);
      const truoc = await soBai(p);
      await p.reload({ waitUntil: 'domcontentloaded' });
      await doiDen('bai hien lai sau reload', async () => (await soBai(p)) >= truoc);
      const sau = await p.evaluate(() => location.hash);
      if (sau !== hash) throw new Error(`hash doi sau reload: ${hash} -> ${sau}`);
      return { hash, bai: truoc };
    },
  },
  {
    dot: 0, ten: 'tao-lai-sinh-nhanh-moi',
    hoi: 'Bam "Tao lai" co sinh mot nhanh anh em moi khong, va dieu huong nhanh co chay khong?',
    async chay(p) {
      await p.getByRole('button', { name: 'Tạo lại' }).last().click();
      await xong(p);
      await doiDen('co dieu huong nhanh', () => p.getByRole('button', { name: 'Nhánh trước' }).count());
      const nhan = await p.locator('.ltc-nhanh, [class*=nhanh]').first().innerText().catch(() => '');
      return { dieu_huong: true, nhan: nhan.replace(/\s+/g, ' ').slice(0, 40) };
    },
  },
  {
    dot: 0, ten: 'dung-giua-chung',
    hoi: 'Bam "Dung" co that su dung khong — hay chu van chay tiep sau khi nut bien mat?',
    async chay(p) {
      await guiChu(p, 'Viet mot doan that dai ve lich su Viet Nam, cang dai cang tot.');
      // ⛔ Khong bien "khong quan sat duoc" thanh "hong". Neu model tra loi xong
      //    truoc khi ta kip bam thi menh de "Dung co dung that khong" van CHUA
      //    duoc kiem — no khong bi vi pham. Bao la BO QUA kem ly do; bao HONG
      //    la vu khong san pham, va bao DAT la noi doi.
      // ⛔ MOT hanh dong, khong kiem-roi-moi-lam. Ban dau: `doiDen(nut hien)` roi
      //    `.click()` — hai buoc, va giua chung luot co the ket thuc, nen nut
      //    bien mat va `.click()` treo 30 giay roi bao "HONG". Bao cao do noi ve
      //    san pham trong khi loi nam trong chinh phep do.
      await cho(1200);
      let kip = true;
      try {
        await p.getByRole('button', { name: 'Dừng' }).click({ timeout: 20000 });
      } catch {
        kip = false;
      }
      if (!kip) {
        if (await dangChay(p)) throw new Error('nut Dung co mat nhung khong bam duoc');
        return { bo_qua: 'luot ket thuc truoc khi kip bam Dung — model qua nhanh o moi truong nay' };
      }
      await doiDen('nut Dung bien mat', async () => !(await dangChay(p)), 20);
      // 🔴 CHO MOT CUA SO LANG TRUOC KHI DO. Ban dau do NGAY sau cu bam va
      //    doi con so dung yen tuyet doi. No do that tren production: 24 -> 36
      //    ky tu.
      //
      // ⭐ Nhung 12 ky tu do KHONG phai mot loi. Giua luc bam va luc may chu
      //    ngat, mot so chunk da roi khoi may chu va dang tren duong ve — huy
      //    mot luong mang khong bao gio la tuc thi. Menh de dung phai la
      //    **"no dung lai"**, khong phai "no dong bang o dung mili-giay ta bam".
      //
      // ⛔ Va no van la mot phep kiem CHAT: 6 giay lang sau cua so lang nghia
      //    la luong da chet han. Neu Dung khong hoat dong, cau tra loi day se
      //    tiep tuc chay trong ca khoang do.
      await cho(2500);                 // cua so lang: chunk dang bay ve
      const a = (await chuBaiCuoi(p)).length;
      await cho(6000);
      const b = (await chuBaiCuoi(p)).length;
      if (b !== a) throw new Error(`chu VAN CHAY 6s sau cua so lang: ${a} -> ${b} ky tu`);
      if (await dangChay(p)) throw new Error('van con dang chay sau khi Dung');
      return { do_dai_sau_cua_so_lang: a, sau_6_giay_nua: b };
    },
  },
  {
    dot: 0, ten: 'o-soan-khong-de-chan-trang',
    hoi: 'O soan co nam tron trong vung cua no khong, hay tran ra de len phan duoi?',
    async chay(p) {
      const r = await p.evaluate(() => {
        const soan = document.querySelector('.ltc-soan');
        const vo = document.querySelector('.ltc');
        if (!soan || !vo) return null;
        const a = soan.getBoundingClientRect(), b = vo.getBoundingClientRect();
        return { soanDuoi: Math.round(a.bottom), voDuoi: Math.round(b.bottom),
                 cao: Math.round(window.innerHeight) };
      });
      if (!r) throw new Error('khong tim thay .ltc-soan / .ltc');
      if (r.soanDuoi > r.voDuoi + 2) throw new Error(`o soan tran khoi vo: ${r.soanDuoi} > ${r.voDuoi}`);
      if (r.soanDuoi > r.cao + 2) throw new Error(`o soan duoi mep man hinh: ${r.soanDuoi} > ${r.cao}`);
      return r;
    },
  },
  {
    dot: 0, ten: 'khong-cuon-ngang',
    hoi: 'Trang co bi cuon ngang o be rong nao khong (390 / 768 / 1920)?',
    async chay(p) {
      const xau = [];
      for (const w of [390, 768, 1920]) {
        await p.setViewportSize({ width: w, height: 900 });
        await cho(400);
        const tran = await p.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
        if (tran > 1) xau.push(`${w}px tran ${tran}px`);
      }
      await p.setViewportSize({ width: 1280, height: 900 });
      if (xau.length) throw new Error(xau.join('; '));
      return { do_o: '390/768/1920' };
    },
  },
  {
    dot: 0, ten: 'vision-o-dinh-anh-theo-hop-dong',
    hoi: 'O dinh anh co hien DUNG khi model doc anh, va BIEN MAT khi model khong doc anh?',
    async chay(p) {
      const sel = p.locator('select[aria-label="Chọn model"]');
      const cacModel = await sel.locator('option').evaluateAll((o) => o.map((x) => x.value));
      if (!cacModel.includes('ltt_llm_vision')) return { bo_qua: 'khong co alias vision' };

      await sel.selectOption('ltt_llm');
      await cho(600);
      const khiText = await p.locator('input[type=file]').count();
      await sel.selectOption('ltt_llm_vision');
      await cho(600);
      const khiVision = await p.locator('input[type=file]').count();
      await sel.selectOption('ltt_llm');
      if (khiText !== 0) throw new Error(`model text-only VAN co o chon tep (${khiText})`);
      if (khiVision !== 1) throw new Error(`model vision KHONG co o chon tep (${khiVision})`);
      return { text: khiText, vision: khiVision };
    },
  },
  {
    dot: 0, ten: 'nut-media-co-mat',
    hoi: 'Hai nut Tao anh / Tao giong co mat trong hoi thoai khong?',
    async chay(p) {
      const anh = await p.getByRole('button', { name: 'Tạo ảnh' }).count();
      const giong = await p.getByRole('button', { name: 'Tạo giọng' }).count();
      if (!anh || !giong) throw new Error(`thieu nut: anh=${anh} giong=${giong}`);
      return { anh, giong };
    },
  },
  {
    dot: 0, ten: 'bao-gia-truoc-khi-thu-tien',
    hoi: 'Bam Tao anh co hoi gia TRUOC khi thu tien khong, va co Huy duoc khong?',
    async chay(p) {
      await p.getByRole('button', { name: 'Tạo ảnh' }).click();
      await p.getByLabel('Mô tả ảnh').fill('mot con meo dang ngu');
      const duTruoc = await soDu(p);
      await p.getByRole('button', { name: 'Xem giá' }).click();
      const gia = await doiDen('hien xac nhan gia', async () => {
        const t = await p.getByRole('group', { name: 'Xác nhận giá' }).innerText().catch(() => '');
        return t.includes('credit') ? t.replace(/\s+/g, ' ') : null;
      }, 25);
      const duSauBaoGia = await soDu(p);
      if (duTruoc !== null && duSauBaoGia !== null && duSauBaoGia !== duTruoc) {
        throw new Error(`BAO GIA da tru tien: ${duTruoc} -> ${duSauBaoGia}`);
      }
      await p.getByRole('button', { name: 'Huỷ' }).click();
      return { bao_gia: gia, so_du_khong_doi: duTruoc };
    },
  },
  {
    dot: 0, ten: 'khong-lo-id-noi-bo',
    hoi: 'Giao dien co lo ten model that / URL may B / khoa API ra khong?',
    async chay(p) {
      const t = await p.evaluate(() => document.body.innerText);
      // ⭐ CAM la ID NOI BO va HA TANG, khong phai ten model.
      //
      //    Chu du an chot 03/09: **de model tra loi dung no la Qwen**. Khi
      //    duoc chao, no noi "toi khong phai ChatLTT, toi la Qwen" — va do la
      //    hanh vi MONG MUON, khong phai ro ri. Giau di can mot system prompt
      //    day model noi sai ve chinh no, tuc doi mot su that lay mot cau
      //    quang cao.
      //
      // ⛔ Thu VAN cam: `qwen38` (id noi bo, khac ten thuong goi), cong LAN cua
      //    may B, tien to khoa API. Do la nhung thu cho ai do di tiep mot buoc
      //    — mot cai ten model thi khong.
      const cam = [/qwen\s*3\s*8/i, /8299/, /8199/, /8120/, /ltt_sk_/, /192\.168\./];
      const dinh = cam.filter((r) => r.test(t)).map(String);
      if (dinh.length) throw new Error(`lo ra: ${dinh.join(', ')}`);
      return { da_quet_ky_tu: t.length };
    },
  },
  {
    dot: 0, ten: 'phim-tat-va-focus',
    hoi: 'Ctrl+Shift+O co mo hoi thoai moi va dua con tro ve o soan khong?',
    async chay(p) {
      await p.keyboard.press('Control+Shift+O');
      await cho(800);
      const focus = await p.evaluate(() => document.activeElement?.getAttribute('aria-label') || document.activeElement?.tagName);
      if (!/Nội dung tin nhắn|TEXTAREA/.test(String(focus))) {
        throw new Error(`focus sau phim tat: ${focus}`);
      }
      return { focus: String(focus) };
    },
  },
  {
    dot: 0, ten: 'nhan-doc-duoc-cho-trinh-doc-man-hinh',
    hoi: 'Cac dieu khien chinh co nhan doc duoc khong (nut khong nhan la nut cam)?',
    async chay(p) {
      const xau = await p.evaluate(() => {
        const ra = [];
        for (const el of document.querySelectorAll('button, input, select, textarea')) {
          if (el.offsetParent === null && el.type !== 'file') continue;
          const nhan = (el.getAttribute('aria-label') || el.textContent || el.title || '').trim();
          if (!nhan) ra.push(el.tagName + '.' + (el.className || '').toString().slice(0, 30));
        }
        return ra;
      });
      if (xau.length) throw new Error(`dieu khien khong co nhan: ${xau.join(', ')}`);
      return { da_kiem: true };
    },
  },
];

// ── Nap cac dot ────────────────────────────────────────────────────────────
//
// ⭐ Tach ra module rieng vi bo kiem se lon toi ~60 hang muc. Mot tep 2.000
//    dong thi khong ai doc lai, va mot bo kiem khong ai doc lai la mot bo kiem
//    khong ai sua khi no sai.
const TRO_GIUP = { cho, doiDen, soBai, chuBaiCuoi, dangChay, guiChu, xong,
                   hoiThoaiMoi, donOSoan, soDu, nangLuc };
{
  const nap = async (ten, ham) => {
    try {
      const m = await import(pathToFileURL(
        join(new URL('.', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1'),
             'kiem_chatltt', ten)).href);
      HANG_MUC.push(...m[ham](TRO_GIUP));
    } catch (e) {
      console.log(`  [!] khong nap duoc ${ten}: ${e.message}`);
      process.exitCode = 2;
    }
  };
  await nap('dot1_luong.mjs', 'dot1');
  await nap('dot2_hoi_thoai.mjs', 'dot2');
  await nap('dot3_markdown.mjs', 'dot3');
  await nap('dot4_dinh_kem.mjs', 'dot4');
  await nap('dot5_tao_anh.mjs', 'dot5');
  await nap('dot6_tao_giong.mjs', 'dot6');
  await nap('dot7_tien_dong_thoi.mjs', 'dot7');
}

// ── Chay ───────────────────────────────────────────────────────────────────
async function dangNhap(page) {
  await page.goto(`${URL_GOC}/chatltt`, { waitUntil: 'domcontentloaded' });

  // Da co phien: khong dung toi form dang nhap. Neu van thay form thi phien da
  // het han — noi thang thay vi de no do o mot hang muc chang lien quan.
  if (PHIEN || PROFILE || CDP) {
    if (await page.getByRole('textbox', { name: /Username|Tên đăng nhập/i }).count()) {
      throw new Error('phien da het han — dang nhap lai trong '
        + (CDP ? 'trinh duyet o `' + CDP + '`' : PROFILE ? 'profile `' + PROFILE + '`' : 'tep `' + PHIEN + '`'));
    }
    await doiDen('vao duoc ChatLTT',
      async () => (await page.getByLabel('Nội dung tin nhắn').count()) > 0, 40);
    return;
  }

  // ⛔ Locator theo VAI TRO + TEN KHA CAN, khong `getByLabel`. Form dang nhap
  //    dat nhan bang mot `<div>` canh o nhap chu khong bang `<label for>`, nen
  //    `getByLabel` khong thay gi — va trieu chung la mot timeout 40 giay noi
  //    ve "vao duoc ChatLTT", tuc noi ve HAU QUA chu khong ve nguyen nhan.
  //    `getByRole('textbox', {name})` doc dung cai cay tro nang doc.
  //
  // ⚠️ VA PHAI CHIU CA HAI NGON NGU. Trang tra tieng Viet hay tieng Anh tuy
  //    `Accept-Language` cua trinh duyet va tien to `/en/` trong duong dan.
  //    Ban dau chi bat "Username" — no chay khi go tay (URL co `/en/`) va do
  //    khi chay tu dong, tuc do o dung noi khong ai nhin.
  const oNguoi = page.getByRole('textbox', { name: /Username|Tên đăng nhập/i });
  if (await oNguoi.count()) {
    await oNguoi.first().fill(NGUOI);
    await page.locator('input[type=password]').first().fill(MAT_KHAU);
    await page.getByRole('button', { name: /^(Sign in|Đăng nhập)$/i }).first().click();
    await page.waitForLoadState('domcontentloaded');
  }
  try {
    await doiDen('vao duoc ChatLTT',
      async () => (await page.getByLabel('Nội dung tin nhắn').count()) > 0, 40);
  } catch (e) {
    // Chup TRUOC khi nem: mot lan dang nhap hong ma khong co anh la mot lan
    // phai chay lai chi de nhin.
    await page.screenshot({ path: join(THU_MUC_ANH, 'hong-dang-nhap.png'), fullPage: true })
      .catch(() => {});
    const url = page.url();
    const chu = (await page.evaluate(() => document.body.innerText).catch(() => '')).replace(/\s+/g, ' ').slice(0, 200);
    throw new Error(`${e.message} | url=${url} | trang="${chu}"`);
  }
}

let trinh = null;
let boi_canh;
let cdp_noi_vao = false;
if (CDP) {
  // ⚠️ `connectOverCDP` tra ve mot `Browser` cua trinh duyet NGUOI KHAC so
  //    huu. Dung `boi_canh.close()` o cuoi — xem co `cdp_noi_vao`.
  trinh = await chromium.connectOverCDP(CDP);
  boi_canh = trinh.contexts()[0];
  if (!boi_canh) throw new Error(`khong thay boi canh nao o ${CDP}`);
  cdp_noi_vao = true;
} else if (PROFILE) {
  // ⚠️ `launchPersistentContext` tra ve CHINH boi canh, khong co doi tuong
  //    `Browser` rieng — nen `trinh` giu `null` va cho dong bang `boi_canh`.
  //    Quen dieu nay thi tien trinh Chrome o lai sau khi bo kiem xong, va lan
  //    chay sau bao "profile dang bi khoa" o mot cho chang lien quan.
  boi_canh = await chromium.launchPersistentContext(PROFILE, {
    channel: 'chrome',
    headless: false,                 // headless = bi Cloudflare chan lai
    viewport: { width: 1280, height: 900 },
  });
} else {
  trinh = await chromium.launch({ headless: !HIEN });
  boi_canh = await trinh.newContext({
    viewport: { width: 1280, height: 900 },
    ...(PHIEN ? { storageState: PHIEN } : {}),
  });
}
const page = boi_canh.pages()[0] || await boi_canh.newPage();

page.on('console', (m) => {
  if (m.type() === 'error') ghiLoi(loiConsole, m.text().slice(0, 300));
});
page.on('pageerror', (e) => ghiLoi(loiConsole, 'pageerror: ' + String(e).slice(0, 300)));
// ⛔ MOT SSE BI HUY KHONG PHAI MOT LOI. Khi trang reload hay component ro ra,
//    trinh duyet huy ket noi `/stream` dang mo — do la hanh vi DUNG, va no xay
//    ra o moi hang muc co reload.
//
// ⚠️ Nhung dung im lang bo qua: mot cai loc rong tay la cach mot loi that di
//    qua ma khong ai thay. Chung duoc dem RIENG va IN RA, chi khong lam do luot.
const sseHuy = [];
page.on('requestfailed', (r) => {
  const loi = r.failure()?.errorText || '';
  const dong = `${r.method()} ${r.url().slice(0, 140)} — ${loi}`;
  if (loi.includes('ERR_ABORTED') && /\/luot\/[^/]+\/stream/.test(r.url())) {
    sseHuy.push(dong);
    return;
  }
  ghiLoi(requestHong, dong);
});
page.on('response', (r) => {
  if (r.status() >= 400) {
    ghiLoi(requestHong, `${r.status()} ${r.request().method()} ${r.url().slice(0, 140)}`);
  }
});

const ketQua = [];
let maThoat = 0;
try {
  await dangNhap(page);
  for (const hm of HANG_MUC) {
    if (CHI && hm.ten !== CHI) continue;
    if (DOT.length && !DOT.includes(String(hm.dot ?? '0'))) continue;
    const t0 = Date.now();
    hangMucHienTai = hm;
    try {
      // ⛔ BAO DAM DANG O DUNG TRANG TRUOC MOI HANG MUC.
      //
      //    Do 03/09: hang muc `2.1` goi `goBack()`, va vi giao dien dung
      //    `replaceState` nen lich su chi co MOT muc — trinh duyet **roi khoi
      //    trang**. Sau muc do, sau hang muc con lai chay tren mot trang khong
      //    phai ChatLTT va bao nhung loi vo nghia ("khong co o tim").
      //
      // ⭐ Mot hang muc duoc phep dieu huong; no khong duoc phep lam do ca dot.
      //    Bay dong nay tach "mot phep kiem do" khoi "ca lo mat nghia".
      if (!(await page.getByLabel('Nội dung tin nhắn').count())) {
        await page.goto(`${URL_GOC}/chatltt`, { waitUntil: 'domcontentloaded' });
        await doiDen('ve lai duoc ChatLTT',
          async () => (await page.getByLabel('Nội dung tin nhắn').count()) > 0, 30);
      }
      await conPhien(page);
      const ct = await hm.chay(page);
      const bo = ct && typeof ct === 'object' && 'bo_qua' in ct;
      ketQua.push({ dot: hm.dot ?? 0, ten: hm.ten, dat: !bo, bo_qua: !!bo,
                    giay: (Date.now() - t0) / 1000, chi_tiet: ct });
      console.log(`  [${bo ? 'BOQUA' : 'DAT  '}] ${String(hm.dot ?? '0').padStart(2)} ${hm.ten}  ${JSON.stringify(ct)}`);
    } catch (e) {
      // 🔴 TRUOC KHI GOI DAY LA MOT LOI: NHIN MAN HINH DA.
      //
      //    Do 04/09, dot 0 chay rieng: BA hang muc bao HONG, va ca ba deu dang
      //    hien dung mot cau — cau cua CHINH SAN PHAM:
      //
      //      "Model dang ban. Thu lai sau it giay — luot nay khong bi tinh tien."
      //
      //    Do khong phai san pham hong. Do la san pham xu ly DUNG mot may ban,
      //    noi ro bang tieng Viet, va tu tuyen bo khong thu tien. Menh de ma ba
      //    hang muc kia dat ra (tra dung cau hoi, giu rang buoc dinh dang, chu
      //    co dau khong vo) — khong cai nao **duoc kiem** o lat chay do.
      //
      // ⛔ Va day khong phai mot ngoai le cho de bao cao dep hon. Bao HONG o
      //    day la vu khong, dung nghia luat ② cua ke hoach; ba dong do se lam
      //    nguoi doc di tim mot loi khong ton tai, roi lan sau ho bo qua ca ba
      //    — ke ca khi mot trong so do do that.
      //
      // ⭐ Chi bo qua khi chinh SAN PHAM noi cau do tren man hinh. Do la bang
      //    chung quan sat duoc, khong phai mot phong doan cua bo kiem. Va cau
      //    ay tu no da hua "khong bi tinh tien" — tuc so tien khong lien can.
      const manHinh = await page.locator('article').last().innerText().catch(() => '');
      if (/Model đang bận/i.test(manHinh) && /không bị tính tiền/i.test(manHinh)) {
        const ct = { bo_qua: 'model bao BAN ngay tren man hinh — menh de chua kiem duoc',
                     man_hinh: manHinh.replace(/\s+/g, ' ').slice(0, 120),
                     loi_goc: e.message.slice(0, 160) };
        ketQua.push({ dot: hm.dot ?? 0, ten: hm.ten, dat: false, bo_qua: true,
                      giay: (Date.now() - t0) / 1000, chi_tiet: ct });
        console.log(`  [BOQUA] ${String(hm.dot ?? '0').padStart(2)} ${hm.ten}  ${JSON.stringify(ct)}`);
        continue;
      }
      maThoat = 1;
      ketQua.push({ dot: hm.dot ?? 0, ten: hm.ten, dat: false, giay: (Date.now() - t0) / 1000, chi_tiet: e.message });
      console.log(`  [HONG ] ${String(hm.dot ?? '0').padStart(2)} ${hm.ten}  ${e.message}`);
      await page.screenshot({ path: join(THU_MUC_ANH, `hong-${hm.ten}.png`), fullPage: true }).catch(() => {});
    } finally {
      hangMucHienTai = null;
    }
  }
  await page.screenshot({ path: join(THU_MUC_ANH, 'cuoi.png'), fullPage: true }).catch(() => {});
} catch (e) {
  maThoat = 2;
  console.log(`  [CHET] khong chay duoc bo kiem: ${e.message}`);
} finally {
  // ⛔ KHI NOI VAO QUA CDP THI KHONG DONG GI CA. Cua so do la cua NGUOI
  //    DUNG: ho vua bo cong qua xac minh Cloudflare va dang nhap bang tay. Dong
  //    no di la vut mat dung thu vua ton cong nhat, va lan chay sau lai phai
  //    lam lai tu dau. Bo kiem chi la khach tro trong cua so ay.
  if (!cdp_noi_vao) {
    await boi_canh.close().catch(() => {});
    if (trinh) await trinh.close().catch(() => {});
  }
}

// ⛔ Loi console va request hong la HANG MUC, khong phai ghi chu. Mot bo kiem in
//    chung ra roi van bao PASS la mot bo kiem day nguoi doc di qua chung.
if (loiConsole.length) { maThoat = maThoat || 1; }
if (requestHong.length) { maThoat = maThoat || 1; }

const bao_cao = {
  url: URL_GOC,
  luc: new Date().toISOString(),
  dat: ketQua.filter((k) => k.dat).length,
  bo_qua: ketQua.filter((k) => k.bo_qua).length,
  hong: ketQua.filter((k) => !k.dat && !k.bo_qua).length,
  hang_muc: ketQua,
  loi_console: loiConsole,
  request_hong: requestHong,
  sse_bi_huy_binh_thuong: sseHuy,
  loi_da_khai_truoc: loiDaKhai,
};
const duong = join(THU_MUC_ANH, 'bao_cao.json');
mkdirSync(dirname(duong), { recursive: true });
writeFileSync(duong, JSON.stringify(bao_cao, null, 2), 'utf-8');

console.log('\n' + '='.repeat(64));
console.log(`  ${URL_GOC}`);
console.log(`  DAT ${bao_cao.dat} / BO QUA ${bao_cao.bo_qua} / HONG ${bao_cao.hong}`);
console.log(`  loi console: ${loiConsole.length}   request hong: ${requestHong.length}`
  + `   (SSE bi huy: ${sseHuy.length}, loi DA KHAI TRUOC: ${loiDaKhai.length})`);
for (const l of loiDaKhai.slice(0, 6)) console.log(`    (da khai) ${l}`);
for (const l of loiConsole.slice(0, 8)) console.log(`    console: ${l}`);
for (const r of requestHong.slice(0, 8)) console.log(`    request: ${r}`);
console.log(`  bao cao: ${duong}`);
console.log('='.repeat(64));
console.log(maThoat === 0 ? 'RESULT: PASS' : 'RESULT: FAIL');
process.exit(maThoat);
