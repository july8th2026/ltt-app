/* asv/bien_tap.js — KHUNG HINH + TOC DO (asv-final 22/09).
 *
 * Bon dieu khien -> MOT o an `bien_tap` (JSON). May chu duyet lai o
 * `bien_tap.tu_form` — day chi dong goi, khong phai phep kiem thu hai.
 *
 * ⛔ Ho so VANG MAT khi moi thu la mac dinh: cung luat `cai_dat.KHOA_THUA`
 *    (xem `asv/am_thanh.js`). May chu cung tra `None` cho ho so rong.
 *
 * ⛔ Khong kep ve bien: cat mep qua nhieu thi GUI NGUYEN de may chu tu choi
 *    bang cau cua no — dong chu duoi khoi chi nhac som (luat L2 `vung_che`).
 *
 * ⭐ MOT tam (ngang/doc) dung cho ca phong to lan cat-theo-ti-le: ca hai deu
 *    la "giu phan nao cua khung". Hai cap o tam cho hai buoc lien tiep la hai
 *    thu khach phai hieu thu tu cua chung.
 */
(function () {
  "use strict";
  if (!window.ASV || !ASV.co) return;

  var t = ASV.t;
  var nhom = document.getElementById("asv-nhom-bien-tap");
  var khoi = nhom && nhom.querySelector(".asv-bt-o");
  var chan = document.getElementById("asv-bt-chan");
  var oBt = document.getElementById("asv-bien-tap");
  var tt = document.getElementById("asv-bt-tt");
  if (!nhom || !oBt) return;

  function o(id) { return document.getElementById("asv-bt-" + id); }
  var oToc = o("toc"), oTiLe = o("ti-le"), oCach = o("cach"), oZoom = o("zoom");
  var oTamX = o("tam-x"), oTamY = o("tam-y");
  var oCat = { trai: o("cat-trai"), phai: o("cat-phai"),
               tren: o("cat-tren"), duoi: o("cat-duoi") };
  var oLat = o("lat-guong"), oMau = o("dich-mau");
  var tatCa = [oToc, oTiLe, oCach, oZoom, oTamX, oTamY,
               oCat.trai, oCat.phai, oCat.tren, oCat.duoi, oLat, oMau];

  function so(el, macDinh) {
    var v = parseFloat(el && el.value);
    return isNaN(v) ? macDinh : v;
  }
  function tron(x) { return Math.round(x * 10000) / 10000; }

  function dongBo() {
    var ho = {}, ds = [];
    var toc = so(oToc, 1);
    if (toc !== 1) { ho.toc_do = toc; ds.push(toc + "×"); }

    var tamX = tron(so(oTamX, 50) / 100), tamY = tron(so(oTamY, 50) / 100);

    var c = { trai: so(oCat.trai, 0), phai: so(oCat.phai, 0),
              tren: so(oCat.tren, 0), duoi: so(oCat.duoi, 0) };
    if (c.trai || c.phai || c.tren || c.duoi) {
      ho.cat_khung = { x0: tron(c.trai / 100), x1: tron(1 - c.phai / 100),
                       y0: tron(c.tren / 100), y1: tron(1 - c.duoi / 100) };
      ds.push(t("bt_cat_mep"));
    }

    var z = so(oZoom, 1);
    if (z !== 1) {
      ho.zoom = { he_so: z };
      if (tamX !== 0.5) ho.zoom.tam_x = tamX;
      if (tamY !== 0.5) ho.zoom.tam_y = tamY;
      ds.push(t("bt_phong", { z: z }));
    }

    var tl = oTiLe && oTiLe.value;
    if (oCach) oCach.disabled = !tl;
    if (tl) {
      var cach = (oCach && oCach.value) || "cat";
      ho.khung = { ti_le: tl, cach: cach };
      if (cach === "cat") {
        if (tamX !== 0.5) ho.khung.tam_x = tamX;
        if (tamY !== 0.5) ho.khung.tam_y = tamY;
      }
      ds.push(tl);
    }

    /* ⭐ Hai co: `true` chu khong `"on"`. May chu tu choi moi gia tri khac
     *    `true`/`false` (`bien_tap.chuan_hoa`), va do la co chu dich — mot
     *    chuoi `"false"` la mot gia tri "that" trong JavaScript. */
    if (oLat && oLat.checked) { ho.lat_guong = true; ds.push(t("bt_lat_guong")); }
    if (oMau && oMau.checked) { ho.dich_mau = true; ds.push(t("bt_dich_mau")); }

    /* ⛔ Khong o chet: tam chi co nghia khi co phong to hoac cat theo ti le. */
    var canTam = z !== 1 || !!(ho.khung && ho.khung.cach === "cat");
    if (oTamX) oTamX.disabled = !canTam;
    if (oTamY) oTamY.disabled = !canTam;

    oBt.value = Object.keys(ho).length ? JSON.stringify(ho) : "";
    var min = parseFloat(nhom.getAttribute("data-canh-min")) || 20;
    if (100 - c.trai - c.phai < min || 100 - c.tren - c.duoi < min) {
      ASV.chu(tt, t("bt_cat_qua_nhieu", { p: min }));
    } else {
      ASV.chu(tt, ds.length ? t("bt_tom_tat", { ds: ds.join(" · ") })
                            : t("bt_mac_dinh"));
    }
  }

  function veMacDinh() {
    if (oToc) oToc.value = "1";
    if (oTiLe) oTiLe.value = "";
    if (oCach) oCach.value = "cat";
    if (oZoom) oZoom.value = "1";
    if (oTamX) oTamX.value = "50";
    if (oTamY) oTamY.value = "50";
    Object.keys(oCat).forEach(function (k) { if (oCat[k]) oCat[k].value = "0"; });
    if (oLat) oLat.checked = false;
    if (oMau) oMau.checked = false;
  }

  /* ⛔ Doi sang preset giu hinh ma chi AN khoi la giu lai gia tri trong form —
   *    may chu se tu choi ca lan chay. Ve mac dinh han, cung luat `asv/cat.js`. */
  function theoPreset() {
    var duoc = ASV.hopPreset(nhom);
    if (khoi) khoi.hidden = !duoc;
    if (chan) chan.hidden = duoc;
    if (!duoc) veMacDinh();
    dongBo();
  }

  tatCa.forEach(function (el) {
    if (!el) return;
    el.addEventListener("input", dongBo);
    el.addEventListener("change", dongBo);
  });
  ASV.khiDoiPreset(theoPreset);
  theoPreset();
})();
