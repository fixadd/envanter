document.addEventListener('DOMContentLoaded', () => {
  let donanimSel, markaSel, modelSel, lisansSel;

  const modal = document.getElementById('modalStockAdd');
  modal?.addEventListener('shown.bs.modal', () => {
    donanimSel = document.getElementById('stok_donanim_tipi');
    markaSel   = document.getElementById('stok_marka');
    modelSel   = document.getElementById('stok_model');
    lisansSel  = document.getElementById('lisans_adi');
  });

  const chkIsLicense   = document.getElementById('chkIsLicense');
  const hardwareFields = document.getElementById('hardwareFields');
  const licenseFields  = document.getElementById('licenseFields');
  const miktarInput    = document.getElementById('miktar');
  const rowMiktar      = document.getElementById('rowMiktar');

  chkIsLicense?.addEventListener('change', e => {
    const isLic = e.target.checked;
    hardwareFields?.classList.toggle('d-none', isLic);
    licenseFields?.classList.toggle('d-none', !isLic);
    donanimSel?.toggleAttribute('required', !isLic);
    rowMiktar?.classList.toggle('d-none', isLic);
    hardwareFields?.querySelectorAll('input,select').forEach(el => el.disabled = isLic);
    licenseFields?.querySelectorAll('input,select').forEach(el => el.disabled = !isLic);
    if (isLic) {
      if (miktarInput) {
        miktarInput.value = 1;
        miktarInput.readOnly = true;
      }
    } else if (miktarInput) {
      miktarInput.readOnly = false;
    }
  });

  document.getElementById('frmStockAdd')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    if (chkIsLicense?.checked) {
      fd.set('miktar', '1');
      fd.set('donanim_tipi', fd.get('lisans_adi') || '');
      fd.set('is_lisans', '1');
      fd.delete('is_license');
    }
    const payload = Object.fromEntries(fd.entries());
    const miktar = Number(payload.miktar);
    if (!miktar || miktar <= 0) { alert('Miktar 0\'dan büyük olmalı'); return; }
    try {
      const res = await fetch('/stock/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        let errMsg = `HTTP ${res.status}`;
        if (res.statusText) {
          errMsg += ` ${res.statusText}`;
        }
        try {
          const bodyText = await res.text();
          if (bodyText) {
            errMsg += `\n${bodyText}`;
          }
        } catch (bodyErr) {
          console.error('stock add response read failed', bodyErr);
        }
        alert(`Kayıt başarısız: ${errMsg}`);
        return;
      }

      let j;
      try {
        j = await res.json();
      } catch (jsonErr) {
        console.error('stock add response parse failed', jsonErr);
        alert('Sunucudan geçerli JSON alınamadı.');
        return;
      }

      if (j.ok) {
        location.reload();
      } else {
        alert(j.error || 'Kayıt başarısız');
      }
    } catch (err) {
      console.error('stock add failed', err);
      alert('Kayıt başarısız');
    }
  });
});

// --- Yeni stok atama modali -------------------------------------------------
/* ================== AYAR ================== */
const API_PREFIX = ""; // Örn: "/api"
const URL_STOCK_OPTIONS = `${API_PREFIX}/stock/options`;
const URL_ASSIGN_SOURCES = `${API_PREFIX}/inventory/assign/sources`;
const URL_STOCK_ASSIGN  = `${API_PREFIX}/stock/assign`;
window.sa_preselectStockId = null;

/* ============== Yardımcılar/Toast ============== */
const $ = (s) => document.querySelector(s);
const $$ = (s) => Array.from(document.querySelectorAll(s));
function show(el, on){ if(el) el.classList.toggle('d-none', !on); }
function req(el, on){ if(el){ on ? el.setAttribute('required','required') : el.removeAttribute('required'); } }

function showBanner(msg, type="danger"){
  // modal body'nin üstüne kısa uyarı
  let holder = $("#sa_banner");
  if (!holder) {
    const body = $("#stokAtamaModal .modal-body");
    holder = document.createElement("div");
    holder.id = "sa_banner";
    body.prepend(holder);
  }
  holder.innerHTML = `<div class="alert alert-${type} py-2 px-3 mb-2">${msg}</div>`;
  setTimeout(()=>{ holder.innerHTML = "" }, 6000);
  console.log("[StokAtama]", msg);
}

/* ============== Listeleri Yükle ============== */
async function sa_loadStocks(){
  const sel = $("#sa_stock"); if(!sel) return;
  sel.innerHTML = `<option value="">Seçiniz...</option>`;
  try{
    const res = await fetch(URL_STOCK_OPTIONS, {headers:{Accept:"application/json"}});
    if(!res.ok){ showBanner(`Stok listesi başarısız (HTTP ${res.status})`); return; }
    const data = await res.json();
    if(!Array.isArray(data) || data.length===0){
      showBanner("Uygun stok bulunamadı (miktar > 0).", "warning"); return;
    }
    data.forEach(o=>{
      const opt = document.createElement("option");
      opt.value = o.id;
      opt.textContent = o.label ?? `${o.donanim_tipi||'Donanım'} | IFS:${o.ifs_no||'-'} | Mevcut:${o.mevcut_miktar??0}`;
      opt.dataset.tip = o.donanim_tipi||"";
      opt.dataset.ifs = o.ifs_no||"";
      opt.dataset.qty = Number(o.mevcut_miktar??0);
      sel.appendChild(opt);
    });
    if(window.sa_preselectStockId){
      sel.value = window.sa_preselectStockId;
      sel.dispatchEvent(new Event('change'));
      window.sa_preselectStockId = null;
    }
  }catch(e){
    showBanner("Stok listesi yüklenemedi. Konsolu kontrol edin."); console.error(e);
  }
}

async function sa_loadSources(){
  const fill = (id, arr, valueKey="id", labelKey="ad")=>{
    const el = $(id); if(!el) return;
    el.innerHTML = `<option value="">Seçiniz...</option>`;
    (arr||[]).forEach(x=>{
      const o = document.createElement("option");
      o.value = x[valueKey]; o.textContent = x[labelKey] ?? x[valueKey];
      el.appendChild(o);
    });
  };

  try{
    const [userResponse, licenseResponse, inventoryResponse, printerResponse] = await Promise.all([
      fetch(`${URL_ASSIGN_SOURCES}?type=users`),
      fetch(`${URL_ASSIGN_SOURCES}?type=licenses`),
      fetch(`${URL_ASSIGN_SOURCES}?type=envanter`),
      fetch(`${URL_ASSIGN_SOURCES}?type=yazici`)
    ]);
    if(!userResponse.ok||!licenseResponse.ok||!inventoryResponse.ok||!printerResponse.ok){
      showBanner("Atama kaynakları alınamadı. URL prefix doğru mu?");
    }
    const users       = userResponse.ok? await userResponse.json():[];
    const licenses    = licenseResponse.ok? await licenseResponse.json():[];
    const inventories = inventoryResponse.ok? await inventoryResponse.json():[];
    const printers    = printerResponse.ok? await printerResponse.json():[];

    fill("#sa_user", users, "id", "ad");
    fill("#sa_user2", users, "id", "ad");
    fill("#sa_lisans", licenses, "id", "lisans_adi");
    fill("#sa_envanter", inventories, "id", "envanter_no");
    fill("#sa_envanter_for_lic", inventories, "id", "envanter_no");
    fill("#sa_yazici", printers, "id", "model");
  }catch(e){
    showBanner("Atama kaynakları yüklenemedi. Konsolu kontrol edin."); console.error(e);
  }
}

/* ============== Stok seçilince meta + miktar max ============== */
function sa_bindStockMeta(){
  const sel = $("#sa_stock"); if(!sel) return;
  sel.addEventListener("change", ()=>{
    const opt = sel.selectedOptions[0];
    const meta = $("#sa_stock_meta");
    if(!opt || !opt.value){ meta?.classList.add("d-none"); return; }
    $("#sa_meta_tip").textContent = opt.dataset.tip || "-";
    $("#sa_meta_ifs").textContent = opt.dataset.ifs || "-";
    $("#sa_meta_qty").textContent = opt.dataset.qty || "0";
    meta?.classList.remove("d-none");

    const miktar = $("#sa_miktar");
    if(miktar){
      const max = Number(opt.dataset.qty||1);
      miktar.max = String(max);
      if(Number(miktar.value)>max) miktar.value = String(max);
    }
  });
}

/* ============== Sekmeye göre gerekli alanlar ============== */
function sa_applyFieldRules(){
  const active = $("#sa_tabs .nav-link.active");
  const isLic = active?.dataset.bsTarget?.includes("lisans");
  const isEnv = active?.dataset.bsTarget?.includes("envanter");
  const isYaz = active?.dataset.bsTarget?.includes("yazici");

  show($("#sa_tab_lisans"),   !!isLic);
  show($("#sa_tab_envanter"), !!isEnv);
  show($("#sa_tab_yazici"),   !!isYaz);

  req($("#sa_lisans"),   !!isLic);
  req($("#sa_envanter"), !!isEnv);
  req($("#sa_yazici"),   !!isYaz);
}
function sa_bindTabChange(){
  $$("#sa_tabs .nav-link").forEach(b=> b.addEventListener("shown.bs.tab", sa_applyFieldRules));
}

/* ============== Gönder ============== */
async function sa_submit(){
  const stockId = Number($("#sa_stock")?.value||0);
  if(!stockId){ showBanner("Lütfen stok seçiniz.", "warning"); return; }

  let atama_turu = "lisans";
  const active = $("#sa_tabs .nav-link.active");
  if(active?.dataset.bsTarget?.includes("envanter")) atama_turu = "envanter";
  else if(active?.dataset.bsTarget?.includes("yazici")) atama_turu = "yazici";

  const payload = {
    stock_id: stockId,
    atama_turu,
    miktar: Number($("#sa_miktar")?.value||1),
    notlar: $("#sa_not")?.value||null,
    lisans_id: null,
    hedef_envanter_id: null,
    hedef_yazici_id: null,
    sorumlu_personel_id: null,
  };

  if(atama_turu==="lisans"){
    payload.lisans_id = Number($("#sa_lisans")?.value||0) || null;
    payload.sorumlu_personel_id = Number($("#sa_user")?.value||0) || null;
    const eforlic = Number($("#sa_envanter_for_lic")?.value||0);
    if(eforlic) payload.hedef_envanter_id = eforlic;
  }else if(atama_turu==="envanter"){
    payload.hedef_envanter_id = Number($("#sa_envanter")?.value||0) || null;
    payload.sorumlu_personel_id = Number($("#sa_user2")?.value||0) || null;
  }else{
    payload.hedef_yazici_id = Number($("#sa_yazici")?.value||0) || null;
  }

  try{
    const res = await fetch(URL_STOCK_ASSIGN, {
      method:"POST", headers:{"Content-Type":"application/json"},
      body: JSON.stringify(payload)
    });
    const out = await res.json().catch(()=> ({}));
    if(!res.ok){ showBanner(out?.detail || "Atama başarısız.", "danger"); return; }
    showBanner(out?.message || "Atama tamamlandı.", "success");
    document.querySelector('#stokAtamaModal .btn-close')?.click();
  }catch(e){
    showBanner("Atama gönderilemedi. Konsolu kontrol edin."); console.error(e);
  }
}

/* ============== Boot ============== */
(function boot(){
  // Script’in yüklendiğini anlamak için log
  console.log("[StokAtama] boot start");
  // DOM yüklendiğinde
  document.addEventListener("DOMContentLoaded", async ()=>{
    console.log("[StokAtama] DOMContentLoaded");
    await sa_loadStocks();
    await sa_loadSources();
    sa_bindStockMeta();
    sa_bindTabChange();
    sa_applyFieldRules();
  });
  // Modal açıldığında tekrar yükle
  document.addEventListener("shown.bs.modal", async (ev)=>{
    if(ev.target.id !== "stokAtamaModal") return;
    console.log("[StokAtama] modal shown -> reload lists");
    await sa_loadStocks();
    await sa_loadSources();
    sa_applyFieldRules();
  });
  // Submit
  document.getElementById("sa_submit")?.addEventListener("click", sa_submit);
})();

function assignFromStatus(encoded){
  const item = JSON.parse(decodeURIComponent(encoded));
  window.sa_preselectStockId = [item.donanim_tipi, item.marka || '', item.model || '', item.ifs_no || ''].join('|');
  const modalEl = document.getElementById('stokAtamaModal');
  if(modalEl){
    const m = new bootstrap.Modal(modalEl);
    m.show();
  }
}

async function scrapFromStatus(encoded){
  const item = JSON.parse(decodeURIComponent(encoded));
  const qtyStr = prompt('Miktar', '1');
  if(qtyStr===null) return;
  const qty = Number(qtyStr);
  if(!qty || qty<=0){ alert('Geçersiz miktar'); return; }
  if(!confirm(`${qty} adet hurdaya ayrılacak. Onaylıyor musunuz?`)) return;
  const payload = { donanim_tipi:item.donanim_tipi, marka:item.marka, model:item.model, ifs_no:item.ifs_no, miktar:qty, islem:'hurda', islem_yapan:'UI'};
  try{
    const res = await fetch('/stock/add', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)});
    const j = await res.json();
    if(j.ok){ loadStockStatus(); sa_loadStocks(); }
    else{ alert(j.error || 'İşlem başarısız'); }
  }catch(e){ console.error('scrap failed', e); alert('İşlem başarısız'); }
}

function filterStockTable(){
  const q = document.getElementById('stockSearch')?.value.toLowerCase() || '';
  document.querySelectorAll('#tblStockStatus tbody tr').forEach(tr=>{
    tr.style.display = tr.textContent.toLowerCase().includes(q) ? '' : 'none';
  });
}
document.getElementById('stockSearch')?.addEventListener('input', filterStockTable);

// Stok durumu sekmesini yükle
function loadStockStatus() {
  fetch('/api/stock/status', { headers: { Accept: 'application/json' } })
    .then(r => {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    })
    .then(data => {
      const tbody = document.querySelector('#tblStockStatus tbody');
      if (!tbody) return;
      const items = Array.isArray(data) ? data : (data.items || data.rows);
      if (!Array.isArray(items) || items.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">Stok bulunamadı</td></tr>';
        return;
      }
      const rows = items
        .map(item => {
          const payload = encodeURIComponent(JSON.stringify(item));
          return `<tr>
            <td>${item.donanim_tipi || '-'}</td>
            <td>${item.marka || '-'}</td>
            <td>${item.model || '-'}</td>
            <td>${item.ifs_no || '-'}</td>
            <td class="text-end">${item.net_miktar}</td>
            <td>${item.son_islem_ts ? new Date(item.son_islem_ts).toLocaleString('tr-TR', { day:'2-digit', month:'2-digit', year:'numeric', hour:'2-digit', minute:'2-digit', hour12:false }) : '-'}</td>
            <td class="text-center">
              <button class="btn btn-sm btn-outline-primary me-1" onclick="assignFromStatus('${payload}')">Atama</button>
              <button class="btn btn-sm btn-outline-danger" onclick="scrapFromStatus('${payload}')">Hurda</button>
            </td>
          </tr>`;
        })
        .join('');
      tbody.innerHTML = rows;
      filterStockTable();
    })
    .catch(err => {
      console.error('stock status load failed', err);
      const tbody = document.querySelector('#tblStockStatus tbody');
      if (tbody) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">Veri alınamadı</td></tr>';
      }
    });
}

// Tab gösterildiğinde yükle
const stockStatusTab = document.getElementById('tab-status');
stockStatusTab?.addEventListener('shown.bs.tab', loadStockStatus);

// Sayfa yüklenirken de bir kez dene
loadStockStatus();
