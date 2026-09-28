// UI-3 — hoi quy BO CUC MOBILE (390x844). Chay tren may chu CO LAP 8198.
//
// Giu HAI dieu, va dieu thu hai la mot loi THAT da bat duoc:
//
//  1. Tab "Canvas" phai hien KHUNG VE, khong phai Inspector.
//     (Moc nen 27/09 TRUOC UI-3: chon tab Canvas nhung Inspector de len.)
//
//  2. 🔴 Doi tab phai TAT inspector. Bam mot node dat `desktopPanel`
//     ='inspector', va dieu kien cu `(desktopPanel==='inspector' ||
//     mobilePanel==='inspector')` lam inspector DINH CUNG: doi sang
//     "Cong cu" hay quay ve "Canvas" no van hien.
//     Do duoc 27/09 sau UI-3: Chi tiet ✅ · Cong cu ❌ · Canvas ❌.
//     Day la loi KE THUA tu CanvasShell cu — lo ra vi day la phep kiem
//     dau tien DOI TAB. Sua o `EditorShell.tsx` (inspector theo
//     `mobilePanel` khi `readOnly`).
//
// Cung kiem mobile la CHI-XEM: moi o trong inspector phai `disabled`.
async page => {
  const base = 'http://127.0.0.1:8198';
  const loi = [], soLieu = {};
  const check = (dk, m) => { if (!dk) loi.push(m); };

  await page.setViewportSize({width: 390, height: 844});
  await page.goto(base + '/agent/canvas');
  await page.locator('#agent-canvas-root').waitFor();
  await page.locator('.react-flow__node').first().waitFor({timeout: 15000});
  await page.waitForTimeout(700);

  const doTab = async () => await page.evaluate(() => {
    const hien = el => el && getComputedStyle(el).display !== 'none'
                    && el.getBoundingClientRect().width > 0;
    const tab = [...document.querySelectorAll('.canvas-mobile-tabs button')]
      .find(b => b.getAttribute('aria-pressed') === 'true');
    const o = [...document.querySelectorAll(
      '.canvas-inspector input, .canvas-inspector textarea, .canvas-inspector select')];
    return {
      tab: tab ? tab.textContent.trim() : null,
      khungVe: hien(document.querySelector('.canvas-stage')),
      inspector: hien(document.querySelector('.canvas-inspector')),
      palette: hien(document.querySelector('.canvas-palette')),
      soO: o.length,
      oKhoa: o.filter(x => x.disabled).length,
    };
  });

  const bamTab = async (ten) => {
    await page.evaluate((ten) => {
      const b = [...document.querySelectorAll('.canvas-mobile-tabs button')]
        .find(x => x.textContent.trim() === ten);
      if (b) b.click();
    }, ten);
    await page.waitForTimeout(600);
  };

  soLieu.canvas = await doTab();

  // Chon mot node truoc (Inspector chi co noi dung khi co node dang chon).
  await page.evaluate(() => {
    const n = document.querySelector('.react-flow__node');
    if (n) n.dispatchEvent(new MouseEvent('click', {bubbles: true}));
  });
  await page.waitForTimeout(500);

  await bamTab('Chi tiết');
  soLieu.chiTiet = await doTab();

  await bamTab('Công cụ');
  soLieu.congCu = await doTab();

  await bamTab('Canvas');
  soLieu.veCanvas = await doTab();

  check(soLieu.canvas.khungVe && !soLieu.canvas.inspector,
    'tab Canvas: khung ve phai hien, inspector phai an');
  check(soLieu.chiTiet.inspector,
    'tab "Chi tiet" KHONG hien inspector — UI-3 da sua QUA TAY');
  check(soLieu.congCu.palette,
    'tab "Cong cu" khong hien palette');
  check(soLieu.veCanvas.khungVe && !soLieu.veCanvas.inspector,
    'quay lai tab Canvas: trang thai khong ve dung');
  if (soLieu.chiTiet.soO > 0) {
    check(soLieu.chiTiet.oKhoa === soLieu.chiTiet.soO,
      `mobile phai CHI-XEM: ${soLieu.chiTiet.oKhoa}/${soLieu.chiTiet.soO} o bi khoa`);
  }

  return loi.length ? {status: 'FAIL', loi, so_lieu: soLieu}
                    : {status: 'PASS', so_lieu: soLieu};
}
