/* asv/xem_truoc.js — o XEM TRUOC: chon tep, hien khung hinh, hoi uoc gia.
 *
 * Hai viec, va khong viec nao trong so do la "logic nghiep vu":
 *
 *   1. Xem truoc video khach vua chon   (URL.createObjectURL — khong tai len)
 *   2. Hoi may chu uoc gia theo do dai  (/uoc-tinh)
 *
 * ⛔ Khong tinh gia o day. `/uoc-tinh` la mot duong may chu co chu dinh: cong
 *    thuc gia la thu san pham, va mot ban thu hai trong JavaScript se troi khoi
 *    ban that ngay lan dau ai do sua mot con so.
 */
(function () {
  "use strict";
  if (!window.ASV || !ASV.co) return;

  var form = ASV.form;
  var t = ASV.t;
  var chu = ASV.chu;

  var oTep = document.getElementById("asv-video");
  var video = document.getElementById("asv-xem");
  var rong = document.getElementById("asv-rong");
  var lop = document.getElementById("asv-lop");
  var tenTep = document.getElementById("asv-tep-ten");
  var uocTien = document.getElementById("asv-uoc-tien");
  var uocGio = document.getElementById("asv-uoc-gio");
  var oVe = document.getElementById("asv-ve");

  function moTep() {
    var f = oTep && oTep.files && oTep.files[0];
    if (!f) return;

    // ⭐ `createObjectURL` — tep KHONG di dau ca. Khach thay khung hinh ngay,
    //    truoc khi mot byte nao roi khoi may ho.
    video.src = URL.createObjectURL(f);
    video.hidden = false;
    video.controls = true;
    if (lop) lop.hidden = false;
    if (rong) rong.hidden = true;

    var mb = (f.size / (1024 * 1024)).toFixed(1);
    chu(tenTep, f.name + " · " + mb + " MB");

    /* 🔴 **Tran phai la tran cua DUONG SE DUOC DUNG, khong phai tran nho nhat.**

       Truoc pha 08 dong nay luon do voi `data-tran-mb` (90 MB, tran cua duong
       multipart). Hau qua do duoc TREN TRINH DUYET: mot tep MP4 500 MB — dung
       thu ma duong BEN VUNG ton tai de cho — bi KHOA NUT ngay luc chon, kem
       cau *"vuot qua 90 MB"*.

       ⛔ Tuc ca tinh nang tai len truc tiep (tran 2 GiB, khong qua Cloudflare)
          **khong ai di toi duoc tu giao dien**, dung cho nhung tep no sinh ra
          de phuc vu. Nang luc co, khong ai di tren duong — va lan nay chinh
          hang rao chan duong.

       ⚠️ Hai duong nhan HAI tap kieu khac nhau (`x-matroska`/`webm` chi di duoc
          duong multipart), nen tran phu thuoc TEP chu khong phai mot hang so.

       ⚠️ `ASV.benVungKieuDuocKhong` do `asv/tai_len.js` dat. Loi goi nay xay ra
          luc khach CHON TEP — rat lau sau khi ca tam module da nap — nen thu tu
          the `<script>` khong anh huong gi o day. */
    var duocBenVung = !!(ASV.benVungKieuDuocKhong
                         && ASV.benVungKieuDuocKhong(f));
    var tran = parseInt(
      (duocBenVung ? (oVe && oVe.getAttribute("data-tran-ben-vung"))
                   : form.getAttribute("data-tran-mb")) || "0", 10);
    /* ⚠️ KHONG ghi `#asv-batdau.disabled` o day nua. Xem so ly do o
     *    `asv/nen.js`: mot thuoc tinh, mot nguoi ghi (`asv/thanh.js`). */
    if (tran > 0 && f.size > tran * 1024 * 1024) {
      /* Kieu khong di duoc duong ben vung thi noi RO ly do: doi sang MP4 la
         dung duoc ngay, con "cat ngan video" thi khong giai quyet gi. */
      chu(tenTep, f.name + " · "
          + t(duocBenVung ? "vuot_tran" : "vuot_tran_kieu", {mb: tran}));
      ASV.datChan("tep_lon", duocBenVung ? "vuot_tran" : "vuot_tran_kieu",
                  {mb: tran});
    } else {
      ASV.datChan("tep_lon", "");
    }
  }

  if (oTep) oTep.addEventListener("change", moTep);

  /* ── Uoc gia — hoi MAY CHU, khong tinh o day ───────────────────────────── */

  if (video) {
    video.addEventListener("loadedmetadata", function () {
      var giay = video.duration;
      if (!isFinite(giay) || giay <= 0) return;

      /* ⭐ Mot loi goi thay cho hai loi goi co thu tu bat buoc. `phatCoVideo`
       *    dat `ASV.thoiLuongVideo` TRUOC khi goi bat ky ai, nen phan CAT va
       *    danh sach VUNG khong con phu thuoc vao ai chay truoc. Xem ghi chu
       *    dai o `asv/nen.js` — day la cho rang buoc do tung song bang mot
       *    dong chu thich. */
      ASV.phatCoVideo(giay);

      var duong = form.getAttribute("data-uoc");
      if (!duong) return;
      fetch(duong + "?giay=" + encodeURIComponent(giay), {
        credentials: "same-origin"
      }).then(function (r) {
        return r.ok ? r.json() : null;
      }).then(function (d) {
        if (!d) return;
        // ⭐ Hien mot KHOANG, va can tren la thu khach thuc su doi mat.
        chu(uocTien, "~" + d.credit_thap + "–" + d.credit_cao
                     + " " + t("credit"));
        chu(uocGio, t("khoang") + " " + ASV.phutGiay(d.thoi_gian_giay));
      }).catch(function () {
        /* ⛔ Nuot CO CHU DICH: uoc gia hong khong duoc chan khach bat dau.
           Ho van thay so giu cho that o trang chi tiet. */
      });
    });
  }
})();
