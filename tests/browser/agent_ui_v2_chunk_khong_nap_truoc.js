// Chunk nạp trễ ⛔ KHÔNG được tải TRƯỚC khi người dùng cần nó.
//
// ## Vì sao mệnh đề này là bản lề của cả làn UI-10a
//
// UI-10a nạp trễ `CommandPalette`, `LayersDrawer`, `StepInspector` và báo giảm
// ~20 KB thô / ~5,6 KB zstd. Con số ấy đúng **CHỈ KHI** trình duyệt thật sự ⛔
// không tải ba chunk kia ở lần ghé đầu.
//
// 🔴 Nếu có preload, cái "giảm" là ẢO: tổng byte **tăng** (thêm overhead ba
//    request) trong khi trần ⛔ không thấy gì — và trần mới sẽ đo **CÁCH ĐÓNG
//    GÓI** thay vì đo **TÍNH CHẤT**, đúng cái bẫy `.typed-port` đã dạy.
//
// ## Ba lớp bằng chứng, và chỉ lớp thứ ba là HÀNH VI
//
//   1. `manifest.json`: entry có `dynamicImports`, ⛔ không có `imports` tĩnh.
//   2. `bundle_assets()` chỉ inject `entry['file']` + `entry['css']` — ⛔ không
//      `modulepreload`, ⛔ không `dynamicImports`.
//   3. **BÀI NÀY**: nạp trang, ⛔ KHÔNG bấm gì, rồi đếm request thật.
//
// ⚠️ Hai lớp đầu đọc **cấu hình**; chỉ lớp ba đọc **thứ đã xảy ra**. Vite có thể
//    tự thêm `<link rel="modulepreload">` vào entry chunk qua mã runtime của nó,
//    và ⛔ không có cách nào biết điều đó bằng cách đọc manifest.
//
//     python tools\chay_web_that.py <tep nay>   (hoac playwright-cli tren 8196)
async page => {
  const GOC = 'http://127.0.0.1:8196';
  const CHUNK = ['CommandPalette', 'LayersDrawer', 'StepInspector'];

  const daTai = [];
  page.on('response', r => {
    const u = r.url();
    if (/\/static\/agent-canvas\/assets\//.test(u)) daTai.push(u.split('/').pop());
  });

  // Đăng nhập nếu cần (hồ sơ Playwright GIỮ cookie giữa các lượt).
  await page.goto(`${GOC}/login`, { waitUntil: 'load' });
  if (await page.locator('input[name="username"]').count()) {
    await page.fill('input[name="username"]', 'agent-ui0@example.com');
    await page.fill('input[name="password"]', 'Browser-ui0-2026');
    await Promise.all([
      page.waitForNavigation({ waitUntil: 'load', timeout: 30000 }),
      page.click('button[type="submit"], input[type="submit"]'),
    ]);
  }

  daTai.length = 0;
  await page.goto(`${GOC}/agent/canvas`, { waitUntil: 'load', timeout: 60000 });
  await page.waitForSelector('[data-testid="flow-store-status"]', { timeout: 45000 });
  // ⭐ Chờ thêm một nhịp: một preload có thể đến MUỘN hơn `load`.
  await page.waitForTimeout(2500);

  const loi = [];
  const so = { sau_khi_nap: [...daTai] };

  for (const ten of CHUNK) {
    const thay = daTai.filter(u => u.startsWith(ten));
    if (thay.length)
      loi.push(`${ten} DA duoc tai ma nguoi dung CHUA bam gi (${thay.join(', ')}) `
        + '⇒ "giam byte" cua UI-10a la AO, va tran moi dang do CACH DONG GOI');
  }
  so.entry = daTai.filter(u => u.startsWith('main-'));
  if (!so.entry.length)
    loi.push('⛔ khong thay entry `main-*` nao duoc tai — bo do nay dang do sai cho');

  // ── Ve DOI CHUNG: bam vao thi chunk PHAI toi ────────────────────────────
  // ⛔ Khong co ve nay, mot ban va "chan moi chunk mai mai" cung lam bai tren
  //    xanh — va tinh nang chet hoan toan trong im lang.
  await page.keyboard.press('Control+k');
  await page.waitForTimeout(2500);
  so.sau_khi_bam_ctrl_k = daTai.filter(u => u.startsWith('CommandPalette'));
  if (!so.sau_khi_bam_ctrl_k.length)
    loi.push('bam Ctrl+K ma chunk `CommandPalette` KHONG duoc tai ⇒ nap tre da '
      + 'lam tinh nang chet, ⛔ khong phai lam no nhanh');

  return loi.length ? { status: 'FAIL', loi, so } : { status: 'PASS', so };
}
