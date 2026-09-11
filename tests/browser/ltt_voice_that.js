// ltt_voice_that.js — MOT luong VI (preset) + MOT luong EN (giong ghi danh tu
// clip tieng Anh) qua cong giong THAT (khong phai `voice_mock_sidecar.py`).
//
//   playwright-cli run-code --filename=tests/browser/ltt_voice_that.js
//
// ⛔ CHI CHAY khi bien moi truong `LTT_VOICE_SIDECAR_TOKEN` DA duoc dat —
//    nguoi goi tu dat no (token that, tro toi may chu dang chay cong giong
//    THAT o cong that, khong phai `voice_mock_sidecar.py`). Tep nay KHONG bao
//    gio tu dat bien do va KHONG doc bat ky bi mat/secret nao — no chi HOI
//    `process.env.LTT_VOICE_SIDECAR_TOKEN` co mat khong. Vang mat -> in SKIP
//    va thoat 0 (khong phai loi, khong phai bo qua am tham — dong SKIP tu
//    khai ro ly do).
//
// ⭐ VI SAO KHONG PHAI TANG duy nhat. `ltt_voice_golden.js`/`ltt_voice_rc1.js`
//    chay tren mock — nhanh, khong can GPU, chay trong moi CI. Tep nay la
//    tang doi chung THAT: hai luong (VI + EN) chay dung engine that, xac
//    minh WAV tra ve la tieng THAT (khong mang dau van tay `ltt-voice-mock`)
//    va RIFF hop le — dieu ma tang mock KHONG the noi len duoc, vi no luon
//    tra tieng gia lap.
//
// ⛔ KHONG dung du lieu production khi CHUA duoc nguoi dung cho phep ro rang
//    (CLAUDE.md, muc "Global browser testing policy"). Tep nay chi mo khi
//    nguoi goi da tu dat token — no khong tu suy hay doan mot may chu nao.
//
// ⛔ CAU TRUC: cung khuon `ltt_voice_rc1.js` — `run-code --filename=` boc
//    NGUYEN VAN noi dung tep thanh `await (<noi dung>)(page)`, chi hop le
//    neu la MOT bieu thuc duy nhat. Moi khai bao (`SEL`, `kiemTrang`) nam BEN
//    TRONG than ham `async page => {...}` duoi day, khong con o top-level.
//
// ⛔ SANDBOX cua `run-code` KHONG co `process`/`Buffer`/`require` (xem xac
//    minh doc lap o `ltt_voice_rc1.js` va bao cao
//    .superpowers/sdd/2026-09-11-ltt-voice-rc1/tang1-e2e-report.md).
//      · Ba lan doc `process.env.*` duoi day dung mot shim CUC BO o dau than
//        ham (`const process = ... || { env: {} }`) — trong sandbox se luon
//        roi ve rong (tuc TOKEN vang mat -> SKIP, dung tinh an toan ban dau:
//        khong bao gio tu doan/tu bat mot cong that nao). Neu sau nay tep
//        nay duoc goi qua mot trinh chay Node khac CO `process` that (vd de
//        thuc su chay tang THAT voi token that), shim se dung dung
//        `process` do — khong mat hanh vi.
//      · Hai cho `buf.includes(Buffer.from('ltt-voice-mock'))` doi mot
//        Buffer that de dung lam gia tri tim — nhung `Buffer.prototype
//        .includes(value)` nhan THANG mot chuoi JS (khong can Buffer nao de
//        dung), nen doi thanh `buf.includes('ltt-voice-mock')`: cung phep
//        tim, cung ket qua, khong can goi `Buffer.from`.

async page => {
  // Local shim: xem chu thich sandbox o dau tep.
  const process = (typeof globalThis !== 'undefined' && globalThis.process) || { env: {} };

  const SEL = {
    ngonNguNut: (ma) => `[data-ngonngu="${ma}"]`,
    vanBan: '#lv-text',
    nutTao: '#lv-nut-tao',
    ketQuaXong: '#lv-kq-xong',
    taiWav: '#lv-tai',
  };

  /**
   * Cung khuon `kiemTrang` voi `ltt_voice_rc1.js` — 4 loai bat loi + danh sach
   * cho phep 400 theo tung buoc. Xem chu thich day du o `ltt_voice_rc1.js`.
   */
  function kiemTrang(page) {
    const vanDe = [];
    const choPhep = [];
    page.on('console', (m) => {
      if (m.type() !== 'error') return;
      // Cung khuon `ltt_voice_rc1.js`: loc dong "Failed to load resource:..."
      // (Chromium tu sinh cho response HTTP >=400) qua CUNG danh sach
      // `choPhep400()`, chi theo URL that bai (m.location().url) — khong
      // dung o tep nay (khong flow nao goi choPhep400 hay mong 400 qua
      // fetch trong trang) nhung giu dung mold de hai tep khong lech nhau.
      if (/^Failed to load resource:/.test(m.text())) {
        const locUrl = (m.location() && m.location().url) || '';
        if (locUrl && choPhep.some((sub) => locUrl.includes(sub))) return;
      }
      vanDe.push('console.error: ' + m.text());
    });
    page.on('pageerror', (e) => vanDe.push('pageerror: ' + e.message));
    page.on('requestfailed', (r) => {
      const tb = r.failure();
      vanDe.push('requestfailed: ' + r.url() + ' — ' + (tb ? tb.errorText : '?'));
    });
    page.on('response', (r) => {
      const st = r.status();
      if (st < 400) return;
      const u = r.url();
      if (choPhep.some((sub) => u.includes(sub))) return;
      vanDe.push(`response ${st}: ${u}`);
    });
    return {
      choPhep400(...chuoiCon) { choPhep.push(...chuoiCon); },
      // Xoa danh sach cho phep — dung GIUA hai luong doc lap trong CUNG mot
      // `page` de mot cho-phep cua luong truoc khong lay sang luong sau (cung
      // khuon `ltt_voice_rc1.js`).
      xoaCho() { choPhep.length = 0; },
      dat() { vanDe.length = 0; },
      khangDinh(nhan) {
        if (vanDe.length) throw new Error(`${nhan}: ${vanDe.length} van de — ${vanDe.join(' | ')}`);
      },
    };
  }

  if (!process.env.LTT_VOICE_SIDECAR_TOKEN) {
    console.log('SKIP ltt_voice_that.js — LTT_VOICE_SIDECAR_TOKEN chua duoc dat. '
      + 'Tep nay CHI chay khi nguoi goi tu tro toi mot may chu dang mo cong '
      + 'giong THAT va tu dat bien nay; khong tu doan, khong tu bat mot cong '
      + 'nao.');
    return;
  }

  // Cung quy uoc `LTT_QA_BASE_URL` voi `ltt_voice_rc1.js` — mac dinh may chu
  // E2E cach ly, nhung tep nay CHI co y nghia khi may chu do dang thuc su tro
  // `sidecar_client` toi cong giong THAT (nguoi goi tu cau hinh, xem
  // `apps/ltt_voice/sidecar_client.py`: `LTT_VOICE_SIDECAR_PORT`/`_TOKEN`).
  const BASE = process.env.LTT_QA_BASE_URL || 'http://127.0.0.1:8129';
  const kt = kiemTrang(page);

  await page.goto(BASE + '/ltt-voice');
  if (/\/login/.test(page.url())) {
    await page.getByRole('textbox', { name: 'Username' }).fill('voice-e2e@test.local');
    await page.getByRole('textbox', { name: 'Password' }).fill('khong-phai-mat-khau-that-12');
    await page.getByRole('button', { name: 'Sign in' }).click();
    await page.waitForLoadState('networkidle');
    await page.goto(BASE + '/ltt-voice');
  }
  kt.khangDinh('dang-nhap');
  kt.dat();

  async function taoVaCho(vanBan, { chonAdam = false } = {}) {
    kt.xoaCho();
    await page.goto(BASE + '/ltt-voice');
    kt.dat();
    if (chonAdam) await page.getByRole('radio', { name: /Adam/ }).first().check();
    await page.locator(SEL.vanBan).fill(vanBan);
    await page.locator(SEL.nutTao).click();
    // Cong giong THAT co the mat vai chuc giay — cho lau hon tang mock.
    await page.locator(SEL.ketQuaXong).waitFor({ state: 'visible', timeout: 120000 });
    const href = await page.locator(SEL.taiWav).getAttribute('href');
    if (!href || !href.includes('/ltt-voice/audio/'))
      throw new Error('link tai khong di qua /ltt-voice/audio/: ' + href);
    const res = await page.request.get(BASE + href);
    if (![200, 206].includes(res.status()))
      throw new Error('tai WAV -> HTTP ' + res.status());
    const buf = await res.body();
    if (!(buf[0] === 0x52 && buf[1] === 0x49 && buf[2] === 0x46 && buf[3] === 0x46))
      throw new Error('tep tai ve KHONG phai WAV (thieu RIFF)');
    // RAO: day la CONG THAT, KHONG duoc mang dau van tay gia lap — thay dau
    // do o day nghia la duong da vo tinh tro vao mock, sai tang. Tim thang
    // bang chuoi (khong can `Buffer.from` — xem chu thich sandbox o dau tep).
    if (buf.includes('ltt-voice-mock'))
      throw new Error('WAV mang dau van tay ltt-voice-mock — duong nay dang '
        + 'CHAY TREN MOCK, khong phai cong giong THAT');
    return buf;
  }

  // ── Luong 1 — VI (preset dung san) ─────────────────────────────────────────
  await taoVaCho('Đây là lượt kiểm tra tiếng Việt trên cổng giọng thật.',
    { chonAdam: true });
  kt.khangDinh('that-vi');
  kt.dat();

  // ── Luong 2 — EN (giong ghi danh tu MOT clip tieng Anh) ─────────────────────
  //
  // ⛔ Tep nay KHONG tu upload mot clip tieng Anh moi (moi lan chay se ghi
  //    danh mot giong that, ton dung luong that qua cong giong). Nguoi goi
  //    (co token that) chuan bi san MOT giong EN da ghi danh — cung khuon voi
  //    "tai khoan test do nguoi dung cung cap cho ung dung development" o
  //    CLAUDE.md — va dat ten no dung `LTT_VOICE_THAT_GIONG_EN` (rong = bo
  //    qua nhanh 2, chi luong VI o tren chay).
  const tenGiongEn = (process.env.LTT_VOICE_THAT_GIONG_EN || '').trim();
  if (!tenGiongEn) {
    console.log('SKIP luong EN cua ltt_voice_that.js — chua dat '
      + 'LTT_VOICE_THAT_GIONG_EN (ten mot giong EN da ghi danh san tren cong '
      + 'that). Luong VI o tren van la bang chung day du cho token hien co.');
    return;
  }
  kt.xoaCho();
  await page.goto(BASE + '/ltt-voice');
  kt.dat();
  await page.locator(SEL.ngonNguNut('en')).click();
  await page.getByRole('radio', { name: new RegExp(tenGiongEn) }).first().check();
  await page.locator(SEL.vanBan).fill(
    'This is an English test through the real voice engine.');
  await page.locator(SEL.nutTao).click();
  await page.locator(SEL.ketQuaXong).waitFor({ state: 'visible', timeout: 120000 });
  const hrefEn = await page.locator(SEL.taiWav).getAttribute('href');
  if (!hrefEn || !hrefEn.includes('/ltt-voice/audio/'))
    throw new Error('EN: link tai khong di qua /ltt-voice/audio/: ' + hrefEn);
  const resEn = await page.request.get(BASE + hrefEn);
  if (![200, 206].includes(resEn.status()))
    throw new Error('EN: tai WAV -> HTTP ' + resEn.status());
  const bufEn = await resEn.body();
  if (!(bufEn[0] === 0x52 && bufEn[1] === 0x49 && bufEn[2] === 0x46 && bufEn[3] === 0x46))
    throw new Error('EN: tep tai ve KHONG phai WAV (thieu RIFF)');
  if (bufEn.includes('ltt-voice-mock'))
    throw new Error('EN: WAV mang dau van tay ltt-voice-mock — sai tang');
  kt.khangDinh('that-en');

  console.log('THAT OK — luong VI (preset) + luong EN (giong ghi danh) qua '
    + 'cong giong THAT, 0 loi console/pageerror/requestfailed/HTTP>=400.');
}
