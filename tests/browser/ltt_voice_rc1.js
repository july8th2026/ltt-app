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
// MOT SELECTOR MAP DUY NHAT (`SEL`) o ngay duoi day cho luong D002 (Studio):
// Task 11 (mot phien KHAC, cung cay worktree) dang doi giao dien Studio CUNG
// LUC voi task nay. Danh sach "selector co the phai sua sau khi Task 11 hop
// nhat" o cuoi tep va o dong report.

const SEL = {
  // ── Studio (D002) — CO THE DOI khi Task 11 hop nhat ──────────────────────
  ngonNguNut: (ma) => `[data-ngonngu="${ma}"]`,      // nut chon Tu dong/VI/EN
  ngonNguAn: '#lv-ngon-ngu',                          // input an giu gia tri
  giongRadio: (nhan) => `input[name="giong"]`,        // radiogroup chon giong
  vanBan: '#lv-text',                                 // textarea kich ban
  nutTao: '#lv-nut-tao',                              // nut "Tao"
  ketQuaLoi: '#lv-kq-loi',                            // hop loi sau khi nop
  // ── Man Giong (D003/D004/T-08) — on dinh, khong thuoc pham vi Task 11 ────
  formGhiDanh: '#lv-form-giong',
  detailsGhiDanh: '#lv-tao-giong',
  gioLoiGhiDanh: '#lv-g-loi',
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
    if (m.type() === 'error') vanDe.push('console.error: ' + m.text());
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

async page => {
  // Mac dinh may chu E2E CACH LY (voice_e2e_server.py). `LTT_QA_BASE_URL` mo
  // mot tang-2 (tier-2) TRO TOI MOT DICH KHAC do nguoi chay tu dat qua env —
  // KHONG bao gio ghim mot URL production thang vao tep nay (xem
  // `check_voice_qa.py`, rao G-BROWSER-GUARD "tro toi PRODUCTION").
  const BASE = process.env.LTT_QA_BASE_URL || 'http://127.0.0.1:8129';
  const kt = kiemTrang(page);

  // ── Dang nhap MOT LAN (tai khoan E2E dung mot lan) ─────────────────────────
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
    await page.goto(BASE + '/ltt-voice/giong');
    kt.dat();

    // 1a. KHONG khai lan (`ngon_ngu` rong) -> 400 `voice_language_required`,
    //     KHONG job nao duoc nop. Di THANG qua server (giong khuon
    //     `ltt_voice_negative.js`) vi <select required> chan native truoc
    //     khi JS kip nem — bai hoc D003 la ve CUA SERVER, khong ve HTML5.
    const csrf = await page.getAttribute('#lv-form-giong input[name="csrf_token"]', 'value');
    if (!csrf) throw new Error('D003: khong lay duoc csrf tu form ghi danh');

    kt.choPhep400('/ltt-voice/giong/tao');
    const tepGia = { name: 'clip.wav', mimeType: 'audio/wav',
                     buffer: Buffer.from('RIFF0000WAVEfmt ', 'utf-8') };
    const r1 = await page.request.post(BASE + '/ltt-voice/giong/tao', {
      multipart: {
        csrf_token: csrf, ten: 'RC1 khong khai lan', dong_y: '1',
        ngon_ngu: '', tep: tepGia,
      },
    });
    if (r1.status() !== 400)
      throw new Error(`D003: khong khai lan mong 400, nhan ${r1.status()} — CUA MO`);
    const b1 = await r1.json();
    if (b1.ok !== false || b1.ma_loi !== 'voice_language_required')
      throw new Error(`D003: ma_loi sai — mong voice_language_required, nhan ${JSON.stringify(b1)}`);

    // Khong co giong "RC1 khong khai lan" nao duoc tao — kiem lai qua trang.
    await page.reload();
    kt.khangDinh('D003-khong-khai-lan (sau kiem 400)');
    kt.dat();
    if (await page.getByText('RC1 khong khai lan').first().isVisible().catch(() => false))
      throw new Error('D003: mot giong DA duoc tao du khong khai lan — cua van mo');

    // 1b. Ghi danh HOP LE voi ngon_ngu=en -> the giong moi hien dung lan EN.
    const tenGiongMoi = 'RC1 ghi danh EN ' + Date.now();
    const r2 = await page.request.post(BASE + '/ltt-voice/giong/tao', {
      multipart: {
        csrf_token: csrf, ten: tenGiongMoi, dong_y: '1',
        ngon_ngu: 'en', tep: tepGia,
      },
    });
    if (r2.status() !== 200)
      throw new Error(`D003: ghi danh EN hop le mong 200, nhan ${r2.status()}`);
    const b2 = await r2.json();
    if (!b2.ok || !b2.voice_id)
      throw new Error('D003: ghi danh EN hop le khong tra ok+voice_id: ' + JSON.stringify(b2));

    await page.reload();
    kt.khangDinh('D003-ghi-danh-en');
    kt.dat();
    // The moi (`ngon_ngu_nguon=khai_bao` ngay tu luc tao) phai hien khu vuc
    // "Doi ngon ngu" (khong phai "Xac nhan…", vi khong phai dong `mac_dinh_cu`)
    // voi <option value="en" selected>.
    const theEn = page.locator(`article[data-ma="${b2.voice_id}"]`);
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

  // ═══════════════════════════════════════════════════════════════════════
  // LUONG 3 — T-08: nut nghe thu cua giong KHO CHUNG tra 200 cho KHACH
  // KHONG PHAI CHU (seed `vce_e2e_kho_chung`, chu la mot tai khoan gia khac).
  // ═══════════════════════════════════════════════════════════════════════
  {
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

  // ═══════════════════════════════════════════════════════════════════════
  // LUONG 4 — D005: xoa lich su hien hop xac nhan neu KHOI bi anh huong, roi
  // xoa that; khoi Du an tuong ung sau do bao "Can tao lai".
  // ═══════════════════════════════════════════════════════════════════════
  {
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

    // Hop confirm() liet ke dung khoi do — bat dialog TRUOC khi bam Xoa.
    let dongConfirm = '';
    page.once('dialog', async (d) => { dongConfirm = d.message(); await d.accept(); });
    await dong.locator(SEL.nutXoaLichSu).click();
    await page.waitForTimeout(400);   // cho fetch xoa + reload
    if (!dongConfirm.includes('3') || !dongConfirm.includes('Kich ban E2E'))
      throw new Error('D005: hop xac nhan KHONG nhac khoi 3 / "Kich ban E2E": ' + dongConfirm);

    await page.waitForLoadState('networkidle');
    kt.khangDinh('D005-xoa-lich-su');
    kt.dat();

    // Dong da xoa phai bao "Da xoa".
    const dongSauXoa = page.locator(SEL.dongLichSu, { hasText: 'RC1 D005' });
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

  // ═══════════════════════════════════════════════════════════════════════
  // LUONG 5 — D002 (Studio): khai VI + giong VI (Adam) + van ban EN CHAC
  // -> CHAN, `voice_language_mismatch`. (D006 — nghe thu vs Tao — KHONG co
  // nguoi goi tren giao dien: khong co nut "nghe thu" nao goi
  // `lan_ngon_ngu.quyet_dinh` de HIEN trang thai truoc khi Tao. BO QUA,
  // ghi ro o day theo dung brief.)
  // ═══════════════════════════════════════════════════════════════════════
  {
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

  console.log('RC1 OK — 6 khung hinh x 4 man, D003, D004, T-08, D005, D002: '
    + '5/5 luong dat (D006 bo qua — khong co nguoi goi tren giao dien, xem chu thich).');
}
