// /static/js/talep.js
(function () {
  const modal = document.getElementById("talepModal");
  const cardContainer = document.getElementById("talepItems");
  const tableBody = document.querySelector("#rowsTable tbody");
  const rowsContainer = cardContainer || tableBody;
  const addRowBtn = document.getElementById("btnAddRow");
  const talepForm = document.getElementById("talepForm");
  const ifsInput = document.getElementById("ifs_no");

  if (!rowsContainer || !talepForm || !ifsInput) {
    return;
  }

  ifsInput.addEventListener("input", () => {
    ifsInput.setCustomValidity("");
    ifsInput.classList.remove("is-invalid");
  });

  const isCardLayout = Boolean(cardContainer);

  const actionHeader = !isCardLayout
    ? document.querySelector("#rowsTable thead th.talep-action-col")
    : null;

  // Basit cache
  const cache = {};
  const numericIdPattern = /^\d+$/;

  const fetchErrorState = { lookup: false, model: false };

  let fetchAlertEl = null;
  let fetchAlertMsgEl = null;

  function ensureFetchAlert() {
    if (fetchAlertEl || !talepForm) return fetchAlertEl;
    const wrapper = document.createElement("div");
    wrapper.className =
      "alert alert-danger alert-dismissible fade d-none mb-3 d-flex align-items-center";
    wrapper.setAttribute("role", "alert");
    wrapper.id = "talep-fetch-alert";
    const msg = document.createElement("div");
    msg.className = "me-3 flex-fill js-talep-alert-msg";
    const closeBtn = document.createElement("button");
    closeBtn.type = "button";
    closeBtn.className = "btn-close";
    closeBtn.setAttribute("aria-label", "Kapat");
    closeBtn.addEventListener("click", () => {
      wrapper.classList.add("d-none");
      wrapper.classList.remove("show");
    });
    wrapper.appendChild(msg);
    wrapper.appendChild(closeBtn);
    talepForm.prepend(wrapper);
    fetchAlertEl = wrapper;
    fetchAlertMsgEl = msg;
    return fetchAlertEl;
  }

  function showFetchError(message) {
    if (!talepForm) {
      if (window.showAlert) {
        window.showAlert(message, {
          variant: "danger",
          title: "Yükleme Hatası",
        });
      } else {
        window.alert(message);
      }
      return;
    }
    ensureFetchAlert();
    if (!fetchAlertEl || !fetchAlertMsgEl) return;
    fetchAlertMsgEl.textContent = message;
    fetchAlertEl.classList.remove("d-none");
    fetchAlertEl.classList.add("show");
  }

  function hideFetchError() {
    if (!fetchAlertEl) return;
    fetchAlertEl.classList.add("d-none");
    fetchAlertEl.classList.remove("show");
  }

  function setSelectDisabledForError(select, disabled, originalDisabled) {
    if (!select) return;
    if (disabled) {
      if (!select.dataset.disabledDueToError) {
        const state =
          typeof originalDisabled === "boolean"
            ? originalDisabled
            : select.disabled;
        select.dataset.disabledDueToError = state ? "1" : "0";
      }
      select.disabled = true;
    } else if (select.dataset.disabledDueToError) {
      const wasDisabled = select.dataset.disabledDueToError === "1";
      select.disabled = wasDisabled;
      delete select.dataset.disabledDueToError;
    }
  }

  function setStaticSelectsDisabled(disabled) {
    rowsContainer
      ?.querySelectorAll(".sel-donanim, .sel-marka")
      .forEach((sel) => setSelectDisabledForError(sel, disabled));
  }

  function getRowElements() {
    if (!rowsContainer) return [];
    if (isCardLayout) {
      return Array.from(rowsContainer.querySelectorAll(".talep-item"));
    }
    return Array.from(rowsContainer.querySelectorAll("tr"));
  }

  function setFetchError(scope, hasError, message) {
    fetchErrorState[scope] = hasError;
    if (hasError) {
      if (scope === "lookup") {
        setStaticSelectsDisabled(true);
      }
      showFetchError(message);
      return;
    }

    if (scope === "lookup") {
      setStaticSelectsDisabled(false);
    }

    if (!fetchErrorState.lookup && !fetchErrorState.model) {
      hideFetchError();
    }
  }

  async function getLookup(name) {
    if (cache[name]) return cache[name];
    try {
      const r = await fetch(`/api/lookup/${name}`);
      if (!r.ok) {
        const text = await r.text().catch(() => "");
        throw new Error(text || `HTTP ${r.status}`);
      }
      const data = await r.json(); // [{id, name}]
      cache[name] = data;
      return data;
    } catch (err) {
      console.error(`Lookup ${name} alınırken hata oluştu`, err);
      setFetchError(
        "lookup",
        true,
        "Seçim listeleri yüklenirken bir hata oluştu. Lütfen bağlantınızı kontrol edip tekrar deneyin.",
      );
      return null;
    }
  }

  async function getModelsByBrand(brandId) {
    const key = `model_${brandId}`;
    if (cache[key]) return cache[key];
    try {
      const isNumeric = numericIdPattern.test(String(brandId));
      const searchParam = isNumeric
        ? `marka_id=${encodeURIComponent(brandId)}`
        : `marka=${encodeURIComponent(brandId)}`;
      const r = await fetch(`/api/lookup/model?${searchParam}`);
      if (!r.ok) {
        const text = await r.text().catch(() => "");
        throw new Error(text || `HTTP ${r.status}`);
      }
      const data = await r.json(); // [{id, name}]
      cache[key] = data;
      return data;
    } catch (err) {
      console.error(`Marka ${brandId} modelleri alınırken hata oluştu`, err);
      setFetchError(
        "model",
        true,
        "Seçilen markaya ait modeller alınırken bir hata oluştu. Lütfen tekrar deneyin.",
      );
      return null;
    }
  }

  function updateRemoveButtons() {
    if (!rowsContainer) return;
    const rows = getRowElements();
    const shouldHide = rows.length <= 1;

    rows.forEach((row, index) => {
      const removeBtn = row.querySelector(".btn-remove");
      const actionCell = row.querySelector(".talep-action-col");
      if (removeBtn) {
        removeBtn.classList.toggle("d-none", shouldHide);
        removeBtn.disabled = shouldHide;
      }
      if (actionCell) {
        actionCell.classList.toggle("talep-action-col--compact", shouldHide);
      }
      if (isCardLayout) {
        const indexEl = row.querySelector(".talep-item__index");
        if (indexEl) {
          indexEl.textContent = String(index + 1);
        }
      }
    });

    if (actionHeader) {
      actionHeader.classList.toggle("talep-action-col--compact", shouldHide);
    }
  }

  function optionHtml(arr, placeholder = "Seçiniz…") {
    const head = `<option value="">${placeholder}</option>`;
    if (!Array.isArray(arr) || !arr.length)
      return head + '<option value="">Seçenek yok</option>';

    const options = arr.map((item) => {
      if (item == null) {
        return '<option value=""></option>';
      }

      if (typeof item === "string" || typeof item === "number") {
        const text = String(item);
        return `<option value="${text}">${text}</option>`;
      }

      const value =
        item.id ?? item.value ?? (item.text != null ? item.text : "");
      const label =
        item.name ||
        item.text ||
        item.ad ||
        item.adi ||
        item.label ||
        (value !== undefined && value !== null ? String(value) : "");
      return `<option value="${value}">${label}</option>`;
    });

    return head + options.join("");
  }

  function rowTemplate() {
    if (isCardLayout) {
      const div = document.createElement("div");
      div.className = "talep-item soft-card stack-md";
      div.innerHTML = `
        <div class="talep-item__header d-flex flex-wrap align-items-center justify-content-between gap-2">
          <div class="talep-item__title">
            <span class="talep-item__badge">Kalem</span>
            <span class="talep-item__index">1</span>
          </div>
          <button type="button" class="btn btn-outline-danger btn-sm btn-remove">
            <i class="bi bi-x-lg"></i>
            Kaldır
          </button>
        </div>
        <div class="row g-3 talep-item__grid">
          <div class="col-md-6 col-xl-3">
            <label class="form-label">Donanım Tipi <span class="text-danger">*</span></label>
            <select class="form-select sel-donanim" required></select>
          </div>
          <div class="col-md-6 col-xl-3">
            <label class="form-label">Miktar <span class="text-danger">*</span></label>
            <input
              type="number"
              min="1"
              step="1"
              value="1"
              inputmode="numeric"
              class="form-control inp-miktar"
              required
            >
          </div>
          <div class="col-md-6 col-xl-3">
            <label class="form-label">Marka</label>
            <select class="form-select sel-marka"></select>
          </div>
          <div class="col-md-6 col-xl-3">
            <label class="form-label">Model</label>
            <select class="form-select sel-model" disabled>
              <option value="">Önce marka seçin…</option>
            </select>
          </div>
          <div class="col-12">
            <label class="form-label">Açıklama</label>
            <textarea class="form-control inp-aciklama" rows="2" placeholder="Opsiyonel açıklama"></textarea>
          </div>
        </div>
      `;
      return div;
    }

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
      <td class="text-end talep-action-col">
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

    if (!Array.isArray(donanimlar) || !Array.isArray(markalar)) {
      setSelectDisabledForError(donanimSel, true);
      setSelectDisabledForError(markaSel, true);
      modelSel.innerHTML = '<option value="">Seçiniz…</option>';
      modelSel.disabled = true;
      return;
    }

    donanimSel.innerHTML = optionHtml(donanimlar);
    markaSel.innerHTML = optionHtml(markalar);
    modelSel.innerHTML = '<option value="">Seçiniz…</option>';
    modelSel.disabled = true;
    setFetchError("lookup", false);
  }

  async function onBrandChange(tr, brandId) {
    const modelSel = tr.querySelector(".sel-model");
    if (!brandId) {
      modelSel.innerHTML = '<option value="">Seçiniz…</option>';
      modelSel.disabled = true;
      return;
    }
    const prevInnerHTML = modelSel.innerHTML;
    const prevValue = modelSel.value;
    const wasDisabledBeforeLoading = modelSel.disabled;
    modelSel.disabled = true;
    modelSel.innerHTML = "<option>Yükleniyor…</option>";
    const modeller = await getModelsByBrand(brandId);
    if (!Array.isArray(modeller)) {
      modelSel.innerHTML = prevInnerHTML;
      modelSel.value = prevValue;
      setSelectDisabledForError(modelSel, true, wasDisabledBeforeLoading);
      return;
    }
    modelSel.innerHTML = optionHtml(modeller);
    if (prevValue) {
      const hasPrevOption = Array.from(modelSel.options).some(
        (opt) => opt.value === prevValue,
      );
      modelSel.value = hasPrevOption ? prevValue : "";
    } else {
      modelSel.value = "";
    }
    setSelectDisabledForError(modelSel, false);
    modelSel.disabled = !modeller.length;
    setFetchError("model", false);
  }

  async function addRow() {
    const tr = rowTemplate();
    rowsContainer.appendChild(tr);
    await fillStaticLookups(tr);

    // Eventler
    const markaSelect = tr.querySelector(".sel-marka");
    const removeButton = tr.querySelector(".btn-remove");

    markaSelect?.addEventListener("change", (e) => {
      onBrandChange(tr, e.target.value);
    });
    removeButton?.addEventListener("click", () => {
      tr.remove();
      updateRemoveButtons();
    });

    updateRemoveButtons();
  }

  // Modal açıldığında ilk satırı garanti ekle
  modal?.addEventListener("shown.bs.modal", async () => {
    if (!getRowElements().length) {
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

    if (!ifs_no) {
      ifsInput.classList.add("is-invalid");
      ifsInput.setCustomValidity("IFS numarası zorunludur.");
      ifsInput.reportValidity();
      ifsInput.focus();
      return;
    }

    ifsInput.setCustomValidity("");
    ifsInput.classList.remove("is-invalid");
    const lines = [];
    getRowElements().forEach((tr) => {
      const donanimSelect = tr.querySelector(".sel-donanim");
      const miktarInput = tr.querySelector(".inp-miktar");
      const markaSelect = tr.querySelector(".sel-marka");
      const modelSelect = tr.querySelector(".sel-model");
      const aciklamaInput = tr.querySelector(".inp-aciklama");

      const donanim_tipi_id = Number(donanimSelect?.value || 0);
      const miktar = Number(miktarInput?.value || 0);
      const markaValue = markaSelect?.value ?? "";
      const modelValue = modelSelect?.value ?? "";
      const marka_id = numericIdPattern.test(markaValue)
        ? Number(markaValue)
        : 0;
      const model_id = numericIdPattern.test(modelValue)
        ? Number(modelValue)
        : 0;
      const markaOption = markaSelect?.selectedOptions?.[0] || null;
      const modelOption = modelSelect?.selectedOptions?.[0] || null;
      const markaLabel = markaOption?.textContent
        ? markaOption.textContent.trim()
        : "";
      const modelLabel = modelOption?.textContent
        ? modelOption.textContent.trim()
        : "";
      const marka_adi = marka_id > 0 ? null : markaLabel || null;
      const model_adi = model_id > 0 ? null : modelLabel || null;
      const aciklama = aciklamaInput?.value.trim() || null;

      if (donanim_tipi_id && miktar > 0) {
        lines.push({
          donanim_tipi_id,
          miktar,
          marka_id,
          marka_adi,
          model_id,
          model_adi,
          aciklama,
        });
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

  updateRemoveButtons();

  // Modal dışında ayrı sayfada kullanıldığında ilk satırı otomatik ekle
  if (!modal && rowsContainer && !getRowElements().length) {
    addRow().catch((err) => console.error("Talep satırı eklenemedi", err));
  }
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
  const markaWrap = selMarka?.closest(".field, .mb-3");
  const modelWrap = selModel?.closest(".field, .mb-3");

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
    if (fldId) fldId.value = String(id);
    if (fldAdet) {
      fldAdet.max = mevcut;
      fldAdet.value = mevcut > 1 ? mevcut : 1;
    }
    if (fldAcik) fldAcik.value = "";
    if (selMarka) selMarka.value = "";
    if (selModel) selModel.value = "";

    const row = Array.from(document.querySelectorAll("tbody tr")).find(
      (tr) => tr.firstElementChild?.textContent.trim() === String(id),
    );
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
    const markaTxt = row?.children[2]?.textContent.trim();
    const modelTxt = row?.children[3]?.textContent.trim();

    if (selMarka && selModel) {
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
        if (window.showAlert) {
          window.showAlert("İşlem başarısız", {
            variant: "danger",
            title: "İşlem Başarısız",
          });
        } else {
          alert("İşlem başarısız");
        }
        return;
      }
      bootstrap.Modal.getInstance(modalEl)?.hide();
      location.reload();
    } catch (err) {
      console.error(err);
      if (window.showAlert) {
        window.showAlert("İşlem başarısız", {
          variant: "danger",
          title: "İşlem Başarısız",
        });
      } else {
        alert("İşlem başarısız");
      }
    }
  });
})();
