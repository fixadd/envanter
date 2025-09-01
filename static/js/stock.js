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
  fd.set('islem', 'girdi');
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

// Bölümleri göster/gizle
const sectionLicense  = document.getElementById('sectionLicense');
const sectionInventory= document.getElementById('sectionInventory');
const sectionPrinter  = document.getElementById('sectionPrinter');
const showSection = (t)=>{
  sectionLicense?.classList.toggle('d-none', t!=='license');
  sectionInventory?.classList.toggle('d-none', t!=='inventory');
  sectionPrinter?.classList.toggle('d-none', t!=='printer');
};
['ttLisans','ttEnvanter','ttYazici'].forEach(id=>{
  document.getElementById(id)?.addEventListener('change', e=> showSection(e.target.value));
});

// Kaynakları doldur
Promise.all([
  fetch('/inventory/assign/sources').then(r=>r.json()), // { users, inventories }
  fetch('/api/licenses/list').then(r=>r.json()),
  fetch('/api/printers/list').then(r=>r.json()),
]).then(([src, lic, prn])=>{
  const invSel = document.getElementById('selInventory');
  const licSel = document.getElementById('selLicense');
  const prnSel = document.getElementById('selPrinter');
  if(invSel) invSel.innerHTML = '<option value="">Seçiniz</option>' + (src.inventories||[]).map(i=>`<option value="${i.id}">${i.envanter_no} - ${i.marka||''} ${i.model||''}</option>`).join('');
  if(licSel) licSel.innerHTML = '<option value="">Seçiniz</option>' + (lic.items||[]).map(l=>`<option value="${l.id}">${l.lisans_adi} ${l.lisans_anahtari?('('+l.lisans_anahtari+')'):''}</option>`).join('');
  if(prnSel) prnSel.innerHTML = '<option value="">Seçiniz</option>' + (prn.items||[]).map(p=>`<option value="${p.id}">${p.marka||''} ${p.model||''} ${p.seri_no?('('+p.seri_no+')'):''}</option>`).join('');
});

// Atama submit
document.getElementById('frmStockAssign')?.addEventListener('submit', async (e)=>{
  e.preventDefault();
  const fd = new FormData(e.target);
  const payload = Object.fromEntries(fd.entries());
  const res = await fetch('/stock/assign', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload) });
  const j = await res.json();
  if(j.ok){ location.reload(); } else { alert(j.error || 'Atama başarısız'); }
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
