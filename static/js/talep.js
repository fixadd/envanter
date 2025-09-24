// /static/js/talep.js
(function () {
  const modal = document.getElementById("talepModal");
  const tableBody = document.querySelector("#rowsTable tbody");
  const addRowBtn = document.getElementById("btnAddRow");
  const talepForm = document.getElementById("talepForm");
  const ifsInput = document.getElementById("ifs_no");

  if (!tableBody || !talepForm || !ifsInput) {
    return;
  }

  // Basit cache
  const cache = {};

  async function getLookup(name) {
    if (cache[name]) return cache[name];
    const r = await fetch(`/api/lookup/${name}`);
    if (!r.ok) return [];
    const data = await r.json(); // [{id, name}]
    cache[name] = data;
    return data;
  }

  async function getModelsByBrand(brandId) {
    const key = `model_${brandId}`;
    if (cache[key]) return cache[key];
    const r = await fetch(
      `/api/lookup/model?marka_id=${encodeURIComponent(brandId)}`,
    );
    if (!r.ok) return [];
    const data = await r.json(); // [{id, name}]
    cache[key] = data;
    return data;
  }

  function optionHtml(arr, placeholder = "Seçiniz…") {
    const head = `<option value="">${placeholder}</option>`;
    if (!Array.isArray(arr) || !arr.length)
      return head + `<option value="">Seçenek yok</option>`;
    return (
      head +
      arr
        .map((x) => `<option value="${x.id}">${x.name || x.adi || ""}</option>`)
        .join("")
    );
  }

  function rowTemplate() {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>
        <select class="form-select sel-donanim" required></select>
      </td>
      <td>
        <input type="number" min="1" value="1" class="form-control inp-miktar" required>
      </td>
      <td>
        <select class="form-select sel-marka"></select>
      </td>
      <td>
        <select class="form-select sel-model" disabled>
          <option value="">Seçiniz…</option>
        </select>
      </td>
      <td>
        <input type="text" class="form-control inp-aciklama" placeholder="Açıklama">
      </td>
      <td class="text-end">
        <button type="button" class="btn btn-outline-danger btn-sm btn-remove">Sil</button>
      </td>
    `;
    return tr;
  }

  async function fillStaticLookups(tr) {
    const donanimSel = tr.querySelector(".sel-donanim");
    const markaSel = tr.querySelector(".sel-marka");
    const modelSel = tr.querySelector(".sel-model");

    const [donanimlar, markalar] = await Promise.all([
      getLookup("donanim_tipi"),
      getLookup("marka"),
    ]);

    donanimSel.innerHTML = optionHtml(donanimlar);
    markaSel.innerHTML = optionHtml(markalar);
    modelSel.innerHTML = `<option value="">Seçiniz…</option>`;
    modelSel.disabled = true;
  }

  async function onBrandChange(tr, brandId) {
    const modelSel = tr.querySelector(".sel-model");
    if (!brandId) {
      modelSel.innerHTML = `<option value="">Seçiniz…</option>`;
      modelSel.disabled = true;
      return;
    }
    modelSel.disabled = true;
    modelSel.innerHTML = `<option>Yükleniyor…</option>`;
    const modeller = await getModelsByBrand(brandId);
    modelSel.innerHTML = optionHtml(modeller);
    modelSel.disabled = !modeller.length;
  }

  async function addRow() {
    const tr = rowTemplate();
    tableBody.appendChild(tr);
    await fillStaticLookups(tr);

    // Eventler
    const markaSelect = tr.querySelector(".sel-marka");
    const removeButton = tr.querySelector(".btn-remove");

    markaSelect?.addEventListener("change", (e) => {
      onBrandChange(tr, e.target.value);
    });
    removeButton?.addEventListener("click", () => {
      tr.remove();
    });
  }

  // Modal açıldığında ilk satırı garanti ekle
  modal?.addEventListener("shown.bs.modal", async () => {
    if (!tableBody.children.length) {
      await addRow();
    }
  });

  // Satır ekle butonu
  addRowBtn?.addEventListener("click", async () => {
    await addRow();
  });

  // Form submit
  talepForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const ifs_no = ifsInput.value.trim();
    const lines = [];
    tableBody.querySelectorAll("tr").forEach((tr) => {
      const donanimSelect = tr.querySelector(".sel-donanim");
      const miktarInput = tr.querySelector(".inp-miktar");
      const markaSelect = tr.querySelector(".sel-marka");
      const modelSelect = tr.querySelector(".sel-model");
      const aciklamaInput = tr.querySelector(".inp-aciklama");

      const donanim_tipi_id = Number(donanimSelect?.value || 0);
      const miktar = Number(miktarInput?.value || 0);
      const marka_id = Number(markaSelect?.value || 0);
      const model_id = Number(modelSelect?.value || 0);
      const aciklama = aciklamaInput?.value.trim() || null;

      if (donanim_tipi_id && miktar > 0) {
        lines.push({ donanim_tipi_id, miktar, marka_id, model_id, aciklama });
      }
    });

    if (!lines.length) {
      alert("En az bir satır doldurun.");
      return;
    }

    try {
      const r = await fetch("/api/talep/ekle", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ifs_no, lines }),
      });
      if (!r.ok) throw new Error(await r.text());
      bootstrap.Modal.getInstance(modal)?.hide();
      window.location.reload();
    } catch (err) {
      console.error(err);
      alert("Talep kaydedilemedi.");
    }
  });
})();

// Talep iptal
window.talepIptal = async function (id, mevcut) {
  let adet = 1;
  if (mevcut > 1) {
    const inp = prompt(`Kaç adet iptal edilecek? (1-${mevcut})`, mevcut);
    if (!inp) return;
    adet = Number(inp);
    if (!adet || adet < 1 || adet > mevcut) {
      alert("Geçersiz adet");
      return;
    }
  }
  const fd = new FormData();
  fd.append("adet", String(adet));
  try {
    const r = await fetch(`/talepler/${id}/cancel`, {
      method: "POST",
      body: fd,
    });
    if (!r.ok) {
      alert("İşlem başarısız");
      return;
    }
    location.reload();
  } catch (err) {
    console.error(err);
    alert("İşlem başarısız");
  }
};

// Talep kapat ve stoğa aktar (modal ile)
(() => {
  const modalEl = document.getElementById("talepKapatModal");
  if (!modalEl) return;

  const form = document.getElementById("talepKapatForm");
  const fldId = document.getElementById("tkTalepId");
  const fldAdet = document.getElementById("tkAdet");
  const selMarka = document.getElementById("tkMarka");
  const selModel = document.getElementById("tkModel");
  const fldAcik = document.getElementById("tkAciklama");
  const selTur = document.getElementById("tkTur");
  const markaWrap = selMarka?.closest(".mb-3");
  const modelWrap = selModel?.closest(".mb-3");

  let initialized = false;
  async function initSelects() {
    if (initialized) return;
    await _selects.fillChoices({
      endpoint: "/api/lookup/marka",
      selectId: "tkMarka",
      placeholder: "Marka seçiniz…",
    });
    await _selects.bindMarkaModel("tkMarka", "tkModel");
    initialized = true;
  }

  function updateCloseFormFields() {
    const type = (selTur?.value || "envanter").toLowerCase();
    const isLicense = type === "lisans";
    if (selMarka) {
      selMarka.disabled = isLicense;
      selMarka.required = !isLicense;
      if (isLicense) selMarka.value = "";
    }
    if (selModel) {
      selModel.disabled = isLicense;
      selModel.required = !isLicense;
      if (isLicense) selModel.value = "";
    }
    if (markaWrap) markaWrap.classList.toggle("d-none", isLicense);
    if (modelWrap) modelWrap.classList.toggle("d-none", isLicense);
  }

  selTur?.addEventListener("change", updateCloseFormFields);

  window.talepKapat = async function (id, mevcut) {
    await initSelects();
    fldId.value = String(id);
    fldAdet.max = mevcut;
    fldAdet.value = mevcut > 1 ? mevcut : 1;
    fldAcik.value = "";
    selMarka.value = "";
    selModel.value = "";
    if (selTur) {
      const turAttr = (row?.dataset?.tur || "").toLowerCase();
      const normalized =
        turAttr === "lisans"
          ? "lisans"
          : turAttr === "yazici"
            ? "yazici"
            : "envanter";
      selTur.value = normalized;
    }

    const row = Array.from(document.querySelectorAll("tbody tr")).find(
      (tr) => tr.firstElementChild?.textContent.trim() === String(id),
    );
    const markaTxt = row?.children[2]?.textContent.trim();
    const modelTxt = row?.children[3]?.textContent.trim();

    if (markaTxt && markaTxt !== "-") {
      const opt = Array.from(selMarka.options).find(
        (o) => o.textContent.trim() === markaTxt,
      );
      if (opt) {
        selMarka.value = opt.value;
        await _selects.fillChoices({
          endpoint: "/api/lookup/model",
          selectId: "tkModel",
          params: { marka_id: selMarka.value },
          placeholder: "Model seçiniz…",
        });
        if (modelTxt && modelTxt !== "-") {
          const mOpt = Array.from(selModel.options).find(
            (o) => o.textContent.trim() === modelTxt,
          );
          if (mOpt) selModel.value = mOpt.value;
        }
      } else {
        await _selects.fillChoices({
          endpoint: "/api/lookup/model",
          selectId: "tkModel",
          params: { marka_id: selMarka.value },
          placeholder: "Model seçiniz…",
        });
      }
    } else {
      await _selects.fillChoices({
        endpoint: "/api/lookup/model",
        selectId: "tkModel",
        params: { marka_id: "" },
        placeholder: "Model seçiniz…",
      });
    }

    updateCloseFormFields();
    bootstrap.Modal.getOrCreateInstance(modalEl).show();
  };

  form?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const id = fldId.value;
    const adet = Number(fldAdet.value) || 1;
    const marka = selMarka.selectedOptions[0]?.textContent.trim() || "";
    const model = selModel.selectedOptions[0]?.textContent.trim() || "";
    const acik = fldAcik.value.trim();

    const fd = new FormData();
    fd.append("adet", String(adet));
    fd.append("marka", marka);
    fd.append("model", model);
    if (acik) fd.append("aciklama", acik);
    if (selTur) fd.append("tur", selTur.value || "envanter");
    try {
      const r = await fetch(`/talepler/${id}/stock`, {
        method: "POST",
        body: fd,
      });
      if (!r.ok) {
        alert("İşlem başarısız");
        return;
      }
      bootstrap.Modal.getInstance(modalEl)?.hide();
      location.reload();
    } catch (err) {
      console.error(err);
      alert("İşlem başarısız");
    }
  });
})();
