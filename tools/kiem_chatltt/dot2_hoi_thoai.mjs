/**
 * Đợt 2 — TRẠNG THÁI HỘI THOẠI VÀ CÂY NHÁNH.
 *
 * 🔴 VÌ SAO ĐỢT NÀY ĐỨNG THỨ HAI. URL hash mới thêm **ngày 03/09**, và mã mới
 *    nhất là mã ít mắt nhìn nhất. Cộng đồng đã dính đúng vùng này ba lần:
 *
 *      · *New chat has no label until page refresh and improper handling of
 *        back button* — **VẪN ĐANG MỞ** trong kho họ.
 *      · *Switching to another conversation and then switching back causes
 *        confusion in the messages.*
 *      · *Saved conversation structure collapse.*
 *
 * ⛔ Cây hội thoại là chỗ một lỗi KHÔNG mất dữ liệu ngay mà làm **hỏng nghĩa**:
 *    một nhánh gắn nhầm cha thì hội thoại vẫn đầy đủ, chỉ là kể sai chuyện. Loại
 *    hỏng đó không có thông báo lỗi nào, và người dùng phát hiện ra sau nhiều
 *    ngày — khi không còn khôi phục được nữa.
 */

export function dot2({ cho, doiDen, soBai, chuBaiCuoi, guiChu, xong, hoiThoaiMoi }) {
  const hash = (p) => p.evaluate(() => location.hash);

  return [
    {
      dot: 2,
      ten: '2.1-nut-Back-cua-trinh-duyet',
      hoi: 'Nút Back đi được giữa các hội thoại, hay nhảy ra khỏi trang?',
      async chay(p) {
        await hoiThoaiMoi(p);
        await guiChu(p, 'Ghi nho tu khoa: CAMAP');
        await xong(p);
        const a = await hash(p);
        await hoiThoaiMoi(p);
        await guiChu(p, 'Ghi nho tu khoa: HUOUCAO');
        await xong(p);
        const b = await hash(p);
        if (a === b || !a || !b) throw new Error(`hai hoi thoai cung hash: ${a} / ${b}`);

        await p.goBack({ waitUntil: 'domcontentloaded' });
        await cho(2500);
        const sau = await hash(p);
        if (sau !== a) {
          throw new Error(`Back khong ve hoi thoai truoc: mong ${a}, nhan "${sau}"`);
        }
        await doiDen('noi dung hoi thoai truoc hien lai', async () => {
          const t = await p.locator('article').first().innerText().catch(() => '');
          return /CAMAP/i.test(t);
        }, 25);
        return { hash_a: a, hash_b: b, sau_back: sau };
      },
    },
    {
      dot: 2,
      ten: '2.2-doi-hoi-thoai-A-B-A',
      hoi: 'Đi A→B→A thì nội dung có lẫn giữa hai hội thoại không?',
      async chay(p) {
        const ds = p.locator('aside li button');
        if ((await ds.count()) < 2) throw new Error('can it nhat hai hoi thoai — chay 2.1 truoc');
        const tenA = (await ds.nth(0).innerText()).trim();
        const tenB = (await ds.nth(1).innerText()).trim();

        await ds.nth(0).click(); await cho(1800);
        const a1 = await p.locator('article').first().innerText();
        await ds.nth(1).click(); await cho(1800);
        const b1 = await p.locator('article').first().innerText();
        await ds.nth(0).click(); await cho(1800);
        const a2 = await p.locator('article').first().innerText();

        if (a1.trim() !== a2.trim()) {
          throw new Error(`quay lai A thi noi dung DOI:\n  lan 1: ${JSON.stringify(a1.slice(0, 90))}\n  lan 2: ${JSON.stringify(a2.slice(0, 90))}`);
        }
        if (a1.trim() === b1.trim()) throw new Error('A va B hien cung noi dung');
        return { A: tenA.slice(0, 30), B: tenB.slice(0, 30), on_dinh: true };
      },
    },
    {
      dot: 2,
      ten: '2.3-tieu-de-hien-ngay-khong-can-F5',
      hoi: 'Hội thoại mới có tên trong thanh bên ngay, hay phải tải lại trang?',
      async chay(p) {
        // ⛔ Day la issue DANG MO cua LibreChat: "New chat has no label until
        //    page refresh". Neu ta cung the, no chi lo ra khi ai do dung that.
        await hoiThoaiMoi(p);
        const truoc = await p.locator('aside li button').count();
        await guiChu(p, 'Tra loi ngan: mot cong mot bang may?');
        await xong(p);
        await doiDen('thanh ben co them muc VA muc do co ten', async () => {
          const ds = p.locator('aside li button');
          if ((await ds.count()) <= truoc) return false;
          const ten = (await ds.first().innerText()).trim();
          return ten.length > 3;
        }, 25);
        const ten = (await p.locator('aside li button').first().innerText()).trim();
        return { tieu_de: ten.slice(0, 50) };
      },
    },
    {
      dot: 2,
      ten: '2.4-sua-gui-lai-o-LUOT-DAU-TIEN',
      hoi: 'Sửa lượt đầu tiên tạo anh em ở gốc, hay đẻ ra một hội thoại mới?',
      async chay(p) {
        // 🔴 `parent_id = null` (gan o GOC) khac `parent_id` VANG MAT (noi vao
        //    la dang xem). Hai nghia khac nhau di qua cung mot khoa JSON — dung
        //    cho `luot.MAC_DINH` sinh ra de phan biet, va dung cho mot lan sua
        //    vo y se lam hong lang le.
        await hoiThoaiMoi(p);
        await guiChu(p, 'Cau hoi GOC ban dau.');
        await xong(p);
        const hashTruoc = await hash(p);
        const baiTruoc = await soBai(p);

        p.once('dialog', (d) => d.accept('Cau hoi GOC da SUA.'));
        await p.getByRole('button', { name: 'Sửa và gửi lại' }).first().click();
        await xong(p);

        const hashSau = await hash(p);
        if (hashSau !== hashTruoc) {
          throw new Error(`sua lat dau da tao HOI THOAI MOI: ${hashTruoc} -> ${hashSau}`);
        }
        await doiDen('co dieu huong nhanh o goc', () =>
          p.getByRole('button', { name: 'Nhánh trước' }).count(), 20);
        const nhan = await p.locator('article').first().innerText();
        if (!/2\s*\/\s*2/.test(nhan)) {
          throw new Error(`mong "2 / 2" o nut goc, nhan: ${JSON.stringify(nhan.replace(/\n+/g, ' | ').slice(0, 120))}`);
        }
        return { bai_truoc: baiTruoc, hash_giu_nguyen: true };
      },
    },
    {
      dot: 2,
      ten: '2.5-nhanh-song-qua-F5-va-dung-nhanh-dang-chon',
      hoi: 'Chọn nhánh 1/2 rồi F5 — có về đúng nhánh đó không?',
      async chay(p) {
        const truoc = p.getByRole('button', { name: 'Nhánh trước' }).first();
        if (!(await truoc.count())) throw new Error('khong co dieu huong nhanh — chay 2.4 truoc');
        await truoc.click();
        await cho(1800);
        const chuTruoc = (await p.locator('article').first().innerText()).replace(/\s+/g, ' ');
        if (!/1\s*\/\s*2/.test(chuTruoc)) throw new Error(`chua ve nhanh 1: ${chuTruoc.slice(0, 90)}`);

        await p.reload({ waitUntil: 'domcontentloaded' });
        await doiDen('hoi thoai hien lai', async () => (await soBai(p)) >= 2, 30);
        const chuSau = (await p.locator('article').first().innerText()).replace(/\s+/g, ' ');
        if (!/1\s*\/\s*2/.test(chuSau)) {
          throw new Error(`F5 lam mat nhanh dang chon: ${chuSau.slice(0, 110)}`);
        }
        return { truoc_F5: '1/2', sau_F5: '1/2' };
      },
    },
    {
      dot: 2,
      ten: '2.6-hash-la-khong-lam-mac-ket',
      hoi: 'Một link hội thoại không tồn tại có làm người dùng mắc kẹt không?',
      async chay(p) {
        const goc = p.url().split('#')[0];
        await p.goto(`${goc}#cv_khong_he_ton_tai_0000`, { waitUntil: 'domcontentloaded' });
        await doiDen('hash duoc go va ve man hinh trong', async () =>
          (await p.evaluate(() => location.hash)) === '', 25);
        const coOSoan = await p.getByLabel('Nội dung tin nhắn').count();
        if (!coOSoan) throw new Error('khong ve duoc man hinh soan');
        return { hash_da_go: true };
      },
    },
    {
      dot: 2,
      ten: '2.7-tim-hoi-thoai-loc-dung',
      hoi: 'Ô tìm có lọc đúng, và xoá từ khoá có trả lại danh sách đầy đủ không?',
      async chay(p) {
        const o = p.getByRole('searchbox', { name: 'Tìm hội thoại' });
        if (!(await o.count())) throw new Error('khong co o tim');
        const tong = await p.locator('aside li button').count();
        await o.fill('CAMAP');
        await cho(1500);
        const loc = await p.locator('aside li button').count();
        await o.fill('');
        await cho(1500);
        const lai = await p.locator('aside li button').count();
        if (loc >= tong) throw new Error(`tim khong loc gi: ${tong} -> ${loc}`);
        if (lai !== tong) throw new Error(`xoa tu khoa khong tra lai day du: ${tong} -> ${lai}`);
        return { tong, khi_loc: loc, sau_khi_xoa: lai };
      },
    },
  ];
}
