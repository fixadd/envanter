(function () {
  const API = {
    async list(entity) {
      const params = new URLSearchParams({ entity, status: 'arızalı' });
      const res = await fetch(`/faults/list?${params.toString()}`, { credentials: 'same-origin' });
      if (!res.ok) throw new Error('Arızalı kayıtlar alınamadı');
      return res.json();
    },
    async get(entity, entityId, entityKey) {
      const params = new URLSearchParams({ entity });
      if (entityId != null) params.append('entity_id', String(entityId));
      if (entityKey) params.append('entity_key', entityKey);
      const res = await fetch(`/faults/entity?${params.toString()}`, { credentials: 'same-origin' });
      if (!res.ok) throw new Error('Arıza kaydı alınamadı');
      return res.json();
    },
    async mark(formData) {
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
        const title = item.device_no || item.title || '-';
        const reason = item.reason || '-';
        const destination = item.destination || '';
        const created = formatDate(item.created_at);
        return `
          <div class="fault-summary-item">
            <h6 class="mb-1">${title}</h6>
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
    const containerState = state.get(entity);
    if (!containerState) return;
    try {
      const data = await API.list(entity);
      renderSummary(containerState, data.items || []);
    } catch (err) {
      if (containerState.countEl) containerState.countEl.textContent = '!';
      if (containerState.listEl) {
        containerState.listEl.innerHTML = `<div class="text-danger small">${err.message}</div>`;
      }
    }
  }

  async function openSummary(entity) {
    const containerState = state.get(entity);
    if (!containerState) return;
    await refresh(entity);
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
    const containerState = state.get(entity);
    if (!containerState) return;
    const { markModal, markForm, inputs } = containerState;
    if (!markModal || !markForm || !inputs) return;
    const { entityId = null, entityKey = '', deviceNo = '', title = '', meta = null } = options || {};
    inputs.entityId.value = entityId != null ? entityId : '';
    inputs.entityKey.value = entityKey || '';
    inputs.device.value = deviceNo || '';
    inputs.title.value = title || '';
    inputs.meta.value = meta ? JSON.stringify(meta) : '';
    await populateExistingFault(entity, entityId, entityKey, inputs);
    ensureBootstrapModal(markModal).show();
  }

  async function openRepairModal(entity, options) {
    const containerState = state.get(entity);
    if (!containerState) return;
    const { repairModal, repairForm, repairInputs } = containerState;
    if (!repairModal || !repairForm || !repairInputs) return;
    const { entityId = null, entityKey = '', deviceNo = '' } = options || {};
    try {
      const data = await API.get(entity, entityId, entityKey);
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
    const entity = container.dataset.faultEntity;
    if (!entity) return;
    const prefix = container.dataset.faultPrefix || entity;
    const summaryModal = document.getElementById(`${prefix}FaultSummaryModal`);
    const markModal = document.getElementById(`${prefix}FaultMarkModal`);
    const repairModal = document.getElementById(`${prefix}FaultRepairModal`);
    const markForm = markModal?.querySelector('[data-fault-mark-form]') || null;
    const repairForm = repairModal?.querySelector('[data-fault-repair-form]') || null;
    const countEl = container.querySelector('[data-fault-count]');
    const listEl = summaryModal?.querySelector('[data-fault-list]') || null;

    const containerState = {
      entity,
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
    };
    state.set(entity, containerState);

    const trigger = container.querySelector('[data-fault-summary-trigger]');
    if (trigger) {
      trigger.addEventListener('click', () => openSummary(entity));
    }

    if (markForm) {
      markForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        try {
          await API.mark(new FormData(markForm));
          ensureBootstrapModal(markModal).hide();
          await refresh(entity);
          if (entity === 'stock' && typeof window.loadStockStatus === 'function') {
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
          await refresh(entity);
          if (entity === 'stock' && typeof window.loadStockStatus === 'function') {
            window.loadStockStatus();
          }
        } catch (err) {
          alert(err.message || 'İşlem tamamlanamadı');
        }
      });
    }

    refresh(entity);
  }

  function initAll() {
    document.querySelectorAll('[data-fault-entity]').forEach(initContainer);
  }

  window.Faults = {
    initAll,
    openMarkModal,
    openRepairModal,
    refresh: refresh,
  };

  document.addEventListener('DOMContentLoaded', () => {
    initAll();
  });
})();
