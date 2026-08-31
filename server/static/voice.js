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

  /* ── Song am that, ve tu chinh tep vua sinh ───────────────────────────────
   *
   * ⭐ KHONG THU VIEN. `AudioContext.decodeAudioData` + mot `<canvas>` la du,
   *    va CSP cua nen tang chan CDN ngoai nen mot thu vien se phai tu-host —
   *    them mot tep nua phai nho dinh `?v=`.
   *
   * ⛔ CHI ve o cho co MOT tep cu the de ve. Hinh song trong luoi giong la SVG
   *    dung san, khong phai song that: giai ma mot tep tieng cho moi o trong
   *    mot luoi hai muoi o la tra mot cai gia that cho mot thu trang tri.
   *
   * ⚠️ `decodeAudioData` giai ma TOAN BO tep trong bo nho. Voi mot luot doc
   *    1.500 ky tu (~90 giay, WAV 48 kHz mono ~8,6 MB) thi on. Neu tran ky tu
   *    duoc noi nhieu lan thi cho nay phai doi sang doc dan — nhung do la mot
   *    van de chua ton tai, va no se bao bang mot khoang lag chu khong bang
   *    mot loi im lang.
   */
  function veSong(canvas, url) {
    if (!canvas || !url || !window.AudioContext) return;
    var Ctx = window.AudioContext || window.webkitAudioContext;
    fetch(url)
      .then(function (r) { return r.arrayBuffer(); })
      .then(function (buf) { return new Ctx().decodeAudioData(buf); })
      .then(function (am) {
        var dpr = window.devicePixelRatio || 1;
        var rong = canvas.clientWidth || 300;
        var cao = canvas.clientHeight || 72;
        canvas.width = Math.round(rong * dpr);
        canvas.height = Math.round(cao * dpr);
        var g = canvas.getContext("2d");
        g.scale(dpr, dpr);

        var du = am.getChannelData(0);
        var rongCot = 3, khe = 1;
        var soCot = Math.max(1, Math.floor(rong / rongCot));
        var moiCot = Math.floor(du.length / soCot) || 1;

        // Mau lay tu bien CSS, khong go cung — doi bang mau la doi mot cho.
        var mau = getComputedStyle(document.documentElement)
          .getPropertyValue("--brand-hover").trim() || "#ff514a";
        g.fillStyle = mau;

        for (var i = 0; i < soCot; i++) {
          var dinh = 0;
          for (var j = 0; j < moiCot; j++) {
            var v = Math.abs(du[i * moiCot + j] || 0);
            if (v > dinh) dinh = v;
          }
          var h = Math.max(2, dinh * cao * 0.92);
          g.fillRect(i * rongCot, (cao - h) / 2, rongCot - khe, h);
        }
      })
      .catch(function () {
        // Khong ve duoc song thi trinh phat van chay. An canvas di, dung de
        // mot o trong khong giai thich duoc.
        canvas.hidden = true;
      });
  }

  /* ── Man Studio ───────────────────────────────────────────────────────── */
  function studio(cauHinh) {
    var form = document.getElementById("lv-form");
    if (!form) return;

    var cfg = cauHinh || {};
    var chu = cfg.chu || {};
    var duong = cfg.duong || "";

    var oText = document.getElementById("lv-text");
    var oSo = document.getElementById("lv-so");
    var oUoc = document.getElementById("lv-uoc");
    var oUocDong = document.getElementById("lv-uoc-dong");
    var nutTao = document.getElementById("lv-nut-tao");

    /* Dem ky tu.
     * ⛔ Con so credit o day CHI de hien thi. So that do may chu tinh khi nop —
     *    hai cho tinh tien la hai cho lech nhau, nen cho nay khong bao gio duoc
     *    la nguon cua con so bi tru. No la mot uoc luong tho de khach khong bi
     *    bat ngo; `POST /xem-truoc` moi cho con so dung. */
    function dem() {
      var n = oText.value.length;
      oSo.textContent = String(n);
      var tran = cfg.tranKyTu || 0;
      if (tran) oSo.classList.toggle("sap-tran", n >= tran * 0.9);
      if (oUocDong) oUocDong.hidden = n === 0;
      if (oUoc && n) oUoc.textContent = String(Math.max(1, Math.ceil((1.5 + n / 18) * 0.2)));
    }
    oText.addEventListener("input", dem);
    dem();

    document.getElementById("lv-nut-xoa").addEventListener("click", function () {
      oText.value = ""; dem(); oText.focus();
      document.getElementById("lv-xt").hidden = true;
    });

    /* Xem truoc cach doc. */
    var oXt = document.getElementById("lv-xt");
    document.getElementById("lv-xt-dong").addEventListener("click", function () {
      oXt.hidden = true;
    });
    document.getElementById("lv-nut-xem").addEventListener("click", function () {
      var fd = new FormData();
      fd.append("csrf_token", form.csrf_token.value);
      fd.append("text", oText.value);
      fetch(duong + "/xem-truoc", {method: "POST", body: fd})
        .then(function (r) { return r.json(); })
        .then(function (d) {
          var oChu = document.getElementById("lv-xt-chu");
          var oGhi = document.getElementById("lv-xt-ghi");
          if (!d.ok) { oChu.textContent = d.loi || chu.khongXem; oGhi.textContent = ""; }
          else {
            oChu.textContent = d.da_chuan_hoa;
            var ghi = [];
            if (!d.doi_khac) ghi.push(chu.khongDoi);
            if (d.so_doan > 1) ghi.push((chu.doanNhieu || "").replace("{n}", d.so_doan));
            ghi.push(d.so_ky_tu + " / " + (cfg.tranKyTu || "?"));
            oGhi.textContent = ghi.join(" · ");
            // Con so nay den tu CHINH ham ra hoa don (`gia.uoc_tran`), nen no
            // khong the lech voi phan se bi tam giu.
            if (oUoc && d.uoc_credit != null) oUoc.textContent = String(d.uoc_credit);
          }
          oXt.hidden = false;
        })
        .catch(function () {
          document.getElementById("lv-xt-chu").textContent = chu.khongXem;
          document.getElementById("lv-xt-ghi").textContent = "";
          oXt.hidden = false;
        });
    });

    /* Nop + theo doi TAI CHO.
     *
     * ⭐ Ban truoc lam `window.location.href = '/jobs/' + id` — tuc bam Tao la
     *    ROI KHOI trang, mat van ban, va muon sinh lai thi phai go lai. Anh
     *    tham chieu 01 (va le thuong) muon ket qua hien ngay tai cho. */
    var oCho = document.getElementById("lv-kq-cho");
    var oChay = document.getElementById("lv-kq-chay");
    var oXong = document.getElementById("lv-kq-xong");
    var oLoi = document.getElementById("lv-kq-loi");
    var oTt = document.getElementById("lv-kq-tt");
    var oThanh = document.getElementById("lv-tiendo-thanh");
    var oBuoc = document.getElementById("lv-kq-buoc");
    var dongHo = null;

    function nhan(lop, chuNhan) {
      oTt.innerHTML = "";
      var s = document.createElement("span");
      s.className = "badge " + lop;
      var d = document.createElement("span"); d.className = "dot";
      s.appendChild(d); s.appendChild(document.createTextNode(chuNhan));
      oTt.appendChild(s);
    }

    function hien(cai) {
      oCho.hidden = cai !== "cho";
      oChay.hidden = cai !== "chay";
      oXong.hidden = cai !== "xong";
      oLoi.hidden = cai !== "loi";
    }

    function baoLoi(cau) {
      if (dongHo) clearTimeout(dongHo);
      oLoi.textContent = cau;
      hien("loi");
      nhan("b-err", chu.loi);
      nutTao.disabled = false;
    }

    function xong(d, jobId) {
      if (dongHo) clearTimeout(dongHo);
      hien("xong");
      nhan("b-ok", chu.xong);
      nutTao.disabled = false;

      var au = document.getElementById("lv-player");
      au.src = d.audio_url;
      var tai = document.getElementById("lv-tai");
      tai.href = d.audio_url;
      tai.setAttribute("download", "ltt-voice-" + jobId.slice(0, 8) + ".wav");
      document.getElementById("lv-mo-job").href = "/jobs/" + jobId;
      document.getElementById("lv-ct-giay").textContent =
        d.giay != null ? d.giay + "s" : "-";
      document.getElementById("lv-ct-credit").textContent =
        d.credit != null ? String(d.credit) : "-";
      document.getElementById("lv-ct-job").textContent = jobId;
      var nutChep = document.getElementById("lv-ct-job-chep");
      if (nutChep) { nutChep.dataset.ma = jobId; chay(oXong); }

      var canvas = document.getElementById("lv-song");
      canvas.hidden = false;
      veSong(canvas, d.audio_url);
    }

    function theoDoi(jobId, cho) {
      // Gian cach tang dan: nhanh luc dau (job ngan xong trong vai giay), thua
      // dan de mot job dai khong bien thanh mot may bom yeu cau.
      fetch(duong + "/ket-qua/" + encodeURIComponent(jobId))
        .then(function (r) {
          if (!r.ok) throw new Error("http " + r.status);
          return r.json();
        })
        .then(function (d) {
          if (d.trang_thai === "done") { xong(d, jobId); return; }
          if (d.trang_thai === "error" || d.trang_thai === "cancelled") {
            baoLoi(d.loi || chu.loi); return;
          }
          hien("chay");
          nhan("b-warn", d.trang_thai === "running" ? chu.dangTao : chu.dangCho);
          oThanh.style.width = (d.tien_do || 0) + "%";
          oThanh.setAttribute("aria-valuenow", String(d.tien_do || 0));
          oBuoc.textContent = d.trang_thai === "running" ? chu.dangTao : chu.dangCho;
          dongHo = setTimeout(function () {
            theoDoi(jobId, Math.min(cho * 1.4, 8000));
          }, cho);
        })
        .catch(function () {
          // Mang chap chon KHONG phai job hong. Noi ro va thu lai cham hon,
          // dung bao khach rang luot doc cua ho da that bai.
          oBuoc.textContent = chu.matKetNoi;
          dongHo = setTimeout(function () {
            theoDoi(jobId, Math.min(cho * 2, 15000));
          }, Math.min(cho * 2, 15000));
        });
    }

    form.addEventListener("submit", function (e) {
      e.preventDefault();
      if (dongHo) clearTimeout(dongHo);
      nutTao.disabled = true;
      hien("chay");
      nhan("b-warn", chu.dangCho);
      oThanh.style.width = "0%";
      oBuoc.textContent = chu.dangCho;

      var g = (form.querySelector('input[name="giong"]:checked') || {}).value || "";
      var fd = new FormData();
      fd.append("csrf_token", form.csrf_token.value);
      fd.append("text", oText.value);
      // Hai tien to, hai truong khac nhau o phia may chu — va
      // `features.chuan_hoa` TU CHOI neu gui ca hai.
      if (g.indexOf("v:") === 0) fd.append("voice_id", g.slice(2));
      else if (g.indexOf("m:") === 0) fd.append("preset", g.slice(2));

      fetch(duong + "/tao", {method: "POST", body: fd})
        .then(function (r) { return r.json(); })
        .then(function (d) {
          if (!d.ok) { baoLoi(d.loi); return; }
          theoDoi(d.job_id, 1200);
        })
        .catch(function () { baoLoi(chu.khongGui); });
    });

    /* Loc trong bo chon giong. */
    var dsMuc = [].slice.call(document.querySelectorAll(".lv-chon-muc"));
    var oTimChon = document.getElementById("lv-chon-tim");
    var oChonRong = document.getElementById("lv-chon-rong");
    var locLoai = "";

    function locChon() {
      var q = ((oTimChon && oTimChon.value) || "").trim().toLowerCase();
      var con = 0;
      for (var i = 0; i < dsMuc.length; i++) {
        var m = dsMuc[i], d = m.dataset;
        // Muc mac dinh (data-loai rong) LUON hien: no la loi thoat khi bo loc
        // khong con gi, va la thu khach chon neu ho khong muon nghi.
        var hop = d.loai === ""
          || ((!locLoai || d.loai === locLoai)
              && (!q || (d.ten || "").toLowerCase().indexOf(q) >= 0));
        m.hidden = !hop;
        if (hop && d.loai !== "") con++;
      }
      if (oChonRong) oChonRong.hidden = con !== 0;
    }

    var nutChonLoai = document.querySelectorAll("[data-chon-loai]");
    for (var i = 0; i < nutChonLoai.length; i++) {
      (function (nut) {
        nut.addEventListener("click", function () {
          locLoai = nut.dataset.chonLoai || "";
          var anhEm = nut.parentNode.querySelectorAll(".lv-loc-nut");
          for (var k = 0; k < anhEm.length; k++) anhEm[k].classList.remove("on");
          nut.classList.add("on");
          locChon();
        });
      })(nutChonLoai[i]);
    }
    if (oTimChon) oTimChon.addEventListener("input", locChon);

    chay();
  }

  /* ── Man Lich su: chon mot dong -> panel chi tiet ──────────────────────────
   *
   * ⭐ Loc o man nay chay PHIA MAY CHU (form GET), khac man Giong. Ly do: lich
   *    su co the dai va duoc doc theo tran, nen loc phia trinh duyet se loc tren
   *    mot tap DA BI CAT — tra ra it hon su that ma khong noi gi. Loc o may chu
   *    thi tran duoc ap SAU khi loc, va giao dien noi ro pham vi.
   *
   *    Doi lai: moi lan doi bo loc la mot vong tai trang. Chap nhan duoc, va no
   *    cho URL chia se duoc — mot thu loc phia trinh duyet khong cho.
   */
  function lichSu(cauHinh) {
    var ds = [].slice.call(document.querySelectorAll(".lv-ls-dong"));
    if (!ds.length) return;

    var chu = (cauHinh || {}).chu || {};
    var oCt = document.getElementById("lv-ls-ct");
    if (!oCt) return;

    var TEN_TT = {
      done: chu.sanSang, running: chu.dangTao, queued: chu.dangCho,
      cancelled: chu.daHuy, error: chu.loi
    };
    var LOP_TT = {
      done: "b-ok", running: "b-warn", queued: "b-warn",
      cancelled: "b-grey", error: "b-err"
    };

    function dat(id, v) {
      var o = document.getElementById(id);
      if (o) o.textContent = (v === "" || v == null) ? (chu.khong || "-") : String(v);
    }

    function mo(dong) {
      var d = dong.dataset;
      for (var i = 0; i < ds.length; i++) ds[i].classList.remove("chon");
      dong.classList.add("chon");

      var tt = document.getElementById("lv-ls-ct-tt");
      tt.innerHTML = "";
      var s = document.createElement("span");
      s.className = "badge " + (LOP_TT[d.tt] || "b-grey");
      var cham = document.createElement("span"); cham.className = "dot";
      s.appendChild(cham);
      s.appendChild(document.createTextNode(TEN_TT[d.tt] || d.tt));
      tt.appendChild(s);

      dat("lv-ls-ct-luc", d.luc);
      dat("lv-ls-ct-giong", d.giong);
      dat("lv-ls-ct-giay", d.giay ? d.giay + "s" : "");
      dat("lv-ls-ct-credit", d.credit);
      dat("lv-ls-ct-id", d.id);

      var nutChep = document.getElementById("lv-ls-ct-chep");
      if (nutChep) { nutChep.dataset.ma = d.id; chay(oCt); }

      var tai = document.getElementById("lv-ls-ct-tai");
      if (tai) {
        // An nut tai khi khong co tep — mot nut tai ve mot thu khong ton tai la
        // mot nut lam nguoi dung tuong ho lam sai.
        tai.hidden = !d.audio;
        if (d.audio) {
          tai.href = d.audio;
          tai.setAttribute("download", "ltt-voice-" + d.id.slice(0, 8) + ".wav");
        }
      }
      var job = document.getElementById("lv-ls-ct-job");
      if (job) job.href = "/jobs/" + d.id;

      oCt.hidden = false;
    }

    for (var i = 0; i < ds.length; i++) {
      (function (dong) {
        dong.addEventListener("click", function (e) {
          // Trinh phat va lien ket giu cu bam cua chinh chung.
          if (e.target.closest("audio, a, button")) return;
          mo(dong);
        });
        dong.addEventListener("keydown", function (e) {
          if (e.key === "Enter" || e.key === " ") { e.preventDefault(); mo(dong); }
        });
      })(ds[i]);
    }

    chay();
  }

  // Cho phan duoc them sau (ket qua sinh, danh sach tai them) tu gan lai.
  window.LttVoice = {
    gan: chay, luoiGiong: luoiGiong, studio: studio, lichSu: lichSu
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () { chay(); });
  } else {
    chay();
  }
})();
