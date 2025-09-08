document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("talepForm");

  // initial lookup fills
  if (window._selects) {
    _selects.fillChoices({ endpoint: "/api/lookup/donanim_tipi", selectId: "donanim_tipi", placeholder: "Donanım tipi" });
    _selects.fillChoices({ endpoint: "/api/lookup/marka", selectId: "marka", placeholder: "Marka" });
  }

  const markaSel = document.getElementById("marka");
  const modelSel = document.getElementById("model");

  markaSel?.addEventListener("change", async function () {
    const markaId = this.value;
    modelSel.innerHTML = '<option value="">Yükleniyor...</option>';
    try {
      const r = await fetch(`/api/lookup/model?marka_id=${encodeURIComponent(markaId)}`);
      const data = await r.json();
      modelSel.innerHTML = data.map(m => `<option value="${m.id}">${m.name || m.adi}</option>`).join("");
    } catch {
      modelSel.innerHTML = '<option value="">Model bulunamadı</option>';
    }
  });

  form?.addEventListener("submit", async (e) => {
    e.preventDefault();

    const payload = {
      ifs_no: document.getElementById("ifs_no").value?.trim(),
      donanim_tipi_id: Number(document.getElementById("donanim_tipi").value || 0),
      marka_id: Number(markaSel?.value || 0),
      model_id: Number(modelSel?.value || 0),
      miktar: Number(document.getElementById("miktar").value || 0),
      aciklama: document.getElementById("aciklama").value?.trim() || null
    };

    try {
      const resp = await fetch("/api/talep/ekle", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (!resp.ok) throw new Error(await resp.text());
      window.location.reload();
    } catch (err) {
      alert("Talep kaydedilemedi: " + err.message);
    }
  });
});
