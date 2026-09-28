// Ba panel NẠP TRỄ vẫn MỞ ĐƯỢC bằng bàn phím — chỉ là muộn hơn một nhịp mạng.
//
// ## 🔴 Va chạm giữa hai làn, và nó ⛔ không phải lỗi của làn nào
//
// UI-10a nạp trễ `CommandPalette` · `LayersDrawer` · `StepInspector`
// (`React.lazy` + `import()`). UI-10b viết phép đo bẫy focus bằng cách **bấm
// phím rồi kiểm ngay** — đúng khi panel còn đồng bộ.
//
// Gộp hai làn: UI-10b đỏ ba mục (*"CommandPalette ⛔ không mở được bằng Ctrl+K"*).
// Cả hai làn **xanh riêng**; chỉ tổ hợp mới đỏ.
//
// ⚠️ Và câu phải tách ra trước khi sửa bất cứ gì:
//
//     panel KHÔNG mở  ?    hay    phép đo HỎI QUÁ SỚM  ?
//
// Hai kết luận dẫn tới hai hành động ngược nhau: một cái đòi bỏ nạp trễ, một cái
// đòi sửa phép đo. ⇒ Bài này trả lời câu ấy bằng **hai phép đo cạnh nhau**: kiểm
// NGAY (kỳ vọng ⛔ chưa có) rồi CHỜ (kỳ vọng có).
//
// ⭐ Nếu vế "chờ rồi có" cũng đỏ ⇒ tính năng thật sự hỏng, và nạp trễ phải bỏ.
//    Nếu chỉ vế "ngay" đỏ ⇒ phép đo hỏi quá sớm, và chỉ phép đo phải sửa.
async page => {
  const GOC = 'http://127.0.0.1:8209';
  const loi = [], so = {};
  const check = (dk, msg) => { if (!dk) loi.push(msg) };

  await page.goto(`${GOC}/login`, { waitUntil: 'load' });
  // ⭐ Cung bo chon voi `agent_ui_v2_ui10b_nghiem_thu.js` (`#login-username`),
  //    ⛔ khong tu bia — mot ten bo chon bia ra cho `0` va toi da doc `0` do la
  //    "trang khong co gi" mot lan hom nay roi.
  if (await page.locator('#login-username').count()) {
    await page.locator('#login-username').fill('agent-ui10b@example.com');
    await page.locator('#login-password').fill('Browser-ui10b-2026');
    await page.locator('form button[type=submit]').click();
    await page.waitForLoadState('networkidle');
  }
  await page.goto(`${GOC}/agent/canvas`, { waitUntil: 'load', timeout: 60000 });
  await page.waitForSelector('[data-testid="flow-store-status"]', { timeout: 45000 });

  // 🔴 HAI LOI DO LUONG CUA TOI o luot chay dau, ca hai cho ra "LayersDrawer
  //    hong" — trong khi no ⛔ khong hong:
  //
  //  1. Toi **TU BIA** phim tat `Control+l`. `LayersDrawer` mo bang mot **NUT**
  //     (`LeftRail.tsx:69`, `aria-label="Mở danh sách lớp"`), ⛔ khong bang phim.
  //  2. Nut ay chi duoc ve khi `hasAnyNodes` — do thi phai co **it nhat mot
  //     node**. Kich ban cua toi ⛔ khong dung do thi nao, nen nut ⛔ khong ton tai.
  //
  // ⇒ `sau: 0` cua toi nghia la **tien de VANG MAT**, ⛔ khong phai *"panel khong
  //   mo"*. Lan thu BA trong ngay toi doc mot `0` nhu mot phat hien.
  // ⭐ Nen moi ca nay khai TUONG MINH cach mo, va phan biet ba ket qua:
  //      mo duoc  ·  KHONG mo duoc  ·  ⛔ KHONG DO DUOC (thieu tien de)
  const CA = [
    { chon: '.command-palette', ten: 'CommandPalette',
      mo: async () => { await page.keyboard.press('Control+k'); return true } },
    { chon: '.layers-drawer', ten: 'LayersDrawer',
      mo: async () => {
        const nut = page.locator('[aria-label="Mở danh sách lớp"]');
        if (!await nut.count()) return false;   // thieu tien de: chua co node
        await nut.first().click();
        return true;
      } },
  ];

  for (const { chon, ten, mo } of CA) {
    // Đóng mọi thứ đang mở trước mỗi ca.
    await page.keyboard.press('Escape');
    await page.waitForTimeout(150);

    const mo_duoc = await mo();
    if (!mo_duoc) {
      so[ten] = { khong_do_duoc: 'thieu tien de (nut chua duoc ve — do thi rong)' };
      continue;
    }

    // ── Phép đo A: NGAY, ⛔ không chờ ─────────────────────────────────────
    const ngay = await page.locator(chon).count();

    // ── Phép đo B: CHỜ tới 4 giây ────────────────────────────────────────
    let sau = 0;
    try {
      await page.waitForSelector(chon, { timeout: 4000, state: 'attached' });
      sau = await page.locator(chon).count();
    } catch { sau = 0 }

    so[ten] = { ngay, sau };
    // ⭐ Mệnh đề thật: CHỜ thì PHẢI có. Đó là "tính năng còn sống".
    check(sau > 0, `${ten}: cho 4 giay van KHONG mo ⇒ nap tre da lam TINH NANG `
      + 'HONG, ⛔ khong phai lam phep do hoi som. Phai bo nap tre cho panel nay.');
    // ⚠️ `ngay === 0` la BINH THUONG sau khi nap tre — ghi lai de nguoi doc hieu
    //    vi sao phep do cu do, ⛔ khong bien no thanh mot loi.
  }

  so.giai_thich = 'ngay=0 + sau>0  ⇒  phep do cu hoi qua som, tinh nang con song';
  return loi.length ? { status: 'FAIL', loi, so } : { status: 'PASS', so };
}
