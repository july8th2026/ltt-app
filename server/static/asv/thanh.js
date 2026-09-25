/* asv/thanh.js — THANH HANH DONG: ba bo dem song + nut chinh biet noi.
 *
 * Khuon lay tu GUI tham chieu (`D:\Viral`), nhung **van hanh viet lai cho SaaS**:
 * o do bo dem dem "0 video / 1 ngon ngu / 0 ket qua" cua mot lo hang loat chay
 * ngay trong tien trinh; o day mot lan chay la MOT video, di qua hang doi job va
 * **ton credit**, nen ba con so dung nghia o ta la: video nao · long tieng sang
 * dau · het bao nhieu.
 *
 * Hai viec, khong viec nao la logic nghiep vu:
 *
 *   1. Ba bo dem — doc lai tu chinh cac o khach vua sua
 *   2. Nut chinh: gop SO LY DO cua `asv/nen.js` roi ghi `disabled` + cau vi sao
 *
 * 🔴 **Viec thu hai la ca ly do tep nay ton tai.** `xem_truoc.js` tung ghi
 *    `disabled` truc tiep, va no dung **chung nao chi co mot ly do**. Ly do thu
 *    hai — *chua chon video* — thuoc ve mot cho khac, va hai module cung ghi mot
 *    thuoc tinh thi nguoi chay sau mo lai cai nguoi kia vua dong. Nen o day:
 *    mot nguoi ghi, moi nguoi khac **bao** (`ASV.datChan`).
 *
 * ⛔ Khong chuoi tieng Viet nao trong tep nay. Nhan lay tu `#asv-chu`, va nhan
 *    ngon ngu lay tu chinh `<option>` khach dang chon — tuc tu bang cua
 *    `ngon_ngu.py`, khong tu mot ban sao o JavaScript.
 */
(function () {
  "use strict";
  if (!window.ASV || !ASV.co) return;

  var t = ASV.t;
  var chu = ASV.chu;

  var nut = document.getElementById("asv-batdau");
  var viSao = document.getElementById("asv-batdau-vi-sao");
  var demVideo = document.getElementById("asv-dem-video");
  var demLan = document.getElementById("asv-dem-lan");
  var oTep = document.getElementById("asv-video");
  var oLan = document.getElementById("asv-nn-dich");
  if (!nut) return;

  /* ── Nut chinh ────────────────────────────────────────────────────────── */

  function veNut() {
    var ly = ASV.lyDoChan();
    nut.disabled = !!ly;
    /* ⛔ Xoa cau khi khong con ly do, khong giu cau cu. Mot nut BAM DUOC kem
     *    dong chu "Chon video de bat dau" la mot man hinh tu noi nguoc minh. */
    if (viSao) {
      chu(viSao, ly ? t(ly.khoa, ly.thay) : "");
      viSao.hidden = !ly;
    }
  }

  ASV.khiDoiChan(veNut);

  /* ── Bo dem 1: video ──────────────────────────────────────────────────────
   *
   * ⭐ Cung mot su kien `change` da nuoi `xem_truoc.js`, nhung KHONG doc lai
   *    ket qua cua no: hai module doc cung mot `input.files`, khong ai doc DOM
   *    cua ai. Doc DOM cua module khac la buoc thu tu thuc thi tro lai. */
  function demTep() {
    var f = oTep && oTep.files && oTep.files[0];
    if (!f) {
      ASV.datChan("chua_chon", "chua_chon_video");
      return;
    }
    var mb = (f.size / (1024 * 1024)).toFixed(1);
    chu(demVideo, f.name + " · " + mb + " MB");
    ASV.datChan("chua_chon", "");
  }

  if (oTep) oTep.addEventListener("change", demTep);

  /* ── Bo dem 2: ngon ngu dich ──────────────────────────────────────────────
   *
   * ⛔ Nhan doc tu `<option>` dang chon, khong tu mot bang trong tep nay. Bang
   *    that song o `ngon_ngu.NHAN`; mot ban sao o day se troi ngay lan dau ai
   *    them mot ngon ngu, va troi im lang. */
  function demLanDich() {
    if (!oLan || !demLan) return;
    var o = oLan.options[oLan.selectedIndex];
    chu(demLan, (o && o.textContent.trim()) || "—");
  }

  if (oLan) oLan.addEventListener("change", demLanDich);

  /* Trang co the nap voi cai dat cu da dien san (`?run_id=`), nen doc mot lan
   * luc khoi dong chu khong cho su kien dau tien. */
  demTep();
  demLanDich();
  veNut();
})();
