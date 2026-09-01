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

  /* ── Bat mot nut trong nhom loc ───────────────────────────────────────────
   *
   * ⭐ MOT LUAT CHO CA LOP, khong va tung cho. Truoc P7 co HAI vong lap rieng
   *    cung lam mot viec (`.lv-loc-nut` o man Giong, `[data-chon-loai]` o bo
   *    chon giong) va ca hai chi doi lop CSS `on`. Lop CSS la thu con MAT nhin
   *    thay; trinh doc man hinh khong thay gi ca, nen no khong bao gio biet bo
   *    loc nao dang bat. Them nut thu ba o mot man thu ba ma quen dong bo la
   *    loi tai dien — nen no phai la mot ham, khong phai mot danh sach.
   *
   * ⛔ `aria-pressed` chu khong phai `role="radio"`. Radio bat buoc di kem mo
   *    hinh ban phim mui ten + roving tabindex; khai vai radio ma khong dung
   *    ban phim ay thi con te hon la khong khai gi — nguoi dung tin loi hua
   *    cua vai dien roi bam mui ten va khong co gi xay ra.
   */
  function batNut(nut) {
    var anhEm = nut.parentNode.querySelectorAll(".lv-loc-nut");
    for (var k = 0; k < anhEm.length; k++) {
      anhEm[k].classList.remove("on");
      anhEm[k].setAttribute("aria-pressed", "false");
    }
    nut.classList.add("on");
    nut.setAttribute("aria-pressed", "true");
  }

  /* ── Noi mot cau cho trinh doc man hinh ───────────────────────────────────
   *
   * 🔴 TIEN DO CHI TON TAI BANG MAT. Cac trang Du an va Chay lo cap nhat con so
   *    "3/12" tai cho khi hoi job — mot nguoi nhin thay ngay, mot nguoi dung
   *    trinh doc man hinh KHONG BIET GI CA cho toi khi ho tu tab lai qua o do.
   *    Man Studio da co vung `aria-live` tu dau; hai man nay thi khong, va do
   *    la khac biet duy nhat giua chung.
   *
   * ⛔ KHONG dat `aria-live` len chinh luoi con so. Moi luot hoi ghi lai ca bon
   *    o, nen trinh doc man hinh se doc lai ca bon MOI VAI GIAY — dung ky thuat
   *    ma khong dung duoc. Mot cau, va chi khi cau ay DOI.
   */
  function baoTin(cau) {
    var o = document.getElementById("lv-bao");
    if (!o || !cau || o.textContent === cau) return;
    o.textContent = cau;
  }

  /* Thay {x} {y} {e} trong mot cau da dich. */
  function dienSo(mau, so) {
    var cau = String(mau || "");
    for (var k in so) {
      if (Object.prototype.hasOwnProperty.call(so, k)) {
        cau = cau.split("{" + k + "}").join(String(so[k]));
      }
    }
    return cau;
  }

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
      /* Hai nguon: `data-ma` cho mot chuoi ngan, `data-chep-tu` cho noi dung
       * cua mot phan tu khac (vi du mot khoi lenh nhieu dong).
       *
       * ⭐ VI SAO CO DANG THU HAI. Nhet ca mot lenh curl vao mot thuoc tinh la
       *    tao BAN THU HAI cua chinh cai lenh dang hien tren trang — hai ban
       *    cua mot su that, va ban sai se la ban khong ai nho phai sua. Doc
       *    thang tu khoi ma thi chi co mot ban. */
      var ma = nut.dataset.ma || "";
      if (!ma && nut.dataset.chepTu) {
        var nguon = document.getElementById(nut.dataset.chepTu);
        ma = nguon ? (nguon.innerText || nguon.textContent || "") : "";
      }
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

  /* ── Trinh phat gon: NANG CAP mot the `<audio>` da co ─────────────────────
   *
   * 🔴 VI SAO CAN. `<audio controls>` mac dinh cua trinh duyet la mot thanh
   *    TRANG XAM. Dat no giua mot giao dien den/do la pha dung thu ma ca bo
   *    anh tham chieu dung lam ngon ngu chung — `VISUAL_REFERENCE_NOTES` viet
   *    "audio waveform dung nhu visual language chung". No xuat hien o BA man
   *    (Du an, Lich su, phien ban khoi), nen mot ban sua o day sua ca ba.
   *
   * ⭐ NANG CAP chu khong THAY THE. The `<audio>` van la dong co phat, chi bo
   *    `controls`. Khong co JS thi trang van co mot trinh phat that — dung
   *    nguyen tac tang cuong dan ma tep nay tuyen bo o dau.
   *
   * ⚠️ Song am chi ve khi bam PHAT lan dau. Mot trang Lich su muoi dong ma tai
   *    truoc ca muoi tep la vai chuc MB cho mot thu khach co the khong bam.
   */
  function ganTrinhPhat(au) {
    if (!au || au.dataset.daNang === "1") return;
    au.dataset.daNang = "1";
    au.removeAttribute("controls");

    var hop = document.createElement("div");
    hop.className = "lv-phat";
    au.parentNode.insertBefore(hop, au);

    var nut = document.createElement("button");
    nut.type = "button";
    nut.className = "lv-phat-nut";
    nut.setAttribute("aria-label", "Phat");
    nut.textContent = "▶";

    var song = document.createElement("canvas");
    song.className = "lv-phat-song";
    song.height = 40;

    var gio = document.createElement("span");
    gio.className = "lv-phat-gio";
    /* `—` chu khong phai `0:00`: voi `preload="none"` ta CHUA BIET do dai, va
       mot con so cu the ma sai con te hon mot dau gach thanh that. */
    gio.textContent = "—";

    hop.appendChild(nut);
    hop.appendChild(song);
    hop.appendChild(gio);
    hop.appendChild(au);

    function dinhDang(gy) {
      if (!isFinite(gy) || gy < 0) return "0:00";
      var ph = Math.floor(gy / 60), gi = Math.floor(gy % 60);
      return ph + ":" + (gi < 10 ? "0" : "") + gi;
    }

    /* ── Song TRANG TRI truoc khi co song THAT ────────────────────────────
     *
     * ⛔ `preload="none"` nghia la ta chua co du lieu de ve, nen dai song la
     *    mot vet TRONG cho toi khi khach bam phat — trong y het mot phan tu
     *    dung do. Do tren production 01/09: bon dong Lich su, bon vet trong.
     *
     * ⭐ Ve mot song GIA, tinh, mo — dung cach `_voice_the.html` da chon cho
     *    luoi giong va da ghi ly do: "Hinh song chi la NGON NGU THI GIAC, khong
     *    phai du lieu." No bi thay bang song THAT ngay khi bam phat.
     *
     * ⚠️ Hinh dang suy tu chinh URL, khong phai ngau nhien: mot dong Lich su
     *    phai trong Y HET nhau qua moi lan tai trang. Song nhay mua giua hai
     *    lan F5 la mot thu khien nguoi ta nghi du lieu doi. */
    function songGia() {
      var rong = song.clientWidth || 300;
      var dpr = window.devicePixelRatio || 1;
      var cao = song.clientHeight || 40;
      song.width = Math.round(rong * dpr);
      song.height = Math.round(cao * dpr);
      song.getContext("2d").scale(dpr, dpr);
      var h = 0, src = au.getAttribute("src") || "";
      for (var i = 0; i < src.length; i++) h = (h * 31 + src.charCodeAt(i)) | 0;
      var cot = Math.max(1, Math.floor(rong / 3)), d = [];
      for (var k = 0; k < cot; k++) {
        h = (h * 1103515245 + 12345) | 0;
        d.push(0.18 + (Math.abs(h % 1000) / 1000) * 0.55);
      }
      song.__dinh = d;
      veLaiSong(song, 0);
    }
    /* Cho mot nhip de canvas co be ngang that trong luoi flex. */
    setTimeout(songGia, 0);

    var daVe = false;
    nut.addEventListener("click", function () {
      if (au.paused) {
        /* Dung MOI trinh phat khac truoc. Hai ban thu chay chong nhau la mot
           mo am thanh khong ai nghe ra duoc gi. */
        var khac = document.querySelectorAll(".lv-phat audio");
        for (var i = 0; i < khac.length; i++) {
          if (khac[i] !== au && !khac[i].paused) khac[i].pause();
        }
        au.play();
        if (!daVe) { daVe = true; veSong(song, au.src); }
      } else {
        au.pause();
      }
    });

    au.addEventListener("play", function () {
      nut.textContent = "⏸";
      nut.setAttribute("aria-label", "Tam dung");
      hop.classList.add("dang-phat");
    });
    function dungLai() {
      nut.textContent = "▶";
      nut.setAttribute("aria-label", "Phat");
      hop.classList.remove("dang-phat");
    }
    au.addEventListener("pause", dungLai);
    au.addEventListener("ended", function () { dungLai(); veLaiSong(song, 0); });

    au.addEventListener("timeupdate", function () {
      gio.textContent = dinhDang(au.currentTime);
      if (au.duration) veLaiSong(song, au.currentTime / au.duration);
    });
    au.addEventListener("loadedmetadata", function () {
      gio.textContent = dinhDang(au.duration);
    });

    /* Bam vao song de tua. Khong tua duoc thi mot thanh song chi la trang tri
       — va mot trinh phat khong tua duoc te hon thanh mac dinh cua trinh duyet
       du no dep hon. */
    song.addEventListener("click", function (e) {
      if (!au.duration) return;
      var o = song.getBoundingClientRect();
      au.currentTime = Math.max(0, Math.min(1, (e.clientX - o.left) / o.width))
                       * au.duration;
    });
  }

  function chay(goc) {
    var pv = goc || document;
    var ds = pv.querySelectorAll(".lv-ma-chep");
    for (var i = 0; i < ds.length; i++) ganChep(ds[i]);
    /* Moi `<audio data-nang="1">` deu duoc nang cap — ke ca the chen
       vao sau (danh sach phien ban), vi `chay()` goi lai voi goc moi. */
    var au = pv.querySelectorAll('audio[data-nang="1"]');
    for (var k = 0; k < au.length; k++) ganTrinhPhat(au[k]);
    ganTabViDu(pv);
  }

  /* ── Tab ngon ngu vi du (man API) ─────────────────────────────────────────
   *
   * ⭐ O trong `chay()` chu khong o mot module rieng: man API co y KHONG co
   *    module JS rieng (xem chu thich cuoi `ltt_voice_api.html`), va them mot
   *    module chi de doi hai the la them mot cho de quen nap. */
  function ganTabViDu(pv) {
    var nut = (pv || document).querySelectorAll("[data-vidu]");
    for (var i = 0; i < nut.length; i++) {
      (function (n) {
        if (n.dataset.daGan === "1") return;
        n.dataset.daGan = "1";
        n.addEventListener("click", function () {
          var ten = n.dataset.vidu;
          var hop = document.querySelectorAll("[data-vidu-cho]");
          for (var j = 0; j < hop.length; j++) {
            hop[j].hidden = hop[j].dataset.viduCho !== ten;
          }
          batNut(n);
        });
      })(nut[i]);
    }
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
    var oAnMat = document.getElementById("lv-g-anmat");
    var dangLoc = {loai: "", gioi: "", vung: "", phongcach: ""};

    function loc() {
      var q = ((oTim && oTim.value) || "").trim().toLowerCase();
      var con = 0;
      // Bao nhieu the bi an CHI vi no thieu nhan dang duoc loc — khong phai vi
      // no that su khong khop. Hai thu do rat khac nhau voi nguoi dung, va
      // truoc 01/09 giao dien khong phan biet chung.
      var anViThieuNhan = 0;
      for (var i = 0; i < the.length; i++) {
        var t = the[i], d = t.dataset;
        // Giong nhan ban khong co ba mat cua giong mau. Khi mot mat do dang
        // duoc loc thi chung KHONG khop — va do la dung: loc "giong nu mien
        // Bac" ma van tra ve mot giong rieng chua phan loai la tra ket qua sai.
        //
        // ⛔ Nhung "dung" khong co nghia la "khong can noi". Do tren production
        //    01/09: bam "Nam" -> 45 giong con 9, va ca 25 giong cua khach bien
        //    mat khong mot loi nao. Nen ta van an chung, VA dem chung.
        var thieuNhan =
          (dangLoc.gioi && !d.gioi) ||
          (dangLoc.vung && !d.vung) ||
          (dangLoc.phongcach && !d.phongcach);
        var hop =
          (!dangLoc.loai || d.loai === dangLoc.loai) &&
          (!dangLoc.gioi || d.gioi === dangLoc.gioi) &&
          (!dangLoc.vung || d.vung === dangLoc.vung) &&
          (!dangLoc.phongcach || d.phongcach === dangLoc.phongcach) &&
          (!q || (d.ten || "").toLowerCase().indexOf(q) >= 0);
        t.hidden = !hop;
        if (hop) {
          con++;
        } else if (thieuNhan) {
          // Chi dem khi cai DUY NHAT chan no la nhan bi thieu. Mot giong bi
          // loai boi o tim hay boi "Giong mau" thi khong thuoc cau chuyen nay.
          var hopNeuBoNhan =
            (!dangLoc.loai || d.loai === dangLoc.loai) &&
            (!q || (d.ten || "").toLowerCase().indexOf(q) >= 0);
          if (hopNeuBoNhan) anViThieuNhan++;
        }
      }
      if (oSo) oSo.textContent = String(con);
      if (oKhongHop) oKhongHop.hidden = con !== 0;
      if (oAnMat) {
        oAnMat.hidden = anViThieuNhan === 0;
        // Mot goi khong truyen chuoi nay thi im lang chu dung nem — mot loi
        // JS o day se giet ca bo loc, tuc doi mot khiem khuyet hien thi lay
        // mot man hinh chet.
        var mau = (cauHinh.chu && cauHinh.chu.anViThieuNhan) || "";
        oAnMat.textContent = (anViThieuNhan && mau)
          ? mau.replace("{n}", String(anViThieuNhan))
          : "";
        if (!mau) oAnMat.hidden = true;
      }
    }

    var nutLoc = document.querySelectorAll(".lv-loc-nut");
    for (var i = 0; i < nutLoc.length; i++) {
      (function (nut) {
        nut.addEventListener("click", function () {
          dangLoc[nut.dataset.loc] = nut.dataset.gt || "";
          // Chi mot nut sang trong moi nhom.
          batNut(nut);
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
  /* Ve lai song da co dinh, to mau theo TIEN DO phat.
   *
   * ⭐ Tach khoi `veSong` vi giai ma lai am thanh moi lan `timeupdate` (4 lan
   *    mot giay) la mot viec ngu ngoc va rat ton. Dinh song tinh MOT LAN roi
   *    cat vao chinh phan tu canvas; ve lai chi la mot vong `fillRect`. */
  function veLaiSong(canvas, tienDo) {
    var dinh = canvas.__dinh;
    if (!dinh || !dinh.length) return;
    var rong = canvas.clientWidth || 300, cao = canvas.clientHeight || 40;
    var g = canvas.getContext("2d");
    g.clearRect(0, 0, rong, cao);
    var css = getComputedStyle(document.documentElement);
    var sang = css.getPropertyValue("--brand-hover").trim() || "#ff514a";
    var mo = css.getPropertyValue("--line2").trim() || "#63332e";
    var rongCot = 3, khe = 1, moc = (tienDo || 0) * dinh.length;
    for (var i = 0; i < dinh.length; i++) {
      g.fillStyle = i <= moc ? sang : mo;
      var h = Math.max(2, dinh[i] * cao * 0.92);
      g.fillRect(i * rongCot, (cao - h) / 2, rongCot - khe, h);
    }
  }

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
        var cacDinh = [];
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
          cacDinh.push(dinh);
        }
        // Cat lai de `veLaiSong` khong phai giai ma lan nua.
        canvas.__dinh = cacDinh;
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

    /* ── Nhap TXT ──────────────────────────────────────────────────────────
       Doc o trinh duyet, khong gui tep len may chu.

       ⚠️ CAT theo `maxlength` cua chinh o nhap, va NOI RA khi cat. Mot tep dai
          hon tran ma bi cat lang le la cach de nhat de khach mat mot doan cuoi
          ma khong biet — va ho chi phat hien khi nghe het ban thu. */
    var oNhap = document.getElementById("lv-nhap-txt");
    if (oNhap) {
      oNhap.addEventListener("change", function () {
        var f = oNhap.files && oNhap.files[0];
        if (!f) return;
        var doc = new FileReader();
        doc.onload = function () {
          var s = String(doc.result || "").replace(/\r\n?/g, "\n").trim();
          var tran = parseInt(oText.getAttribute("maxlength"), 10) || 0;
          var bicat = tran > 0 && s.length > tran;
          oText.value = bicat ? s.slice(0, tran) : s;
          dem();
          var oBao = document.getElementById("lv-nhap-bao");
          if (oBao) {
            oBao.hidden = !bicat;
            oBao.textContent = bicat && chu.nhapBiCat
              ? chu.nhapBiCat.replace("{n}", String(s.length))
                             .replace("{t}", String(tran))
              : "";
          }
          oNhap.value = "";   /* cho phep chon lai DUNG tep vua chon */
        };
        doc.onerror = function () {
          var oBao = document.getElementById("lv-nhap-bao");
          if (oBao && chu.nhapHong) { oBao.hidden = false; oBao.textContent = chu.nhapHong; }
          oNhap.value = "";
        };
        doc.readAsText(f, "utf-8");
      });
    }
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
      var taiMp3 = document.getElementById("lv-tai-mp3");
      if (taiMp3) {
        /* `?mp3=1` tren CHINH duong audio — khong ghep mot duong rieng o day.
           Mot tien to route ghep tay se lech ngay khi ai do doi `route_prefix`. */
        taiMp3.href = d.audio_url + (d.audio_url.indexOf("?") >= 0 ? "&" : "?") + "mp3=1";
        taiMp3.setAttribute("download", "ltt-voice-" + jobId.slice(0, 8) + ".mp3");
      }
      document.getElementById("lv-mo-job").href = "/jobs/" + jobId;
      document.getElementById("lv-ct-giay").textContent =
        d.giay != null ? d.giay + "s" : "-";
      document.getElementById("lv-ct-credit").textContent =
        d.credit != null ? String(d.credit) : "-";
      document.getElementById("lv-ct-job").textContent = jobId;
      var nutChep = document.getElementById("lv-ct-job-chep");
      if (nutChep) { nutChep.dataset.ma = jobId; chay(oXong); }

      /* Khong ve song o day nua: `ganTrinhPhat` da nang cap `lv-player`
         thanh trinh phat co song am rieng, giong ba man kia. Ve them mot
         canvas thu hai la ve cung mot thu hai lan. */
      ganTrinhPhat(au);

      /* Luu vao du an: nut chi mo hop, viec that o `/du-an/luu-tu-studio`.
         Hop DONG LAI moi lan co ket qua moi — de mo tu luot truoc thi bam
         "Luu" se luu nham job cu, va khong co gi tren man hinh noi ra dieu do. */
      var hop = document.getElementById("lv-luu-hop");
      if (hop) {
        hop.hidden = true;
        hop.dataset.job = jobId;
        var bao = document.getElementById("lv-luu-bao");
        if (bao) bao.hidden = true;
      }
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
      /* ⛔ Khoi nay dung `new FormData()` RONG roi them TUNG TRUONG, khong phai
         `new FormData(form)`. Nen mot `<input>` moi trong form KHONG tu dong
         duoc gui — no phai co mot dong o day.

         Da tra gia 01/09: nut toc do ghi dung vao input an, toi kiem input an
         thay dung, va ket luan la xong. Nhung khong ai doc input ay. Job chay
         o 1,0x trong khi giao dien sang den nut 1,25x — khong loi nao bao. */
      var oTd = document.getElementById("lv-toc-do");
      if (oTd) fd.append("toc_do", oTd.value || "1.0");

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
    /* Lan ngon ngu cua giong (vi | en | "" = moi lan).
     *
     * ⭐ Mot bo loc THU HAI tren cung mot danh sach, va no phai la mot bien
     *    RIENG chu khong phai gop vao `locLoai`. Gop hai mat loc vao mot bien
     *    la bat khach chon "giong cua toi" HOAC "tieng Anh" thay vi ca hai —
     *    va dung luc kho giong dong len thi do la luc ho can ca hai nhat. */
    var locLan = "";

    function locChon() {
      var q = ((oTimChon && oTimChon.value) || "").trim().toLowerCase();
      var con = 0;
      for (var i = 0; i < dsMuc.length; i++) {
        var m = dsMuc[i], d = m.dataset;
        // Muc mac dinh (data-loai rong) LUON hien: no la loi thoat khi bo loc
        // khong con gi, va la thu khach chon neu ho khong muon nghi.
        /* ⛔ Muc chua dat lan (`data-lan` rong) KHONG bi loc bo. `ngon_ngu`
         *    tung la mot cot khong noi nao doc, nen du lieu cu hoan toan co the
         *    trong — an chung di la khach mat giong cua chinh minh ma khong
         *    hieu vi sao. Chua biet lan thi hien o moi lan. */
        var hop = d.loai === ""
          || ((!locLoai || d.loai === locLoai)
              && (!locLan || !d.lan || d.lan === locLan)
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
          batNut(nut);
          locChon();
        });
      })(nutChonLoai[i]);
    }
    var nutChonLan = document.querySelectorAll("[data-chon-lan]");
    for (var j = 0; j < nutChonLan.length; j++) {
      (function (nut) {
        nut.addEventListener("click", function () {
          locLan = nut.dataset.chonLan || "";
          batNut(nut);
          locChon();
        });
      })(nutChonLan[j]);
    }
    if (oTimChon) oTimChon.addEventListener("input", locChon);

    /* ── Toc do hau ky ─────────────────────────────────────────────────────
       Nut chi ghi vao mot input an; VIEC THAT lam o may chu sau khi tao xong
       tep (`apps/ltt_voice/toc_do.py`). Day khong phai `playbackRate` cua
       trinh phat — tep tai ve cung phai doi theo, neu khong thi cai khach
       nghe va cai khach nhan la hai thu khac nhau. */
    var oTocDo = document.getElementById("lv-toc-do");
    var nutTocDo = document.querySelectorAll("[data-tocdo]");
    for (var k = 0; k < nutTocDo.length; k++) {
      (function (nut) {
        nut.addEventListener("click", function () {
          if (oTocDo) oTocDo.value = nut.dataset.tocdo || "1.0";
          batNut(nut);
        });
      })(nutTocDo[k]);
    }

    /* ── Tu dien phat am rieng ─────────────────────────────────────────────
       Nap KHI MO lan dau, khong nap san: hau het khach khong mo no, va no la
       mot vong mang cho mot thu ho khong nhin. */
    var tdHop = document.getElementById("lv-td-hop");
    var tdMo = document.getElementById("lv-td-mo");
    var tdDs = document.getElementById("lv-td-ds");
    var tdRong = document.getElementById("lv-td-rong");
    var tdBao = document.getElementById("lv-td-bao");
    var tdDaNap = false;

    function tdNoi(cau, la_loi) {
      if (!tdBao) return;
      tdBao.hidden = !cau;
      tdBao.textContent = cau || "";
      tdBao.classList.toggle("loi", !!la_loi);
    }

    function tdVe(muc) {
      if (!tdDs) return;
      tdDs.textContent = "";
      if (tdRong) tdRong.hidden = muc.length > 0;
      muc.forEach(function (m) {
        var li = document.createElement("li");
        var chu = document.createElement("span");
        /* `textContent`, KHONG `innerHTML`: day la chuoi KHACH GO. Dung
           innerHTML o day la mo mot duong XSS vao chinh trang cua ho. */
        chu.textContent = m.tu + " → " + m.thay;
        li.appendChild(chu);
        var xoa = document.createElement("button");
        xoa.type = "button";
        xoa.className = "lv-td-xoa";
        xoa.setAttribute("aria-label", (chu.xoaMuc || "Xoa") + " " + m.tu);
        xoa.textContent = "×";
        xoa.addEventListener("click", function () {
          xoa.disabled = true;
          var fdX = new FormData();
          fdX.append("csrf_token", form.csrf_token.value);
          fetch(duong + "/tu-dien/" + m.id + "/xoa", {method: "POST", body: fdX})
            .then(function (r) { return r.json(); })
            .then(function (d) {
              if (d.ok) { tdNap(); } else { xoa.disabled = false; }
            })
            .catch(function () { xoa.disabled = false; tdNoi(chu.khongGui, true); });
        });
        li.appendChild(xoa);
        tdDs.appendChild(li);
      });
    }

    function tdNap() {
      return fetch(duong + "/tu-dien")
        .then(function (r) { return r.json(); })
        .then(function (d) { if (d.ok) tdVe(d.muc || []); });
    }

    if (tdMo) {
      tdMo.addEventListener("click", function () {
        var dang_an = tdHop.hidden;
        tdHop.hidden = !dang_an;
        tdMo.setAttribute("aria-expanded", dang_an ? "true" : "false");
        if (dang_an && !tdDaNap) { tdDaNap = true; tdNap(); }
      });
    }
    var tdLuu = document.getElementById("lv-td-luu");
    if (tdLuu) {
      tdLuu.addEventListener("click", function () {
        var oTu = document.getElementById("lv-td-tu");
        var oThay = document.getElementById("lv-td-thay");
        tdLuu.disabled = true;
        tdNoi("");
        var fd = new FormData();
        fd.append("csrf_token", form.csrf_token.value);
        fd.append("tu", oTu.value);
        fd.append("thay", oThay.value);
        fetch(duong + "/tu-dien/them", {method: "POST", body: fd})
          .then(function (r) { return r.json(); })
          .then(function (d) {
            tdLuu.disabled = false;
            if (!d.ok) { tdNoi(d.loi, true); return; }
            oTu.value = ""; oThay.value = "";
            tdNap();
          })
          .catch(function () { tdLuu.disabled = false; tdNoi(chu.khongGui, true); });
      });
    }

    /* ── Luu ket qua vao mot Du an ─────────────────────────────────────────
       Khong sinh lai, khong thu tien lan hai: may chu tro khoi moi thang vao
       `audio_key` cua job vua xong. Xem `_p_du_an.luu_tu_studio`. */
    var luuHop = document.getElementById("lv-luu-hop");
    var luuMo = document.getElementById("lv-luu-mo");
    var luuChon = document.getElementById("lv-luu-chon");
    var luuTen = document.getElementById("lv-luu-ten");
    var luuBao = document.getElementById("lv-luu-bao");

    function luuHienTen() {
      if (luuTen) luuTen.hidden = !!(luuChon && luuChon.value);
    }
    if (luuChon) { luuChon.addEventListener("change", luuHienTen); luuHienTen(); }
    if (luuMo) {
      luuMo.addEventListener("click", function () {
        if (luuHop) luuHop.hidden = !luuHop.hidden;
      });
    }
    var luuHuy = document.getElementById("lv-luu-huy");
    if (luuHuy) {
      luuHuy.addEventListener("click", function () { luuHop.hidden = true; });
    }
    var luuOk = document.getElementById("lv-luu-ok");
    if (luuOk) {
      luuOk.addEventListener("click", function () {
        var job = luuHop ? luuHop.dataset.job : "";
        if (!job) return;
        luuOk.disabled = true;
        var fd = new FormData();
        fd.append("csrf_token", form.csrf_token.value);
        fd.append("job_id", job);
        fd.append("du_an_id", luuChon ? luuChon.value : "");
        fd.append("ten_moi", luuTen ? luuTen.value : "");
        fetch(duong + "/du-an/luu-tu-studio", {method: "POST", body: fd})
          .then(function (r) { return r.json(); })
          .then(function (d) {
            luuOk.disabled = false;
            if (!luuBao) return;
            luuBao.hidden = false;
            if (!d.ok) { luuBao.textContent = d.loi || "?"; return; }
            /* Duong dan THAT tu may chu, khong ghep chuoi o day: mot tien to
               route ghep tay se lech ngay khi ai do doi `route_prefix`. */
            luuBao.innerHTML = "";
            var a = document.createElement("a");
            a.href = d.duong;
            a.textContent = (chu.daLuuVao || "Da luu vao") + " " + d.ten;
            luuBao.appendChild(a);
          })
          .catch(function () {
            luuOk.disabled = false;
            if (luuBao) { luuBao.hidden = false; luuBao.textContent = chu.loiMang || "?"; }
          });
      });
    }

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

  /* ── Tien ich chung cho hai man Du an ─────────────────────────────────── */

  function nop(duong, csrf, du_lieu) {
    var fd = new FormData();
    fd.append("csrf_token", csrf);
    for (var k in du_lieu) {
      if (du_lieu[k] !== null && du_lieu[k] !== undefined) fd.append(k, du_lieu[k]);
    }
    return fetch(duong, {method: "POST", body: fd}).then(function (r) {
      return r.json();
    });
  }

  function csrfCua(goc) {
    var o = (goc || document).querySelector('input[name="csrf_token"]');
    return o ? o.value : "";
  }

  /* ── Man danh sach du an ───────────────────────────────────────────────── */
  function duAnDanhSach(cauHinh) {
    var form = document.getElementById("lv-da-moi");
    if (!form) return;
    var cfg = cauHinh || {}, chu = cfg.chu || {}, duong = cfg.duong || "";
    var oLoi = document.getElementById("lv-da-loi");

    function mo(hien) {
      form.hidden = !hien;
      if (hien) document.getElementById("lv-da-ten").focus();
    }
    document.getElementById("lv-da-nut-moi").addEventListener("click", function () {
      mo(form.hidden);
    });
    document.getElementById("lv-da-huy").addEventListener("click", function () {
      mo(false);
    });

    form.addEventListener("submit", function (e) {
      e.preventDefault();
      oLoi.hidden = true;
      var nut = form.querySelector('button[type="submit"]');
      nut.disabled = true;
      var giong = (form.querySelector('input[name="giong"]:checked') || {}).value || "";
      nop(duong + "/du-an/tao", csrfCua(form),
          {ten: form.ten.value, giong: giong})
        .then(function (d) {
          if (!d.ok) { oLoi.textContent = d.loi; oLoi.hidden = false; nut.disabled = false; return; }
          // Di thang vao du an vua tao: nguoi ta tao du an DE soan no, khong de
          // ngam no trong danh sach.
          window.location.href = duong + "/du-an/" + encodeURIComponent(d.id);
        })
        .catch(function () {
          oLoi.textContent = chu.khongGui; oLoi.hidden = false; nut.disabled = false;
        });
    });

    chay();
  }

  /* ── Man mot du an ─────────────────────────────────────────────────────── */
  function motDuAn(cauHinh) {
    var ds = document.getElementById("lv-khoi-ds");
    var cfg = cauHinh || {}, chu = cfg.chu || {};
    var duong = cfg.duong || "";
    var goc = duong + "/du-an/" + encodeURIComponent(cfg.maDuAn || "");
    var csrf = csrfCua(document);
    var oLoi = document.getElementById("lv-mda-loi");
    var dongHo = null;

    function baoLoi(cau) {
      if (!oLoi) return;
      oLoi.textContent = cau || chu.khongGui;
      oLoi.hidden = false;
    }
    function xoaLoi() { if (oLoi) oLoi.hidden = true; }

    /* Luu mot khoi. Goi khi o van ban mat tieu diem, khong goi moi phim go.
     *
     * ⭐ `blur` chu khong `input`: mot yeu cau moi ky tu la mot yeu cau moi 50ms
     *    khi go nhanh, va no khong cho them gi — khoi chi can dung TRUOC khi
     *    duoc doc. Cai gia la neu khach dong tab giua chung thi mat, nen o van
     *    ban co vien doi mau bao "chua luu". */
    function luuKhoi(li, xong) {
      var id = li.dataset.id;
      var chuMoi = li.querySelector(".lv-khoi-chu").value;
      var giongMoi = li.querySelector(".lv-khoi-giong").value;
      return nop(goc + "/khoi/" + id + "/sua", csrf, {text: chuMoi, giong: giongMoi})
        .then(function (d) {
          if (d.ok) {
            li.classList.remove("chua-luu");
            if (d.trang_thai) datTrangThai(li, d.trang_thai);
          }
          if (xong) xong(d);
          return d;
        });
    }

    function datTrangThai(li, tt) {
      li.dataset.tt = tt;
      var o = li.querySelector(".lv-khoi-tt");
      if (!o) return;
      var ban = {xong: ["b-ok", chu.daDoc], dang_tao: ["b-warn", chu.dangDoc],
                 can_tao_lai: ["b-warn", chu.doiChu], loi: ["b-err", chu.loi],
                 moi: ["b-grey", chu.chuaDoc]}[tt] || ["b-grey", tt];
      o.innerHTML = "";
      var s = document.createElement("span");
      s.className = "badge " + ban[0];
      var c = document.createElement("span"); c.className = "dot";
      s.appendChild(c); s.appendChild(document.createTextNode(ban[1]));
      o.appendChild(s);
    }

    function ganKhoi(li) {
      var oChu = li.querySelector(".lv-khoi-chu");
      var oGiong = li.querySelector(".lv-khoi-giong");

      oChu.addEventListener("input", function () { li.classList.add("chua-luu"); });
      oChu.addEventListener("blur", function () {
        if (li.classList.contains("chua-luu")) luuKhoi(li);
      });
      oGiong.addEventListener("change", function () { luuKhoi(li); });

      li.querySelector(".lv-khoi-doc").addEventListener("click", function () {
        xoaLoi();
        // Luu TRUOC khi doc. Doc mot khoi voi van ban cu la tieu tien that cho
        // mot ket qua khach khong con muon.
        luuKhoi(li, function () {
          nop(goc + "/khoi/" + li.dataset.id + "/doc", csrf, {})
            .then(function (d) {
              if (!d.ok) { baoLoi(d.loi); return; }
              datTrangThai(li, "dang_tao");
              batDauTheoDoi();
            })
            .catch(function () { baoLoi(chu.khongGui); });
        });
      });

      li.querySelector(".lv-khoi-xoa").addEventListener("click", function () {
        if (!window.confirm(chu.xacNhanXoa)) return;
        nop(goc + "/khoi/" + li.dataset.id + "/xoa", csrf, {})
          .then(function (d) { if (d.ok) window.location.reload(); });
      });
    }

    if (ds) {
      var cac = [].slice.call(ds.querySelectorAll(".lv-khoi"));
      for (var i = 0; i < cac.length; i++) ganKhoi(cac[i]);
    }

    /* Theo doi ca du an bang MOT loi goi, khong mot loi goi moi khoi. */
    function batDauTheoDoi() {
      if (dongHo) return;
      var cho = 1500;
      (function vong() {
        fetch(goc + "/trang-thai")
          .then(function (r) { return r.json(); })
          .then(function (d) {
            if (!d.ok) return;
            var conChay = 0;
            for (var i = 0; i < d.khoi.length; i++) {
              var k = d.khoi[i];
              var li = ds && ds.querySelector('[data-id="' + k.id + '"]');
              if (!li) continue;
              if (li.dataset.tt !== k.trang_thai) datTrangThai(li, k.trang_thai);
              if (k.trang_thai === "dang_tao") conChay++;
              // Tep vua xong: gan trinh phat vao, khong bat tai lai trang.
              if (k.audio_url && !li.querySelector(".lv-khoi-phat")) {
                var au = document.createElement("audio");
                au.className = "lv-khoi-phat";
                au.controls = true; au.preload = "none"; au.src = k.audio_url;
                li.querySelector(".lv-khoi-chan").appendChild(au);
              }
            }
            var tk = d.tom_tat || {};
            datSo("lv-tk-khoi", tk.so_khoi);
            datSo("lv-tk-xong", tk.xong);
            datSo("lv-tk-credit", tk.credit);
            var oTd = document.getElementById("lv-mda-tiendo");
            if (oTd) oTd.textContent = (tk.xong || 0) + "/" + (tk.so_khoi || 0);
            var xg = tk.xong || 0, tg = tk.so_khoi || 0;
            baoTin(dienSo(!conChay && xg === tg && tg ? chu.baoXong : chu.baoTienDo,
                          {x: xg, y: tg}));

            if (conChay) {
              cho = Math.min(cho * 1.3, 8000);
              dongHo = setTimeout(vong, cho);
            } else {
              dongHo = null;   // het viec thi THOI hoi, dung dap nhip mai
            }
          })
          .catch(function () {
            cho = Math.min(cho * 2, 15000);
            dongHo = setTimeout(vong, cho);
          });
      })();
      dongHo = 1;
    }

    function datSo(id, v) {
      var o = document.getElementById(id);
      if (o && v !== undefined && v !== null) o.textContent = String(v);
    }

    // Con khoi dang doc luc mo trang thi theo doi ngay.
    if (ds && ds.querySelector('[data-tt="dang_tao"]')) batDauTheoDoi();

    /* Thanh cong cu */
    var nutTatCa = document.getElementById("lv-doc-tat-ca");
    if (nutTatCa) nutTatCa.addEventListener("click", function () {
      xoaLoi();
      nutTatCa.disabled = true;
      nop(goc + "/doc-tat-ca", csrf, {})
        .then(function (d) {
          nutTatCa.disabled = false;
          if (!d.ok) { baoLoi(d.loi); return; }
          if (!d.so_nop) { baoLoi(chu.hetKhoi); return; }
          // Bao ca so da nop LAN cho con lai neu dung giua chung — mot con so
          // "da gui 3" ma khong noi con 17 la mot nua su that.
          if (d.loi) baoLoi(chu.daNop.replace("{n}", d.so_nop) + " " + d.loi);
          batDauTheoDoi();
          window.location.reload();
        })
        .catch(function () { nutTatCa.disabled = false; baoLoi(chu.khongGui); });
    });

    var nutThem = document.getElementById("lv-them-khoi");
    if (nutThem) nutThem.addEventListener("click", function () {
      nop(goc + "/khoi/them", csrf, {text: ""})
        .then(function (d) {
          if (!d.ok) { baoLoi(d.loi); return; }
          window.location.reload();
        })
        .catch(function () { baoLoi(chu.khongGui); });
    });

    var formNhap = document.getElementById("lv-nhap");
    var nutNhap = document.getElementById("lv-nut-nhap");
    if (formNhap && nutNhap) {
      nutNhap.addEventListener("click", function () { formNhap.hidden = !formNhap.hidden; });
      document.getElementById("lv-nhap-huy").addEventListener("click", function () {
        formNhap.hidden = true;
      });
      formNhap.addEventListener("submit", function (e) {
        e.preventDefault();
        xoaLoi();
        var nut = formNhap.querySelector('button[type="submit"]');
        nut.disabled = true;
        nop(goc + "/nhap", csrf, {text: formNhap.text.value})
          .then(function (d) {
            if (!d.ok) { baoLoi(d.loi); nut.disabled = false; return; }
            window.location.reload();
          })
          .catch(function () { baoLoi(chu.khongGui); nut.disabled = false; });
      });
    }

    var formCaiDat = document.getElementById("lv-mda-caidat");
    if (formCaiDat) formCaiDat.addEventListener("submit", function (e) {
      e.preventDefault();
      var giong = (formCaiDat.querySelector('input[name="giong"]:checked') || {}).value || "";
      var nut = formCaiDat.querySelector('button[type="submit"]');
      nut.disabled = true;
      nop(goc + "/sua", csrf, {ten: formCaiDat.ten.value, giong: giong})
        .then(function () { window.location.reload(); })
        .catch(function () { nut.disabled = false; baoLoi(chu.khongGui); });
    });


    /* ── Phien ban cua mot khoi (V1/V2/V3) ────────────────────────────────
       Nap KHI BAM. Mot du an 24 khoi ma nap san la 24 luot tra lich su cho
       mot thu hau het khach khong mo.

       ⭐ KHONG co bang `block_version` — du lieu doc tu lich su job qua
          `params.block_id`. Xem `du_an.cac_phien_ban`. */
    var nutPb = document.querySelectorAll(".lv-khoi-pb");
    for (var p = 0; p < nutPb.length; p++) {
      (function (nut) {
        nut.addEventListener("click", function () {
          var id = nut.dataset.khoi;
          var hop = document.querySelector('[data-pb-cho="' + id + '"]');
          if (!hop) return;
          if (!hop.hidden) {
            hop.hidden = true;
            nut.setAttribute("aria-expanded", "false");
            return;
          }
          hop.hidden = false;
          nut.setAttribute("aria-expanded", "true");
          hop.textContent = chu.dangTai || "...";
          fetch(goc + "/khoi/" + encodeURIComponent(id) + "/phien-ban")
            .then(function (r) { return r.json(); })
            .then(function (d) {
              hop.textContent = "";
              if (!d.ok || !d.phien_ban || !d.phien_ban.length) {
                hop.textContent = chu.chuaCoPb || "-";
                return;
              }
              var ul = document.createElement("ul");
              ul.className = "lv-pb-ds";
              d.phien_ban.forEach(function (v) {
                var li = document.createElement("li");
                if (v.dang_dung) li.className = "dang-dung";
                var ten = document.createElement("b");
                ten.textContent = v.ten;
                li.appendChild(ten);
                var meta = document.createElement("span");
                meta.className = "dim";
                meta.textContent = " " + v.giay + "s · " + v.credit + " credit";
                li.appendChild(meta);
                var au = document.createElement("audio");
                au.preload = "none";
                au.src = v.audio_url;
                au.dataset.nang = "1";
                li.appendChild(au);
                ganTrinhPhat(au);
                ul.appendChild(li);
              });
              hop.appendChild(ul);
            })
            .catch(function () { hop.textContent = chu.khongGui || "?"; });
        });
      })(nutPb[p]);
    }

    chay();
  }

  /* ── Man tao lo ────────────────────────────────────────────────────────────
   *
   * 🔴 NUT "TAO LO" KHOA TOI KHI MOI DONG HOP LE. Do la luat lon nhat cua man
   *    nay, va o day no chi la mot thuoc tinh `disabled` — nhung thuoc tinh do
   *    la thu dung giua khach va mot lo 500 dong bi giu tien roi hong o dong 47.
   *
   * ⚠️ Va no KHONG phai lop bao ve duy nhat: `POST /lo/tao` kiem lai o may chu
   *    va tu choi neu con dong hong. Mot nut bi khoa la mot tien nghi; may chu
   *    moi la cua.
   */
  function taoLo(cauHinh) {
    var form = document.getElementById("lv-lo-form");
    if (!form) return;
    var cfg = cauHinh || {}, chu = cfg.chu || {}, duong = cfg.duong || "";

    var oChu = document.getElementById("lv-lo-chu");
    var oFile = document.getElementById("lv-lo-file");
    var oXem = document.getElementById("lv-lo-xem");
    var oBody = document.getElementById("lv-lo-tbody");
    var oDem = document.getElementById("lv-lo-dem");
    var oGhi = document.getElementById("lv-lo-ghi");
    var oLoi = document.getElementById("lv-lo-loi");
    var nutTao = document.getElementById("lv-lo-nut-tao");
    var laCsv = false;

    function baoLoi(cau) {
      oLoi.textContent = cau || chu.khongGui;
      oLoi.hidden = false;
    }

    var nutNguon = document.querySelectorAll("[data-nguon]");
    for (var i = 0; i < nutNguon.length; i++) {
      (function (nut) {
        nut.addEventListener("click", function () {
          var la = nut.dataset.nguon === "tep";
          document.getElementById("lv-lo-dan").hidden = la;
          document.getElementById("lv-lo-tep").hidden = !la;
          batNut(nut);
          // Doi nguon thi ket qua kiem cu khong con dung nua. Khoa lai.
          nutTao.disabled = true;
          oXem.hidden = true;
        });
      })(nutNguon[i]);
    }

    function ve(d) {
      oBody.textContent = "";
      for (var i = 0; i < d.dong.length; i++) {
        var r = d.dong[i];
        var tr = document.createElement("tr");
        if (!r.hop_le) tr.className = "hong";
        function o(chuNoi, lop) {
          var td = document.createElement("td");
          if (lop) td.className = lop;
          td.textContent = chuNoi;
          return td;
        }
        tr.appendChild(o(String(r.thu_tu), "dim tnum"));
        tr.appendChild(o(r.text.slice(0, 70), "lv-mlo-chu"));
        tr.appendChild(o((r.giong || "").split(":").pop() || chu.theoLo, "mono"));
        tr.appendChild(o(r.nhan, "mono"));

        var td = document.createElement("td");
        var s = document.createElement("span");
        s.className = "badge " + (r.hop_le ? "b-ok" : "b-err");
        var cham = document.createElement("span"); cham.className = "dot";
        s.appendChild(cham);
        s.appendChild(document.createTextNode(r.hop_le ? chu.ok : (r.loi || "")));
        td.appendChild(s);
        tr.appendChild(td);
        oBody.appendChild(tr);
      }

      oDem.textContent = (chu.hopLe || "")
        .replace("{n}", d.so_hop_le).replace("{t}", d.dong.length);
      oDem.className = "badge " + (d.so_hong ? "b-err" : "b-ok");
      oGhi.textContent = d.so_hong
        ? (chu.conHong || "").replace("{n}", d.so_hong)
        : chu.tatCaHopLe;
      oXem.hidden = false;
      nutTao.disabled = d.so_hong > 0 || d.dong.length === 0;
    }

    function goiKiem() {
      oLoi.hidden = true;
      var fd = new FormData();
      fd.append("csrf_token", form.csrf_token.value);
      fd.append("noi_dung", oChu ? oChu.value : "");
      fd.append("giong", (form.querySelector('input[name="giong"]:checked') || {}).value || "");
      if (oFile && oFile.files && oFile.files[0]) {
        fd.append("tep", oFile.files[0]);
        laCsv = /\.csv$/i.test(oFile.files[0].name);
      }
      return fetch(duong + "/lo/kiem", {method: "POST", body: fd})
        .then(function (r) { return r.json(); })
        .then(function (d) {
          if (!d.ok) { baoLoi(d.loi); nutTao.disabled = true; return null; }
          ve(d);
          return d;
        })
        .catch(function () { baoLoi(chu.khongGui); return null; });
    }

    document.getElementById("lv-lo-nut-kiem").addEventListener("click", goiKiem);
    // Doi noi dung thi ket qua kiem cu het hieu luc — khoa lai ngay.
    if (oChu) oChu.addEventListener("input", function () {
      nutTao.disabled = true;
    });
    if (oFile) oFile.addEventListener("change", goiKiem);

    form.addEventListener("submit", function (e) {
      e.preventDefault();
      oLoi.hidden = true;
      nutTao.disabled = true;
      var fd = new FormData();
      fd.append("csrf_token", form.csrf_token.value);
      fd.append("ten", document.getElementById("lv-lo-ten").value);
      fd.append("noi_dung", oChu ? oChu.value : "");
      fd.append("la_csv", laCsv ? "1" : "");
      fd.append("giong", (form.querySelector('input[name="giong"]:checked') || {}).value || "");
      fetch(duong + "/lo/tao", {method: "POST", body: fd})
        .then(function (r) { return r.json(); })
        .then(function (d) {
          if (!d.ok) { baoLoi(d.loi); if (d.dong) ve(d); return; }
          window.location.href = duong + "/lo/" + encodeURIComponent(d.id);
        })
        .catch(function () { baoLoi(chu.khongGui); nutTao.disabled = false; });
    });

    chay();
  }

  /* ── Man mot lo dang chay ─────────────────────────────────────────────── */
  function motLo(cauHinh) {
    var bang = document.querySelector(".lv-mlo-bang tbody");
    if (!bang) return;
    var cfg = cauHinh || {}, chu = cfg.chu || {};
    var goc = (cfg.duong || "") + "/lo/" + encodeURIComponent(cfg.maLo || "");
    var csrf = csrfCua(document);
    var oLoi = document.getElementById("lv-mlo-loi");
    var dongHo = null;

    var TEN = {xong: chu.daXong, dang_tao: chu.dangDoc, moi: chu.cho, loi: chu.loi};
    var LOP = {xong: "b-ok", dang_tao: "b-warn", moi: "b-warn", loi: "b-err"};

    function baoLoi(cau) { oLoi.textContent = cau || chu.khongGui; oLoi.hidden = false; }

    function datSo(id, v) {
      var o = document.getElementById(id);
      if (o && v !== undefined && v !== null) o.textContent = String(v);
    }

    function theoDoi() {
      if (dongHo) return;
      var cho = 2000;
      (function vong() {
        fetch(goc + "/trang-thai")
          .then(function (r) { return r.json(); })
          .then(function (d) {
            if (!d.ok) return;
            var conChay = 0;
            for (var i = 0; i < d.dong.length; i++) {
              var x = d.dong[i];
              var tr = bang.querySelector('[data-id="' + x.id + '"]');
              if (!tr) continue;
              if (x.trang_thai === "dang_tao" || x.trang_thai === "moi") conChay++;
              if (tr.dataset.tt === x.trang_thai && !x.audio_url) continue;
              tr.dataset.tt = x.trang_thai;

              var oTt = tr.querySelector(".lv-mlo-tt");
              oTt.textContent = "";
              var s = document.createElement("span");
              s.className = "badge " + (LOP[x.trang_thai] || "b-grey");
              var cham = document.createElement("span"); cham.className = "dot";
              s.appendChild(cham);
              s.appendChild(document.createTextNode(TEN[x.trang_thai] || x.trang_thai));
              oTt.appendChild(s);
              if (x.loi) {
                var sm = document.createElement("small");
                sm.className = "lv-mlo-cau-loi";
                sm.textContent = x.loi;
                oTt.appendChild(sm);
              }
              if (x.giay) tr.querySelector(".lv-mlo-giay").textContent = x.giay + "s";
              if (x.audio_url && !tr.querySelector("audio")) {
                var au = document.createElement("audio");
                au.controls = true; au.preload = "none"; au.src = x.audio_url;
                tr.querySelector(".lv-mlo-phat").appendChild(au);
              }
            }
            var t = d.tom_tat || {};
            datSo("lv-so-tong", t.so_khoi);
            datSo("lv-so-xong", t.xong);
            datSo("lv-so-loi", t.loi);
            var so = {x: t.xong || 0, y: t.so_khoi || 0, e: t.loi || 0};
            baoTin(dienSo(conChay ? chu.baoTienDo : chu.baoXong, so));
            datSo("lv-so-uoc", t.uoc_con_lai_s || "—");
            var tai = document.getElementById("lv-lo-tai");
            if (tai && t.xong) tai.hidden = false;

            if (conChay) {
              cho = Math.min(cho * 1.25, 10000);
              dongHo = setTimeout(vong, cho);
            } else {
              dongHo = null;   // het viec thi THOI hoi
            }
          })
          .catch(function () {
            cho = Math.min(cho * 2, 20000);
            dongHo = setTimeout(vong, cho);
          });
      })();
      dongHo = 1;
    }

    if (bang.querySelector('[data-tt="dang_tao"]')) theoDoi();

    var nutChay = document.getElementById("lv-lo-chay");
    if (nutChay) nutChay.addEventListener("click", function () {
      oLoi.hidden = true;
      nutChay.disabled = true;
      nop(goc + "/chay", csrf, {})
        .then(function (d) {
          nutChay.disabled = false;
          if (!d.ok) { baoLoi(d.loi); return; }
          if (!d.so_nop) { baoLoi(chu.hetDong); return; }
          if (d.loi) baoLoi(chu.daNop.replace("{n}", d.so_nop) + " " + d.loi);
          window.location.reload();
        })
        .catch(function () { nutChay.disabled = false; baoLoi(chu.khongGui); });
    });

    chay();
  }

  // Cho phan duoc them sau (ket qua sinh, danh sach tai them) tu gan lai.
  window.LttVoice = {
    gan: chay, luoiGiong: luoiGiong, studio: studio, lichSu: lichSu,
    duAnDanhSach: duAnDanhSach, motDuAn: motDuAn, taoLo: taoLo, motLo: motLo
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () { chay(); });
  } else {
    chay();
  }
})();
