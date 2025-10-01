(() => {
  "use strict";

  // ---------------------------------------------------------------------------
  // DOM yardımcıları
  // ---------------------------------------------------------------------------
  const dom = {
    one(selector, root = document) {
      return root.querySelector(selector);
    },
    all(selector, root = document) {
      return Array.from(root.querySelectorAll(selector));
    },
    toggle(element, visible) {
      if (!element) return;
      element.classList.toggle("d-none", !visible);
    },
    require(element, on) {
      if (!element) return;
      if (on) {
        element.setAttribute("required", "required");
      } else {
        element.removeAttribute("required");
      }
    },
  };

  function toggleDisabled(container, disabled) {
    if (!container) return;
    dom.all("input,select,textarea,button", container).forEach((el) => {
      if (disabled) {
        el.setAttribute("disabled", "disabled");
      } else {
        el.removeAttribute("disabled");
      }
    });
  }

  // ---------------------------------------------------------------------------
  // HTTP yardımcıları
  // ---------------------------------------------------------------------------
  const http = {};

  http.requestJson = async function requestJson(url, options = {}) {
    const headers = { Accept: "application/json", ...(options.headers || {}) };
    const response = await fetch(url, { ...options, headers });

    let bodyText = "";
    try {
      bodyText = await response.text();
    } catch (err) {
      console.error("response read failed", err);
    }

    let data = null;
    if (bodyText) {
      try {
        data = JSON.parse(bodyText);
      } catch (err) {
        if (response.ok) {
          const parseError = new Error("Sunucudan geçerli JSON alınamadı.");
          parseError.cause = err;
          throw parseError;
        }
      }
    }

    if (!response.ok) {
      const fallback = bodyText || `HTTP ${response.status}`;
      const message =
        (data && (data.detail || data.error || data.message)) || fallback;
      const error = new Error(message);
      error.status = response.status;
      error.data = data;
      throw error;
    }

    return data ?? {};
  };

  http.getJson = function getJson(url, options = {}) {
    return http.requestJson(url, {
      ...options,
      method: options.method || "GET",
    });
  };

  http.postJson = function postJson(url, payload, options = {}) {
    const headers = {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    };
    return http.requestJson(url, {
      ...options,
      method: "POST",
      body: JSON.stringify(payload),
      headers,
    });
  };

  // ---------------------------------------------------------------------------
  // Meta ve API kökleri
  // ---------------------------------------------------------------------------
  function getMetaApiRoot() {
    if (typeof document === "undefined") return "/api";
    const meta = document.querySelector('meta[name="api-root"]');
    if (!meta) return "/api";
    const content = (meta.getAttribute("content") || "").trim();
    return content ? content.replace(/\/$/, "") : "/api";
  }

  const API_ROOT_META = getMetaApiRoot();
  const STOCK_STATUS_URL = `${API_ROOT_META}/stock/status`;
  

  function baseSourceType(value) {
    if (!value) return "";
    const parts = String(value).toLowerCase().split(":");
    return parts.length > 1 ? parts[parts.length - 1] : parts[0];
  }

  function normaliseSystemKey(item = {}) {
    const type = (
      item.item_type ||
      baseSourceType(item.source_type) ||
      "envanter"
    ).toLowerCase();
    const clean = (val) => {
      if (val === null || val === undefined) return null;
      const text = String(val).trim();
      return text ? text : null;
    };
    return {
     item_type: ['envanter', 'lisans', 'yazici'].includes(type) ? type : 'envanter',
     donanim_tipi: String(item.donanim_tipi || '').trim(),
     marka: clean(item.marka),
     model: clean(item.model),
     ifs_no: clean(item.ifs_no),
    };
  }

  function encodeSystemKey(item) {
    return encodeURIComponent(JSON.stringify(normaliseSystemKey(item)));
  }

  function parseSystemKey(encoded) {
    if (!encoded) return null;
    try {
      const raw = JSON.parse(decodeURIComponent(encoded));
      return normaliseSystemKey(raw);
    } catch (err) {
      console.warn("system key parse failed", err);
      return null;
    }
  }

  const systemRoomState = {
    selectedNormal: new Set(),
    selectedSystem: new Set(),
  };

  const TYPE_LABELS = {
    envanter: "Envanter",
    lisans: "Lisans",
    yazici: "Yazıcı",
  };

  const LICENSE_TYPE_KEYS = new Set([
    "lisans",
    "lisanslar",
    "license",
    "software",
    "yazilim",
  ]);
  const PRINTER_TYPE_KEYS = new Set(["yazici", "printer"]);

  function normaliseCategoryValue(value) {
    if (value === null || value === undefined) return "";
    return String(value).trim().toLowerCase();
  }

  function matchesCategory(value, keys) {
    if (!value) return false;
    if (keys.has(value)) return true;
    const lastSegment = value.includes(":") ? value.split(":").pop() : value;
    if (lastSegment && keys.has(lastSegment)) return true;
    for (const key of keys) {
      if (value.includes(key)) return true;
    }
    return false;
  }

  function detectItemCategory(item) {
    const candidates = [];
    const base = normaliseCategoryValue(
      baseSourceType(item?.item_type || item?.source_type),
    );
    if (base) candidates.push(base);
    const rawType = normaliseCategoryValue(item?.item_type);
    if (rawType) candidates.push(rawType);
    const sourceType = normaliseCategoryValue(item?.source_type);
    if (sourceType) candidates.push(sourceType);

    if (candidates.some((value) => matchesCategory(value, LICENSE_TYPE_KEYS))) {
      return "license";
    }
    if (candidates.some((value) => matchesCategory(value, PRINTER_TYPE_KEYS))) {
      return "printer";
    }
    return "inventory";
  }

  function updateSystemRoomButtons() {
    const addBtn = dom.one("#btnSystemRoomAdd");
    const removeBtn = dom.one("#btnSystemRoomRemove");
    if (addBtn) addBtn.disabled = systemRoomState.selectedNormal.size === 0;
    if (removeBtn)
      removeBtn.disabled = systemRoomState.selectedSystem.size === 0;
  }

  // ---------------------------------------------------------------------------
  // Stok ekleme formu
  // ---------------------------------------------------------------------------
  const StockAddForm = (() => {
    const state = {
      currentType: "inventory",
      elements: {
        modal: null,
        form: null,
        hardwareFields: null,
        licenseFields: null,
        miktarInput: null,
        rowMiktar: null,
        typeButtons: [],
      },
    };

    function cacheElements() {
      state.elements.modal = dom.one("#modalStockAdd");
      state.elements.form = dom.one("#frmStockAdd");
      state.elements.hardwareFields = dom.one("#hardwareFields");
      state.elements.licenseFields = dom.one("#licenseFields");
      state.elements.miktarInput = dom.one("#miktar");
      state.elements.rowMiktar = dom.one("#rowMiktar");
      state.elements.typeButtons = dom.all("[data-stock-add-type]");
    }

    function detectInitialType() {
     const active = dom.one('[data-stock-add-type].active');
     return active?.dataset.stockAddType === 'license' ? 'license' : 'inventory';
    }

    function updateSectionVisibility(isLicense) {
      dom.toggle(state.elements.hardwareFields, !isLicense);
      dom.toggle(state.elements.licenseFields, isLicense);
      dom.toggle(state.elements.rowMiktar, !isLicense);
    }

    function updateFieldAvailability(isLicense) {
      toggleDisabled(state.elements.hardwareFields, isLicense);
      toggleDisabled(state.elements.licenseFields, !isLicense);
    }

    function updateMiktarField(isLicense) {
      const input = state.elements.miktarInput;
      if (!input) return;
      if (isLicense) {
        input.value = "1";
        input.readOnly = true;
      } else {
        input.readOnly = false;
      }
    }

    function updateDonanimRequirement(isLicense) {
      const select = dom.one("#stok_donanim_tipi");
      dom.require(select, !isLicense);
    }

    function updateTypeButtons() {
      state.elements.typeButtons.forEach((btn) => {
        const btnType = btn.dataset.stockAddType || "inventory";
        const isActive = btnType === state.currentType;
        btn.classList.toggle("active", isActive);
        btn.setAttribute("aria-selected", isActive ? "true" : "false");
      });
    }

    function applyStockAddType(type) {
      state.currentType = type === "license" ? "license" : "inventory";
      const isLicense = state.currentType === "license";
      updateSectionVisibility(isLicense);
      updateFieldAvailability(isLicense);
      updateDonanimRequirement(isLicense);
      updateMiktarField(isLicense);
      updateTypeButtons();
    }

    function bindTypeButtons() {
      state.elements.typeButtons.forEach((btn) => {
        btn.addEventListener("click", () => {
          applyStockAddType(btn.dataset.stockAddType || "inventory");
        });
      });
    }

    function normaliseFormData(form) {
      const formData = new FormData(form);
      const isLicense = state.currentType === "license";
      if (isLicense) {
        const licenseName = formData.get("lisans_adi") || "";
        formData.set("miktar", "1");
        formData.set("donanim_tipi", licenseName);
        formData.set("is_lisans", "1");
        formData.delete("is_license");
      } else {
        formData.delete("is_lisans");
      }
      return formData;
    }

    function buildPayload(form) {
      const formData = normaliseFormData(form);
      const payload = Object.fromEntries(formData.entries());
      const miktar = Number(payload.miktar);
      if (!miktar || miktar <= 0) {
        throw new Error("Miktar 0'dan büyük olmalı");
      }
      return payload;
    }

    async function submitStockAdd(event) {
      event.preventDefault();
      const form = state.elements.form;
      if (!form) return;
      let payload;
      try {
        payload = buildPayload(form);
      } catch (err) {
        alert(err.message || "Kayıt başarısız");
        return;
      }
      try {
        const result = await http.postJson("/stock/add", payload);
        if (result?.ok) {
          window.location.reload();
          return;
        }
        alert(result?.error || "Kayıt başarısız");
      } catch (err) {
        console.error("stock add failed", err);
        alert(`Kayıt başarısız${err?.message ? `: ${err.message}` : ""}`);
      }
    }

    function handleModalShown() {
      cacheElements();
      applyStockAddType(state.currentType);
    }

    function init() {
      cacheElements();
      state.currentType = detectInitialType();
      bindTypeButtons();
      applyStockAddType(state.currentType);

      if (state.elements.form) {
        state.elements.form.addEventListener("submit", submitStockAdd);
      }

      if (state.elements.modal) {
        state.elements.modal.addEventListener(
          "shown.bs.modal",
          handleModalShown,
        );
      }
    }

    return { init };
  })();

  // ---------------------------------------------------------------------------
  // Stok atama modülü
  // ---------------------------------------------------------------------------
  const StockAssign = (() => {
    const state = {
      selectedStockMeta: null,
      currentStockId: null,
      sourceCache: new Map(),
      sourceRequestId: 0,
    };

    function showBanner(message, type = "danger") {
      let holder = dom.one("#sa_banner");
      if (!holder) {
        const body = dom.one("#stokAtamaModal .modal-body");
        holder = document.createElement("div");
        holder.id = "sa_banner";
        body?.prepend(holder);
      }
      if (!holder) return;
      holder.innerHTML = `<div class="alert alert-${type} py-2 px-3 mb-2">${message}</div>`;
      window.setTimeout(() => {
        if (holder) holder.innerHTML = "";
      }, 6000);
      console.log("[StokAtama]", message);
    }

    function fillSelect(selector, data, valueKey = "id", labelKey = "text") {
      const element = dom.one(selector);
      if (!element) return;
      element.innerHTML = '<option value="">Seçiniz...</option>';
      (data || []).forEach((item) => {
        const option = document.createElement("option");
        const value = item[valueKey] ?? item.id ?? item.value ?? "";
        const label = item[labelKey] ?? item.name ?? item.text ?? value;
        option.value = value || "";
        option.textContent = label || value || "";
        element.appendChild(option);
      });
    }

    async function loadList(url) {
      try {
        const data = await http.getJson(url);
        return { data: Array.isArray(data) ? data : [], error: null };
      } catch (err) {
        console.error("assign source request failed", url, err);
        return { data: [], error: err };
      }
    }

    async function loadSources() {
      try {
        const [
          usersRes,
          inventoryRes,
          factoryRes,
          deptRes,
          usageRes,
          licenseNamesRes,
        ] = await Promise.all([
          loadList(`${URLS.assignSources}?type=users`),
          loadList(`${URLS.assignSources}?type=envanter`),
          loadList("/api/lookup/fabrika"),
          loadList(`${URLS.assignSources}?type=departman`),
          loadList("/api/lookup/kullanim_alani"),
          loadList("/api/licenses/names"),
        ]);

        let printersRes = { data: [], error: null };
        try {
          const printerData = await http.getJson("/api/printers/list");
          const items = Array.isArray(printerData?.items)
            ? printerData.items
            : [];
          printersRes.data = items.map((item) => ({
            id: item.envanter_no || item.id || "",
            text:
              [
                item.envanter_no || item.id || "",
                item.marka,
                item.model,
                item.seri_no,
              ]
                .filter((part) => part)
                .join(" - ") || item.envanter_no || item.id || "",
          }));
        } catch (err) {
          printersRes = { data: [], error: err };
        }

        const hadError = [
          usersRes,
          inventoryRes,
          factoryRes,
          deptRes,
          usageRes,
          licenseNamesRes,
          printersRes,
        ].some((r) => r.error);
        if (hadError) {
          showBanner(
            "Atama kaynakları alınamadı. URL prefix doğru mu?",
            "warning",
          );
        }

        fillSelect("#sa_license_owner", usersRes.data, "id", "text");
        fillSelect("#sa_license_person", usersRes.data, "id", "text");
        fillSelect("#sa_inventory_owner", usersRes.data, "id", "text");
        fillSelect("#sa_inv_person", usersRes.data, "id", "text");
        fillSelect("#sa_license_inventory", inventoryRes.data, "id", "text");
        fillSelect("#sa_inventory_select", inventoryRes.data, "id", "text");
        const licenseOptions = (licenseNamesRes.data || []).map((name) => ({
          id: name,
          text: name,
        }));
        fillSelect("#sa_license_select", licenseOptions, "id", "text");
        fillSelect("#sa_printer_select", printersRes.data, "id", "text");
        fillSelect("#sa_inv_factory", factoryRes.data, "id", "name");
        fillSelect("#sa_inv_department", deptRes.data, "id", "text");
        fillSelect("#sa_inv_usage", usageRes.data, "id", "name");
        fillSelect("#sa_prn_usage", usageRes.data, "id", "name");
        updateAutoFields();
      } catch (err) {
        showBanner(
          "Atama kaynakları yüklenemedi. Konsolu kontrol edin.",
          "danger",
        );
        console.error("sa_loadSources failed", err);
      }
    }

    function resetStockMetaDisplay() {
      state.selectedStockMeta = null;
      state.currentStockId = null;
      dom.toggle(dom.one("#sa_stock_meta"), false);
      dom.toggle(dom.one("#sa_stock_alert"), true);
      const defaults = {
        "#sa_meta_tip": "-",
        "#sa_meta_ifs": "-",
        "#sa_meta_qty": "0",
        "#sa_meta_brand": "-",
        "#sa_meta_model": "-",
        "#sa_meta_license": "-",
        "#sa_meta_mail": "-",
      };
      Object.entries(defaults).forEach(([selector, value]) => {
        const el = dom.one(selector);
        if (el) el.textContent = value;
      });
      [
        "#sa_meta_brand_wrap",
        "#sa_meta_model_wrap",
        "#sa_meta_license_wrap",
        "#sa_meta_mail_wrap",
        "#sa_meta_license_row",
      ].forEach((selector) => {
        const el = dom.one(selector);
        el?.classList.add("d-none");
      });
      const miktar = dom.one("#sa_miktar");
      if (miktar) {
        miktar.value = "1";
        miktar.removeAttribute("max");
      }
      [
        "#sa_license_select",
        "#sa_license_owner",
        "#sa_inventory_select",
        "#sa_inventory_owner",
        "#sa_printer_select",
      ].forEach((selector) => {
        const el = dom.one(selector);
        if (el) saSetFieldValue(el, "");
      });
      ["#sa_license_note", "#sa_printer_note", "#sa_general_note"].forEach(
        (selector) => {
          const el = dom.one(selector);
          if (el) el.value = "";
        },
      );
      const submitBtn =
        dom.one("#sa_submit") ||
        dom.one('#stokAtamaModal button[type="submit"]');
      submitBtn?.setAttribute("disabled", "disabled");
    }

    function computeStockId(meta) {
      if (!meta) return "";
      return [
        meta.donanim_tipi || "",
        meta.marka || "",
        meta.model || "",
        meta.ifs_no || "",
      ].join("|");
    }

    function normaliseStockMeta(meta) {
      if (!meta) return null;
      const normalised = { ...meta };
      if (normalised.mevcut_miktar === undefined) {
        if (normalised.net_miktar !== undefined) {
          normalised.mevcut_miktar = normalised.net_miktar;
        } else if (normalised.net !== undefined) {
          normalised.mevcut_miktar = normalised.net;
        }
      }
      const numericQty = Number(normalised.mevcut_miktar ?? 0);
      normalised.mevcut_miktar = Number.isNaN(numericQty) ? 0 : numericQty;
      return normalised;
    }

    function renderStockMeta(meta) {
      const normalised = normaliseStockMeta(meta);
      if (!normalised) {
        resetStockMetaDisplay();
        return;
      }
      state.selectedStockMeta = normalised;
      state.currentStockId = computeStockId(normalised);
      const tipEl = dom.one("#sa_meta_tip");
      if (tipEl) {
        tipEl.textContent = normalised?.donanim_tipi || "-";
        tipEl.classList.add("text-break");
      }
      const ifsEl = dom.one("#sa_meta_ifs");
      if (ifsEl) {
        ifsEl.textContent = normalised?.ifs_no || "-";
        ifsEl.classList.add("text-break");
      }
      const qtyEl = dom.one("#sa_meta_qty");
      if (qtyEl) qtyEl.textContent = String(normalised.mevcut_miktar || 0);

      const brand = normalised?.marka || "";
      const model = normalised?.model || "";
      const licenseKey = normalised?.lisans_anahtari || "";
      const mail = normalised?.mail_adresi || "";
      const brandWrap = dom.one("#sa_meta_brand_wrap");
      const modelWrap = dom.one("#sa_meta_model_wrap");
      const licenseWrap = dom.one("#sa_meta_license_wrap");
      const mailWrap = dom.one("#sa_meta_mail_wrap");
      const licenseRow = dom.one("#sa_meta_license_row");

      dom.toggle(brandWrap, Boolean(brand));
      dom.toggle(modelWrap, Boolean(model));
      dom.toggle(licenseWrap, Boolean(licenseKey));
      dom.toggle(mailWrap, Boolean(mail));
      const brandEl = dom.one("#sa_meta_brand");
      if (brandEl) {
        brandEl.textContent = brand || "-";
        brandEl.classList.add("text-break");
      }
      const modelEl = dom.one("#sa_meta_model");
      if (modelEl) {
        modelEl.textContent = model || "-";
        modelEl.classList.add("text-break");
      }
      const licenseEl = dom.one("#sa_meta_license");
      if (licenseEl) {
        licenseEl.textContent = licenseKey || "-";
        licenseEl.classList.add("text-break");
      }
      const mailEl = dom.one("#sa_meta_mail");
      if (mailEl) {
        mailEl.textContent = mail || "-";
        mailEl.classList.add("text-break");
      }
      if (licenseRow) {
        const hasLicenseInfo = Boolean(licenseKey || mail);
        dom.toggle(licenseRow, hasLicenseInfo);
      }
      const miktar = dom.one("#sa_miktar");
      if (miktar) {
        const max = Math.max(1, Number(normalised.mevcut_miktar || 0));
        miktar.max = String(max);
        if (Number(miktar.value) > max) {
          miktar.value = String(max);
        }
      }
      dom.toggle(dom.one("#sa_stock_meta"), true);
      dom.toggle(dom.one("#sa_stock_alert"), false);
      const submitBtn =
        dom.one("#sa_submit") ||
        dom.one('#stokAtamaModal button[type="submit"]');
      submitBtn?.removeAttribute("disabled");
    }

    function setSelectedStock(meta) {
      if (!meta) {
        resetStockMetaDisplay();
        updateAutoFields();
        return;
      }
      renderStockMeta(meta);
      updateAutoFields();
    }

    function applyFieldRules() {
      const active = dom.one("#sa_tabs .nav-link.active");
      const isLicense = active?.dataset.bsTarget?.includes("lisans");
      const isInventory = active?.dataset.bsTarget?.includes("envanter");
      const isPrinter = active?.dataset.bsTarget?.includes("yazici");
      const licenseField =
        dom.one("#sa_license_select") || dom.one("#sa_license_name");
      const inventoryField =
        dom.one("#sa_inventory_select") || dom.one("#sa_inv_no");
      const printerField =
        dom.one("#sa_printer_select") || dom.one("#sa_prn_no");
      dom.require(licenseField, Boolean(isLicense));
      dom.require(inventoryField, Boolean(isInventory));
      dom.require(printerField, Boolean(isPrinter));
    }

    function bindTabChange() {
      dom.all("#sa_tabs .nav-link").forEach((btn) => {
        btn.addEventListener("shown.bs.tab", applyFieldRules);
      });
    }

    function getAssignmentType() {
      const active = dom.one("#sa_tabs .nav-link.active");
      if (active?.dataset.bsTarget?.includes("envanter")) return "envanter";
      if (active?.dataset.bsTarget?.includes("yazici")) return "yazici";
      return "lisans";
    }

    function valueOf(selector) {
      return (dom.one(selector)?.value || "").trim();
    }

    function valueOrNull(selector) {
      const value = valueOf(selector);
      return value ? value : null;
    }

    function valueOfAny(...selectors) {
      for (const selector of selectors) {
        const value = valueOf(selector);
        if (value) return value;
      }
      return "";
    }

    function valueOrNullAny(...selectors) {
      for (const selector of selectors) {
        const value = valueOrNull(selector);
        if (value !== null && value !== undefined) {
          return value;
        }
      }
      return null;
    }

    function combineNotes(...notes) {
      const filtered = notes
        .map((note) => (typeof note === "string" ? note.trim() : note))
        .filter((note) => typeof note === "string" && note);
      if (!filtered.length) return null;
      return filtered.join("\n\n");
    }

    function buildLicenseForm() {
      const name = valueOfAny("#sa_license_select", "#sa_license_name");
      if (!name) {
        throw new Error("Lisans adı giriniz.");
      }
      return {
        lisans_adi: name,
        lisans_anahtari: valueOrNullAny("#sa_license_key"),
        sorumlu_personel: valueOrNullAny(
          "#sa_license_owner",
          "#sa_license_person",
        ),
        bagli_envanter_no: valueOrNullAny("#sa_license_inventory"),
        mail_adresi: valueOrNullAny("#sa_license_mail"),
        ifs_no: valueOrNullAny("#sa_license_ifs"),
      };
    }

    function buildInventoryForm() {
      const invNo = valueOfAny("#sa_inventory_select", "#sa_inv_no");
      if (!invNo) {
        throw new Error("Envanter numarası giriniz.");
      }
      return {
        envanter_no: invNo,
        bilgisayar_adi: valueOrNullAny("#sa_inv_pc"),
        fabrika: valueOrNullAny("#sa_inv_factory"),
        departman: valueOrNullAny("#sa_inv_department"),
        sorumlu_personel: valueOrNullAny(
          "#sa_inventory_owner",
          "#sa_inv_person",
        ),
        kullanim_alani: valueOrNullAny("#sa_inv_usage"),
        seri_no: valueOrNullAny("#sa_inv_serial"),
        bagli_envanter_no: valueOrNullAny("#sa_inv_machine"),
        notlar: valueOrNullAny("#sa_inv_note"),
        ifs_no: valueOrNullAny("#sa_inv_ifs"),
        marka: valueOrNullAny("#sa_inv_brand"),
        model: valueOrNullAny("#sa_inv_model"),
        donanim_tipi: valueOrNullAny("#sa_inv_hardware"),
      };
    }

    function buildPrinterForm() {
      const printerNo = valueOfAny("#sa_printer_select", "#sa_prn_no");
      if (!printerNo) {
        throw new Error("Yazıcı envanter numarası giriniz.");
      }
      return {
        envanter_no: printerNo,
        marka: valueOrNullAny("#sa_prn_brand"),
        model: valueOrNullAny("#sa_prn_model"),
        kullanim_alani: valueOrNullAny("#sa_prn_usage"),
        ip_adresi: valueOrNullAny("#sa_prn_ip"),
        mac: valueOrNullAny("#sa_prn_mac"),
        hostname: valueOrNullAny("#sa_prn_host"),
        ifs_no: valueOrNullAny("#sa_prn_ifs"),
        bagli_envanter_no: valueOrNullAny("#sa_prn_machine"),
        sorumlu_personel: valueOrNullAny("#sa_prn_person"),
        fabrika: valueOrNullAny("#sa_prn_factory"),
        notlar: valueOrNullAny("#sa_printer_note", "#sa_prn_note"),
      };
    }

    function buildAssignmentPayload() {
      const stockValue = state.currentStockId;
      if (!stockValue) {
        throw new Error("Lütfen stok seçiniz.");
      }
      const type = getAssignmentType();
      const generalNote =
        valueOrNull("#sa_general_note") ?? valueOrNull("#sa_not");
      const payload = {
        stock_id: stockValue,
        atama_turu: type,
        miktar: Number(valueOf("#sa_miktar") || "1") || 1,
        notlar: combineNotes(generalNote),
      };

      if (type === "lisans") {
        const licenseNote = valueOrNull("#sa_license_note");
        payload.license_form = buildLicenseForm();
        payload.notlar = combineNotes(generalNote, licenseNote);
      } else if (type === "envanter") {
        payload.envanter_form = buildInventoryForm();
      } else {
        const printerForm = buildPrinterForm();
        const printerNote = valueOrNull("#sa_printer_note");
        if (printerNote && !printerForm.notlar) {
          printerForm.notlar = printerNote;
        }
        payload.printer_form = printerForm;
        payload.notlar = combineNotes(generalNote, printerNote);
      }

      return payload;
    }

    async function submitAssignment(event) {
      event.preventDefault();
      let payload;
      try {
        payload = buildAssignmentPayload();
      } catch (err) {
        showBanner(err.message || "Atama başarısız.", "warning");
        return;
      }

      try {
        const result = await http.postJson(URLS.stockAssign, payload);
        if (result?.ok === false) {
          showBanner(
            result?.message || result?.detail || "Atama başarısız.",
            "danger",
          );
          return;
        }
        showBanner(result?.message || "Atama tamamlandı.", "success");
        dom.one("#stokAtamaModal .btn-close")?.click();
        await refreshStockStatus();
      } catch (err) {
        showBanner(err.message || "Atama gönderilemedi.", "danger");
        console.error("stock assign failed", err);
      }
    }

    function saSetFieldValue(input, value) {
      if (!input) return;
      if (input.tagName === "SELECT") {
        const stringValue =
          value !== undefined && value !== null ? String(value) : "";
        if (!stringValue) {
          Array.from(
            input.querySelectorAll('option[data-auto-option="1"]'),
          ).forEach((opt) => opt.remove());
          input.value = "";
          return;
        }
        let option = Array.from(input.options).find(
          (opt) => opt.value === stringValue,
        );
        if (!option) {
          option = document.createElement("option");
          option.value = stringValue;
          option.textContent = stringValue;
          option.dataset.autoOption = "1";
          input.appendChild(option);
        }
        input.value = stringValue;
      } else if (input.tagName === "TEXTAREA") {
        input.value = value ?? "";
      } else if (input.type === "checkbox" || input.type === "radio") {
        input.checked = Boolean(value);
      } else {
        input.value = value ?? "";
      }
    }

    function applyAutoData(data, options = {}) {
      const {
        source = null,
        clearMissing = false,
        onlySource = false,
        skipHide = false,
      } = options;
      dom.all("[data-auto-key]").forEach((input) => {
        const keyAttr = input.dataset.autoKey || "";
        const keys = keyAttr
          .split(/[|,]/)
          .map((k) => k.trim())
          .filter(Boolean);
        const sources = (input.dataset.autoSource || "")
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean);
        const hasSourceRestriction = sources.length > 0;
        if (source) {
          if (hasSourceRestriction) {
            if (!sources.includes(source)) {
              if (onlySource) return;
              return;
            }
          } else if (onlySource) {
            return;
          }
        } else if (onlySource) {
          return;
        }

        let value;
        for (const key of keys) {
          if (data && Object.prototype.hasOwnProperty.call(data, key)) {
            value = data[key];
            break;
          }
        }
        const hasValue = value !== undefined && value !== null && value !== "";
        if (hasValue) {
          saSetFieldValue(input, value);
        } else if (clearMissing) {
          saSetFieldValue(input, "");
        }
        if (!skipHide) {
          const container = input.closest("[data-auto-field]");
          if (container) {
            container.classList.toggle("d-none", hasValue);
          }
        }
      });
    }

    function autoSelectTab(meta) {
      let hint = (meta?.assignment_hint || "").toLowerCase();
      if (!hint && meta?.item_type) {
        hint = String(meta.item_type).toLowerCase();
      }
      if (!hint) {
        hint = baseSourceType(meta?.source_type);
      }
      let target = "#sa_tab_envanter";
      if (hint === "lisans" || meta?.lisans_anahtari) {
        target = "#sa_tab_lisans";
      } else if (hint === "yazici") {
        target = "#sa_tab_yazici";
      }
      const button = document.querySelector(
        `#sa_tabs [data-bs-target="${target}"]`,
      );
      if (button && !button.classList.contains("active")) {
        try {
          bootstrap.Tab.getOrCreateInstance(button).show();
        } catch (err) {
          console.warn("tab switch failed", err);
        }
      }
    }

    function resetSourceSpecificFields() {
      ["envanter", "lisans", "yazici"].forEach((type) => {
        applyAutoData(
          {},
          { source: type, clearMissing: true, onlySource: true },
        );
      });
    }

    async function fetchSourceDetail(sourceType, sourceId) {
      const cacheKey = `${sourceType}:${sourceId}`;
      if (state.sourceCache.has(cacheKey)) {
        return state.sourceCache.get(cacheKey);
      }
      const params = new URLSearchParams({
        type: sourceType,
        id: String(sourceId),
      });
      const data = await http.getJson(
        `${URLS.assignSourceDetail}?${params.toString()}`,
      );
      state.sourceCache.set(cacheKey, data);
      return data;
    }

    function fillSourceDetails(meta) {
      resetSourceSpecificFields();
      if (!meta || !meta.source_type || !meta.source_id) {
        return;
      }
      const requestId = ++state.sourceRequestId;
      fetchSourceDetail(meta.source_type, meta.source_id)
        .then((detail) => {
          if (requestId !== state.sourceRequestId) return;
          if (detail && detail.data) {
            applyAutoData(detail.data, {
              source: detail.type,
              clearMissing: true,
            });
          }
        })
        .catch((err) => {
          if (requestId !== state.sourceRequestId) return;
          console.error("source detail load failed", err);
        });
    }

    function updateAutoFields() {
      const meta = state.selectedStockMeta || {};
      applyAutoData(meta, { clearMissing: true });
      autoSelectTab(meta);
      fillSourceDetails(meta);
    }

    function assignFromStatus(encoded) {
      try {
        const item = JSON.parse(decodeURIComponent(encoded));
        setSelectedStock({
          ...item,
          mevcut_miktar: item.mevcut_miktar ?? item.net_miktar ?? item.net,
        });
        const modalEl = document.getElementById("stokAtamaModal");
        if (modalEl) {
          const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
          modal.show();
        }
      } catch (err) {
        console.error("assign decode failed", err);
      }
    }

    async function scrapFromStatus(encoded) {
      let item;
      try {
        item = JSON.parse(decodeURIComponent(encoded));
      } catch (err) {
        console.error("scrap decode failed", err);
        alert("Geçersiz kayıt");
        return;
      }
      const qtyStr = window.prompt("Miktar", "1");
      if (qtyStr === null) return;
      const qty = Number(qtyStr);
      if (!qty || qty <= 0) {
        alert("Geçersiz miktar");
        return;
      }
      const confirmed = await showConfirm({
        message: `${qty} adet hurdaya ayrılacak. Onaylıyor musunuz?`,
        confirmLabel: "Onayla",
        confirmVariant: "danger",
      });
      if (!confirmed) return;
      const payload = {
        donanim_tipi: item.donanim_tipi,
        marka: item.marka,
        model: item.model,
        ifs_no: item.ifs_no,
        miktar: qty,
        islem: "hurda",
        islem_yapan: "UI",
      };
      try {
        const result = await http.postJson("/stock/add", payload);
        if (result?.ok) {
          await closeFaultAfterScrap(item);
          if (window.Faults && typeof window.Faults.refresh === "function") {
            window.Faults.refresh("stock");
          }
          await refreshStockStatus();
        } else {
          alert(result?.error || "İşlem başarısız");
        }
      } catch (err) {
        console.error("scrap failed", err);
        alert(err.message || "İşlem başarısız");
      }
    }

    function buildFaultKey(item) {
      if (!item) return "";
      const fields = [
        item?.donanim_tipi,
        item?.marka,
        item?.model,
        item?.ifs_no,
        item?.source_type,
        item?.source_id,
      ];
      const parts = fields
        .map((part) => (part == null ? "" : String(part).trim()))
        .filter(Boolean);
      return (
        parts.join("|") ||
        (item?.donanim_tipi
          ? `stock:${String(item.donanim_tipi).trim()}`
          : "stock")
      );
    }

    function buildFaultLabel(item) {
      if (!item) return "Stok Kaydı";
      const parts = [item.donanim_tipi, item.marka, item.model]
        .map((part) => (part == null ? "" : String(part).trim()))
        .filter(Boolean);
      if (parts.length) return parts.join(" - ");
      if (item.ifs_no) return String(item.ifs_no);
      return "Stok Kaydı";
    }

    function buildFaultMeta(item) {
      return {
        donanim_tipi: item?.donanim_tipi || "",
        marka: item?.marka || "",
        model: item?.model || "",
        ifs_no: item?.ifs_no || "",
      };
    }

    function markFaultFromStatus(encoded) {
      if (!window.Faults || typeof window.Faults.openMarkModal !== "function") {
        alert("Arıza ekranı açılamadı.");
        return;
      }
      let item;
      try {
        item = JSON.parse(decodeURIComponent(encoded));
      } catch (err) {
        console.error("fault decode failed", err);
        alert("Geçersiz kayıt");
        return;
      }
      const key = buildFaultKey(item);
      const label = buildFaultLabel(item);
      window.Faults.openMarkModal("stock", {
        entityId: null,
        entityKey: key,
        deviceNo: label,
        title: label,
        meta: buildFaultMeta(item),
      });
    }

    function repairFromStatus(encoded) {
      if (
        !window.Faults ||
        typeof window.Faults.openRepairModal !== "function"
      ) {
        alert("Arıza ekranı açılamadı.");
        return;
      }
      let item;
      try {
        item = JSON.parse(decodeURIComponent(encoded));
      } catch (err) {
        console.error("repair decode failed", err);
        alert("Geçersiz kayıt");
        return;
      }
      const key = buildFaultKey(item);
      const label = buildFaultLabel(item);
      window.Faults.openRepairModal("stock", {
        entityId: null,
        entityKey: key,
        deviceNo: label,
      });
    }

    async function closeFaultAfterScrap(item) {
      if (!item) return;
      const key = buildFaultKey(item);
      if (!key || typeof fetch !== "function") return;
      const fd = new FormData();
      fd.append("entity", "stock");
      fd.append("entity_key", key);
      fd.append("status", "hurda");
      try {
        const res = await fetch("/faults/repair", {
          method: "POST",
          body: fd,
          credentials: "same-origin",
        });
        if (!res.ok && res.status !== 404) {
          const text = await res.text();
          console.warn("fault close failed", text);
        }
      } catch (err) {
        console.warn("fault close request failed", err);
      }
    }

    function setStockStatusMessage(tbody, message, colspan = 9) {
      if (!tbody) return;
      tbody.innerHTML = `<tr data-empty-row="1"><td colspan="${colspan}" class="text-center text-muted">${message}</td></tr>`;
    }

    function formatLastOperation(item) {
      if (!item?.son_islem_ts) return "-";
      const date = new Date(item.son_islem_ts);
      if (Number.isNaN(date.getTime())) return "-";
      return date.toLocaleString("tr-TR", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
      });
    }

    function createNormalRow(item) {
      const encoded = encodeURIComponent(JSON.stringify(item));
      const systemKey = encodeSystemKey(item);
      const checkedAttr = systemRoomState.selectedNormal.has(systemKey)
        ? " checked"
        : "";
      const hasDetail = Boolean(item?.source_type || item?.source_id);
      const detailButton = hasDetail
        ? `<button type="button" class="btn btn-sm btn-outline-secondary" data-stock-detail="${encoded}" title="Detay"><span aria-hidden="true">&#9776;</span><span class="visually-hidden">Detay</span></button>`
        : "";
      const availableQty = Number(item?.net_miktar) || 0;
      const menuItems = [];
      if (availableQty > 0) {
        menuItems.push(
          `<li><button class="dropdown-item" type="button" onclick="assignFromStatus('${encoded}')">Atama Yap</button></li>`,
        );
      }
      const key = buildFaultKey(item);
      const hasFault =
        typeof window !== "undefined" &&
        window.Faults &&
        typeof window.Faults.hasOpenFault === "function"
          ? window.Faults.hasOpenFault("stock", key)
          : false;
      if (hasFault) {
        menuItems.push(
          `<li><button class="dropdown-item" type="button" onclick="repairFromStatus('${encoded}')">Aktif Et</button></li>`,
        );
      } else {
        menuItems.push(
          `<li><button class="dropdown-item" type="button" onclick="markFaultFromStatus('${encoded}')">Arızalı</button></li>`,
        );
      }
      if (menuItems.length) {
        menuItems.push('<li><hr class="dropdown-divider"></li>');
      }
      menuItems.push(
        `<li><button class="dropdown-item text-danger" type="button" onclick="scrapFromStatus('${encoded}')">Hurda</button></li>`,
      );
      const actionsMenu = `
    <div class="btn-group">
      <button class="btn btn-sm btn-outline-primary dropdown-toggle" type="button" data-bs-toggle="dropdown" aria-expanded="false">
        İşlemler
      </button>
      <ul class="dropdown-menu dropdown-menu-end">
        ${menuItems.join("")}
      </ul>
    </div>`;
      const lastOp = formatLastOperation(item);
      return `<tr>
    <td class="text-center"><input type="checkbox" class="form-check-input" data-system-select value="${systemKey}"${checkedAttr}></td>
    <td>${item.donanim_tipi || "-"}</td>
    <td>${item.marka || "-"}</td>
    <td>${item.model || "-"}</td>
    <td>${item.ifs_no || "-"}</td>
    <td class="text-end">${item.net_miktar ?? "-"}</td>
    <td>${lastOp}</td>
    <td class="text-center">
      <div class="d-inline-flex align-items-center gap-1">
        ${detailButton}
        ${actionsMenu}
      </div>
    </td>
    <td class="text-center">
      <button type="button" class="btn btn-sm btn-outline-secondary" data-system-room-action="add" data-system-item="${systemKey}">Sistem Odasına Ata</button>
    </td>
  </tr>`;
    }

    function createSystemRoomRow(item) {
      const encoded = encodeURIComponent(JSON.stringify(item));
      const systemKey = encodeSystemKey(item);
      const checkedAttr = systemRoomState.selectedSystem.has(systemKey)
        ? " checked"
        : "";
      const normalisedKey = normaliseSystemKey(item);
      const typeLabel =
        TYPE_LABELS[normalisedKey.item_type] || normalisedKey.item_type || "-";
      const lastOp = formatLastOperation(item);
      const assignedDate = formatStockDetailDate(item?.system_room_assigned_at);
      const assignedInfo = item?.system_room_assigned_by
        ? assignedDate && assignedDate !== "-"
          ? `${item.system_room_assigned_by} - ${assignedDate}`
          : item.system_room_assigned_by
        : assignedDate || "-";
      const hasDetail = Boolean(item?.source_type || item?.source_id);
      const detailButton = hasDetail
        ? `<button type="button" class="btn btn-sm btn-outline-secondary" data-stock-detail="${encoded}" title="Detay"><span aria-hidden="true">&#9776;</span><span class="visually-hidden">Detay</span></button>`
        : "";
      return `<tr>
    <td class="text-center"><input type="checkbox" class="form-check-input" data-system-room-select value="${systemKey}"${checkedAttr}></td>
    <td>${typeLabel}</td>
    <td>${item.donanim_tipi || "-"}</td>
    <td>${item.marka || "-"}</td>
    <td>${item.model || "-"}</td>
    <td>${item.ifs_no || "-"}</td>
    <td class="text-end">${item.net_miktar ?? "-"}</td>
    <td>${lastOp}</td>
    <td>${assignedInfo}</td>
    <td class="text-center">
      <div class="d-inline-flex align-items-center gap-1">
        ${detailButton}
        <button type="button" class="btn btn-sm btn-outline-danger" data-system-room-action="remove" data-system-item="${systemKey}">Çıkar</button>
      </div>
    </td>
  </tr>`;
    }

    function renderStockStatusTable(tbody, items) {
      if (!tbody) return;
      if (!Array.isArray(items) || items.length === 0) {
        setStockStatusMessage(tbody, "Stok bulunamadı", 9);
        return;
      }
      tbody.innerHTML = items.map(createNormalRow).join("");
    }

    function renderSystemRoomTable(tbody, items) {
      if (!tbody) return;
      if (!Array.isArray(items) || items.length === 0) {
        setStockStatusMessage(tbody, "Sistem odasında kayıt bulunmuyor", 10);
        return;
      }
      tbody.innerHTML = items.map(createSystemRoomRow).join("");
    }

    function filterStockTable() {
      const query = (dom.one("#stockSearch")?.value || "").toLowerCase();
      const activePane = document.querySelector(
        "#stockStatusTabContent .tab-pane.active",
      );
      if (!activePane) return;
      activePane.querySelectorAll("tbody tr").forEach((tr) => {
        if (tr.dataset.emptyRow === "1") {
          tr.style.display = "";
          return;
        }
        const text = tr.textContent || "";
        tr.style.display = text.toLowerCase().includes(query) ? "" : "none";
      });
    }

    async function refreshStockStatus() {
      const inventoryTbody = document.querySelector(
        "#tblStockStatusInventory tbody",
      );
      const printerTbody = document.querySelector(
        "#tblStockStatusPrinters tbody",
      );
      const licenseTbody = document.querySelector(
        "#tblStockStatusLicense tbody",
      );
      const systemTbody = document.querySelector(
        "#tblStockStatusSystemRoom tbody",
      );
      setStockStatusMessage(inventoryTbody, "Yükleniyor…", 9);
      setStockStatusMessage(printerTbody, "Yükleniyor…", 9);
      setStockStatusMessage(licenseTbody, "Yükleniyor…", 9);
      setStockStatusMessage(systemTbody, "Yükleniyor…", 10);
      try {
        const data = await http.requestJson(STOCK_STATUS_URL, {
          credentials: "same-origin",
        });
        const items = Array.isArray(data)
          ? data
          : data.items || data.rows || [];
        if (!Array.isArray(items)) {
          setStockStatusMessage(inventoryTbody, "Veri alınamadı", 9);
          setStockStatusMessage(printerTbody, "Veri alınamadı", 9);
          setStockStatusMessage(licenseTbody, "Veri alınamadı", 9);
          setStockStatusMessage(systemTbody, "Veri alınamadı", 10);
          return;
        }
        const inventoryItems = [];
        const printerItems = [];
        const licenseItems = [];
        const systemItems = [];
        items.forEach((item) => {
          if (item?.system_room) {
            systemItems.push(item);
            return;
          }
          const category = detectItemCategory(item);
          if (category === "license") {
            licenseItems.push(item);
          } else if (category === "printer") {
            printerItems.push(item);
          } else {
            inventoryItems.push(item);
          }
        });
        systemRoomState.selectedNormal.clear();
        systemRoomState.selectedSystem.clear();
        renderStockStatusTable(inventoryTbody, inventoryItems);
        renderStockStatusTable(printerTbody, printerItems);
        renderStockStatusTable(licenseTbody, licenseItems);
        renderSystemRoomTable(systemTbody, systemItems);
        updateSystemRoomButtons();
        filterStockTable();
      } catch (err) {
        console.error("stock status load failed", err);
        setStockStatusMessage(inventoryTbody, "Veri alınamadı", 9);
        setStockStatusMessage(printerTbody, "Veri alınamadı", 9);
        setStockStatusMessage(licenseTbody, "Veri alınamadı", 9);
        setStockStatusMessage(systemTbody, "Veri alınamadı", 10);
      }
    }

    function collectItemsFromSet(store) {
      const items = [];
      store.forEach((value) => {
        const key = parseSystemKey(value);
        if (key) items.push(key);
      });
      return items;
    }

    async function addToSystemRoom(items) {
      if (!items.length) return;
      try {
        await http.postJson("/api/stock/system-room/add", { items });
        systemRoomState.selectedNormal.clear();
        systemRoomState.selectedSystem.clear();
        updateSystemRoomButtons();
        await refreshStockStatus();
      } catch (err) {
        console.error("system room add failed", err);
        alert(err.message || "İşlem başarısız");
      }
    }

    async function removeFromSystemRoom(items) {
      if (!items.length) return;
      try {
        await http.postJson("/api/stock/system-room/remove", { items });
        systemRoomState.selectedNormal.clear();
        systemRoomState.selectedSystem.clear();
        updateSystemRoomButtons();
        await refreshStockStatus();
      } catch (err) {
        console.error("system room remove failed", err);
        alert(err.message || "İşlem başarısız");
      }
    }

    function handleSystemSelectionChange(event) {
      const checkbox = event.target.closest("[data-system-select]");
      if (checkbox) {
        const key = checkbox.value;
        if (checkbox.checked) {
          systemRoomState.selectedNormal.add(key);
        } else {
          systemRoomState.selectedNormal.delete(key);
        }
        updateSystemRoomButtons();
        return;
      }
      const roomCheckbox = event.target.closest("[data-system-room-select]");
      if (roomCheckbox) {
        const key = roomCheckbox.value;
        if (roomCheckbox.checked) {
          systemRoomState.selectedSystem.add(key);
        } else {
          systemRoomState.selectedSystem.delete(key);
        }
        updateSystemRoomButtons();
      }
    }

    async function handleSystemRoomAction(event) {
      const btn = event.target.closest("[data-system-room-action]");
      if (!btn) return;
      const encoded = btn.getAttribute("data-system-item");
      const key = parseSystemKey(encoded);
      if (!key) return;
      const action = btn.dataset.systemRoomAction;
      btn.disabled = true;
      try {
        if (action === "add") {
          await addToSystemRoom([key]);
        } else if (action === "remove") {
          await removeFromSystemRoom([key]);
        }
      } catch (err) {
        console.error("system room action failed", err);
        alert(err.message || "İşlem başarısız");
      } finally {
        btn.disabled = false;
      }
    }

    async function handleSystemRoomAddSelected() {
      const items = collectItemsFromSet(systemRoomState.selectedNormal);
      if (!items.length) return;
      await addToSystemRoom(items);
    }

    async function handleSystemRoomRemoveSelected() {
      const items = collectItemsFromSet(systemRoomState.selectedSystem);
      if (!items.length) return;
      await removeFromSystemRoom(items);
    }

    const STOCK_DETAIL_SOURCE_LABELS = {
      envanter: "Envanter",
      lisans: "Lisans",
      yazici: "Yazıcı",
    };

    function formatStockDetailValue(value) {
      return value === undefined || value === null || value === ""
        ? "-"
        : `${value}`;
    }

    function formatStockDetailDate(value) {
      if (!value) return "-";
      const date = new Date(value);
      if (Number.isNaN(date.getTime())) return "-";
      return date.toLocaleString("tr-TR", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
      });
    }

    function stockDetailUrl(item) {
      if (!item || !item.source_id) return "";
      const type = baseSourceType(item.source_type);
      if (type === "envanter") return `/inventory/${item.source_id}`;
      if (type === "lisans") return `/lisans/${item.source_id}`;
      if (type === "yazici") return `/printers/${item.source_id}`;
      return "";
    }

    function getStockDetailRows(item) {
      const rows = [
        ["Donanım Tipi", formatStockDetailValue(item?.donanim_tipi)],
        ["Marka", formatStockDetailValue(item?.marka)],
        ["Model", formatStockDetailValue(item?.model)],
        ["IFS No", formatStockDetailValue(item?.ifs_no)],
        ["Stok", formatStockDetailValue(item?.net_miktar)],
        ["Son İşlem", formatStockDetailDate(item?.son_islem_ts)],
      ];

      if (item?.source_type || item?.source_id) {
        const type = baseSourceType(item?.source_type);
        const label = type
          ? STOCK_DETAIL_SOURCE_LABELS[type] || item.source_type
          : item?.source_type || "";
        let value = label;
        if (item?.source_id) {
          value = value
            ? `${value} (#${item.source_id})`
            : `#${item.source_id}`;
        }
        if (value) {
          rows.push(["Kaynak", value]);
        }
      }

      return rows;
    }

    function openStockDetailModal(item) {
      const rows = getStockDetailRows(item);
      const modalEl = document.getElementById("stokDetailModal");
      const listEl = modalEl?.querySelector("#stokDetailList");
      const linkWrap = modalEl?.querySelector("#stokDetailLinkWrap");
      const linkEl = modalEl?.querySelector("#stokDetailLink");

      if (!modalEl || !listEl) {
        alert(rows.map(([label, value]) => `${label}: ${value}`).join("\n"));
        return;
      }

      listEl.innerHTML = "";
      rows.forEach(([label, value]) => {
        const dt = document.createElement("dt");
        dt.className = "col-5 fw-semibold";
        dt.textContent = label;
        const dd = document.createElement("dd");
        dd.className = "col-7 text-break";
        dd.textContent = value;
        listEl.appendChild(dt);
        listEl.appendChild(dd);
      });

      if (linkWrap && linkEl) {
        const url = stockDetailUrl(item);
        if (url) {
          linkEl.href = url;
          linkWrap.classList.remove("d-none");
        } else {
          linkEl.removeAttribute("href");
          linkWrap.classList.add("d-none");
        }
      }

      try {
        const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
        modal.show();
      } catch (err) {
        console.error("stock detail modal failed", err);
        alert(rows.map(([label, value]) => `${label}: ${value}`).join("\n"));
      }
    }

    function handleDetailClick(event) {
      const btn = event.target.closest("[data-stock-detail]");
      if (!btn) return;
      const encoded = btn.getAttribute("data-stock-detail");
      if (!encoded) return;
      event.preventDefault();
      try {
        const item = JSON.parse(decodeURIComponent(encoded));
        openStockDetailModal(item);
      } catch (err) {
        console.error("stock detail decode failed", err);
      }
    }

    function init() {
      console.log("[StokAtama] boot start");
      resetStockMetaDisplay();
      document.addEventListener("click", handleDetailClick);
      document.addEventListener("change", handleSystemSelectionChange);
      document.addEventListener("click", handleSystemRoomAction);
      dom
        .one("#btnSystemRoomAdd")
        ?.addEventListener("click", handleSystemRoomAddSelected);
      dom
        .one("#btnSystemRoomRemove")
        ?.addEventListener("click", handleSystemRoomRemoveSelected);
      dom.one("#stockSearch")?.addEventListener("input", filterStockTable);
      document
        .querySelectorAll('#stockStatusTabs [data-bs-toggle="tab"]')
        .forEach((btn) => {
          btn.addEventListener("shown.bs.tab", filterStockTable);
        });
      const statusTab = document.getElementById("tab-status");
      statusTab?.addEventListener("shown.bs.tab", refreshStockStatus);

      dom.one("#sa_submit")?.addEventListener("click", submitAssignment);
      dom
        .one("#stockAssignForm")
        ?.addEventListener("submit", submitAssignment);
      bindTabChange();
      applyFieldRules();

      console.log("[StokAtama] DOMContentLoaded");
      loadSources();

      document.addEventListener("shown.bs.modal", async (event) => {
        if (event.target.id !== "stokAtamaModal") return;
        await loadSources();
        if (state.selectedStockMeta) {
          renderStockMeta(state.selectedStockMeta);
        } else {
          resetStockMetaDisplay();
        }
        updateAutoFields();
        applyFieldRules();
      });

      document.addEventListener("hidden.bs.modal", (event) => {
        if (event.target.id !== "stokAtamaModal") return;
        setSelectedStock(null);
      });
    }

    return {
      init,
      assignFromStatus,
      scrapFromStatus,
      markFaultFromStatus,
      repairFromStatus,
      refreshStockStatus,
    };
  })();

  // ---------------------------------------------------------------------------
  // Başlat
  // ---------------------------------------------------------------------------

  function showBootstrapTab(selector) {
    const el = document.querySelector(selector);
    if (!el) return;
    try {
      bootstrap.Tab.getOrCreateInstance(el).show();
    } catch (err) {
      console.warn("tab activation failed", selector, err);
    }
  }

  function applyInitialTabSelection() {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search || "");
    const tabParam = (params.get("tab") || "").toLowerCase();
    const moduleParam = (params.get("module") || "").toLowerCase();

    if (tabParam === "status") {
      showBootstrapTab("#tab-status");
    } else if (tabParam === "log") {
      showBootstrapTab("#tab-log");
    }

    if (!moduleParam) return;

    showBootstrapTab("#tab-status");

    if (moduleParam === "inventory" || moduleParam === "envanter") {
      showBootstrapTab("#status-tab-inventory");
    } else if (moduleParam === "printer" || moduleParam === "yazici") {
      showBootstrapTab("#status-tab-printer");
    } else if (
      moduleParam === "license" ||
      moduleParam === "lisans" ||
      moduleParam === "lisanslar" ||
      moduleParam === "software" ||
      moduleParam === "yazilim"
    ) {
      showBootstrapTab("#status-tab-license");
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    StockAddForm.init();
    StockAssign.init();
    applyInitialTabSelection();
    StockAssign.refreshStockStatus();
  });

  window.assignFromStatus = (encoded) => StockAssign.assignFromStatus(encoded);
  window.scrapFromStatus = (encoded) => StockAssign.scrapFromStatus(encoded);
  window.markFaultFromStatus = (encoded) =>
    StockAssign.markFaultFromStatus(encoded);
  window.repairFromStatus = (encoded) => StockAssign.repairFromStatus(encoded);
  window.loadStockStatus = () => StockAssign.refreshStockStatus();
  window.onStockFaultsUpdated = () => StockAssign.refreshStockStatus();
})();
