// Donanım tipi lookup doldur
fetch('/api/lookup/donanim_tipi')
  .then(r=>r.json())
  .then(d=>{
    const sel = document.getElementById('donanim_tipi');
    if(!sel) return;
    sel.innerHTML = '<option value="">Seçiniz</option>' + (d.items||[]).map(x=>`<option>${x.ad}</option>`).join('');
  });

// Ekle form submit
document.getElementById('frmStockAdd')?.addEventListener('submit', async (e)=>{
  e.preventDefault();
  const fd = new FormData(e.target);
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
