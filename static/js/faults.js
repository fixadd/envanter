(function () {
  const ENTITY_ALIASES = {
    inventory: 'inventory',
    envanter: 'inventory',
    inventories: 'inventory',
    license: 'license',
    licenses: 'license',
    lisans: 'license',
    yazilim: 'license',
    software: 'license',
    printer: 'printer',
    printers: 'printer',
    yazici: 'printer',
    stok: 'stock',
    stock: 'stock',
  };

  function normaliseEntityName(value) {
    if (value == null) return '';
    const key = String(value).trim().toLowerCase();
    return ENTITY_ALIASES[key] || key;
  }

  const API = {
    async list(entity) {
      const entityName = normaliseEntityName(entity);
      if (!entityName) throw new Error('Modül bilgisi eksik');
      const params = new URLSearchParams({ entity: entityName, status: 'arızalı' });
      const res = await fetch(`/faults/list?${params.toString()}`, { credentials: 'same-origin' });
      if (!res.ok) throw new Error('Arızalı kayıtlar alınamadı');
      return res.json();
    },
    async get(entity, entityId, entityKey) {
      const entityName = normaliseEntityName(entity);
      if (!entityName) throw new Error('Modül bilgisi eksik');
      const params = new URLSearchParams({ entity: entityName });
      if (entityId != null) params.append('entity_id', String(entityId));
      if (entityKey) params.append('entity_key', entityKey);
      const res = await fetch(`/faults/entity?${params.toString()}`, { credentials: 'same-origin' });
      if (!res.ok) throw new Error('Arıza kaydı alınamadı');
      return res.json();
    },
    async mark(formData) {
      const entityField = formData.get('entity');
      if (entityField) {
        formData.set('entity', normaliseEntityName(entityField));
      }
      const res = await fetch('/faults/mark', {
        method: 'POST',
        body: formData,
        credentials: 'same-origin',
      });
      if (!res.ok) {
        const msg = await res.text();
        throw new Error(msg || 'Arıza kaydedilemedi');
      }
      return res.json();
    },
    async repair(formData) {
      const entityField = formData.get('entity');
      if (entityField) {
        formData.set('entity', normaliseEntityName(entityField));
      }
      const res = await fetch('/faults/repair', {
        method: 'POST',
        body: formData,
        credentials: 'same-origin',
      });
      if (!res.ok) {
        const msg = await res.text();
        throw new Error(msg || 'İşlem başarısız');
      }
      return res.json();
    },
  };

  const state = new Map();

  function formatDate(value) {
    if (!value) return '';
    try {
      const dt = new Date(value);
      if (Number.isNaN(dt.getTime())) return '';
      return dt.toLocaleString('tr-TR', { hour12: false });
    } catch (err) {
      return '';
    }
  }

  function ensureBootstrapModal(el) {
    return bootstrap.Modal.getOrCreateInstance(el);
  }

  function renderSummary(containerState, items) {
    const { countEl, listEl } = containerState;
    if (countEl) countEl.textContent = String(items.length);
    if (!listEl) return;
    if (!items.length) {
      listEl.innerHTML = '<div class="text-muted small">Kayıt bulunamadı.</div>';
      return;
    }
    const content = items
      .map((item) => {
        const title = item.title || item.device_no || item.entity_key || '-';
        const reason = item.reason || '-';
        const destination = item.destination || '';
        const created = formatDate(item.created_at);
        const meta = item.meta && typeof item.meta === 'object' ? item.meta : null;

        const detailParts = [];
        const addDetail = (label, value) => {
          if (!value) return;
          const text = `${label}: ${value}`;
          if (!detailParts.includes(text)) detailParts.push(text);
        };

        if (item.entity_key && item.entity_key !== title) {
          addDetail('Kayıt', item.entity_key);
        }
        if (item.device_no && item.device_no !== title) {
          addDetail('Cihaz No', item.device_no);
        }
        if (meta && typeof meta === 'object') {
          const lineValue = meta.line || meta.row || meta.satir || meta.line_no;
          const deviceName =
            meta.device_name || meta.deviceName || meta.device_label || meta.device || meta.cihaz_adi;
          if (lineValue) addDetail('Satır', lineValue);
          if (deviceName && deviceName !== item.device_no) {
            addDetail('Cihaz', deviceName);
          }
        }

        const details = detailParts.length
          ? `<div class="small text-muted">${detailParts.join(' • ')}</div>`
          : '';

        return `
          <div class="fault-summary-item">
            <h6 class="mb-1">${title}</h6>
            ${details}
            <div class="small">${reason}</div>
            ${destination ? `<div class="small text-muted">Gönderildiği: ${destination}</div>` : ''}
            ${created ? `<div class="text-muted small">${created}</div>` : ''}
          </div>
        `;
      })
      .join('');
    listEl.innerHTML = content;
  }

  async function refresh(entity) {
    const entityName = normaliseEntityName(entity);
    if (!entityName) return;
    const containerState = state.get(entityName);
    if (!containerState) return;
    try {
      const data = await API.list(containerState.entityParam || entityName);
      const items = Array.isArray(data?.items) ? data.items : [];
      containerState.items = items;
      renderSummary(containerState, items);
      if (entityName === 'stock' && typeof window.onStockFaultsUpdated === 'function') {
        try {
          window.onStockFaultsUpdated();
        } catch (callbackErr) {
          console.warn('stock fault sync failed', callbackErr);
        }
      }
    } catch (err) {
      containerState.items = [];
      if (containerState.countEl) containerState.countEl.textContent = '!';
      if (containerState.listEl) {
        containerState.listEl.innerHTML = `<div class="text-danger small">${err.message}</div>`;
      }
    }
  }

  async function openSummary(entity) {
    const entityName = normaliseEntityName(entity);
    if (!entityName) return;
    const containerState = state.get(entityName);
    if (!containerState) return;
    await refresh(containerState.entityParam || entityName);
    if (containerState.summaryModal) {
      ensureBootstrapModal(containerState.summaryModal).show();
    }
  }

  async function populateExistingFault(entity, entityId, entityKey, inputs) {
    try {
      const data = await API.get(entity, entityId, entityKey);
      const fault = data?.fault;
      if (!fault) {
        inputs.reason.value = '';
        inputs.destination.value = '';
        return;
      }
      if (inputs.reason) inputs.reason.value = fault.reason || '';
      if (inputs.destination) inputs.destination.value = fault.destination || '';
    } catch (err) {
      console.warn('fault fetch failed', err);
    }
  }

  async function openMarkModal(entity, options) {
    const entityName = normaliseEntityName(entity);
    if (!entityName) return;
    const containerState = state.get(entityName);
    if (!containerState) return;
    const { markModal, markForm, inputs } = containerState;
    if (!markModal || !markForm || !inputs) return;
    const { entityId = null, entityKey = '', deviceNo = '', title = '', meta = null } = options || {};
    inputs.entityId.value = entityId != null ? entityId : '';
    inputs.entityKey.value = entityKey || '';
    inputs.device.value = deviceNo || '';
    inputs.title.value = title || '';
    inputs.meta.value = meta ? JSON.stringify(meta) : '';
    await populateExistingFault(containerState.entityParam || entityName, entityId, entityKey, inputs);
    ensureBootstrapModal(markModal).show();
  }

  async function openRepairModal(entity, options) {
    const entityName = normaliseEntityName(entity);
    if (!entityName) return;
    const containerState = state.get(entityName);
    if (!containerState) return;
    const { repairModal, repairForm, repairInputs } = containerState;
    if (!repairModal || !repairForm || !repairInputs) return;
    const { entityId = null, entityKey = '', deviceNo = '' } = options || {};
    try {
      const data = await API.get(containerState.entityParam || entityName, entityId, entityKey);
      const fault = data?.fault;
      if (!fault) {
        alert('Aktif arıza kaydı bulunamadı.');
        return;
      }
      repairInputs.entityId.value = entityId != null ? entityId : '';
      repairInputs.entityKey.value = entityKey || '';
      repairInputs.note.value = '';
      if (repairInputs.device) repairInputs.device.textContent = fault.device_no || deviceNo || '-';
      if (repairInputs.reason) repairInputs.reason.textContent = fault.reason || '-';
      if (repairInputs.destination) repairInputs.destination.textContent = fault.destination || '-';
      ensureBootstrapModal(repairModal).show();
    } catch (err) {
      console.error(err);
      alert(err.message || 'Arıza bilgisi alınamadı');
    }
  }

  function findFaultRecord(entity, entityKey) {
    const entityName = normaliseEntityName(entity);
    if (!entityName) return null;
    const key = entityKey == null ? '' : String(entityKey).trim();
    if (!key) return null;
    const containerState = state.get(entityName);
    if (!containerState || !Array.isArray(containerState.items)) return null;
    const lookupKey = key.toLowerCase();
    return (
      containerState.items.find((item) => {
        const itemKey = item?.entity_key;
        return itemKey && String(itemKey).trim().toLowerCase() === lookupKey;
      }) || null
    );
  }

  function collectInputs(form) {
    return {
      entityId: form.querySelector('[data-fault-input="entity-id"]'),
      entityKey: form.querySelector('[data-fault-input="entity-key"]'),
      title: form.querySelector('[data-fault-input="title"]'),
      device: form.querySelector('[data-fault-input="device"]'),
      reason: form.querySelector('[data-fault-input="reason"]'),
      destination: form.querySelector('[data-fault-input="destination"]'),
      meta: form.querySelector('[data-fault-input="meta"]'),
    };
  }

  function collectRepairInputs(form) {
    return {
      entityId: form.querySelector('[data-fault-repair="entity-id"]'),
      entityKey: form.querySelector('[data-fault-repair="entity-key"]'),
      note: form.querySelector('textarea[name="note"]'),
      device: form.querySelector('[data-fault-info="device"]'),
      reason: form.querySelector('[data-fault-info="reason"]'),
      destination: form.querySelector('[data-fault-info="destination"]'),
    };
  }

  function initContainer(container) {
    const rawEntity = container.dataset.faultEntity;
    const entityName = normaliseEntityName(rawEntity);
    if (!entityName) return;
    const prefix = container.dataset.faultPrefix || entityName;
    const summaryModal = document.getElementById(`${prefix}FaultSummaryModal`);
    const markModal = document.getElementById(`${prefix}FaultMarkModal`);
    const repairModal = document.getElementById(`${prefix}FaultRepairModal`);
    const markForm = markModal?.querySelector('[data-fault-mark-form]') || null;
    const repairForm = repairModal?.querySelector('[data-fault-repair-form]') || null;
    const countEl = container.querySelector('[data-fault-count]');
    const listEl = summaryModal?.querySelector('[data-fault-list]') || null;

    const containerState = {
      entity: entityName,
      entityParam: entityName,
      prefix,
      container,
      summaryModal,
      markModal,
      repairModal,
      markForm,
      repairForm,
      inputs: markForm ? collectInputs(markForm) : null,
      repairInputs: repairForm ? collectRepairInputs(repairForm) : null,
      countEl,
      listEl,
      items: [],
    };
    state.set(entityName, containerState);

    const trigger = container.querySelector('[data-fault-summary-trigger]');
    if (trigger) {
      trigger.addEventListener('click', () => openSummary(entityName));
    }

    if (markForm) {
      markForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        try {
          await API.mark(new FormData(markForm));
          ensureBootstrapModal(markModal).hide();
          await refresh(entityName);
          if (entityName === 'stock' && typeof window.loadStockStatus === 'function') {
            window.loadStockStatus();
          }
        } catch (err) {
          alert(err.message || 'Arıza kaydı oluşturulamadı');
        }
      });
    }

    if (repairForm) {
      repairForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        try {
          await API.repair(new FormData(repairForm));
          ensureBootstrapModal(repairModal).hide();
          await refresh(entityName);
          if (entityName === 'stock' && typeof window.loadStockStatus === 'function') {
            window.loadStockStatus();
          }
        } catch (err) {
          alert(err.message || 'İşlem tamamlanamadı');
        }
      });
    }

    refresh(entityName);
  }

  function initAll() {
    document.querySelectorAll('[data-fault-entity]').forEach(initContainer);
  }

  window.Faults = {
    initAll,
    openMarkModal,
    openRepairModal,
    refresh: refresh,
    hasOpenFault(entity, entityKey) {
      return Boolean(findFaultRecord(entity, entityKey));
    },
    getOpenFault(entity, entityKey) {
      const record = findFaultRecord(entity, entityKey);
      return record ? { ...record } : null;
    },
  };

  document.addEventListener('DOMContentLoaded', () => {
    initAll();
  });
})();
