// ltt_voice_rc1.js — cac LUONG RC1 cua LTT Voice trong trinh duyet that (spec
// Sec9, task-15-brief.md).
//
//   playwright-cli run-code --filename=tests/browser/ltt_voice_rc1.js
//
// Doi may chu E2E CACH LY dang chay (mac dinh 127.0.0.1:8129), cung khuon
// `ltt_voice_golden.js`/`ltt_voice_negative.js`/`ltt_voice_smoke.js`:
//   python tools\voice_mock_sidecar.py --cong 8131 --token mock-token
//   python tools\voice_e2e_server.py   --cong 8129 --mock-cong 8131
//
// `voice_e2e_server.py` (ham `_seed_rc1`, Task 15) seed THEM bon manh du lieu
// rieng cho cac luong duoi day: giong LEGACY + giong DO_ASR (D004), giong KHO
// CHUNG co san mot tep nghe thu THAT (T-08), va mot luot Lich su DA CO TIENG
// gan vao khoi thu ba cua du an `prj_e2e_0001` (D005).
//
// ⛔ SIMULATED INFERENCE tang CI — xem dau tich o dau `ltt_voice_golden.js`.
//
// ⛔ CAU TRUC: `run-code --filename=` boc NGUYEN VAN noi dung tep thanh
//    `await (<noi dung>)(page)` — chi hop le neu noi dung la MOT bieu thuc
//    duy nhat (`async page => {...}`). Vi vay MOI khai bao (`SEL`,
//    `KHUNG_HINH`, `TRANG_CHINH`, `kiemTrang`) nam BEN TRONG than ham duoi
//    day, khong con o cap top-level nhu ban truoc (ban truoc gay
//    `SyntaxError: Unexpected token 'const'` — xem
//    .superpowers/sdd/2026-09-11-ltt-voice-rc1/tang1-e2e-report.md §5.1).
//
// ⛔ SANDBOX cua `run-code` KHONG co `process`/`Buffer`/`require` (do doc lap
//    bang `typeof` — thay `undefined` ca ba). Hai cho tung dua vao chung:
//      · BASE/co tang-2 dua vao `process.env` — dung mot shim CUC BO
//        (`const process = ... || { env: {} }`) o dau than ham: KHONG throw
//        trong sandbox (roi ve mac dinh loopback, dung y het 3 tep kia), va
//        van dung dung `process` THAT neu sau nay tep nay duoc goi qua mot
//        trinh chay Node khac co `process`.
//      · D003 dung tao mot Buffer that cho `multipart.tep` (Playwright doi
//        `Buffer.isBuffer(...)`, tu choi Uint8Array — xem
//        playwright-core `client/fetch.ts`). Thay vi `page.request.post`
//        (phia Node), goi qua `fetch` NGAY TRONG TRANG (`page.evaluate`) voi
//        `FormData`/`Blob`/`TextEncoder` — deu la API trinh duyet that,
//        khong can Buffer nao. Cung URL, cung truong, cung noi dung tep gia.
//
// ⛔ D005 dung mot window.confirm() THAT (goi tu voice.js). `run-code` co mot
//    loi rieng: no tu bao "does not handle the modal state" NGAY CA KHI
//    `page.once('dialog', ...)` cua kich ban da xu ly xong dialog do (xac
//    minh doc lap: `dialog-accept` sau do bao "already handled" — dialog DA
//    duoc chap nhan, nhung `run-code` van bao loi va cat ket qua). Day la loi
//    CUA CHINH `run-code`, ngoai pham vi sua (khong phai tep nay, khong phai
//    ung dung). De tranh no MA VAN giu dung y nghia phep kiem (doc noi dung
//    hop xac nhan roi coi nhu khach bam "OK"), ghi de `window.confirm` NGAY
//    TRONG TRANG truoc khi bam — khong con hop dialog GOC nao cua trinh
//    duyet duoc mo nua, nen `run-code` khong con gi de nham.
//
// MOT SELECTOR MAP DUY NHAT (`SEL`) o dau than ham duoi day cho luong D002
// (Studio): Task 11 (mot phien KHAC, cung cay worktree) dang doi giao dien
// Studio CUNG LUC voi task nay. Danh sach "selector co the phai sua sau khi
// Task 11 hop nhat" o cuoi tep va o dong report.

async page => {
  // Local shim: sandbox khong co `process` (xem chu thich dau tep). Dinh
  // nghia CUC BO thay vi doc global truc tiep — tranh ReferenceError trong
  // sandbox, va van dung dung `process` THAT o mot trinh chay khac co no.
  const process = (typeof globalThis !== 'undefined' && globalThis.process) || { env: {} };

  const SEL = {
    // ── Studio (D002) — CO THE DOI khi Task 11 hop nhat ──────────────────────
    ngonNguNut: (ma) => `[data-ngonngu="${ma}"]`,      // nut chon Tu dong/VI/EN
    ngonNguAn: '#lv-ngon-ngu',                          // input an giu gia tri
    vanBan: '#lv-text',                                 // textarea kich ban
    nutTao: '#lv-nut-tao',                              // nut "Tao"
    ketQuaLoi: '#lv-kq-loi',                            // hop loi sau khi nop
    // ── Lich su (D005) — on dinh ──────────────────────────────────────────────
    dongLichSu: '.lv-ls-dong',
    nutXoaLichSu: '.lv-ls-xoa',
  };

  //: 6 khung hinh bat buoc (spec Sec9) — desktop pho bien + mobile/tablet.
  const KHUNG_HINH = [[1280, 720], [1366, 768], [1440, 900], [1920, 1080],
                      [390, 844], [768, 1024]];

  //: 4 man chinh cua Voice phai khong tran ngang o moi khung hinh.
  const TRANG_CHINH = ['/ltt-voice', '/ltt-voice/giong', '/ltt-voice/du-an',
                       '/ltt-voice/lich-su'];

  /**
   * RAO chong-xanh-gia dung chung cho ca tep: thu console.error, pageerror,
   * requestfailed, va MOI response HTTP >= 400 KHONG nam trong danh sach cho
   * phep cua buoc dang chay (`choPhep400`). Cung khuon `kiemTrang` ma
   * `check_voice_qa.py` (`G-BROWSER-GUARD`) doi thay o bon tep flow.
   */
  function kiemTrang(page) {
    const vanDe = [];
    const choPhep = [];      // mang chuoi con — mot response >=400 duoc THA neu
                              // url chua BAT KY chuoi nao trong day.
    page.on('console', (m) => {
      if (m.type() !== 'error') return;
      // "Failed to load resource: ..." la dong Chromium TU BAO cho MOI
      // response HTTP >=400 tren mang cua trang (khong phai loi ung dung) —
      // xay ra vi LUONG 1/D003 goi multipart qua `fetch` NGAY TRONG TRANG
      // (xem chu thich sandbox o dau tep), khac ban cu dung `page.request`
      // (khong qua network cua trang nen khong sinh dong nay). Dung CUNG
      // danh sach `choPhep400()` nhu 'response' de mot buoc TU BIET no se
      // nhan 400 khong bi bao trung — nhung CHI cho DUNG mau dong nay, va
      // CHI khi URL that bai (`m.location().url` — Chromium khong nhung URL
      // vao chinh van ban loi) khop mot chuoi da cho phep; moi console.error
      // khac (loi ung dung that) van bi bao NHU CU.
      if (/^Failed to load resource:/.test(m.text())) {
        const locUrl = (m.location() && m.location().url) || '';
        if (locUrl && choPhep.some((sub) => locUrl.includes(sub))) return;
      }
      vanDe.push('console.error: ' + m.text());
    });
    page.on('pageerror', (e) => {
      vanDe.push('pageerror: ' + e.message);
    });
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
      // Mot buoc TU BIET no se nhan mot ca 400/404 hop le (vd POST /giong/tao
      // thieu ngon_ngu) goi cai nay TRUOC khi kich hoat buoc do.
      choPhep400(...chuoiCon) { choPhep.push(...chuoiCon); },
      // Xoa danh sach cho phep + van de da ghi — dung GIUA hai luong doc lap
      // trong CUNG mot `page` de loi cua luong truoc khong lay sang luong sau.
      xoaCho() { choPhep.length = 0; },
      dat() { vanDe.length = 0; },
      khangDinh(nhan) {
        if (vanDe.length) {
          throw new Error(`${nhan}: ${vanDe.length} van de — ${vanDe.join(' | ')}`);
        }
      },
    };
  }

  // Mac dinh may chu E2E CACH LY (voice_e2e_server.py). `LTT_QA_BASE_URL` mo
  // mot tang-2 (tier-2) TRO TOI MOT DICH KHAC do nguoi chay tu dat qua env —
  // KHONG bao gio ghim mot URL production thang vao tep nay (xem
  // `check_voice_qa.py`, rao G-BROWSER-GUARD "tro toi PRODUCTION").
  const BASE = process.env.LTT_QA_BASE_URL || 'http://127.0.0.1:8129';
  const kt = kiemTrang(page);

  // TANG-2: du lieu seed (_seed_rc1) va buoc XOA that su (D005) CHI an toan
  // tren may chu E2E loopback — LTT_QA_BASE_URL co the tro toi MOT DICH KHAC
  // (nguoi goi tu dat). `LA_LOOPBACK` phat hien dieu do; `CHO_XOA_TANG2` la
  // canh mo THEM cho mot dong do CHINH luot chay nay tu tao duoi tai khoan
  // test — KHONG bao gio bat mot buoc XOA chi vi co bien nay ma khong co
  // dong do luot nay tu tao (xem LUONG 4 duoi day).
  const LA_LOOPBACK = /^https?:\/\/(127\.0\.0\.1|localhost)(:|\/|$)/.test(BASE);
  const CHO_XOA_TANG2 = process.env.LTT_QA_CHO_XOA === '1';

  // ── Dang nhap MOT LAN (tai khoan E2E dung mot lan) ─────────────────────────
  // Dang nhap TRUOC khi dat cookie ngon ngu (duoi day) — cung khuon dang nhap
  // EN nhu `ltt_voice_smoke.js`/`ltt_voice_golden.js`/`ltt_voice_negative.js`
  // (nhan `Username`/`Password`/`Sign in` gia dinh giao dien tieng Anh mac
  // dinh cua trinh duyet `playwright-cli`; dat cookie VI truoc buoc nay se
  // doi han ca man dang nhap sang tieng Viet va lam ba nhan do khong khop).
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

  // ⚠️ DO THAT: trinh duyet cua `playwright-cli` gui `Accept-Language: en-...`
  //    mac dinh, va `server/i18n_middleware.py` coi day la mot TIN HIEU that
  //    (giong het mot khach that co trinh duyet tieng Anh) — 302 sang
  //    `/en/...`. LUONG 2 (D004) khang dinh CHU tieng Viet cua giao dien
  //    ("Xác nhận ngôn ngữ...", "Đổi ngôn ngữ", "Đo từ clip"), nen se that bai
  //    kieu "khong thay chu" neu chay duoi UI tieng Anh — KHONG phai loi ung
  //    dung, chi la moi truong trinh duyet khong noi tieng Viet. Sua bang
  //    cach dat cookie `ltt_lang=vi` NGAY SAU KHI dang nhap xong — dung cookie
  //    ma `platform_core/i18n.py::chon()` doc (uu tien TREN accept-language),
  //    y het mot khach that da tung chon VI mot lan. Khong dung tien to URL
  //    vi `/ltt-voice` (khong tien to) da la duong GOC=VI theo thiet ke.
  await page.context().addCookies([{ name: 'ltt_lang', value: 'vi', url: BASE }]);

  // ⛔ DON DEP: `smoke.js`/`golden.js`/`negative.js` co the chay TRUOC hoac
  // SAU tep nay trong CUNG mot phien trinh duyet (cookie/dang nhap giu
  // nguyen giua cac lenh `run-code` — dung khuon tai lieu dau moi tep). Cookie
  // `ltt_lang=vi` o tren se RO SANG cac tep do neu khong don, va lam gay gia
  // dinh UI tieng Anh cua chung (vd golden.js doi tieu de "Generate speech").
  // `try/finally` dam bao xoa TOAN BO cookie (ke ca khi mot LUONG nem loi ben
  // duoi) — dang xuat tam thoi la vo hai vi ca ba tep kia tu dang nhap lai
  // neu bi day ve `/login`.
  try {
  // ═══════════════════════════════════════════════════════════════════════
  // KHUNG HINH — 6 khung hinh x 4 man chinh, khong duoc tran ngang.
  // ═══════════════════════════════════════════════════════════════════════
  for (const [w, h] of KHUNG_HINH) {
    await page.setViewportSize({ width: w, height: h });
    for (const duong of TRANG_CHINH) {
      await page.goto(BASE + duong);
      const tran = await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth + 1);
      if (!tran) {
        throw new Error(`TRAN NGANG tai ${duong} o ${w}x${h} `
          + `(scrollWidth > innerWidth)`);
      }
    }
  }
  await page.setViewportSize({ width: 1366, height: 900 });
  kt.khangDinh('khung-hinh-6x4');
  kt.dat();

  // ═══════════════════════════════════════════════════════════════════════
  // LUONG 1 — D003: ghi danh KHONG khai lan bi chan; ghi danh EN -> the hien
  // dung lan EN.
  // ═══════════════════════════════════════════════════════════════════════
  {
    kt.xoaCho();
    await page.goto(BASE + '/ltt-voice/giong');
    kt.dat();

    // 1a. KHONG khai lan (`ngon_ngu` rong) -> 400 `voice_language_required`,
    //     KHONG job nao duoc nop. Di THANG qua server (giong khuon
    //     `ltt_voice_negative.js`) vi <select required> chan native truoc
    //     khi JS kip nem — bai hoc D003 la ve CUA SERVER, khong ve HTML5.
    const csrf = await page.getAttribute('#lv-form-giong input[name="csrf_token"]', 'value');
    if (!csrf) throw new Error('D003: khong lay duoc csrf tu form ghi danh');

    // Goi POST multipart NGAY TRONG TRANG qua `fetch`/`FormData`/`Blob` (xem
    // chu thich sandbox o dau tep) — khac ban cu dung `page.request.post`
    // (Node context, doi mot Buffer that) nen khong can `Buffer`.
    //
    // ⚠️ Tep gia CU chi la chuoi ASCII "RIFF0000WAVEfmt " (16 byte) — DO
    //    THAT hom nay lo no chua bao gio la mot WAV hop le (khong co chunk
    //    `data`, "0000" la bon ky tu ASCII chu khong phai truong kich thuoc
    //    little-endian). Ban cu bi chan o loi Buffer TRUOC KHI kip cham toi
    //    server (xem §5.2 bao cao), nen khong ai thay noi dung gia nay tung
    //    that bai kiem tra o `apps/ltt_voice/audio_input.py::kiem` (`wave`
    //    module Python: "Tệp WAV hỏng hoặc không phải PCM.", 400) — do that
    //    truc tiep bang chinh chuoi cu: server tra 400 ke ca cho luong 1b
    //    (ky vong 200). Day la mot LO HONG DU LIEU KIEM THU co san (khong
    //    phai san pham, khong phai do cau truc lai tep nay) — sua bang mot
    //    WAV PCM 16-bit that (>= 3.0s theo `GIAY_TOI_THIEU`), dung
    //    `DataView` (khong can `Buffer`).
    const taoWavThat = () => {
      const sr = 16000, giay = 3.2, bienDo = 0.3, tanSo = 220;
      const soMau = Math.floor(sr * giay);
      const bytes = new Uint8Array(44 + soMau * 2);
      const dv = new DataView(bytes.buffer);
      const ghiChuoi = (off, s) => { for (let i = 0; i < s.length; i++) bytes[off + i] = s.charCodeAt(i); };
      ghiChuoi(0, 'RIFF');
      dv.setUint32(4, 36 + soMau * 2, true);
      ghiChuoi(8, 'WAVE');
      ghiChuoi(12, 'fmt ');
      dv.setUint32(16, 16, true);        // kich thuoc chunk fmt (PCM)
      dv.setUint16(20, 1, true);         // format PCM
      dv.setUint16(22, 1, true);         // 1 kenh (mono)
      dv.setUint32(24, sr, true);        // sample rate
      dv.setUint32(28, sr * 2, true);    // byte rate (sr * block-align)
      dv.setUint16(32, 2, true);         // block align (16-bit mono)
      dv.setUint16(34, 16, true);        // bit/mau
      ghiChuoi(36, 'data');
      dv.setUint32(40, soMau * 2, true);
      for (let i = 0; i < soMau; i++) {
        const v = Math.sin((2 * Math.PI * tanSo * i) / sr) * bienDo * 32767;
        dv.setInt16(44 + i * 2, v, true);
      }
      return bytes;
    };

    const guiGhiDanh = (fields) => page.evaluate(async ({ url, fields, wavArr }) => {
      const fd = new FormData();
      for (const [k, v] of Object.entries(fields)) fd.append(k, v);
      fd.append('tep', new Blob([new Uint8Array(wavArr)], { type: 'audio/wav' }), 'clip.wav');
      const res = await fetch(url, { method: 'POST', body: fd });
      const text = await res.text();
      let json = null;
      try { json = JSON.parse(text); } catch (e) { /* giu json = null */ }
      return { status: res.status, json, text };
    }, { url: BASE + '/ltt-voice/giong/tao', fields, wavArr: Array.from(taoWavThat()) });

    kt.choPhep400('/ltt-voice/giong/tao');
    const r1 = await guiGhiDanh({
      csrf_token: csrf, ten: 'RC1 khong khai lan', dong_y: '1', ngon_ngu: '',
    });
    if (r1.status !== 400)
      throw new Error(`D003: khong khai lan mong 400, nhan ${r1.status} — CUA MO`);
    if (!r1.json || r1.json.ok !== false || r1.json.ma_loi !== 'voice_language_required')
      throw new Error(`D003: ma_loi sai — mong voice_language_required, nhan ${r1.text}`);

    // Khong co giong "RC1 khong khai lan" nao duoc tao — kiem lai qua trang.
    await page.reload();
    kt.khangDinh('D003-khong-khai-lan (sau kiem 400)');
    kt.dat();
    if (await page.getByText('RC1 khong khai lan').first().isVisible().catch(() => false))
      throw new Error('D003: mot giong DA duoc tao du khong khai lan — cua van mo');

    // 1b. Ghi danh HOP LE voi ngon_ngu=en -> the giong moi hien dung lan EN.
    const tenGiongMoi = 'RC1 ghi danh EN ' + Date.now();
    const r2 = await guiGhiDanh({
      csrf_token: csrf, ten: tenGiongMoi, dong_y: '1', ngon_ngu: 'en',
    });
    if (r2.status !== 200)
      throw new Error(`D003: ghi danh EN hop le mong 200, nhan ${r2.status}`);
    if (!r2.json || !r2.json.ok || !r2.json.voice_id)
      throw new Error('D003: ghi danh EN hop le khong tra ok+voice_id: ' + r2.text);

    await page.reload();
    kt.khangDinh('D003-ghi-danh-en');
    kt.dat();
    // The moi (`ngon_ngu_nguon=khai_bao` ngay tu luc tao) phai hien khu vuc
    // "Doi ngon ngu" (khong phai "Xac nhan…", vi khong phai dong `mac_dinh_cu`)
    // voi <option value="en" selected>.
    const theEn = page.locator(`article[data-ma="${r2.json.voice_id}"]`);
    await theEn.waitFor({ state: 'attached', timeout: 15000 });
    const giaTriLan = await theEn.locator('select[name="ngon_ngu"]').inputValue();
    if (giaTriLan !== 'en')
      throw new Error(`D003: the giong moi hien lan "${giaTriLan}", mong "en"`);
  }

  // ═══════════════════════════════════════════════════════════════════════
  // LUONG 2 — D004: giong LEGACY (mac_dinh_cu) hien "Xac nhan ngon ngu" va
  // xac nhan hoat dong; giong DO_ASR khong hien form doi.
  // ═══════════════════════════════════════════════════════════════════════
  {
    kt.xoaCho();
    if (!LA_LOOPBACK) {
      console.log('SKIP LUONG 2 (D004) — du lieu seed (_seed_rc1: giong LEGACY + DO_ASR) chi ton tai tren may chu E2E loopback; LTT_QA_BASE_URL dang tro toi mot dich khac (tang-2).');
    } else {
      await page.goto(BASE + '/ltt-voice/giong');
      kt.dat();

      // 2a. Giong LEGACY (seed `vce_e2e_legacy_vi`, D004).
      const theLegacy = page.locator('article[data-ma="vce_e2e_legacy_vi"]');
      await theLegacy.waitFor({ state: 'attached', timeout: 15000 });
      const coXacNhan = await theLegacy.getByText('Xác nhận ngôn ngữ của giọng này')
        .isVisible().catch(() => false);
      if (!coXacNhan)
        throw new Error('D004: giong LEGACY (mac_dinh_cu) khong hien "Xac nhan ngon ngu"');

      const csrfXn = await theLegacy.locator('input[name="csrf_token"]').getAttribute('value');
      const r3 = await page.request.post(
        BASE + `/ltt-voice/giong/vce_e2e_legacy_vi/ngon-ngu`,
        { form: { csrf_token: csrfXn, ngon_ngu: 'vi' },
          headers: { Accept: 'application/json' } });
      if (r3.status() !== 200)
        throw new Error(`D004: xac nhan giong LEGACY mong 200, nhan ${r3.status()}`);
      const b3 = await r3.json();
      if (!b3.ok || b3.ngon_ngu !== 'vi')
        throw new Error('D004: xac nhan giong LEGACY khong tra ok+ngon_ngu=vi: ' + JSON.stringify(b3));

      await page.reload();
      kt.khangDinh('D004-legacy');
      kt.dat();
      // Sau xac nhan, nguon thanh `khai_bao` — the phai doi sang "Doi ngon ngu",
      // KHONG con "Xac nhan…" nua.
      const theLegacy2 = page.locator('article[data-ma="vce_e2e_legacy_vi"]');
      if (await theLegacy2.getByText('Xác nhận ngôn ngữ của giọng này').isVisible().catch(() => false))
        throw new Error('D004: giong LEGACY VAN hien "Xac nhan…" sau khi da xac nhan');
      if (!(await theLegacy2.getByText('Đổi ngôn ngữ').isVisible().catch(() => false)))
        throw new Error('D004: giong LEGACY khong chuyen sang "Doi ngon ngu" sau xac nhan');

      // 2b. Giong DO_ASR (seed `vce_e2e_do_asr_en`, D004) — KHONG co form doi.
      const theAsr = page.locator('article[data-ma="vce_e2e_do_asr_en"]');
      await theAsr.waitFor({ state: 'attached', timeout: 15000 });
      if (await theAsr.locator('form[action*="/ngon-ngu"]').count() > 0)
        throw new Error('D004: giong DO_ASR hien mot FORM doi lan — phai KHONG co cua bam nao');
      if (!(await theAsr.getByText('Đo từ clip').isVisible().catch(() => false)))
        throw new Error('D004: giong DO_ASR khong hien nhan "Do tu clip"');

      // Va server van CHAN neu ai co tinh POST doi lan nguoc voi phep do
      // (`voice_language_measured`) — xac nhan cua chan that su ton tai, khong
      // chi la thieu mot form tren giao dien.
      const csrfAsr = await theLegacy2.locator('input[name="csrf_token"]').getAttribute('value')
        || (await page.getAttribute('#lv-form-giong input[name="csrf_token"]', 'value'));
      kt.choPhep400(`/ltt-voice/giong/vce_e2e_do_asr_en/ngon-ngu`);
      const r4 = await page.request.post(
        BASE + `/ltt-voice/giong/vce_e2e_do_asr_en/ngon-ngu`,
        { form: { csrf_token: csrfAsr, ngon_ngu: 'vi' },
          headers: { Accept: 'application/json' } });
      if (r4.status() !== 400)
        throw new Error(`D004: doi lan nguoc PHEP DO mong 400, nhan ${r4.status()}`);
      const b4 = await r4.json();
      if (b4.ma_loi !== 'voice_language_measured')
        throw new Error('D004: ma_loi sai cho doi nguoc PHEP DO: ' + JSON.stringify(b4));
    }
  }

  // ═══════════════════════════════════════════════════════════════════════
  // LUONG 3 — T-08: nut nghe thu cua giong KHO CHUNG tra 200 cho KHACH
  // KHONG PHAI CHU (seed `vce_e2e_kho_chung`, chu la mot tai khoan gia khac).
  // ═══════════════════════════════════════════════════════════════════════
  {
    kt.xoaCho();
    if (!LA_LOOPBACK) {
      console.log('SKIP LUONG 3 (T-08) — giong KHO CHUNG seed (_seed_rc1) chi ton tai tren may chu E2E loopback; LTT_QA_BASE_URL dang tro toi mot dich khac (tang-2).');
    } else {
      await page.goto(BASE + '/ltt-voice/giong');
      kt.dat();
      const theChung = page.locator('article[data-ma="vce_e2e_kho_chung"]');
      await theChung.waitFor({ state: 'attached', timeout: 15000 });
      const nutNghe = theChung.locator('button.lv-nghe[data-nghe]');
      if (await nutNghe.count() === 0)
        throw new Error('T-08: giong KHO CHUNG khong hien nut nghe thu (data-nghe vang mat)');
      const urlNghe = await nutNghe.getAttribute('data-nghe');
      if (!urlNghe || !urlNghe.includes('/audio/voice/chung/'))
        throw new Error('T-08: url nghe thu khong di qua tien to voice/chung/: ' + urlNghe);
      const rNghe = await page.request.get(
        urlNghe.startsWith('http') ? urlNghe : BASE + urlNghe);
      if (rNghe.status() !== 200)
        throw new Error(`T-08: GET nghe thu kho chung (khong phai chu) mong 200, nhan ${rNghe.status()}`);
      const bufNghe = await rNghe.body();
      if (!(bufNghe[0] === 0x52 && bufNghe[1] === 0x49 && bufNghe[2] === 0x46 && bufNghe[3] === 0x46))
        throw new Error('T-08: tep nghe thu kho chung tra ve KHONG phai WAV (thieu RIFF)');
      kt.khangDinh('T-08-kho-chung-nghe-thu');
    }
  }

  // ═══════════════════════════════════════════════════════════════════════
  // LUONG 4 — D005: xoa lich su hien hop xac nhan neu KHOI bi anh huong, roi
  // xoa that; khoi Du an tuong ung sau do bao "Can tao lai".
  // ═══════════════════════════════════════════════════════════════════════
  {
    kt.xoaCho();
    if (!LA_LOOPBACK) {
      console.log('SKIP LUONG 4 (D005) — du lieu seed (_seed_rc1: job + khoi du an prj_e2e_0001) chi ton tai tren may chu E2E loopback; LTT_QA_BASE_URL dang tro toi mot dich khac (tang-2).');
    } else {
      await page.goto(BASE + '/ltt-voice/lich-su');
      kt.dat();

      const dong = page.locator(SEL.dongLichSu, {
        hasText: 'Khoi co tieng, cho luot xoa Lich su (RC1 D005).' });
      await dong.waitFor({ state: 'attached', timeout: 15000 });
      const jobId = await dong.getAttribute('data-id');
      if (!jobId) throw new Error('D005: khong doc duoc data-id cua dong lich su vua seed');

      // /anh-huong PHAI liet ke dung khoi thu ba cua du an E2E TRUOC khi xoa.
      const rAh = await page.request.get(BASE + `/ltt-voice/lich-su/${jobId}/anh-huong`);
      if (rAh.status() !== 200)
        throw new Error(`D005: GET /anh-huong mong 200, nhan ${rAh.status()}`);
      const bAh = await rAh.json();
      const khoi = (bAh && bAh.khoi) || [];
      if (!khoi.some((k) => k.du_an === 'Kich ban E2E' && k.khoi_so === 3))
        throw new Error('D005: /anh-huong khong liet ke dung "Kich ban E2E" khoi so 3: '
          + JSON.stringify(bAh));

      // RAO PHA HUY (khong the dao nguoc — tep bi xoa that khoi kho): buoc
      // XOA duoi day CHI chay khi dich la may chu E2E loopback, HOAC khi
      // nguoi goi tu bat LTT_QA_CHO_XOA=1 CHO MOT dong do CHINH luot chay nay
      // tao duoi tai khoan test. Dong D005 o day luon la du lieu SEED co san
      // (_seed_rc1), KHONG phai dong luot nay tu tao — nen `CHO_XOA_TANG2`
      // MOT MINH KHONG BAO GIO du de mo cua xoa mot dong CO SAN tren dich
      // khac loopback.
      const dongDoLuotNayTao = false;   // D005 dung SEED co san, khong tu tao dong
      const coTheXoa = LA_LOOPBACK || (CHO_XOA_TANG2 && dongDoLuotNayTao);
      if (!coTheXoa) {
        console.log('SKIP buoc XOA cua D005 — khong phai may chu E2E loopback va LTT_QA_CHO_XOA chua duoc bat cho mot dong do CHINH luot nay tao; xoa lich su la KHONG THE DAO NGUOC nen khong tu chay tren dich khac.');
      } else {
        // Ghi de `window.confirm` NGAY TRONG TRANG truoc khi bam (xem chu
        // thich sandbox o dau tep — thay `page.once('dialog', ...)` vi
        // `run-code` tu bao loi tren mot dialog GOC dung du chinh kich ban
        // da xu ly xong). Van doc dung noi dung hop xac nhan (khoi 3 / ten
        // du an) roi coi nhu khach bam "OK", dung y nghia phep kiem cu.
        // Doc gia tri qua `exposeFunction` (phia NODE), khong qua mot bien
        // gan tren `window` — luong nay co the reload trang SAU khi confirm()
        // tra `true` (xoa thanh cong), va mot bien window se mat theo reload
        // TRUOC khi kip doc lai. `exposeFunction` "song sot qua dieu huong"
        // (tai lieu Playwright), nen gia tri ghi o day khong bi mat.
        // Ten ham DUY NHAT moi lan chay: `page.exposeFunction` ghi mot binding
        // theo TEN vao chinh trang/frame — neu tep nay chay hai lan tren CUNG
        // mot phien trinh duyet dang mo (vd goi lai `run-code` lien tiep),
        // ten co dinh se nem "already registered" o lan hai. Hau to
        // Date.now()+random tranh dung do ma khong doi y nghia.
        let dongConfirm = '';
        const tenHamXacNhan = '__lttGhiXacNhan_' + Date.now() + '_' + Math.floor(Math.random() * 1e6);
        await page.exposeFunction(tenHamXacNhan, (msg) => { dongConfirm = msg; });
        await page.evaluate((ten) => {
          window.confirm = (msg) => { window[ten](msg); return true; };
        }, tenHamXacNhan);
        await dong.locator(SEL.nutXoaLichSu).click();
        await page.waitForTimeout(400);   // cho fetch xoa + reload
        if (!dongConfirm.includes('3') || !dongConfirm.includes('Kich ban E2E'))
          throw new Error('D005: hop xac nhan KHONG nhac khoi 3 / "Kich ban E2E": ' + dongConfirm);

        await page.waitForLoadState('networkidle');
        kt.khangDinh('D005-xoa-lich-su');
        kt.dat();

        // Dong da xoa phai bao "Da xoa". DO THAT: `expire_content()`
        // (`platform_core/job_content.py`) xoa `job.params`/`job.result` khi
        // xoa mot luot — dung y (giu hang cho doi chieu so credit, chi het
        // han NOI DUNG) — nen VAN BAN goc ("RC1 D005") KHONG CON sau khi xoa,
        // template doi sang "(không có văn bản)". Tim lai dong bang `data-id`
        // ON DINH (`jobId` da doc o tren), khong con bang chuoi van ban da bi
        // xoa — ban cu tim theo `hasText: 'RC1 D005'` se KHONG khop duoc gi
        // sau buoc xoa, day la mot gia dinh sai san co cua chinh tep test,
        // khong phai loi ung dung.
        const dongSauXoa = page.locator(`${SEL.dongLichSu}[data-id="${jobId}"]`);
        if (!(await dongSauXoa.getByText('Bạn đã xoá lượt này').isVisible().catch(() => false)))
          throw new Error('D005: dong lich su KHONG bao "da xoa" sau khi xoa');

        // Khoi thu ba cua du an E2E gio phai bao "Can tao lai".
        await page.goto(BASE + '/ltt-voice/du-an');
        kt.dat();
        const theDuAn = page.getByText('Kich ban E2E').first();
        await theDuAn.waitFor({ state: 'visible', timeout: 15000 });
        await theDuAn.click();
        await page.waitForLoadState('networkidle');
        if (!(await page.getByText('Cần tạo lại').first().isVisible().catch(() => false)))
          throw new Error('D005: sau khi xoa lich su, du an KHONG hien badge "Can tao lai"');
        kt.khangDinh('D005-du-an-can-tao-lai');
      }
    }
  }

  // ═══════════════════════════════════════════════════════════════════════
  // LUONG 5 — D002 (Studio): khai VI + giong VI (Adam) + van ban EN CHAC
  // -> CHAN, `voice_language_mismatch`. (D006 — nghe thu vs Tao — KHONG co
  // nguoi goi tren giao dien: khong co nut "nghe thu" nao goi
  // `lan_ngon_ngu.quyet_dinh` de HIEN trang thai truoc khi Tao. BO QUA,
  // ghi ro o day theo dung brief.)
  // ═══════════════════════════════════════════════════════════════════════
  {
    kt.xoaCho();
    await page.goto(BASE + '/ltt-voice');
    kt.dat();

    // Khai "Tieng Viet" o nhom Ngon ngu.
    await page.locator(SEL.ngonNguNut('vi')).click();
    const giaTriNn = await page.locator(SEL.ngonNguAn).inputValue();
    if (giaTriNn !== 'vi')
      throw new Error(`D002: bam nut "Tieng Viet" khong doi input an — nhan "${giaTriNn}"`);

    // Chon giong Adam (preset VI — `vung="nam"`, xem giong_mau_engine.json).
    await page.getByRole('radio', { name: /Adam/ }).first().check();

    // Van ban EN CHAC (>= 2 tu chuc nang tieng Anh, dung vi du chinh
    // `lan_ngon_ngu.doan_ngon_ngu` da dan: "the"+"over" deu trong TU_ANH).
    await page.locator(SEL.vanBan).fill(
      'The quick brown fox jumps over the lazy dog.');

    kt.choPhep400('/ltt-voice/tao');
    const [resp] = await Promise.all([
      page.waitForResponse((r) => r.url().includes('/ltt-voice/tao') && r.request().method() === 'POST'),
      page.locator(SEL.nutTao).click(),
    ]);
    if (resp.status() !== 400)
      throw new Error(`D002: khai VI + van ban EN chac mong 400, nhan ${resp.status()} — CUA MO`);
    const bD002 = await resp.json();
    if (bD002.ok !== false || bD002.ma_loi !== 'voice_language_mismatch')
      throw new Error('D002: ma_loi sai — mong voice_language_mismatch, nhan '
        + JSON.stringify(bD002));

    // Giao dien phai HIEN loi (khong chi tra JSON am tham).
    await page.locator(SEL.ketQuaLoi).waitFor({ state: 'visible', timeout: 5000 });
    kt.khangDinh('D002-studio-mismatch');
  }

  if (LA_LOOPBACK) {
    console.log('RC1 OK — 6 khung hinh x 4 man, D003, D004, T-08, D005, D002: '
      + '5/5 luong dat (D006 bo qua — khong co nguoi goi tren giao dien, xem chu thich).');
  } else {
    console.log('RC1 OK (tang-2) — 6 khung hinh x 4 man, D003, D002: 2/5 luong dat; '
      + 'D004, T-08, D005 SKIP (phu thuoc du lieu seed _seed_rc1 chi co tren loopback) — '
      + 'xem dong SKIP o tren cho tung luong.');
  }
  } finally {
    // Xoa cookie `ltt_lang` (dat o tren) du LUONG nao do co nem loi hay
    // khong — khong de phien trinh duyet dung chung sot lai UI tieng Viet
    // cho tep chay SAU.
    await page.context().clearCookies({ name: 'ltt_lang' }).catch(() => {});
  }
}
