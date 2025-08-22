// static/js/refdata.js

// Basit fetch yardımcıları
async function apiGet(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

async function apiPost(url, body) {
  const r = await fetch(url, {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify(body)
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

// /api/ref/{entity} —> kendi tablosuna yaz
async function addRef(entity, name, brandId = null) {
  const payload = { name: (name || '').trim() };
  if (!payload.name) throw new Error('İsim boş olamaz.');
  if (entity === 'model') {
    if (!brandId) throw new Error('Model eklemek için marka seçin.');
    payload.brand_id = parseInt(brandId, 10);
  }
  return apiPost(`/api/ref/${entity}`, payload);
}

// /api/lookup/{entity} —> tablodan oku
async function fetchList(entity, extraParams = {}) {
  const usp = new URLSearchParams(extraParams);
  return apiGet(`/api/lookup/${entity}?${usp.toString()}`);
}

// Liste render
function renderList(containerEl, rows) {
  containerEl.innerHTML =
    (rows && rows.length)
      ? rows.map(r =>
          `<li class="list-group-item d-flex justify-content-between align-items-center">
             <span>${r.name ?? r.ad ?? ''}</span>
           </li>`
        ).join('')
      : `<li class="list-group-item text-muted">Kayıt yok</li>`;
}

// Marka select'ini doldur (model kartı için)
async function fillBrandSelect(selectEl) {
  const rows = await fetchList('marka');
  const opts = [`<option value="">Marka seçiniz…</option>`]
    .concat(rows.map(r => `<option value="${r.id}">${r.name ?? r.ad}</option>`));
  selectEl.innerHTML = opts.join('');

  // Choices.js ile aramalı hale getir
  if (window.Choices) {
    if (!selectEl._choicesInstance) {
      selectEl._choicesInstance = new Choices(selectEl, {
        searchEnabled: true,
        placeholder: true,
        placeholderValue: 'Marka seçiniz…',
        shouldSort: true,
        itemSelectText: '',
        noResultsText: 'Sonuç yok',
        noChoicesText: 'Seçenek yok',
        allowHTML: false
      });
    } else {
      const inst = selectEl._choicesInstance;
      inst.clearStore();
      inst.setChoices(
        rows.map(r => ({value: r.id, label: r.name ?? r.ad})),
        'value','label', true
      );
    }
  }
}

async function refreshCard(card) {
  const entity = card.dataset.entity;
  const listEl  = card.querySelector('.ref-list');

  if (entity === 'model') {
    const brandSel = card.querySelector('.ref-brand');
    const brandId  = brandSel && brandSel.value ? brandSel.value : '';
    const rows = await fetchList('model', brandId ? { marka_id: brandId } : {});
    renderList(listEl, rows);
    return;
  }

  const rows = await fetchList(entity);
  renderList(listEl, rows);
}

function bindCard(card) {
  const entity = card.dataset.entity;
  const input  = card.querySelector('.ref-input');
  const addBtn = card.querySelector('.ref-add');
  const listEl = card.querySelector('.ref-list');

  if (!input || !addBtn || !listEl) return;

  // Model kartı: önce Marka select’ini doldur ve değişimde listeyi yenile
  if (entity === 'model') {
    const brandSel = card.querySelector('.ref-brand');
    if (brandSel) {
      fillBrandSelect(brandSel).then(() => refreshCard(card)).catch(console.error);
      brandSel.addEventListener('change', () => refreshCard(card));
    }
  }

  // Ekle
  addBtn.addEventListener('click', async () => {
    const name = (input.value || '').trim();
    if (!name) { input.focus(); return; }

    try {
      if (entity === 'model') {
        const brandSel = card.querySelector('.ref-brand');
        const brandId  = brandSel && brandSel.value ? parseInt(brandSel.value, 10) : null;
        if (!brandId) { alert('Lütfen önce marka seçin.'); return; }
        await addRef('model', name, brandId);
      } else {
        await addRef(entity, name);
      }
      input.value = '';
      await refreshCard(card);
    } catch (e) {
      alert('Kaydedilemedi: ' + (e?.message || e));
    }
  });

  // Enter ile ekleme
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') addBtn.click();
  });
}

// Sayfa giriş noktası
function initRefAdmin() {
  document.querySelectorAll('.ref-card[data-entity]').forEach(card => {
    bindCard(card);
    refreshCard(card).catch(console.error);
  });
}

window.initRefAdmin = initRefAdmin;
