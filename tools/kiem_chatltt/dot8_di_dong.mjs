/**
 * Đợt 8 — DI ĐỘNG VÀ BÀN PHÍM ẢO.
 *
 * 🔴 VÌ SAO ĐỢT NÀY CẦN, VÀ VÌ SAO NÓ KHÓ. Trên điện thoại, bàn phím ảo **không
 *    thu nhỏ layout viewport** — nó chỉ thu **visual viewport**. Nên `100vh` vẫn
 *    trả về chiều cao *trước khi* bàn phím mở, và một ô soạn đặt theo `100vh`
 *    trượt xuống **dưới bàn phím**: người dùng gõ mà không thấy mình đang gõ gì.
 *
 * ⛔ ĐÂY LÀ ƯỚC LƯỢNG, KHÔNG PHẢI BÀN PHÍM THẬT, và tôi nói thẳng chỗ đó.
 *    Playwright không dựng được bàn phím ảo. Thứ đợt này làm là **thu nhỏ khung
 *    nhìn** xuống đúng phần còn lại khi bàn phím chiếm chỗ (~45 % chiều cao trên
 *    iOS/Android), rồi hỏi: *ô soạn còn thấy được không, tin nhắn cuối còn trong
 *    khung không.*
 *
 * ⭐ Ước lượng đó bắt được đúng lớp lỗi ta lo: bố cục **không co lại** theo chiều
 *    cao khả dụng. Nó KHÔNG bắt được lỗi riêng của `visualViewport` (vd thanh
 *    công cụ trình duyệt trượt). Ghi ra để không ai đọc một dòng `DAT` ở đây rồi
 *    tin rằng đã kiểm trên máy thật.
 *
 * ⚠️ Dùng `Emulation.setDeviceMetricsOverride` qua CDP chứ không `setViewportSize`:
 *    bộ kiểm nay NỐI VÀO một Chrome thật (`--cdp`), và cửa sổ đó là của người
 *    dùng — không được đổi kích thước cửa sổ của họ. Override chỉ tác động lên
 *    trang, và luôn được gỡ trong `finally`.
 */

//: Kích thước một máy phổ thông (iPhone 14 / Pixel 7 cùng cỡ này).
const RONG = 390;
const CAO = 844;

//: Chiều cao còn lại khi bàn phím ảo chiếm chỗ. 45 % là mức đo phổ biến của
//: bàn phím iOS/Android ở chế độ đứng.
const CAO_CO_BAN_PHIM = Math.round(CAO * 0.55);

//: Trần chạm tối thiểu. 44 px là mức của Apple HIG và WCAG 2.5.5 (AAA).
const CHAM_TOI_THIEU = 44;

export function dot8({ cho, doiDen, guiChu, xong, hoiThoaiMoi }) {
  /** Đặt khung nhìn qua CDP, chạy `viec`, rồi **luôn** gỡ override. */
  async function trongKhung(p, { rong, cao }, viec) {
    const cdp = await p.context().newCDPSession(p);
    try {
      await cdp.send('Emulation.setDeviceMetricsOverride', {
        width: rong, height: cao, deviceScaleFactor: 2, mobile: true,
      });
      // ⛔ `mobile: true` MOT MINH KHONG lam `pointer: coarse` khop. Do 04/09:
      //    `matchMedia('(pointer: coarse)').matches` van `false`, nen moi luat
      //    CSS viet cho ngon tay **khong bao gio duoc chay** trong bo kiem — ke
      //    ca luat vua them de sua chinh loi nut 27px.
      //
      // ⭐ Phai bat cham ung rieng. Mot bo kiem di dong khong gia lap cham ung
      //    la mot bo kiem do man hinh hep, khong phai do dien thoai.
      await cdp.send('Emulation.setTouchEmulationEnabled',
                     { enabled: true, maxTouchPoints: 5 }).catch(() => {});
      await cho(700);                        // để layout kịp chạy lại
      return await viec();
    } finally {
      // ⛔ GỠ TRONG `finally`, KHÔNG Ở CUỐI THÂN. Một hạng mục ném giữa chừng mà
      //    để lại override thì MỌI hạng mục sau chạy trên một khung nhìn 390 px
      //    — và chúng sẽ đỏ vì một lý do chẳng liên quan gì tới chúng.
      await cdp.send('Emulation.setTouchEmulationEnabled',
                     { enabled: false, maxTouchPoints: 0 }).catch(() => {});
      await cdp.send('Emulation.clearDeviceMetricsOverride').catch(() => {});
      await cdp.detach().catch(() => {});
      await cho(400);
    }
  }

  const oSoan = (p) => p.getByLabel('Nội dung tin nhắn');

  /** Hình chữ nhật của một phần tử, kèm khung nhìn — đo một lần, tránh lệch nhịp. */
  const doKhung = (p, chon) => p.evaluate((s) => {
    const e = document.querySelector(s);
    if (!e) return null;
    const r = e.getBoundingClientRect();
    return {
      top: Math.round(r.top), duoi: Math.round(r.bottom),
      cao: Math.round(r.height), rong: Math.round(r.width),
      vh: window.innerHeight, vw: window.innerWidth,
      cuonNgang: document.documentElement.scrollWidth > document.documentElement.clientWidth,
    };
  }, chon);

  return [
    {
      dot: 8,
      // Ca dot 8 do BO CUC, khong doc cau tra loi cua model.
      doc_lap_voi_model: true,
      ten: '8.1-o-soan-thay-duoc-o-390px',
      hoi: 'Màn 390 px: ô soạn có nằm trong khung nhìn không?',
      async chay(p) {
        return trongKhung(p, { rong: RONG, cao: CAO }, async () => {
          await doiDen('o soan hien ra', async () => (await oSoan(p).count()) > 0, 20);
          await oSoan(p).scrollIntoViewIfNeeded();
          const k = await doKhung(p, '.ltc-soan__o');
          if (!k) throw new Error('khong thay o soan');
          if (k.duoi > k.vh + 1) {
            throw new Error(`o soan tran khoi khung nhin: duoi=${k.duoi} > vh=${k.vh}`);
          }
          if (k.cuonNgang) throw new Error('trang cuon NGANG o 390px');
          return { rong: k.rong, cao_o_soan: k.cao, vh: k.vh, trong_khung: true };
        });
      },
    },
    {
      dot: 8,
      // Ca dot 8 do BO CUC, khong doc cau tra loi cua model.
      doc_lap_voi_model: true,
      ten: '8.2-ban-phim-ao-KHONG-che-mat-o-soan',
      hoi: 'Bàn phím ảo chiếm 45% màn — ô soạn còn thấy được không?',
      async chay(p) {
        // 🔴 ĐÂY LÀ HẠNG MỤC CHÍNH CỦA CẢ ĐỢT. `#chatltt-root` đặt
        //    `min-height: calc(100vh - 190px)`, và `100vh` **không co lại** khi
        //    bàn phím mở trên máy thật. Nếu bố cục không co theo chiều cao khả
        //    dụng, ô soạn tụt xuống dưới bàn phím và khách gõ mù.
        return trongKhung(p, { rong: RONG, cao: CAO_CO_BAN_PHIM }, async () => {
          await doiDen('o soan hien ra', async () => (await oSoan(p).count()) > 0, 20);
          await oSoan(p).scrollIntoViewIfNeeded();
          await oSoan(p).click().catch(() => {});
          await cho(600);
          const k = await doKhung(p, '.ltc-soan__o');
          if (!k) throw new Error('khong thay o soan');
          if (k.duoi > k.vh + 1) {
            throw new Error(
              `o soan bi CHE khi ban phim mo: duoi=${k.duoi} > vh=${k.vh} `
              + `(thieu ${k.duoi - k.vh}px)`);
          }
          return { vh_con_lai: k.vh, duoi_o_soan: k.duoi, con_thay_duoc: true };
        });
      },
    },
    {
      dot: 8,
      // Ca dot 8 do BO CUC, khong doc cau tra loi cua model.
      doc_lap_voi_model: true,
      ten: '8.3-tin-nhan-CUOI-van-trong-khung-khi-ban-phim-mo',
      hoi: 'Bàn phím mở — câu trả lời vừa nhận có còn nhìn thấy không?',
      async chay(p) {
        await hoiThoaiMoi(p);
        await guiChu(p, 'Tra loi that ngan: mot tu.');
        await xong(p);
        return trongKhung(p, { rong: RONG, cao: CAO_CO_BAN_PHIM }, async () => {
          const k = await p.evaluate(() => {
            const bai = [...document.querySelectorAll('article')].pop();
            if (!bai) return null;
            bai.scrollIntoView({ block: 'end' });
            const r = bai.getBoundingClientRect();
            return { top: Math.round(r.top), duoi: Math.round(r.bottom),
                     vh: window.innerHeight };
          });
          if (!k) throw new Error('khong co bai nao');
          // ⭐ Chỉ đòi **một phần** bài nằm trong khung: một câu trả lời dài hơn
          //    màn hình thì không thể vừa trọn, và đòi thế là đòi một điều không
          //    ai làm được.
          if (k.top >= k.vh) {
            throw new Error(`bai cuoi nam HOAN TOAN duoi khung: top=${k.top} >= vh=${k.vh}`);
          }
          return { top_bai_cuoi: k.top, vh: k.vh, con_trong_khung: true };
        });
      },
    },
    {
      dot: 8,
      // Ca dot 8 do BO CUC, khong doc cau tra loi cua model.
      doc_lap_voi_model: true,
      ten: '8.4-nut-media-cham-duoc-bang-ngon-tay',
      hoi: 'Nút "Tạo ảnh"/"Tạo giọng" có đủ lớn để chạm không?',
      async chay(p) {
        return trongKhung(p, { rong: RONG, cao: CAO }, async () => {
          // ⛔ KHONG NUT NAO = KHONG KIEM DUOC, KHONG PHAI DAT.
          //
          //    Do 04/09: hang muc nay bao DAT voi `.ltc-media > button` tra ve
          //    **danh sach rong** — thanh media chi hien khi dang o trong mot
          //    hoi thoai. "Moi nut deu >= 44px" dung hien nhien tren tap rong,
          //    va do la mot dong xanh khong chung minh gi.
          if (!(await p.locator('.ltc-media > button').count())) {
            await hoiThoaiMoi(p);
            await guiChu(p, 'Chao.');
            await xong(p);
          }
          const soNut = await p.locator('.ltc-media > button').count();
          if (!soNut) throw new Error('khong tim thay nut media nao de do');
          const nho = await p.evaluate((toi_thieu) => {
            const ra = [];
            for (const b of document.querySelectorAll('.ltc-media > button')) {
              const r = b.getBoundingClientRect();
              if (r.height < toi_thieu) {
                ra.push({ chu: b.textContent.trim().slice(0, 20), cao: Math.round(r.height) });
              }
            }
            return ra;
          }, CHAM_TOI_THIEU);
          // 🔴 CON SO 27px TUNG LAM TOI VA MOT THU KHONG HONG.
          //
          //    Lat do dau tien bao "nut cao 27px" va toi da them mot luat
          //    `@media (pointer: coarse)` vao `chatltt.css`. Ca hai deu sai:
          //
          //      · 27px chi xuat hien khi gia lap MAN HEP MA KHONG gia lap CAM
          //        UNG — tuc mot may tinh co cua so nho, noi 27px vua mat;
          //      · va nen tang DA CO san luat do tu truoc, `ltt.css` dong 44:
          //        `@media(pointer:coarse){ :where(button,...){min-height:44px} }`
          //
          // ⭐ Nen bo kiem phai bat cam ung (xem `trongKhung`), va hang muc nay
          //    chot lai chinh cai luat cua NEN TANG — no khong them luat moi.
          if (nho.length) {
            // ⛔ Khong phai bat be thâm my: 44px la nguong cua Apple HIG va
            //    WCAG 2.5.5. Duoi muc do, ty le cham truot tang ro tren man
            //    cam tay — va o day mot cu cham truot la mot lan TIEU TIEN sai.
            throw new Error(`nut media nho hon ${CHAM_TOI_THIEU}px: ${JSON.stringify(nho)}`);
          }
          return { nguong_px: CHAM_TOI_THIEU, so_nut_da_do: soNut, tat_ca_dat: true };
        });
      },
    },
    {
      dot: 8,
      // Ca dot 8 do BO CUC, khong doc cau tra loi cua model.
      doc_lap_voi_model: true,
      ten: '8.5-khong-cuon-ngang-o-moi-be-rong',
      hoi: 'Có bề rộng nào làm trang cuộn ngang không?',
      async chay(p) {
        const xau = [];
        for (const rong of [320, 360, 390, 414]) {
          const k = await trongKhung(p, { rong, cao: CAO }, async () => {
            await cho(400);
            return p.evaluate(() => ({
              sw: document.documentElement.scrollWidth,
              cw: document.documentElement.clientWidth,
            }));
          });
          if (k.sw > k.cw + 1) xau.push({ rong, thua: k.sw - k.cw });
        }
        if (xau.length) throw new Error(`cuon ngang o: ${JSON.stringify(xau)}`);
        return { da_do: [320, 360, 390, 414], khong_cuon_ngang: true };
      },
    },
  ];
}
