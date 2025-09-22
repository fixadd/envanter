(() => {
  'use strict';

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
      element.classList.toggle('d-none', !visible);
    },
    require(element, on) {
      if (!element) return;
      if (on) {
        element.setAttribute('required', 'required');
      } else {
        element.removeAttribute('required');
      }
    },
  };

  function toggleDisabled(container, disabled) {
    if (!container) return;
    dom.all('input,select,textarea,button', container).forEach((el) => {
      if (disabled) {
        el.setAttribute('disabled', 'disabled');
      } else {
        el.removeAttribute('disabled');
      }
    });
  }

  // ---------------------------------------------------------------------------
  // HTTP yardımcıları
  // ---------------------------------------------------------------------------
  const http = {};

  http.requestJson = async function requestJson(url, options = {}) {
    const headers = { Accept: 'application/json', ...(options.headers || {}) };
    const response = await fetch(url, { ...options, headers });

    let bodyText = '';
    try {
      bodyText = await response.text();
    } catch (err) {
      console.error('response read failed', err);
    }

    let data = null;
    if (bodyText) {
      try {
        data = JSON.parse(bodyText);
      } catch (err) {
        if (response.ok) {
          const parseError = new Error('Sunucudan geçerli JSON alınamadı.');
          parseError.cause = err;
          throw parseError;
        }
      }
    }

    if (!response.ok) {
      const fallback = bodyText || `HTTP ${response.status}`;
      const message = (data && (data.detail || data.error || data.message)) || fallback;
      const error = new Error(message);
      error.status = response.status;
      error.data = data;
      throw error;
    }

    return data ?? {};
  };

  http.getJson = function getJson(url, options = {}) {
    return http.requestJson(url, { ...options, method: options.method || 'GET' });
  };

  http.postJson = function postJson(url, payload, options = {}) {
    const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
    return http.requestJson(url, {
      ...options,
      method: 'POST',
      body: JSON.stringify(payload),
      headers,
    });
  };

  // ---------------------------------------------------------------------------
  // Meta ve API kökleri
  // ---------------------------------------------------------------------------
  function getMetaApiRoot() {
    if (typeof document === 'undefined') return '/api';
    const meta = document.querySelector('meta[name="api-root"]');
    if (!meta) return '/api';
    const content = (meta.getAttribute('content') || '').trim();
    return content ? content.replace(/\/$/, '') : '/api';
  }

  const API_ROOT_META = getMetaApiRoot();
  const STOCK_STATUS_URL = `${API_ROOT_META}/stock/status`;
  const API_PREFIX = '';
  const URLS = {
    stockOptions: `${API_PREFIX}/stock/options`,
    assignSources: `${API_PREFIX}/inventory/assign/sources`,
    stockAssign: `${API_PREFIX}/stock/assign`,
    assignSourceDetail: `${API_PREFIX}/stock/assign/source-detail`,
  };

  // ---------------------------------------------------------------------------
  // Stok ekleme formu
  // ---------------------------------------------------------------------------
  const StockAddForm = (() => {
    const state = {
      currentType: 'inventory',
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
      state.elements.modal = dom.one('#modalStockAdd');
      state.elements.form = dom.one('#frmStockAdd');
      state.elements.hardwareFields = dom.one('#hardwareFields');
      state.elements.licenseFields = dom.one('#licenseFields');
      state.elements.miktarInput = dom.one('#miktar');
      state.elements.rowMiktar = dom.one('#rowMiktar');
      state.elements.typeButtons = dom.all('[data-stock-add-type]');
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
        input.value = '1';
        input.readOnly = true;
      } else {
        input.readOnly = false;
      }
    }

    function updateDonanimRequirement(isLicense) {
      const select = dom.one('#stok_donanim_tipi');
      dom.require(select, !isLicense);
    }

    function updateTypeButtons() {
      state.elements.typeButtons.forEach((btn) => {
        const btnType = btn.dataset.stockAddType || 'inventory';
        const isActive = btnType === state.currentType;
        btn.classList.toggle('active', isActive);
        btn.setAttribute('aria-selected', isActive ? 'true' : 'false');
      });
    }

    function applyStockAddType(type) {
      state.currentType = type === 'license' ? 'license' : 'inventory';
      const isLicense = state.currentType === 'license';
      updateSectionVisibility(isLicense);
      updateFieldAvailability(isLicense);
      updateDonanimRequirement(isLicense);
      updateMiktarField(isLicense);
      updateTypeButtons();
    }

    function bindTypeButtons() {
      state.elements.typeButtons.forEach((btn) => {
        btn.addEventListener('click', () => {
          applyStockAddType(btn.dataset.stockAddType || 'inventory');
        });
      });
    }

    function normaliseFormData(form) {
      const formData = new FormData(form);
      const isLicense = state.currentType === 'license';
      if (isLicense) {
        const licenseName = formData.get('lisans_adi') || '';
        formData.set('miktar', '1');
        formData.set('donanim_tipi', licenseName);
        formData.set('is_lisans', '1');
        formData.delete('is_license');
      } else {
        formData.delete('is_lisans');
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
        alert(err.message || 'Kayıt başarısız');
        return;
      }
      try {
        const result = await http.postJson('/stock/add', payload);
        if (result?.ok) {
          window.location.reload();
          return;
        }
        alert(result?.error || 'Kayıt başarısız');
      } catch (err) {
        console.error('stock add failed', err);
        alert(`Kayıt başarısız${err?.message ? `: ${err.message}` : ''}`);
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
        state.elements.form.addEventListener('submit', submitStockAdd);
      }

      if (state.elements.modal) {
        state.elements.modal.addEventListener('shown.bs.modal', handleModalShown);
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
      preselectStockId: null,
      sourceCache: new Map(),
      sourceRequestId: 0,
    };

    function showBanner(message, type = 'danger') {
      let holder = dom.one('#sa_banner');
      if (!holder) {
        const body = dom.one('#stokAtamaModal .modal-body');
        holder = document.createElement('div');
        holder.id = 'sa_banner';
        body?.prepend(holder);
      }
      if (!holder) return;
      holder.innerHTML = `<div class="alert alert-${type} py-2 px-3 mb-2">${message}</div>`;
      window.setTimeout(() => {
        if (holder) holder.innerHTML = '';
      }, 6000);
      console.log('[StokAtama]', message);
    }

    function fillSelect(selector, data, valueKey = 'id', labelKey = 'text') {
      const element = dom.one(selector);
      if (!element) return;
      element.innerHTML = '<option value="">Seçiniz...</option>';
      (data || []).forEach((item) => {
        const option = document.createElement('option');
        const value = item[valueKey] ?? item.id ?? item.value ?? '';
        const label = item[labelKey] ?? item.name ?? item.text ?? value;
        option.value = value || '';
        option.textContent = label || value || '';
        element.appendChild(option);
      });
    }

    async function loadList(url) {
      try {
        const data = await http.getJson(url);
        return { data: Array.isArray(data) ? data : [], error: null };
      } catch (err) {
        console.error('assign source request failed', url, err);
        return { data: [], error: err };
      }
    }

    async function loadStocks() {
      const select = dom.one('#sa_stock');
      if (!select) return;
      select.innerHTML = '<option value="">Seçiniz...</option>';
      try {
        const data = await http.getJson(URLS.stockOptions);
        if (!Array.isArray(data) || data.length === 0) {
          showBanner('Uygun stok bulunamadı (miktar > 0).', 'warning');
          return;
        }
        data.forEach((item) => {
          const option = document.createElement('option');
          option.value = item.id;
          option.textContent =
            item.label ?? `${item.donanim_tipi || 'Donanım'} | IFS:${item.ifs_no || '-'} | Mevcut:${item.mevcut_miktar ?? 0}`;
          option.dataset.tip = item.donanim_tipi || '';
          option.dataset.ifs = item.ifs_no || '';
          option.dataset.qty = String(Number(item.mevcut_miktar ?? 0));
          option.dataset.meta = encodeURIComponent(JSON.stringify(item));
          select.appendChild(option);
        });
        if (state.preselectStockId) {
          select.value = state.preselectStockId;
          select.dispatchEvent(new Event('change'));
          state.preselectStockId = null;
        }
      } catch (err) {
        showBanner('Stok listesi yüklenemedi. Konsolu kontrol edin.', 'danger');
        console.error('sa_loadStocks failed', err);
      }
    }

    async function loadSources() {
      try {
        const [usersRes, inventoryRes, factoryRes, deptRes, usageRes] = await Promise.all([
          loadList(`${URLS.assignSources}?type=users`),
          loadList(`${URLS.assignSources}?type=envanter`),
          loadList('/api/lookup/fabrika'),
          loadList(`${URLS.assignSources}?type=departman`),
          loadList('/api/lookup/kullanim_alani'),
        ]);

        const hadError = [usersRes, inventoryRes, factoryRes, deptRes, usageRes].some((r) => r.error);
        if (hadError) {
          showBanner('Atama kaynakları alınamadı. URL prefix doğru mu?', 'warning');
        }

        fillSelect('#sa_license_person', usersRes.data, 'id', 'text');
        fillSelect('#sa_inv_person', usersRes.data, 'id', 'text');
        fillSelect('#sa_license_inventory', inventoryRes.data, 'id', 'text');
        fillSelect('#sa_inv_factory', factoryRes.data, 'id', 'name');
        fillSelect('#sa_inv_department', deptRes.data, 'id', 'text');
        fillSelect('#sa_inv_usage', usageRes.data, 'id', 'name');
        fillSelect('#sa_prn_usage', usageRes.data, 'id', 'name');
        updateAutoFields();
      } catch (err) {
        showBanner('Atama kaynakları yüklenemedi. Konsolu kontrol edin.', 'danger');
        console.error('sa_loadSources failed', err);
      }
    }

    function resetStockMetaDisplay() {
      state.selectedStockMeta = null;
      dom.toggle(dom.one('#sa_stock_meta'), false);
      const defaults = {
        '#sa_meta_tip': '-',
        '#sa_meta_ifs': '-',
        '#sa_meta_qty': '0',
        '#sa_meta_brand': '-',
        '#sa_meta_model': '-',
        '#sa_meta_license': '-',
        '#sa_meta_mail': '-',
      };
      Object.entries(defaults).forEach(([selector, value]) => {
        const el = dom.one(selector);
        if (el) el.textContent = value;
      });
      ['#sa_meta_brand_wrap', '#sa_meta_model_wrap', '#sa_meta_license_wrap', '#sa_meta_mail_wrap', '#sa_meta_license_row'].forEach(
        (selector) => {
          const el = dom.one(selector);
          el?.classList.add('d-none');
        },
      );
    }

    function renderStockMeta(meta, option) {
      if (!meta || !option) {
        resetStockMetaDisplay();
        return;
      }
      state.selectedStockMeta = meta;
      const tipEl = dom.one('#sa_meta_tip');
      if (tipEl) {
        tipEl.textContent = meta?.donanim_tipi || '-';
        tipEl.classList.add('text-break');
      }
      const ifsEl = dom.one('#sa_meta_ifs');
      if (ifsEl) {
        ifsEl.textContent = meta?.ifs_no || '-';
        ifsEl.classList.add('text-break');
      }
      const qtyEl = dom.one('#sa_meta_qty');
      if (qtyEl) qtyEl.textContent = option.dataset.qty || '0';

      const brand = meta?.marka || '';
      const model = meta?.model || '';
      const licenseKey = meta?.lisans_anahtari || '';
      const mail = meta?.mail_adresi || '';
      const brandWrap = dom.one('#sa_meta_brand_wrap');
      const modelWrap = dom.one('#sa_meta_model_wrap');
      const licenseWrap = dom.one('#sa_meta_license_wrap');
      const mailWrap = dom.one('#sa_meta_mail_wrap');
      const licenseRow = dom.one('#sa_meta_license_row');

      dom.toggle(brandWrap, Boolean(brand));
      dom.toggle(modelWrap, Boolean(model));
      dom.toggle(licenseWrap, Boolean(licenseKey));
      dom.toggle(mailWrap, Boolean(mail));
      const brandEl = dom.one('#sa_meta_brand');
      if (brandEl) {
        brandEl.textContent = brand || '-';
        brandEl.classList.add('text-break');
      }
      const modelEl = dom.one('#sa_meta_model');
      if (modelEl) {
        modelEl.textContent = model || '-';
        modelEl.classList.add('text-break');
      }
      const licenseEl = dom.one('#sa_meta_license');
      if (licenseEl) {
        licenseEl.textContent = licenseKey || '-';
        licenseEl.classList.add('text-break');
      }
      const mailEl = dom.one('#sa_meta_mail');
      if (mailEl) {
        mailEl.textContent = mail || '-';
        mailEl.classList.add('text-break');
      }
      if (licenseRow) {
        const hasLicenseInfo = Boolean(licenseKey || mail);
        dom.toggle(licenseRow, hasLicenseInfo);
      }
      dom.toggle(dom.one('#sa_stock_meta'), true);
    }

    function parseStockOption(option) {
      if (!option) return null;
      if (!option.dataset.meta) {
        return {
          donanim_tipi: option.dataset.tip || '',
          ifs_no: option.dataset.ifs || '',
          mevcut_miktar: Number(option.dataset.qty || 0),
        };
      }
      try {
        return JSON.parse(decodeURIComponent(option.dataset.meta));
      } catch (err) {
        console.warn('meta parse failed', err);
        return {
          donanim_tipi: option.dataset.tip || '',
          ifs_no: option.dataset.ifs || '',
          mevcut_miktar: Number(option.dataset.qty || 0),
        };
      }
    }

    function handleStockChange(event) {
      const select = event.currentTarget;
      const option = select.selectedOptions[0];
      if (!option || !option.value) {
        resetStockMetaDisplay();
        updateAutoFields();
        return;
      }
      const meta = parseStockOption(option);
      renderStockMeta(meta, option);
      updateAutoFields();

      const miktar = dom.one('#sa_miktar');
      if (miktar) {
        const max = Number(option.dataset.qty || 1);
        miktar.max = String(max);
        if (Number(miktar.value) > max) {
          miktar.value = String(max);
        }
      }
    }

    function applyFieldRules() {
      const active = dom.one('#sa_tabs .nav-link.active');
      const isLicense = active?.dataset.bsTarget?.includes('lisans');
      const isInventory = active?.dataset.bsTarget?.includes('envanter');
      const isPrinter = active?.dataset.bsTarget?.includes('yazici');
      dom.require(dom.one('#sa_license_name'), Boolean(isLicense));
      dom.require(dom.one('#sa_inv_no'), Boolean(isInventory));
      dom.require(dom.one('#sa_prn_no'), Boolean(isPrinter));
    }

    function bindTabChange() {
      dom.all('#sa_tabs .nav-link').forEach((btn) => {
        btn.addEventListener('shown.bs.tab', applyFieldRules);
      });
    }

    function getAssignmentType() {
      const active = dom.one('#sa_tabs .nav-link.active');
      if (active?.dataset.bsTarget?.includes('envanter')) return 'envanter';
      if (active?.dataset.bsTarget?.includes('yazici')) return 'yazici';
      return 'lisans';
    }

    function valueOf(selector) {
      return (dom.one(selector)?.value || '').trim();
    }

    function valueOrNull(selector) {
      const value = valueOf(selector);
      return value ? value : null;
    }

    function buildLicenseForm() {
      const name = valueOf('#sa_license_name');
      if (!name) {
        throw new Error('Lisans adı giriniz.');
      }
      return {
        lisans_adi: name,
        lisans_anahtari: valueOrNull('#sa_license_key'),
        sorumlu_personel: valueOrNull('#sa_license_person'),
        bagli_envanter_no: valueOrNull('#sa_license_inventory'),
        mail_adresi: valueOrNull('#sa_license_mail'),
        ifs_no: valueOrNull('#sa_license_ifs'),
      };
    }

    function buildInventoryForm() {
      const invNo = valueOf('#sa_inv_no');
      if (!invNo) {
        throw new Error('Envanter numarası giriniz.');
      }
      return {
        envanter_no: invNo,
        bilgisayar_adi: valueOrNull('#sa_inv_pc'),
        fabrika: valueOrNull('#sa_inv_factory'),
        departman: valueOrNull('#sa_inv_department'),
        sorumlu_personel: valueOrNull('#sa_inv_person'),
        kullanim_alani: valueOrNull('#sa_inv_usage'),
        seri_no: valueOrNull('#sa_inv_serial'),
        bagli_envanter_no: valueOrNull('#sa_inv_machine'),
        notlar: valueOrNull('#sa_inv_note'),
        ifs_no: valueOrNull('#sa_inv_ifs'),
        marka: valueOrNull('#sa_inv_brand'),
        model: valueOrNull('#sa_inv_model'),
        donanim_tipi: valueOrNull('#sa_inv_hardware'),
      };
    }

    function buildPrinterForm() {
      const printerNo = valueOf('#sa_prn_no');
      if (!printerNo) {
        throw new Error('Yazıcı envanter numarası giriniz.');
      }
      return {
        envanter_no: printerNo,
        marka: valueOrNull('#sa_prn_brand'),
        model: valueOrNull('#sa_prn_model'),
        kullanim_alani: valueOrNull('#sa_prn_usage'),
        ip_adresi: valueOrNull('#sa_prn_ip'),
        mac: valueOrNull('#sa_prn_mac'),
        hostname: valueOrNull('#sa_prn_host'),
        ifs_no: valueOrNull('#sa_prn_ifs'),
        notlar: valueOrNull('#sa_prn_note'),
      };
    }

    function buildAssignmentPayload() {
      const stockValue = valueOf('#sa_stock');
      if (!stockValue) {
        throw new Error('Lütfen stok seçiniz.');
      }
      const type = getAssignmentType();
      const payload = {
        stock_id: stockValue,
        atama_turu: type,
        miktar: Number(valueOf('#sa_miktar') || '1') || 1,
        notlar: valueOrNull('#sa_not'),
      };

      if (type === 'lisans') {
        payload.license_form = buildLicenseForm();
      } else if (type === 'envanter') {
        payload.envanter_form = buildInventoryForm();
      } else {
        payload.printer_form = buildPrinterForm();
      }

      return payload;
    }

    async function submitAssignment(event) {
      event.preventDefault();
      let payload;
      try {
        payload = buildAssignmentPayload();
      } catch (err) {
        showBanner(err.message || 'Atama başarısız.', 'warning');
        return;
      }

      try {
        const result = await http.postJson(URLS.stockAssign, payload);
        if (result?.ok === false) {
          showBanner(result?.message || result?.detail || 'Atama başarısız.', 'danger');
          return;
        }
        showBanner(result?.message || 'Atama tamamlandı.', 'success');
        dom.one('#stokAtamaModal .btn-close')?.click();
        await loadStocks();
        await refreshStockStatus();
      } catch (err) {
        showBanner(err.message || 'Atama gönderilemedi.', 'danger');
        console.error('stock assign failed', err);
      }
    }

    function saSetFieldValue(input, value) {
      if (!input) return;
      if (input.tagName === 'SELECT') {
        const stringValue = value !== undefined && value !== null ? String(value) : '';
        if (!stringValue) {
          Array.from(input.querySelectorAll('option[data-auto-option="1"]')).forEach((opt) => opt.remove());
          input.value = '';
          return;
        }
        let option = Array.from(input.options).find((opt) => opt.value === stringValue);
        if (!option) {
          option = document.createElement('option');
          option.value = stringValue;
          option.textContent = stringValue;
          option.dataset.autoOption = '1';
          input.appendChild(option);
        }
        input.value = stringValue;
      } else if (input.tagName === 'TEXTAREA') {
        input.value = value ?? '';
      } else if (input.type === 'checkbox' || input.type === 'radio') {
        input.checked = Boolean(value);
      } else {
        input.value = value ?? '';
      }
    }

    function applyAutoData(data, options = {}) {
      const { source = null, clearMissing = false, onlySource = false, skipHide = false } = options;
      dom.all('[data-auto-key]').forEach((input) => {
        const keyAttr = input.dataset.autoKey || '';
        const keys = keyAttr
          .split(/[|,]/)
          .map((k) => k.trim())
          .filter(Boolean);
        const sources = (input.dataset.autoSource || '')
          .split(',')
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
        const hasValue = value !== undefined && value !== null && value !== '';
        if (hasValue) {
          saSetFieldValue(input, value);
        } else if (clearMissing) {
          saSetFieldValue(input, '');
        }
        if (!skipHide) {
          const container = input.closest('[data-auto-field]');
          if (container) {
            container.classList.toggle('d-none', hasValue);
          }
        }
      });
    }

    function autoSelectTab(meta) {
      const type = (meta?.source_type || '').toLowerCase();
      let target = '#sa_tab_envanter';
      if (type === 'lisans' || meta?.lisans_anahtari) {
        target = '#sa_tab_lisans';
      } else if (type === 'yazici') {
        target = '#sa_tab_yazici';
      }
      const button = document.querySelector(`#sa_tabs [data-bs-target="${target}"]`);
      if (button && !button.classList.contains('active')) {
        try {
          bootstrap.Tab.getOrCreateInstance(button).show();
        } catch (err) {
          console.warn('tab switch failed', err);
        }
      }
    }

    function resetSourceSpecificFields() {
      ['envanter', 'lisans', 'yazici'].forEach((type) => {
        applyAutoData({}, { source: type, clearMissing: true, onlySource: true });
      });
    }

    async function fetchSourceDetail(sourceType, sourceId) {
      const cacheKey = `${sourceType}:${sourceId}`;
      if (state.sourceCache.has(cacheKey)) {
        return state.sourceCache.get(cacheKey);
      }
      const params = new URLSearchParams({ type: sourceType, id: String(sourceId) });
      const data = await http.getJson(`${URLS.assignSourceDetail}?${params.toString()}`);
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
            applyAutoData(detail.data, { source: detail.type, clearMissing: true });
          }
        })
        .catch((err) => {
          if (requestId !== state.sourceRequestId) return;
          console.error('source detail load failed', err);
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
        state.preselectStockId = [item.donanim_tipi, item.marka || '', item.model || '', item.ifs_no || ''].join('|');
        const modalEl = document.getElementById('stokAtamaModal');
        if (modalEl) {
          const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
          modal.show();
        }
      } catch (err) {
        console.error('assign decode failed', err);
      }
    }

    async function scrapFromStatus(encoded) {
      let item;
      try {
        item = JSON.parse(decodeURIComponent(encoded));
      } catch (err) {
        console.error('scrap decode failed', err);
        alert('Geçersiz kayıt');
        return;
      }
      const qtyStr = window.prompt('Miktar', '1');
      if (qtyStr === null) return;
      const qty = Number(qtyStr);
      if (!qty || qty <= 0) {
        alert('Geçersiz miktar');
        return;
      }
      if (!window.confirm(`${qty} adet hurdaya ayrılacak. Onaylıyor musunuz?`)) return;
      const payload = {
        donanim_tipi: item.donanim_tipi,
        marka: item.marka,
        model: item.model,
        ifs_no: item.ifs_no,
        miktar: qty,
        islem: 'hurda',
        islem_yapan: 'UI',
      };
      try {
        const result = await http.postJson('/stock/add', payload);
        if (result?.ok) {
          await refreshStockStatus();
          await loadStocks();
        } else {
          alert(result?.error || 'İşlem başarısız');
        }
      } catch (err) {
        console.error('scrap failed', err);
        alert(err.message || 'İşlem başarısız');
      }
    }

    function setStockStatusMessage(tbody, message) {
      if (!tbody) return;
      tbody.innerHTML = `<tr data-empty-row="1"><td colspan="7" class="text-center text-muted">${message}</td></tr>`;
    }

    function createStockStatusRow(item) {
      const encoded = encodeURIComponent(JSON.stringify(item));
      const hasDetail = Boolean(item?.source_type || item?.source_id);
      const detailButton = hasDetail
        ? `<button type="button" class="btn btn-sm btn-outline-secondary" data-stock-detail="${encoded}" title="Detay"><span aria-hidden="true">&#9776;</span><span class="visually-hidden">Detay</span></button>`
        : '';
      const actionsMenu = `
    <div class="btn-group">
      <button class="btn btn-sm btn-outline-primary dropdown-toggle" type="button" data-bs-toggle="dropdown" aria-expanded="false">
        İşlemler
      </button>
      <ul class="dropdown-menu dropdown-menu-end">
        <li><button class="dropdown-item" type="button" onclick="assignFromStatus('${encoded}')">Atama</button></li>
        <li><button class="dropdown-item text-danger" type="button" onclick="scrapFromStatus('${encoded}')">Hurda</button></li>
      </ul>
    </div>`;
      const lastOp = item.son_islem_ts
        ? new Date(item.son_islem_ts).toLocaleString('tr-TR', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            hour12: false,
          })
        : '-';
      return `<tr>
    <td>${item.donanim_tipi || '-'}</td>
    <td>${item.marka || '-'}</td>
    <td>${item.model || '-'}</td>
    <td>${item.ifs_no || '-'}</td>
    <td class="text-end">${item.net_miktar}</td>
    <td>${lastOp}</td>
    <td class="text-center">
      <div class="d-inline-flex align-items-center gap-1">
        ${detailButton}
        ${actionsMenu}
      </div>
    </td>
  </tr>`;
    }

    function renderStockStatusTable(tbody, items) {
      if (!tbody) return;
      if (!Array.isArray(items) || items.length === 0) {
        setStockStatusMessage(tbody, 'Stok bulunamadı');
        return;
      }
      tbody.innerHTML = items.map(createStockStatusRow).join('');
    }

    function filterStockTable() {
      const query = (dom.one('#stockSearch')?.value || '').toLowerCase();
      const activePane = document.querySelector('#stockStatusTabContent .tab-pane.active');
      if (!activePane) return;
      activePane.querySelectorAll('tbody tr').forEach((tr) => {
        if (tr.dataset.emptyRow === '1') {
          tr.style.display = '';
          return;
        }
        tr.style.display = tr.textContent.toLowerCase().includes(query) ? '' : 'none';
      });
    }

    async function refreshStockStatus() {
      const inventoryTbody = document.querySelector('#tblStockStatusInventory tbody');
      const printerTbody = document.querySelector('#tblStockStatusPrinters tbody');
      const licenseTbody = document.querySelector('#tblStockStatusLicense tbody');
      setStockStatusMessage(inventoryTbody, 'Yükleniyor…');
      setStockStatusMessage(printerTbody, 'Yükleniyor…');
      setStockStatusMessage(licenseTbody, 'Yükleniyor…');
      try {
        const data = await http.requestJson(STOCK_STATUS_URL, { credentials: 'same-origin' });
        const items = Array.isArray(data) ? data : data.items || data.rows || [];
        if (!Array.isArray(items)) {
          setStockStatusMessage(inventoryTbody, 'Veri alınamadı');
          setStockStatusMessage(printerTbody, 'Veri alınamadı');
          setStockStatusMessage(licenseTbody, 'Veri alınamadı');
          return;
        }
        const inventoryItems = [];
        const printerItems = [];
        const licenseItems = [];
        items.forEach((item) => {
          const typeRaw = item?.source_type;
          const type = typeof typeRaw === 'string' ? typeRaw.toLowerCase() : '';
          if (type === 'lisans' || type === 'license' || type === 'yazilim' || type === 'software') {
            licenseItems.push(item);
          } else if (type === 'yazici' || type === 'printer') {
            printerItems.push(item);
          } else {
            inventoryItems.push(item);
          }
        });
        renderStockStatusTable(inventoryTbody, inventoryItems);
        renderStockStatusTable(printerTbody, printerItems);
        renderStockStatusTable(licenseTbody, licenseItems);
        filterStockTable();
      } catch (err) {
        console.error('stock status load failed', err);
        setStockStatusMessage(document.querySelector('#tblStockStatusInventory tbody'), 'Veri alınamadı');
        setStockStatusMessage(document.querySelector('#tblStockStatusPrinters tbody'), 'Veri alınamadı');
        setStockStatusMessage(document.querySelector('#tblStockStatusLicense tbody'), 'Veri alınamadı');
      }
    }

    const STOCK_DETAIL_SOURCE_LABELS = {
      envanter: 'Envanter',
      lisans: 'Lisans',
      yazici: 'Yazıcı',
    };

    function formatStockDetailValue(value) {
      return value === undefined || value === null || value === '' ? '-' : `${value}`;
    }

    function formatStockDetailDate(value) {
      if (!value) return '-';
      const date = new Date(value);
      if (Number.isNaN(date.getTime())) return '-';
      return date.toLocaleString('tr-TR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        hour12: false,
      });
    }

    function stockDetailUrl(item) {
      if (!item || !item.source_id) return '';
      if (item.source_type === 'envanter') return `/inventory/${item.source_id}`;
      if (item.source_type === 'lisans') return `/lisans/${item.source_id}`;
      if (item.source_type === 'yazici') return `/printers/${item.source_id}`;
      return '';
    }

    function getStockDetailRows(item) {
      const rows = [
        ['Donanım Tipi', formatStockDetailValue(item?.donanim_tipi)],
        ['Marka', formatStockDetailValue(item?.marka)],
        ['Model', formatStockDetailValue(item?.model)],
        ['IFS No', formatStockDetailValue(item?.ifs_no)],
        ['Stok', formatStockDetailValue(item?.net_miktar)],
        ['Son İşlem', formatStockDetailDate(item?.son_islem_ts)],
      ];

      if (item?.source_type || item?.source_id) {
        const label = item?.source_type ? STOCK_DETAIL_SOURCE_LABELS[item.source_type] || item.source_type : '';
        let value = label;
        if (item?.source_id) {
          value = value ? `${value} (#${item.source_id})` : `#${item.source_id}`;
        }
        if (value) {
          rows.push(['Kaynak', value]);
        }
      }

      return rows;
    }

    function openStockDetailModal(item) {
      const rows = getStockDetailRows(item);
      const modalEl = document.getElementById('stokDetailModal');
      const listEl = modalEl?.querySelector('#stokDetailList');
      const linkWrap = modalEl?.querySelector('#stokDetailLinkWrap');
      const linkEl = modalEl?.querySelector('#stokDetailLink');

      if (!modalEl || !listEl) {
        alert(rows.map(([label, value]) => `${label}: ${value}`).join('\n'));
        return;
      }

      listEl.innerHTML = '';
      rows.forEach(([label, value]) => {
        const dt = document.createElement('dt');
        dt.className = 'col-5 fw-semibold';
        dt.textContent = label;
        const dd = document.createElement('dd');
        dd.className = 'col-7 text-break';
        dd.textContent = value;
        listEl.appendChild(dt);
        listEl.appendChild(dd);
      });

      if (linkWrap && linkEl) {
        const url = stockDetailUrl(item);
        if (url) {
          linkEl.href = url;
          linkWrap.classList.remove('d-none');
        } else {
          linkEl.removeAttribute('href');
          linkWrap.classList.add('d-none');
        }
      }

      try {
        const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
        modal.show();
      } catch (err) {
        console.error('stock detail modal failed', err);
        alert(rows.map(([label, value]) => `${label}: ${value}`).join('\n'));
      }
    }

    function handleDetailClick(event) {
      const btn = event.target.closest('[data-stock-detail]');
      if (!btn) return;
      const encoded = btn.getAttribute('data-stock-detail');
      if (!encoded) return;
      event.preventDefault();
      try {
        const item = JSON.parse(decodeURIComponent(encoded));
        openStockDetailModal(item);
      } catch (err) {
        console.error('stock detail decode failed', err);
      }
    }

    function init() {
      console.log('[StokAtama] boot start');
      resetStockMetaDisplay();
      document.addEventListener('click', handleDetailClick);
      dom.one('#stockSearch')?.addEventListener('input', filterStockTable);
      document.querySelectorAll('#stockStatusTabs [data-bs-toggle="tab"]').forEach((btn) => {
        btn.addEventListener('shown.bs.tab', filterStockTable);
      });
      const statusTab = document.getElementById('tab-status');
      statusTab?.addEventListener('shown.bs.tab', refreshStockStatus);

      const stockSelect = dom.one('#sa_stock');
      stockSelect?.addEventListener('change', handleStockChange);
      dom.one('#sa_submit')?.addEventListener('click', submitAssignment);
      bindTabChange();
      applyFieldRules();

      console.log('[StokAtama] DOMContentLoaded');
      loadStocks();
      loadSources();

      document.addEventListener('shown.bs.modal', async (event) => {
        if (event.target.id !== 'stokAtamaModal') return;
        await loadStocks();
        await loadSources();
        applyFieldRules();
      });
    }

    return {
      init,
      assignFromStatus,
      scrapFromStatus,
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
      console.warn('tab activation failed', selector, err);
    }
  }

  function applyInitialTabSelection() {
    if (typeof window === 'undefined') return;
    const params = new URLSearchParams(window.location.search || '');
    const tabParam = (params.get('tab') || '').toLowerCase();
    const moduleParam = (params.get('module') || '').toLowerCase();

    if (tabParam === 'status') {
      showBootstrapTab('#tab-status');
    } else if (tabParam === 'log') {
      showBootstrapTab('#tab-log');
    }

    if (!moduleParam) return;

    showBootstrapTab('#tab-status');

    if (moduleParam === 'inventory' || moduleParam === 'envanter') {
      showBootstrapTab('#status-tab-inventory');
    } else if (moduleParam === 'printer' || moduleParam === 'yazici') {
      showBootstrapTab('#status-tab-printer');
    } else if (
      moduleParam === 'license'
      || moduleParam === 'lisans'
      || moduleParam === 'software'
      || moduleParam === 'yazilim'
    ) {
      showBootstrapTab('#status-tab-license');
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    StockAddForm.init();
    StockAssign.init();
    applyInitialTabSelection();
    StockAssign.refreshStockStatus();
  });

  window.assignFromStatus = (encoded) => StockAssign.assignFromStatus(encoded);
  window.scrapFromStatus = (encoded) => StockAssign.scrapFromStatus(encoded);
  window.loadStockStatus = () => StockAssign.refreshStockStatus();
})();
