// Donanım tipi lookup doldur
fetch('/api/lookup/donanim_tipi')
  .then(r=>r.json())
  .then(d=>{
    const sel = document.getElementById('donanim_tipi');
    if(!sel) return;
    sel.innerHTML = '<option value="">Seçiniz</option>' + (d.items||[]).map(x=>`<option>${x.ad}</option>`).join('');
  });

// Ekle form submit
const chkIsLicense = document.getElementById('chkIsLicense');
const hardwareFields = document.getElementById('hardwareFields');
const licenseFields  = document.getElementById('licenseFields');
const miktarInput    = document.getElementById('miktar');
const donanimSel     = document.getElementById('donanim_tipi');
const rowMiktar      = document.getElementById('rowMiktar');

chkIsLicense?.addEventListener('change', e=>{
  const isLic = e.target.checked;
  hardwareFields?.classList.toggle('d-none', isLic);
  licenseFields?.classList.toggle('d-none', !isLic);
  donanimSel.required = !isLic;
  rowMiktar?.classList.toggle('d-none', isLic);
  hardwareFields?.querySelectorAll('input,select').forEach(el=> el.disabled = isLic);
  licenseFields?.querySelectorAll('input,select').forEach(el=> el.disabled = !isLic);
  if(isLic){
    miktarInput.value = 1;
    miktarInput.readOnly = true;
  }else{
    miktarInput.readOnly = false;
  }
});

document.getElementById('frmStockAdd')?.addEventListener('submit', async (e)=>{
  e.preventDefault();
  const fd = new FormData(e.target);
  if(chkIsLicense?.checked){
    fd.set('miktar','1');
    fd.set('donanim_tipi', fd.get('lisans_adi')||'');
    fd.set('is_license','1');
  }
  const payload = Object.fromEntries(fd.entries());
  const res = await fetch('/stock/add', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload) });
  const j = await res.json();
  if(j.ok){ location.reload(); } else { alert(j.error || 'Kayıt başarısız'); }
});

// --- Yeni stok atama modali -------------------------------------------------
document.addEventListener('shown.bs.modal', async (ev) => {
  if (ev.target.id !== 'stokAtamaModal') return;
  await sa_loadStocks();
  await sa_loadSources();
});

async function sa_loadStocks() {
  const sel = document.getElementById('sa_stock');
  if (!sel) return;
  sel.innerHTML = `<option value="">Seçiniz...</option>`;
  try {
    const res = await fetch('/stock/options');
    const data = await res.json();
    data.forEach(o => {
      const opt = document.createElement('option');
      opt.value = o.id;
      opt.textContent = o.label;
      opt.dataset.tip = o.donanim_tipi || '';
      opt.dataset.ifs = o.ifs_no || '';
      opt.dataset.qty = o.mevcut_miktar || 0;
      sel.appendChild(opt);
    });
  } catch (e) {
    console.error(e);
  }
}

async function sa_loadSources() {
  const fillSelect = (el, items, valueKey='id', labelKey='ad') => {
    el.innerHTML = `<option value="">Seçiniz...</option>`;
    items.forEach(x => {
      const opt = document.createElement('option');
      opt.value = x[valueKey];
      opt.textContent = x[labelKey] || x[valueKey];
      el.appendChild(opt);
    });
  };

  try {
    const [srcRes, licRes, prnRes] = await Promise.all([
      fetch('/inventory/assign/sources'),
      fetch('/api/licenses/list'),
      fetch('/api/printers/list'),
    ]);
    const src = await srcRes.json();
    const lic = await licRes.json();
    const prn = await prnRes.json();

    fillSelect(document.getElementById('sa_user'), src.users || [], 'id', 'text');
    fillSelect(document.getElementById('sa_user2'), src.users || [], 'id', 'text');
    fillSelect(document.getElementById('sa_lisans'), lic.items || [], 'id', 'lisans_adi');
    fillSelect(document.getElementById('sa_envanter'), src.inventories || [], 'id', 'envanter_no');
    fillSelect(document.getElementById('sa_envanter_for_lic'), src.inventories || [], 'id', 'envanter_no');
    fillSelect(document.getElementById('sa_yazici'), prn.items || [], 'id', 'model');
  } catch (e) {
    console.error(e);
  }
}

document.getElementById('sa_stock')?.addEventListener('change', (e) => {
  const opt = e.target.selectedOptions[0];
  const meta = document.getElementById('sa_stock_meta');
  if (!opt || !opt.value) {
    meta?.classList.add('d-none');
    return;
  }
  document.getElementById('sa_meta_tip').textContent = opt.dataset.tip || '-';
  document.getElementById('sa_meta_ifs').textContent = opt.dataset.ifs || '-';
  document.getElementById('sa_meta_qty').textContent = opt.dataset.qty || '0';
  meta?.classList.remove('d-none');

  const miktar = document.getElementById('sa_miktar');
  miktar.max = opt.dataset.qty || 1;
  if (Number(miktar.value) > Number(miktar.max)) miktar.value = miktar.max;
});

document.getElementById('sa_submit')?.addEventListener('click', async () => {
  const stockId = document.getElementById('sa_stock').value;
  if (!stockId) { alert('Lütfen stok seçiniz.'); return; }

  const activeTab = document.querySelector('#sa_tabs .nav-link.active');
  let atama_turu = 'lisans';
  if (activeTab && activeTab.dataset.bsTarget) {
    if (activeTab.dataset.bsTarget.includes('envanter')) atama_turu = 'envanter';
    else if (activeTab.dataset.bsTarget.includes('yazici')) atama_turu = 'yazici';
  }

  const payload = {
    stock_id: stockId,
    atama_turu,
    miktar: Number(document.getElementById('sa_miktar').value || 1),
    notlar: document.getElementById('sa_not').value || null,
    lisans_id: null,
    hedef_envanter_id: null,
    hedef_yazici_id: null,
    sorumlu_personel_id: null,
  };

  if (atama_turu === 'lisans') {
    payload.lisans_id = Number(document.getElementById('sa_lisans').value || 0) || null;
    payload.sorumlu_personel_id = document.getElementById('sa_user').value || null;
    const eforlic = Number(document.getElementById('sa_envanter_for_lic').value || 0);
    if (eforlic) payload.hedef_envanter_id = eforlic;
  }
  if (atama_turu === 'envanter') {
    payload.hedef_envanter_id = Number(document.getElementById('sa_envanter').value || 0) || null;
    payload.sorumlu_personel_id = document.getElementById('sa_user2').value || null;
  }
  if (atama_turu === 'yazici') {
    payload.hedef_yazici_id = Number(document.getElementById('sa_yazici').value || 0) || null;
  }

  try {
    const res = await fetch('/stock/assign', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload)
    });
    const out = await res.json();
    if (!res.ok) throw new Error(out?.detail || 'Hata');
    alert(out.message || 'Atama tamamlandı.');
    document.querySelector('#stokAtamaModal .btn-close')?.click();
    location.reload();
  } catch (e) {
    alert(`Hata: ${e.message}`);
    console.error(e);
  }
});

// Stok durumu modalı
const stockStatusModal = document.getElementById('stockStatusModal');
stockStatusModal?.addEventListener('show.bs.modal', () => {
  fetch('/api/stock/status')
    .then(r => r.json())
    .then(d => {
      const tbody = document.querySelector('#tblStockStatus tbody');
      if (!tbody) return;
      const detail = d.detail || {};
      tbody.innerHTML = Object.entries(d.totals || {}).map(([dt, qty]) => {
        const det = detail[dt];
        const id = 'det' + dt.replace(/[^a-zA-Z0-9]/g, '');
        const btn = det ? `<button class="btn btn-sm btn-outline-secondary" data-bs-toggle="collapse" data-bs-target="#${id}"><i class="bi bi-list"></i></button>` : '';
        const detailRows = det ? `<tr id="${id}" class="collapse"><td colspan="3"><table class="table table-sm mb-0">${Object.entries(det).map(([ifs, q]) => `<tr><td>${ifs}</td><td>${q}</td></tr>`).join('')}</table></td></tr>` : '';
        return `<tr><td>${dt}</td><td>${qty}</td><td>${btn}</td></tr>${detailRows}`;
      }).join('');
    });
});
