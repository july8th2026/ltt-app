// Byte THAT tren day cua bundle Canvas — do bang `encodedBodySize`, tren production.
//
// ## 🔴 Vi sao can kich ban nay, khi `agent_ui_v2_nghiem_thu_sau_deploy.js` da PASS
//
// Luot nghiem thu sau deploy `1e34780f` tra ve:
//
//     main-Dj6ighKc.js   tren_day: null   sau_giai_nen: 500649   nen: zstd
//
// `null` ⛔ KHONG phai "khong co byte" — la **khong do duoc**. Cloudflare phuc vu
// `zstd` theo kieu streaming, va phan hoi streaming ⛔ khong mang
// `content-length`. Nen phep do cu hoi mot tieu de **khong ton tai**.
//
// ⚠️ Va do la ca hai lo cung luc:
//   1. `test_95::TRAN_JS_NEN` do **gzip** trong khi khach that tai **zstd** —
//      gzip ⛔ KHONG phai can tren an toan cho zstd (zstd-3 co the LON hon gzip-9
//      tuy du lieu), nen mot tran gzip XANH ⛔ khong chung minh gi ve byte khach tai;
//   2. phep do "byte tren day" o kich ban nghiem thu doc `content-length` ⇒ null,
//      va mot `null` lang le doc y het "chua ai do" — chinh la cai nham ta muon tranh.
//
// ⭐ Dung cu DUNG la `PerformanceResourceTiming.encodedBodySize`: trinh duyet ghi
//    so byte **da nen** nhan tu mang, bat ke kieu nen va bat ke co
//    `content-length` hay khong.
//
//    ⛔ `transferSize` thi KHONG dung o day: no CONG ca tieu de phan hoi, va tra
//      **0** cho mot tai nguyen lay tu cache. Hai ca do lam so lech theo hai
//      chieu nguoc nhau.
//
// ## ⛔ CHI DOC. Day la may THAT
//
//   python tools\chay_web_that.py tests\browser\agent_ui_v2_byte_zstd_production.js --phien byte
async page => {
  const COOKIE = '__LTT_COOKIE__';
  if (!COOKIE || COOKIE.startsWith('__LTT_'))
    throw new Error('chua dien cookie — chay qua `python tools/chay_web_that.py`');

  const GOC = 'https://app.lttstudios.com';
  await page.context().addCookies([{
    name: 'session', value: COOKIE, domain: 'app.lttstudios.com',
    path: '/', httpOnly: true, secure: true, sameSite: 'Lax',
  }]);

  // ⚠️ `reload` voi cache CON SONG tra `encodedBodySize = 0`. Phai tai LAN DAU
  //    tren mot context sach — day la context moi, nhung noi ro de ai sua sau
  //    ⛔ khong them mot `reload()` roi tuong so 0 la "nhe".
  await page.goto(GOC + '/agent/canvas', { waitUntil: 'networkidle', timeout: 90000 });

  const ds = await page.evaluate(() => performance
    .getEntriesByType('resource')
    .filter(e => /\.(js|css)(\?|$)/.test(e.name))
    .map(e => ({
      ten: e.name.split('/').pop(),
      encodedBodySize: e.encodedBodySize,
      decodedBodySize: e.decodedBodySize,
      transferSize: e.transferSize,
      tu_cache: e.transferSize === 0,
    })));

  const js = ds.filter(x => x.ten.endsWith('.js'));
  const css = ds.filter(x => x.ten.endsWith('.css'));
  const tong = n => n.reduce((s, x) => s + x.encodedBodySize, 0);

  const loi = [];
  if (!js.length) loi.push('khong thay tep .js nao — chon sai kieu tai nguyen?');
  // ⛔ KHONG phan quyet mot TRAN o day. Kich ban nay **do**, con tran thuoc
  //    `test_95` — mot nguong thu hai doan o day se lech voi nguong kia va ⛔
  //    khong ai bat khop. Chi bao mot ca VO NGHIA: so 0 tuc chua do duoc gi.
  for (const x of ds)
    if (x.encodedBodySize === 0)
      loi.push(`${x.ten}: encodedBodySize = 0 (lay tu cache?) - CHUA DO DUOC`);

  return {
    status: loi.length ? 'FAIL' : 'PASS',
    loi,
    js_encoded_tong: tong(js),
    css_encoded_tong: tong(css),
    chi_tiet: ds,
  };
}
