/* asv/am_thanh.js — AM THANH (V6 pha 23).
 *
 * 🔴 **MOT thanh muc, khong phai hai.** Ban phoi ket thuc bang `loudnorm` dua
 *    ca ban ve -14 LUFS, nen "giong +3 / nen -3" va "giong 0 / nen -6" ra CUNG
 *    mot tep (do o `PHA23_AUDIO_STUDIO.md` §1). Mot thanh "muc giong" o day se la
 *    mot thanh keo khong lam gi — khach keo len, ban ra khong to hon.
 *
 * ⭐ Am thanh khong cham diem anh, nen khoi nay KHONG an theo preset — khac bon
 *    module sua hinh. Ca hai preset deu tron lai ban phoi.
 *
 * ⛔ Ho so VANG MAT khi khach khong doi gi: mot `{}` hay mot ho so "mac dinh"
 *    gui o moi lan chay se lam ho so cua nhung lan khong chinh am thanh khac di
 *    ma khong vi ly do gi — dung dieu `cai_dat.KHOA_THUA` ton tai de tranh.
 *    May chu cung tra ve `None` cho ho so bang mac dinh (`am_thanh.tu_form`).
 */
(function () {
  "use strict";
  if (!window.ASV || !ASV.co) return;

  var nhom = document.getElementById("asv-nhom-am-thanh");
  var oNen = document.getElementById("asv-am-nen");
  var soNen = document.getElementById("asv-am-nen-so");
  var oTat = document.getElementById("asv-am-tat-nen");
  var oHa = document.getElementById("asv-am-ha-theo-loi");
  var oVao = document.getElementById("asv-am-fade-vao");
  var oRa = document.getElementById("asv-am-fade-ra");
  var oAm = document.getElementById("asv-am-thanh");
  if (!nhom || !oNen || !oAm) return;

  /* Mac dinh den tu MAY CHU (`am_thanh.cho_giao_dien`), khong go o day. */
  var MAC_DINH = parseFloat(nhom.getAttribute("data-nen-mac-dinh"));

  function so(o) {
    var v = parseFloat(o && o.value);
    return isNaN(v) ? 0 : v;
  }

  function dongBo() {
    var tat = !!(oTat && oTat.checked);
    /* ⛔ Tat nen thi "ha nen theo loi" khong con gi de ha — may chu TU CHOI to
     *    hop do. Bo chon + khoa o day de khach khong gui mot lua chon vo nghia. */
    oNen.disabled = tat;
    if (oHa) {
      if (tat) oHa.checked = false;
      oHa.disabled = tat;
    }
    var nen = so(oNen);
    if (soNen) soNen.textContent = tat ? "—" : nen + " dB";
    oNen.setAttribute("aria-valuetext", nen + " dB");

    var ho = {};
    if (tat) ho.nen_db = null;
    else if (nen !== MAC_DINH) ho.nen_db = nen;
    if (oHa && oHa.checked) ho.giam_theo_loi = true;
    if (so(oVao) > 0) ho.fade_vao = so(oVao);
    if (so(oRa) > 0) ho.fade_ra = so(oRa);
    oAm.value = Object.keys(ho).length ? JSON.stringify(ho) : "";
  }

  [oNen, oTat, oHa, oVao, oRa].forEach(function (o) {
    if (!o) return;
    o.addEventListener("input", dongBo);
    o.addEventListener("change", dongBo);
  });
  dongBo();
})();
