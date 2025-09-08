// static/js/talep.js
(function () {
  const modal = document.getElementById("talepModal");

  // Modal açıldığında lookup’ları hazırla (dinamik yükleme güvenli)
  modal?.addEventListener("shown.bs.modal", async () => {
    await lookupDoldur();
  });

  // Marka değişince modelleri doldur
  document.addEventListener("change", async (e) => {
    if (e.target?.id === "marka") {
      await modelleriDoldur(e.target.value);
    }
  });

  // Form submit -> /api/talep/ekle
  document.addEventListener("submit", async (e) => {
    const form = e.target;
    if (form?.id !== "talepForm") return;
    e.preventDefault();

    const payload = {
      ifs_no: document.getElementById("ifs_no").value.trim(),
      donanim_tipi_id: Number(document.getElementById("donanim_tipi").value || 0),
      marka_id: Number(document.getElementById("marka").value || 0),
      model_id: Number(document.getElementById("model").value || 0),
      miktar: Number(document.getElementById("miktar").value || 0),
      aciklama: document.getElementById("aciklama").value.trim() || null
    };

    try {
      const r = await fetch("/api/talep/ekle", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (!r.ok) throw new Error(await r.text());
      // başarılı -> modalı kapat, tabloyu yenile
      bootstrap.Modal.getInstance(modal)?.hide();
      window.location.reload();
    } catch (err) {
      console.error(err);
      alert("Talep kaydedilemedi.");
    }
  });

  async function lookupDoldur() {
    // Donanım Tipi
    const dtSel = document.getElementById("donanım_tipi") || document.getElementById("donanim_tipi");
    const markaSel = document.getElementById("marka");
    const modelSel = document.getElementById("model");

    if (dtSel && !dtSel.options.length) {
      const r = await fetch("/api/lookup/donanim_tipi");
      const data = await r.json(); // [{id, adi}]
      dtSel.innerHTML = data.map(x => `<option value="${x.id}">${x.adi}</option>`).join("");
    }

    if (markaSel && !markaSel.options.length) {
      const r = await fetch("/api/lookup/marka");
      const data = await r.json();
      markaSel.innerHTML = `<option value="">Seçiniz…</option>` +
        data.map(x => `<option value="${x.id}">${x.adi}</option>`).join("");
    }

    modelSel.innerHTML = `<option value="">Seçiniz…</option>`;
    modelSel.disabled = true;
  }

  async function modelleriDoldur(markaId) {
    const modelSel = document.getElementById("model");
    if (!markaId) {
      modelSel.innerHTML = `<option value="">Seçiniz…</option>`;
      modelSel.disabled = true;
      return;
    }
    modelSel.disabled = true;
    modelSel.innerHTML = `<option>Yükleniyor…</option>`;
    try {
      const r = await fetch(`/api/lookup/model?marka_id=${encodeURIComponent(markaId)}`);
      if (!r.ok) throw new Error(await r.text());
      const data = await r.json(); // [{id, adi}]
      modelSel.innerHTML = data.length
        ? data.map(x => `<option value="${x.id}">${x.adi}</option>`).join("")
        : `<option value="">Model bulunamadı</option>`;
      modelSel.disabled = !data.length;
    } catch (e) {
      console.error(e);
      modelSel.innerHTML = `<option value="">Hata</option>`;
      modelSel.disabled = true;
    }
  }
})();
