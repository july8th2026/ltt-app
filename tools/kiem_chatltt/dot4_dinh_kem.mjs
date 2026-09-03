/**
 * Đợt 4 — ĐÍNH KÈM VÀ VISION.
 *
 * 🔴 VÌ SAO ĐỢT NÀY XẾP CAO. Vision được xây **ngày 03/09** — mã mới nhất là mã
 *    ít mắt nhìn nhất. Và cộng đồng dính rất nhiều ở đúng vùng này:
 *
 *      · *Uploading multiple files fails entirely if any single file exceeds
 *        fileSizeLimit* — một tệp xấu giết cả lô.
 *      · *Images attached to messages don't send when using Azure storage*
 *      · *Using S3/Azure Blob Storage passes inaccessible URL for vision
 *        requests* — ta tránh bằng `data:` URI, và có phép kiểm chốt.
 *      · *Agent images frequently broken when using S3 CDN*
 *
 * ⛔ Ba trong bốn lỗi trên đều là **kho lưu trữ** chứ không phải giao diện. Ta
 *    chạy `LocalStorage` hôm nay và R2 ngày mai (`platform_core/storage.py`),
 *    nên chúng là tương lai của ta chứ không phải chuyện của người khác.
 */

import { deflateSync } from 'node:zlib';

/**
 * PNG hợp lệ nhỏ nhất mà `platform_core/image_input.py` chấp nhận.
 *
 * ⚠️ 64 px mỗi chiều là sàn cứng (`image_input.py:47`). Dựng ảnh nhỏ hơn thì
 *    mọi hạng mục đính kèm đỏ cùng lúc với một thông báo về "kích thước" —
 *    không về thứ đang được kiểm. Đã trả giá một lần ở `test_633`.
 */
function pngBuffer(w, h) {
  const crc32 = (buf) => {
    let c = ~0;
    for (const b of buf) {
      c ^= b;
      for (let k = 0; k < 8; k += 1) c = (c >>> 1) ^ (0xEDB88320 & -(c & 1));
    }
    return (~c) >>> 0;
  };
  const chunk = (ten, d) => {
    const len = Buffer.alloc(4); len.writeUInt32BE(d.length);
    const than = Buffer.concat([Buffer.from(ten, 'ascii'), d]);
    const crc = Buffer.alloc(4); crc.writeUInt32BE(crc32(than));
    return Buffer.concat([len, than, crc]);
  };
  const hang = Buffer.concat([Buffer.from([0]), Buffer.alloc(w * 3, 0x80)]);
  const raw = Buffer.concat(Array.from({ length: h }, () => hang));
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(w, 0); ihdr.writeUInt32BE(h, 4);
  ihdr[8] = 8; ihdr[9] = 2;               // 8-bit, truecolor
  return Buffer.concat([
    Buffer.from([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A]),
    chunk('IHDR', ihdr),
    chunk('IDAT', deflateSync(raw)),
    chunk('IEND', Buffer.alloc(0)),
  ]);
}

const anhHopLe = (w = 64, h = 64) => ({
  name: `thu-${w}x${h}.png`, mimeType: 'image/png', buffer: pngBuffer(w, h),
});

export function dot4({ cho, doiDen, chuBaiCuoi, guiChu, xong, hoiThoaiMoi }) {
  /**
   * ⛔ DOI CATALOG VE TRUOC KHI DOC DANH SACH MODEL.
   *
   *    Ban dau ham nay doc `option` ngay. Luc do catalog chua ve, danh sach
   *    RONG, va no ket luan "khong co alias vision" — nen ca nam hang muc cua
   *    dot 4 bao BO QUA. Mot dot im lang bo qua chinh no la kieu hong te nhat:
   *    bao cao van xanh, va khong ai kiem gi ca.
   *
   *    Day la lan thu BA cung mot loi trong bo kiem nay (mac dinh model, mo
   *    hoi thoai moi, va gio la day). Cung mot goc: DOC TRUOC KHI DU LIEU TOI.
   */
  const chonVision = async (p) => {
    const sel = p.locator('select[aria-label="Chọn model"]');
    await doiDen('catalog da ve', async () =>
      (await sel.locator('option').count()) > 0, 30);
    const co = await sel.locator('option').evaluateAll((o) => o.map((x) => x.value));
    if (!co.includes('ltt_llm_vision')) return false;
    await sel.selectOption('ltt_llm_vision');
    await doiDen('o chon tep hien ra', async () =>
      (await p.locator('input[type=file]').count()) > 0, 15);
    return true;
  };

  return [
    {
      dot: 4,
      ten: '4.1-mot-tep-xau-KHONG-giet-ca-lo',
      hoi: 'Chọn 3 ảnh trong đó 1 ảnh hỏng — hai ảnh kia có lên được không?',
      async chay(p) {
        // 🔴 LibreChat dinh dung loi nay: *Uploading multiple files fails
        //    ENTIRELY if any single file exceeds fileSizeLimit*. Nguoi dung
        //    chon 10 anh, mot cai qua co, va mat het — phai lam lai tu dau ma
        //    khong biet cai nao co loi.
        await hoiThoaiMoi(p);
        if (!(await chonVision(p))) return { bo_qua: 'khong co alias vision' };
        await p.locator('input[type=file]').setInputFiles([
          anhHopLe(64, 64),
          { name: 'hong.png', mimeType: 'image/png', buffer: Buffer.from('khong phai anh') },
          anhHopLe(80, 80),
        ]);
        await cho(4000);
        const r = await p.evaluate(() => ({
          chip: [...document.querySelectorAll('.ltc-soan__anh-ten')].map((e) => e.textContent),
          loi: document.querySelector('.ltc-soan__loi')?.textContent || '',
        }));
        if (r.chip.length < 2) {
          throw new Error(`mot tep hong lam mat ca lo: chi con ${r.chip.length}/3 anh — ${JSON.stringify(r)}`);
        }
        if (!r.loi) throw new Error('bo qua tep hong MA KHONG noi gi — nguoi dung khong biet thieu anh');
        return r;
      },
    },
    {
      dot: 4,
      ten: '4.2-tu-choi-theo-BYTE-khong-theo-duoi-tep',
      hoi: 'Một tệp văn bản đổi đuôi thành .png có lọt không?',
      async chay(p) {
        await hoiThoaiMoi(p);
        if (!(await chonVision(p))) return { bo_qua: 'khong co alias vision' };
        await p.locator('input[type=file]').setInputFiles([{
          name: 'giavo.png', mimeType: 'image/png',
          buffer: Buffer.from('#!/bin/sh\necho khong phai anh dau\n'),
        }]);
        await cho(3500);
        const r = await p.evaluate(() => ({
          chip: [...document.querySelectorAll('.ltc-soan__anh-ten')].length,
          loi: document.querySelector('.ltc-soan__loi')?.textContent || '',
        }));
        if (r.chip > 0) throw new Error('tep GIA VO la anh da duoc nhan — kiem theo ten, khong theo byte');
        if (!r.loi) throw new Error('tu choi MA KHONG noi ly do');
        return r;
      },
    },
    {
      dot: 4,
      ten: '4.3-anh-song-qua-F5-va-dung-chu',
      hoi: 'Ảnh đã gửi có còn sau khi tải lại trang, và có đúng chủ không?',
      async chay(p) {
        await hoiThoaiMoi(p);
        if (!(await chonVision(p))) return { bo_qua: 'khong co alias vision' };
        await p.locator('input[type=file]').setInputFiles([anhHopLe(96, 72)]);
        await doiDen('anh da tai len', async () =>
          (await p.locator('.ltc-soan__anh-ten').count()) > 0, 25);
        await guiChu(p, 'Anh nay mau gi? Tra loi ngan.');
        await xong(p);

        await p.reload({ waitUntil: 'domcontentloaded' });
        await doiDen('hoi thoai hien lai', async () => (await p.locator('article').count()) >= 2, 30);
        const r = await p.evaluate(async () => {
          const im = document.querySelector('article img');
          if (!im) return { coAnh: false };
          const ok = await fetch(im.getAttribute('src')).then((x) => x.status).catch(() => 0);
          return { coAnh: true, rong: im.naturalWidth, cao: im.naturalHeight,
                   alt: im.alt, http: ok, src: im.getAttribute('src') };
        });
        if (!r.coAnh) throw new Error('anh bien mat sau F5');
        if (r.rong !== 96) throw new Error(`anh khong tai duoc (naturalWidth=${r.rong})`);
        if (!/bạn đã gửi/i.test(r.alt)) throw new Error(`alt sai cho anh NGUOI DUNG gui: ${JSON.stringify(r.alt)}`);
        if (!String(r.src).includes('/tai-san/')) throw new Error('anh khong di qua cua kiem so huu');
        return { rong: r.rong, cao: r.cao, http: r.http };
      },
    },
    {
      dot: 4,
      ten: '4.4-doi-sang-model-khong-doc-anh',
      hoi: 'Đính ảnh rồi đổi sang model text-only — có gửi lặng lẽ không?',
      async chay(p) {
        // ⛔ Truong hop te nhat: anh van dinh, model khong doc duoc, va he thong
        //    gui di ma khong noi gi. Khach tra tien cho mot luot ma model chua
        //    he thay thu ho hoi ve.
        await hoiThoaiMoi(p);
        if (!(await chonVision(p))) return { bo_qua: 'khong co alias vision' };
        await p.locator('input[type=file]').setInputFiles([anhHopLe()]);
        await doiDen('anh da tai len', async () =>
          (await p.locator('.ltc-soan__anh-ten').count()) > 0, 25);

        await p.locator('select[aria-label="Chọn model"]').selectOption('ltt_llm');
        await cho(1200);
        const r = await p.evaluate(() => ({
          oTep: document.querySelectorAll('input[type=file]').length,
          chip: [...document.querySelectorAll('.ltc-soan__anh-ten')].length,
        }));
        // O chon tep phai bien mat. Anh da dinh thi hoac bi go, hoac phai co
        // canh bao — im lang la lua chon duy nhat KHONG chap nhan duoc.
        if (r.oTep !== 0) throw new Error('model text-only van con o chon tep');
        if (r.chip > 0) {
          const loi = await p.evaluate(() =>
            (document.querySelector('.ltc-soan__loi')?.textContent || '')
            + (document.querySelector('[role=alert]')?.textContent || ''));
          if (!loi.trim()) {
            throw new Error('anh VAN dinh cho mot model khong doc anh, va khong mot canh bao nao');
          }
        }
        return r;
      },
    },
    {
      dot: 4,
      ten: '4.5-anh-KHONG-gui-cho-model-text-only',
      hoi: 'Máy chủ có thật sự từ chối ảnh cho model text-only không?',
      async chay(p) {
        // Kiem o TANG MAY CHU, khong tin giao dien: khoa anh di qua than JSON,
        // nen mot nguoi go tay van gui duoc du giao dien da an o chon tep.
        const r = await p.evaluate(async () => {
          // ⚠️ `data-csrf` tren goc React, do Jinja dat (`chatltt.html:7`).
          //    Khong phai `<meta name=csrf-token>` — doan sai thi moi request
          //    ghi tra 403, va hang muc bao "khong tao duoc hoi thoai de thu"
          //    thay vi kiem thu no sinh ra de kiem.
          const goc = document.querySelector('[data-csrf]');
          const csrf = goc?.getAttribute('data-csrf') || '';
          const hoi = await fetch('/chatltt/api/hoi-thoai', {
            method: 'POST', headers: { 'content-type': 'application/json', 'X-CSRF-Token': csrf },
            body: JSON.stringify({ model_alias: 'ltt_llm' }),
          }).then((x) => x.json()).catch(() => null);
          if (!hoi?.id) return { bo_qua: 'khong tao duoc hoi thoai de thu' };
          const r2 = await fetch(`/chatltt/api/hoi-thoai/${hoi.id}/luot`, {
            method: 'POST', headers: { 'content-type': 'application/json', 'X-CSRF-Token': csrf },
            body: JSON.stringify({ text: 'anh nay la gi', model_alias: 'ltt_llm',
                                   anh: ['chatltt/anh-vao/ai-do/khong-co-that.png'] }),
          });
          return { status: r2.status, than: (await r2.text()).slice(0, 200) };
        });
        if (r.bo_qua) return r;
        if (r.status === 202) throw new Error('may chu NHAN anh cho model text-only');
        if (r.status !== 400 && r.status !== 403) {
          throw new Error(`mong 400/403, nhan ${r.status}: ${r.than}`);
        }
        return r;
      },
    },
  ];
}
