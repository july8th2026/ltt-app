/* asv/cat.js — CAT dau/cuoi.
 *
 * ⭐ Khach nhap GIAY, may chu nhan PHAN SO. Doi don vi xay ra o day va chi o
 *    day, vi day la noi duy nhat phia khach biet `video.duration`.
 *
 * ⛔ **Khong kep ve bien, khong dao lai.** `cat_dau_cuoi` L2 noi thang: mot
 *    cua so bi "sua ho" thanh hop le se duoc thi hanh, tuc ta cat mot doan
 *    khach khong chon va khach khong co cach nao biet. Nen o day ta gui
 *    NGUYEN thu khach nhap va de may chu tu choi — mot bo luat, mot cho phat
 *    bieu. Dong chu duoi o chi la mot loi nhac som, khong phai mot phep kiem
 *    thu hai.
 */
(function () {
  "use strict";
  if (!window.ASV || !ASV.co) return;

  var t = ASV.t;
  var chu = ASV.chu;

  var nhomCat = document.getElementById("asv-nhom-cat");
  var chanCat = document.getElementById("asv-cat-chan");
  var oCatTu = document.getElementById("asv-cat-tu");
  var oCatDen = document.getElementById("asv-cat-den");
  var oCat = document.getElementById("asv-cat");
  var ttCat = document.getElementById("asv-cat-tt");
  var nutCatXoa = document.getElementById("asv-cat-xoa");
  var oCatO = document.querySelector(".asv-cat-o");

  /* Cung hang so voi `cat_dau_cuoi.TOI_THIEU`. Hai ban cua mot nguong la hai
     ban se lech — nhung ban o day chi de NOI SOM, con ban cuong che nam o may
     chu, nen lech chi lam loi toi muon hon chu khong lam sai ket qua. */
  var TOI_THIEU_CAT = 0.02;

  /* ⭐ Hai o mac dinh `disabled`, va chi mo khi da biet thoi luong. Mot o nhan
   *    GIAY trong khi chua ai biet video dai bao nhieu la mot o khong the doi
   *    ra phan so — khach go vao do se gui len mot con so vo nghia. */
  function batCat(giay) {
    if (oCatTu) { oCatTu.disabled = false; oCatTu.max = String(giay); }
    if (oCatDen) {
      oCatDen.disabled = false;
      oCatDen.max = String(giay);
      oCatDen.placeholder = giay.toFixed(1);
    }
    tinhCat();
  }

  function xoaCat() {
    if (oCatTu) oCatTu.value = "";
    if (oCatDen) oCatDen.value = "";
    if (oCat) oCat.value = "";
    chu(ttCat, t("cat_ca_video"));
  }

  function tinhCat() {
    if (!oCat) return;
    var thoiLuongVideo = ASV.thoiLuongVideo;
    if (!(thoiLuongVideo > 0)) { oCat.value = ""; return; }
    var coA = oCatTu && oCatTu.value !== "";
    var coB = oCatDen && oCatDen.value !== "";
    if (!coA && !coB) { oCat.value = ""; chu(ttCat, t("cat_ca_video")); return; }

    var a = coA ? parseFloat(oCatTu.value) : 0;
    var b = coB ? parseFloat(oCatDen.value) : thoiLuongVideo;
    if (!isFinite(a) || !isFinite(b)) {
      oCat.value = ""; chu(ttCat, t("cat_khong_doc_duoc")); return;
    }
    var fa = a / thoiLuongVideo, fb = b / thoiLuongVideo;
    /* L4: khong thu hep gi thi khong gui gi. */
    if (fa <= 0 && fb >= 1) { oCat.value = ""; chu(ttCat, t("cat_ca_video")); return; }

    oCat.value = JSON.stringify([fa, fb]);
    if (!(fa >= 0 && fa < fb && fb <= 1)) { chu(ttCat, t("cat_ngoai_khoang")); return; }
    if (fb - fa < TOI_THIEU_CAT) { chu(ttCat, t("cat_qua_ngan")); return; }
    chu(ttCat, t("cat_con_lai", { giay: ASV.phutGiay(b - a) }));
  }

  if (oCatTu) oCatTu.addEventListener("input", tinhCat);
  if (oCatDen) oCatDen.addEventListener("input", tinhCat);
  if (nutCatXoa) nutCatXoa.addEventListener("click", xoaCat);

  /* ⛔ Doi preset ma chi AN o nhap di la giu lai dung cai loi vua tranh: gia
   *    tri van di theo form len may chu. Xoa han — cung luat voi vung che. */
  function capNhatCatTheoPreset() {
    if (!nhomCat) return;
    var duoc = ASV.hopPreset(nhomCat);
    if (oCatO) oCatO.hidden = !duoc;
    if (chanCat) chanCat.hidden = duoc;
    if (!duoc) xoaCat();
  }

  ASV.khiDoiPreset(capNhatCatTheoPreset);
  capNhatCatTheoPreset();
  ASV.khiCoVideo(batCat);
})();
