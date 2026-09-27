// Byte THẬT trên đường truyền của bundle Canvas, đo trên production.
//
// ## Vì sao cần kịch bản riêng cho một con số
//
// Trần `test_95::TRAN_JS_NEN = 160_000` đo **gzip**. Production phục vụ **zstd**
// (đo 28/09). Tôi đã dùng con số gzip (156.702) để **biện minh việc nâng trần**
// — tức lập luận dựa trên một đại lượng ⛔ KHÔNG phải đại lượng đang tranh luận.
//
// Và hy vọng *"gzip là cận trên an toàn cho zstd"* thì **SAI**, đo được:
//
//     byte thô   517.837
//     gzip -9    158.681
//     zstd -3    164.335   <- LỚN HƠN gzip, và vượt trần 160.000
//     zstd -9    151.422
//     zstd -19   142.514
//
// ⇒ zstd **không** đơn điệu nhỏ hơn gzip: nó phụ thuộc MỨC nén, và ⛔ không ai
//   ngoài Cloudflare biết mức họ dùng. Nên câu hỏi ⛔ không trả lời được bằng
//   cách nén lại ở nhà — phải đo **trên đường**.
//
// ## ⛔ `content-length` KHÔNG dùng được
//
// Phản hồi zstd của Cloudflare là **streaming**, nên header ấy vắng mặt
// (`tren_day: null` ở lượt nghiệm thu). Và `response.body()` của Playwright trả
// **thân đã giải nén** — đúng 517.837, tức nó trả lời một câu khác.
//
// ⭐ Dụng cụ đúng: `PerformanceResourceTiming.encodedBodySize` — trình duyệt tự
//    ghi số byte nó **nhận được trên socket**, sau nén, trước giải nén. Đó chính
//    là đại lượng khách trả tiền băng thông cho.
//
// ⚠️ Nó là `0` khi phản hồi đến từ **cache** hoặc khi thiếu header
//    `Timing-Allow-Origin` cho tài nguyên khác gốc. Cả hai ca ở đây đều cùng gốc
//    và ta `reload` bỏ cache, nhưng `0` vẫn phải được coi là **⛔ KHÔNG ĐO ĐƯỢC**,
//    ⛔ không phải *"nhẹ 0 byte"* — gộp hai thứ đó là mất khả năng phân biệt.
//
//     python tools\chay_web_that.py tests\browser\agent_ui_v2_byte_tren_day.js --phien byte
async page => {
  const COOKIE = '__LTT_COOKIE__';
  if (!COOKIE || COOKIE.startsWith('__LTT_'))
    throw new Error('chua dien cookie — chay qua `python tools/chay_web_that.py`');

  await page.context().addCookies([{
    name: 'session', value: COOKIE, domain: 'app.lttstudios.com', path: '/',
    httpOnly: true, secure: true }]);
  await page.setViewportSize({ width: 1440, height: 900 });

  // ⭐ `reload` voi cache BO QUA: mot phan hoi tu cache cho `encodedBodySize = 0`,
  //    va `0` do la "khong do duoc", ⛔ khong phai mot so nho.
  await page.goto('https://app.lttstudios.com/agent/canvas',
                  { waitUntil: 'load', timeout: 90000 });
  await page.evaluate(() => performance.clearResourceTimings());
  await page.reload({ waitUntil: 'load', timeout: 90000 });
  await page.waitForSelector('[data-testid="flow-store-status"]', { timeout: 60000 });

  const asset = await page.evaluate(() => {
    const ra = [];
    for (const e of performance.getEntriesByType('resource')) {
      if (!/\/static\/agent-canvas\/assets\//.test(e.name)) continue;
      ra.push({
        ten: e.name.split('/').pop(),
        tren_day: e.encodedBodySize,       // sau nen — thu khach TAI
        sau_giai_nen: e.decodedBodySize,   // truoc nen
        ms: Math.round(e.duration),
      });
    }
    return ra;
  });

  const loi = [];
  const so = {};
  const js = asset.find(a => a.ten.endsWith('.js'));
  const css = asset.find(a => a.ten.endsWith('.css'));
  if (!js) loi.push('khong thay tep JS trong resource timing');

  // ⚠️ `0` = KHONG DO DUOC (cache / thieu Timing-Allow-Origin), ⛔ khong phai 0 byte.
  const doDuoc = js && js.tren_day > 0;
  if (js && !doDuoc)
    loi.push(`encodedBodySize = 0 cho ${js.ten} ⇒ KHONG do duoc (cache?), `
      + 'tra ve chua co ket luan — ⛔ dung doc la "0 byte"');

  // ⛔ KICH BAN NAY KHONG PHAN QUYET TRAN, va do la co y.
  //
  //    Tran song o **mot cho duy nhat**: `test_95::TRAN_JS_NEN`. Dat o day mot
  //    nguong thu hai se cho hai su that cho mot cau hoi, va khi chung lech thi
  //    ⛔ khong ai biet cai nao la luat.
  //
  // ⭐ Viec cua kich ban nay la mot menh de KHAC va no dat hon: **mo hinh
  //    `zstd -3` ma `test_95` dung co con khop production khong.** `test_95`
  //    phai chay offline nen no ⛔ khong the hoi Cloudflare; no NEN LAI o nha va
  //    tin rang muc 3 xap xi cai CDN dung. Doi chung 28/09: du doan 164.335 /
  //    do duoc 164.252 = lech **0,05 %**.
  //
  // ⇒ Neu Cloudflare doi muc nen, ti le nay truot, va tran offline im lang thoi
  //   mo ta thuc te. Bai nay la thu duy nhat bat duoc dieu do.
  const MO_HINH = 164335;   // zstd -3 tinh o nha, 28/09, cho `main-CLfcF0-O.js`
  if (doDuoc) {
    const lech = Math.abs(js.tren_day - MO_HINH) / MO_HINH;
    so.lech_mo_hinh = `${(lech * 100).toFixed(2)}%`;
    // Nguong rong (25%): ta do mot **ti le**, va bundle doi kich thuoc moi ngay
    // nen so tuyet doi se troi. Thu can bat la Cloudflare doi MUC NEN — cai do
    // lam ti le nhay han, ⛔ khong nhich vai phan tram.
    if (lech > 0.25)
      loi.push(`mo hinh zstd-3 KHONG con khop production: du doan ~${MO_HINH}, `
        + `do duoc ${js.tren_day} (lech ${so.lech_mo_hinh}). `
        + 'Do lai muc nen roi cap nhat `MUC_ZSTD` trong `test_95`.');
  }

  const tong = asset.reduce((s, a) => s + (a.tren_day || 0), 0);
  return {
    status: loi.length ? 'FAIL' : 'PASS', loi,
    so: { asset, tong_tren_day: tong,
          js_tren_day: js?.tren_day ?? null, css_tren_day: css?.tren_day ?? null,
          mo_hinh_zstd3: MO_HINH, lech_mo_hinh: so.lech_mo_hinh ?? null },
  };
}
