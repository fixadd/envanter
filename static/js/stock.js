// Lookup'ları picker API'sinden doldur
async function loadPicker(sel, url){
  if(!sel) return;
  try{
    const res = await fetch(url, {headers:{Accept:'application/json'}});
    const data = await res.json();
    sel.innerHTML = '<option value="">Seçiniz</option>' + (data||[]).map(x=>`<option value="${x.text}" data-id="${x.id||''}">${x.text}</option>`).join('');
  }catch(e){
    console.error('lookup failed', url, e);
  }
}

let donanimSel, markaSel, modelSel, lisansSel;

async function loadModels(){
  if(!modelSel) return;
  const opt = markaSel?.selectedOptions[0];
  const markaId = opt?.dataset.id;
  modelSel.innerHTML = '<option value="">Seçiniz</option>';
  if(!markaId) return;
  try{
    const res = await fetch(`/api/picker/model?marka_id=${markaId}`, {headers:{Accept:'application/json'}});
    if(!res.ok) return;
    const data = await res.json();
    modelSel.innerHTML = '<option value="">Seçiniz</option>' + (data||[]).map(x=>`<option value="${x.text}" data-id="${x.id||''}">${x.text}</option>`).join('');
  }catch(e){ console.error('model lookup failed', e); }
}

document.getElementById('stockAddModal')?.addEventListener('shown.bs.modal', async () => {
  donanimSel = document.getElementById('donanim_tipi');
  markaSel    = document.getElementById('marka');
  modelSel    = document.getElementById('model');
  lisansSel   = document.getElementById('lisans_adi');

  await Promise.all([
    loadPicker(donanimSel, '/api/picker/donanim_tipi'),
    loadPicker(markaSel, '/api/picker/marka'),
    loadPicker(lisansSel, '/api/picker/lisans_adi'),
  ]);

  loadModels();
  if(markaSel) markaSel.onchange = loadModels;
});

// Ekle form submit
const chkIsLicense = document.getElementById('chkIsLicense');
const hardwareFields = document.getElementById('hardwareFields');
const licenseFields  = document.getElementById('licenseFields');
const miktarInput    = document.getElementById('miktar');
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
/* ================== AYAR ================== */
const API_PREFIX = ""; // Örn: "/api"
const URL_STOCK_OPTIONS = `${API_PREFIX}/stock/options`;
const URL_ASSIGN_SOURCES = `${API_PREFIX}/inventory/assign/sources`;
const URL_STOCK_ASSIGN  = `${API_PREFIX}/stock/assign`;

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
  }catch(e){
    showBanner("Stok listesi yüklenemedi. Konsolu kontrol edin."); console.error(e);
  }
}

async function sa_loadSources(){
  const fill = (id, arr, v="id", l="ad")=>{
    const el = $(id); if(!el) return;
    el.innerHTML = `<option value="">Seçiniz...</option>`;
    (arr||[]).forEach(x=>{
      const o = document.createElement("option");
      o.value = x[v]; o.textContent = x[l] ?? x[v];
      el.appendChild(o);
    });
  };

  try{
    const [u,l,e,y] = await Promise.all([
      fetch(`${URL_ASSIGN_SOURCES}?type=users`),
      fetch(`${URL_ASSIGN_SOURCES}?type=licenses`),
      fetch(`${URL_ASSIGN_SOURCES}?type=envanter`),
      fetch(`${URL_ASSIGN_SOURCES}?type=yazici`)
    ]);
    if(!u.ok||!l.ok||!e.ok||!y.ok){
      showBanner("Atama kaynakları alınamadı. URL prefix doğru mu?"); 
    }
    const users = u.ok? await u.json():[];
    const lic   = l.ok? await l.json():[];
    const env   = e.ok? await e.json():[];
    const yaz   = y.ok? await y.json():[];

    fill("#sa_user", users, "id", "ad");
    fill("#sa_user2", users, "id", "ad");
    fill("#sa_lisans", lic, "id", "lisans_adi");
    fill("#sa_envanter", env, "id", "envanter_no");
    fill("#sa_envanter_for_lic", env, "id", "envanter_no");
    fill("#sa_yazici", yaz, "id", "model");
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
