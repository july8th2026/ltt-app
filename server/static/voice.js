/* voice.js — hanh vi dung chung cua LTT Voice Studio.
 *
 * ⭐ MOT TEP CHO CA SAU MAN, khong mot tep moi trang. Sau man deu chep ma giong,
 *    deu theo doi mot job dang chay — va nhung thu do viet lai sau lan la sau
 *    ban se lech nhau.
 *
 * ⭐ Tang cuong dan (progressive enhancement): khong co JS thi trang van doc va
 *    dung duoc, chi mat vai tien nghi. Khong phu thuoc thu vien nao — CSP cua
 *    nen tang chan CDN ngoai.
 *
 * ⚠️ PHAI dinh `?v={{ asset_ver }}` o cho nap tep nay. Static di qua Cloudflare
 *    co TTL; doi tep ma URL khong doi thi khach nhan ban cu toi khi het TTL.
 *    CLAUDE.md quy tac 6 — da dinh that mot lan voi `ltt.css` (4 gio).
 *
 * ⛔ TEP NAY CHI CHUA THU DANG CO NGUOI DUNG. Khong them san ham cho man chua
 *    xay: ma khong ai goi la ma khong ai kiem, va no se lech khoi cho no phuc vu
 *    truoc khi cho do kip ra doi. Dem ky tu, ve song am va theo doi job se vao
 *    day o P2 — cung luc man Studio that su goi chung.
 */
(function () {
  "use strict";

  /* ── Chep ma giong ────────────────────────────────────────────────────────
   *
   * 🔴 `voice_id` la hop dong dai han: `tables.py` cam ket no khong bao gio doi,
   *    ke ca khi len engine moi. Khach dan no vao ma nguon cua ho. Chep hut mot
   *    ky tu thi loi hien ra o tan luc goi API duoi dang "khong tim thay giong"
   *    — mot thong diep tro sai cho hoan toan.
   *
   * ⚠️ `navigator.clipboard` chi ton tai tren ngu canh bao mat (https hoac
   *    localhost). Trang nay luon https, nhung van phai kiem — thieu buoc do thi
   *    tren mot ngu canh la nut se nem loi va KHONG NOI GI, dung kieu hong im
   *    lang ma du an nay da tra gia nhieu lan.
   */
  function ganChep(nut) {
    if (nut.dataset.ganChep === "1") return;
    nut.dataset.ganChep = "1";

    var goc = nut.textContent;
    var dongHo = null;

    function bao(chu, lop) {
      nut.textContent = chu;
      if (lop) nut.classList.add(lop);
      if (dongHo) clearTimeout(dongHo);
      dongHo = setTimeout(function () {
        nut.textContent = goc;
        nut.classList.remove("da");
      }, 1600);
    }

    nut.addEventListener("click", function () {
      var ma = nut.dataset.ma || "";
      if (!ma) return;
      // Noi that la khong chep duoc, thay vi im lang nhu chua bam.
      var hong = function () { bao("Ctrl+C", null); };
      if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(ma).then(function () {
          bao("✓", "da");
        }, hong);
      } else {
        hong();
      }
    });
  }

  function chay(goc) {
    var pv = goc || document;
    var ds = pv.querySelectorAll(".lv-ma-chep");
    for (var i = 0; i < ds.length; i++) ganChep(ds[i]);
  }

  /* ── Luoi giong: loc + chon the + panel chi tiet ──────────────────────────
   *
   * ⭐ LOC PHIA TRINH DUYET, khong goi may chu.
   *
   *    Tap du lieu la HAI MUOI giong mau cong vai giong rieng — no da nam san
   *    tren trang. Goi mot vong mang cho moi lan bam mot nut loc la tra mot cai
   *    gia that cho mot thu da biet, va no bien mot thao tac tuc thi thanh mot
   *    thao tac co do tre. Ngay tap nay lon toi muc phai phan trang thi doi
   *    sang loc phia may chu — nhung do la mot van de chua ton tai.
   *
   * ⛔ Doi lai: moi the phai mang du du lieu de loc trong `data-*`. Thieu mot
   *    thuoc tinh thi the do bien mat khoi luoi khi loc, va no bien mat IM
   *    LANG — khong loi nao bao.
   */
  function luoiGiong(cauHinh) {
    var luoi = document.getElementById("lv-luoi");
    if (!luoi) return;

    var cfg = cauHinh || {};
    var chu = cfg.chu || {};
    var chiTiet = cfg.chiTiet || {};
    var duong = cfg.duong || "";

    var the = [].slice.call(luoi.querySelectorAll(".lv-the"));
    var oTim = document.getElementById("lv-tim");
    var oSo = document.getElementById("lv-g-so");
    var oKhongHop = document.getElementById("lv-g-khonghop");
    var dangLoc = {loai: "", gioi: "", vung: "", phongcach: ""};

    function loc() {
      var q = ((oTim && oTim.value) || "").trim().toLowerCase();
      var con = 0;
      for (var i = 0; i < the.length; i++) {
        var t = the[i], d = t.dataset;
        // Giong nhan ban khong co ba mat cua giong mau. Khi mot mat do dang
        // duoc loc thi chung KHONG khop — va do la dung: loc "giong nu mien
        // Bac" ma van tra ve mot giong rieng chua phan loai la tra ket qua sai.
        var hop =
          (!dangLoc.loai || d.loai === dangLoc.loai) &&
          (!dangLoc.gioi || d.gioi === dangLoc.gioi) &&
          (!dangLoc.vung || d.vung === dangLoc.vung) &&
          (!dangLoc.phongcach || d.phongcach === dangLoc.phongcach) &&
          (!q || (d.ten || "").toLowerCase().indexOf(q) >= 0);
        t.hidden = !hop;
        if (hop) con++;
      }
      if (oSo) oSo.textContent = String(con);
      if (oKhongHop) oKhongHop.hidden = con !== 0;
    }

    var nutLoc = document.querySelectorAll(".lv-loc-nut");
    for (var i = 0; i < nutLoc.length; i++) {
      (function (nut) {
        nut.addEventListener("click", function () {
          dangLoc[nut.dataset.loc] = nut.dataset.gt || "";
          // Chi mot nut sang trong moi nhom.
          var anhEm = nut.parentNode.querySelectorAll(".lv-loc-nut");
          for (var k = 0; k < anhEm.length; k++) anhEm[k].classList.remove("on");
          nut.classList.add("on");
          loc();
        });
      })(nutLoc[i]);
    }
    if (oTim) oTim.addEventListener("input", loc);

    /* ── Panel chi tiet ───────────────────────────────────────────────────── */
    var oCt = document.getElementById("lv-ct");
    var oCtRong = document.getElementById("lv-ct-rong");

    function dat(id, giaTri) {
      var o = document.getElementById(id);
      if (o) o.textContent = giaTri == null ? "" : String(giaTri);
    }

    function moChiTiet(t) {
      if (!oCt) return;
      var d = t.dataset;
      var laMau = d.loai === "mau";
      var ct = chiTiet[d.ma] || {};

      for (var k = 0; k < the.length; k++) {
        the[k].classList.remove("chon");
        the[k].setAttribute("aria-pressed", "false");
      }
      t.classList.add("chon");
      t.setAttribute("aria-pressed", "true");

      dat("lv-ct-ten", d.ten);
      dat("lv-ct-loai", laMau ? chu.mau : chu.cuaToi);
      dat("lv-ct-ma", d.ma);
      // Dong tinh chat CHI cho giong mau ("Nam · Mien Bac · Tin tuc"). Giong
      // nhan ban khong co ba mat do, va thu the cua no hien la trang thai —
      // thu da co dong rieng ngay duoi. Chep sang day thi panel noi "Ready"
      // hai lan trong bon dong, va lan thu hai khong them thong tin nao.
      var oTinh = t.querySelector(".lv-the-tinh");
      dat("lv-ct-tinh", (laMau && oTinh) ? oTinh.textContent.trim() : "");
      dat("lv-ct-tt", d.trangthai === "active" ? chu.sanSang
        : (d.trangthai === "dang_ghi_danh" ? chu.dangGhiDanh : chu.daTat));

      var nutChep = document.getElementById("lv-ct-chep");
      if (nutChep) nutChep.dataset.ma = d.ma;

      var nutDung = document.getElementById("lv-ct-dung");
      if (nutDung) {
        nutDung.href = duong + "?giong=" + encodeURIComponent(d.ma);
        // Giong dang ghi danh hoac da tat thi khong dung duoc. Mot lien ket dan
        // toi mot man se bao loi ngay la mot lien ket khong nen bam duoc.
        var dungDuoc = d.trangthai === "active";
        nutDung.classList.toggle("lv-tat", !dungDuoc);
        nutDung.setAttribute("aria-disabled", dungDuoc ? "false" : "true");
      }

      var khoiToi = document.getElementById("lv-ct-cuatoi");
      if (khoiToi) {
        khoiToi.hidden = laMau;
        if (!laMau) {
          dat("lv-ct-luot", ct.so_luot || 0);
          dat("lv-ct-phut", ct.phut || 0);
          dat("lv-ct-cuoi", ct.lan_cuoi || chu.chuaDung || "-");

          var oClip = document.getElementById("lv-ct-clip");
          if (oClip) {
            oClip.textContent = "";
            var ds = ct.clip || [];
            for (var j = 0; j < ds.length; j++) {
              var hang = document.createElement("div");
              hang.className = "lv-ct-clip-hang";
              var au = document.createElement("audio");
              au.controls = true; au.preload = "none"; au.src = ds[j].url;
              var nhan = document.createElement("small");
              nhan.textContent = ds[j].giay ? ds[j].giay + "s" : "";
              hang.appendChild(au); hang.appendChild(nhan);
              oClip.appendChild(hang);
            }
          }

          var form = document.getElementById("lv-ct-tat");
          if (form) {
            form.action = duong + "/giong/" + encodeURIComponent(d.ma) + "/tat";
            form.hidden = d.trangthai !== "active";
          }
        }
      }

      oCt.hidden = false;
      if (oCtRong) oCtRong.hidden = true;
      chay(oCt);          // gan lai nut chep ben trong panel
    }

    for (var m = 0; m < the.length; m++) {
      (function (t) {
        t.addEventListener("click", function (e) {
          // Nut "Dung" la mot lien ket that — dung nuot cu bam cua no.
          if (e.target.closest("a")) return;
          moChiTiet(t);
        });
        // The mang `role="button"` nen ban phim phai nhan ca Enter lan Space.
        t.addEventListener("keydown", function (e) {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            moChiTiet(t);
          }
        });
      })(the[m]);
    }

    loc();
  }

  // Cho phan duoc them sau (ket qua sinh, danh sach tai them) tu gan lai.
  window.LttVoice = { gan: chay, luoiGiong: luoiGiong };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () { chay(); });
  } else {
    chay();
  }
})();
