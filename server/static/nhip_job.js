/* nhip_job.js — MOT nhip hoi trang thai job cho ca nen tang.
 *
 *     LTT.nhipJob({
 *       hoi:  async () => { ...tra ve true neu CON viec de hoi... },
 *       nhip: 1200,          // mili giay giua hai luot khi moi thu binh thuong
 *     });
 *
 * ## Vi sao tep nay ton tai
 *
 * Do ngay 05/09: **nam** cho tu viet vong hoi trang thai job, va **khong cho
 * nao** xu ly `visibilitychange`:
 *
 *     apps/taoanh/templates/image.html          setTimeout 1200ms
 *     apps/prompt_ai_ommi/templates/...html     setInterval 1600ms
 *     frontend/autosub-studio/src/StudioShell    setInterval
 *     frontend/chatltt/src/App.tsx              setInterval (hai cho)
 *
 * Trong khi `server/templates/job_detail.html` — trang job cua chinh nen tang —
 * **da lam dung tu lau**: lui theo cap so nhan khi loi, hoa lai ngay khi tab
 * hien lai, thu lai khi `online`, dung han khi roi trang.
 *
 * ⭐ Nen day khong phai mot thiet ke moi. Day la viec **ngung de mot ban dung
 *    nam im mot cho**.
 *
 * ## Vi sao no quan trong tren dien thoai chu khong chi la "cho gon"
 *
 * Mot tab bi an van hoi may chu **1.200 mili giay mot lan**. Tren dien thoai do
 * la pin va dung luong 3G cua khach chay trong khi ho dang lam viec khac — va
 * job thi van chay o may chu du khong ai hoi. Khi khoa may roi mo lai, thu ho
 * can khong phai mot nhip hoi lien tuc, ma la **mot cau tra loi ngay lap tuc**.
 *
 * ## Ranh gioi
 *
 * ⛔ Trang thai job o MAY CHU la chan ly. Tab bi an chi **giam nhip hoi**, no
 *    khong quyet dinh job con song hay khong.
 * ⛔ `navigator.onLine` chi la GOI Y. Mot request that moi la bang chung — nen
 *    su kien `online` o day chi kich hoat mot luot hoi som, khong duoc dung de
 *    ket luan may chu voi toi duoc.
 * ⛔ Khong phu thuoc Background Sync: no khong co o Safari, va mot duong song
 *    con cua san pham khong duoc dat tren mot API mot trinh duyet co.
 */
(function () {
  "use strict";
  var LTT = (window.LTT = window.LTT || {});

  /* @param {object} c
   * @param {function(): Promise<boolean>} c.hoi  hoi may chu mot luot.
   *        Tra `true` = CON viec dang chay, hen luot sau.
   *        Tra `false` = xong het, dung han.
   *        Nem = coi nhu loi mang: lui nhip roi thu lai.
   * @param {number} [c.nhip]     mili giay khi binh thuong (mac dinh 1500)
   * @param {number} [c.nhipToiDa] tran khi lui (mac dinh 30000)
   * @returns {{dung: function()}}
   */
  LTT.nhipJob = function (c) {
    var hoi = c.hoi;
    var nhipGoc = c.nhip || 1500;
    var nhipToiDa = c.nhipToiDa || 30000;
    var nhip = nhipGoc;
    var hen = 0;
    var daDung = false;
    var dangChay = false;

    function huy() { if (hen) { clearTimeout(hen); hen = 0; } }

    function datHen(sau) {
      huy();
      if (daDung) return;
      hen = setTimeout(chay, sau);
    }

    async function chay() {
      hen = 0;
      if (daDung || dangChay) return;
      /* ⭐ Tab an thi KHONG hoi — nhung cung khong dung han: ta hen lai mot
       *    nhip dai de neu `visibilitychange` khong ban (WebView cu), vong lap
       *    van song thay vi chet im. */
      if (document.hidden) { datHen(nhipToiDa); return; }
      dangChay = true;
      try {
        var con = await hoi();
        nhip = nhipGoc;                       /* thanh cong -> ve nhip goc */
        if (con === false) { daDung = true; huy(); return; }
        datHen(nhip);
      } catch (e) {
        /* Lui theo cap so nhan. Mot may chu dang chat ma bi hoi day hon la mot
           may chu chat hon. */
        nhip = Math.min(nhip * 2, nhipToiDa);
        datHen(nhip);
      } finally {
        dangChay = false;
      }
    }

    function hoaLaiNgay() {
      if (daDung || document.hidden) return;
      nhip = nhipGoc;
      datHen(0);
    }

    document.addEventListener("visibilitychange", hoaLaiNgay);
    window.addEventListener("pageshow", hoaLaiNgay);
    window.addEventListener("online", hoaLaiNgay);
    /* ⚠️ `beforeunload` chu khong phai `unload`: `unload` khong ban tren iOS
     *    Safari khi nguoi dung chuyen tab, va mot vong lap khong duoc don la
     *    mot vong lap con hoi sau khi trang da di. */
    window.addEventListener("beforeunload", function () { daDung = true; huy(); });

    datHen(0);
    return { dung: function () { daDung = true; huy(); } };
  };
})();
