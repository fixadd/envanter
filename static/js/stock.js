document.addEventListener('DOMContentLoaded', () => {
  let donanimSel, markaSel, modelSel, lisansSel;

  const modal = document.getElementById('modalStockAdd');
  modal?.addEventListener('shown.bs.modal', () => {
    donanimSel = document.getElementById('stok_donanim_tipi');
    markaSel   = document.getElementById('stok_marka');
    modelSel   = document.getElementById('stok_model');
    lisansSel  = document.getElementById('lisans_adi');
    applyStockAddType(currentStockAddType);
  });

  const hardwareFields = document.getElementById('hardwareFields');
  const licenseFields  = document.getElementById('licenseFields');
  const miktarInput    = document.getElementById('miktar');
  const rowMiktar      = document.getElementById('rowMiktar');
  const stockAddTypeButtons = document.querySelectorAll('[data-stock-add-type]');
  const initialStockTypeButton = document.querySelector('[data-stock-add-type].active');
  let currentStockAddType = initialStockTypeButton?.dataset.stockAddType || 'inventory';

  function applyStockAddType(type) {
    currentStockAddType = type === 'license' ? 'license' : 'inventory';
    const isLicense = currentStockAddType === 'license';
    hardwareFields?.classList.toggle('d-none', isLicense);
    licenseFields?.classList.toggle('d-none', !isLicense);
    rowMiktar?.classList.toggle('d-none', isLicense);

    hardwareFields?.querySelectorAll('input,select').forEach(el => {
      el.disabled = isLicense;
      if (!isLicense) {
        el.removeAttribute('disabled');
      }
    });
    licenseFields?.querySelectorAll('input,select').forEach(el => {
      el.disabled = !isLicense;
    });

    if (donanimSel) {
      if (isLicense) {
        donanimSel.removeAttribute('required');
      } else {
        donanimSel.setAttribute('required', 'required');
      }
    }

    if (miktarInput) {
      if (isLicense) {
        miktarInput.value = 1;
        miktarInput.readOnly = true;
      } else {
        miktarInput.readOnly = false;
      }
    }

    stockAddTypeButtons.forEach(btn => {
      const isActive = (btn.dataset.stockAddType || 'inventory') === currentStockAddType;
      btn.classList.toggle('active', isActive);
      btn.setAttribute('aria-selected', isActive ? 'true' : 'false');
    });
  }

  stockAddTypeButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      applyStockAddType(btn.dataset.stockAddType || 'inventory');
    });
  });

  applyStockAddType(currentStockAddType);

  document.getElementById('frmStockAdd')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const activeType = document.querySelector('[data-stock-add-type].active');
    const isLicense = (activeType?.dataset.stockAddType || 'inventory') === 'license';
    if (isLicense) {
      fd.set('miktar', '1');
      fd.set('donanim_tipi', fd.get('lisans_adi') || '');
      fd.set('is_lisans', '1');
      fd.delete('is_license');
    } else {
      fd.delete('is_lisans');
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
function getMetaApiRoot() {
  if (typeof document === 'undefined') return '/api';
  const meta = document.querySelector('meta[name="api-root"]');
  if (!meta) return '/api';
  const content = (meta.getAttribute('content') || '').trim();
  return content ? content.replace(/\/$/, '') : '/api';
}

const API_ROOT_META = getMetaApiRoot();
const STOCK_STATUS_URL = `${API_ROOT_META}/stock/status`;

const API_PREFIX = ""; // Örn: "/api"
const URL_STOCK_OPTIONS = `${API_PREFIX}/stock/options`;
const URL_ASSIGN_SOURCES = `${API_PREFIX}/inventory/assign/sources`;
const URL_STOCK_ASSIGN  = `${API_PREFIX}/stock/assign`;
const URL_ASSIGN_SOURCE_DETAIL = `${API_PREFIX}/stock/assign/source-detail`;
window.sa_preselectStockId = null;
let SA_SELECTED_STOCK_META = null;
const SA_SOURCE_CACHE = new Map();
let SA_SOURCE_REQUEST_ID = 0;

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
      opt.dataset.meta = encodeURIComponent(JSON.stringify(o));
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
  const fill = (selector, data, valueKey = "id", labelKey = "text") => {
    const el = document.querySelector(selector);
    if (!el) return;
    el.innerHTML = `<option value="">Seçiniz...</option>`;
    (data || []).forEach(item => {
      const opt = document.createElement("option");
      const value = item[valueKey] ?? item.id ?? item.value ?? "";
      const label = item[labelKey] ?? item.name ?? item.text ?? value;
      opt.value = value || "";
      opt.textContent = label || value || "";
      el.appendChild(opt);
    });
  };

  try {
    const [userRes, inventoryRes, factoryRes, deptRes, usageRes] = await Promise.all([
      fetch(`${URL_ASSIGN_SOURCES}?type=users`),
      fetch(`${URL_ASSIGN_SOURCES}?type=envanter`),
      fetch(`/api/lookup/fabrika`),
      fetch(`${URL_ASSIGN_SOURCES}?type=departman`),
      fetch(`/api/lookup/kullanim_alani`),
    ]);

    if (!userRes.ok || !inventoryRes.ok || !factoryRes.ok || !deptRes.ok || !usageRes.ok) {
      showBanner("Atama kaynakları alınamadı. URL prefix doğru mu?");
    }

    const users = userRes.ok ? await userRes.json() : [];
    const inventories = inventoryRes.ok ? await inventoryRes.json() : [];
    const factories = factoryRes.ok ? await factoryRes.json() : [];
    const departments = deptRes.ok ? await deptRes.json() : [];
    const usageAreas = usageRes.ok ? await usageRes.json() : [];

    fill('#sa_license_person', users, 'id', 'text');
    fill('#sa_inv_person', users, 'id', 'text');
    fill('#sa_license_inventory', inventories, 'id', 'text');
    fill('#sa_inv_factory', factories, 'id', 'name');
    fill('#sa_inv_department', departments, 'id', 'text');
    fill('#sa_inv_usage', usageAreas, 'id', 'name');
    fill('#sa_prn_usage', usageAreas, 'id', 'name');
    sa_updateAutoFields();
  } catch (e) {
    showBanner("Atama kaynakları yüklenemedi. Konsolu kontrol edin.");
    console.error(e);
  }
}

/* ============== Stok seçilince meta + miktar max ============== */
function sa_bindStockMeta(){
  const sel = $("#sa_stock"); if(!sel) return;
  sel.addEventListener("change", ()=>{
    const opt = sel.selectedOptions[0];
    const metaBox = $("#sa_stock_meta");
    if(!opt || !opt.value){
      SA_SELECTED_STOCK_META = null;
      metaBox?.classList.add("d-none");
      $("#sa_meta_tip")?.textContent = '-';
      $("#sa_meta_ifs")?.textContent = '-';
      $("#sa_meta_qty")?.textContent = '0';
      $("#sa_meta_brand")?.textContent = '-';
      $("#sa_meta_model")?.textContent = '-';
      $("#sa_meta_license")?.textContent = '-';
      $("#sa_meta_mail")?.textContent = '-';
      $("#sa_meta_brand_wrap")?.classList.add('d-none');
      $("#sa_meta_model_wrap")?.classList.add('d-none');
      $("#sa_meta_license_wrap")?.classList.add('d-none');
      $("#sa_meta_mail_wrap")?.classList.add('d-none');
      $("#sa_meta_license_row")?.classList.add('d-none');
      sa_updateAutoFields();
      return;
    }

    let parsedMeta = null;
    if (opt.dataset.meta) {
      try {
        parsedMeta = JSON.parse(decodeURIComponent(opt.dataset.meta));
      } catch (err) {
        console.warn('meta parse failed', err);
      }
    }
    SA_SELECTED_STOCK_META = parsedMeta || {
      donanim_tipi: opt.dataset.tip || '',
      ifs_no: opt.dataset.ifs || '',
      mevcut_miktar: Number(opt.dataset.qty || 0)
    };

    $("#sa_meta_tip").textContent = SA_SELECTED_STOCK_META?.donanim_tipi || "-";
    $("#sa_meta_ifs").textContent = SA_SELECTED_STOCK_META?.ifs_no || "-";
    $("#sa_meta_qty").textContent = opt.dataset.qty || "0";
    const brand = SA_SELECTED_STOCK_META?.marka || '';
    const model = SA_SELECTED_STOCK_META?.model || '';
    const licenseKey = SA_SELECTED_STOCK_META?.lisans_anahtari || '';
    const mail = SA_SELECTED_STOCK_META?.mail_adresi || '';
    const brandWrap = $("#sa_meta_brand_wrap");
    const modelWrap = $("#sa_meta_model_wrap");
    const licenseWrap = $("#sa_meta_license_wrap");
    const mailWrap = $("#sa_meta_mail_wrap");
    const licenseRow = $("#sa_meta_license_row");
    if (brandWrap) brandWrap.classList.toggle('d-none', !brand);
    if (modelWrap) modelWrap.classList.toggle('d-none', !model);
    if (licenseWrap) licenseWrap.classList.toggle('d-none', !licenseKey);
    if (mailWrap) mailWrap.classList.toggle('d-none', !mail);
    $("#sa_meta_brand")?.textContent = brand || '-';
    $("#sa_meta_model")?.textContent = model || '-';
    $("#sa_meta_license")?.textContent = licenseKey || '-';
    $("#sa_meta_mail")?.textContent = mail || '-';
    if (licenseRow) {
      const hasLicenseInfo = Boolean(licenseKey || mail);
      licenseRow.classList.toggle('d-none', !hasLicenseInfo);
    }
    metaBox?.classList.remove("d-none");
    sa_updateAutoFields();

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
  req($("#sa_license_name"), !!isLic);
  req($("#sa_inv_no"), !!isEnv);
  req($("#sa_prn_no"), !!isYaz);
}
function sa_bindTabChange(){
  $$("#sa_tabs .nav-link").forEach(b=> b.addEventListener("shown.bs.tab", sa_applyFieldRules));
}

/* ============== Gönder ============== */
async function sa_submit(){
  const stockValue = $("#sa_stock")?.value || "";
  if(!stockValue){ showBanner("Lütfen stok seçiniz.", "warning"); return; }

  let atama_turu = "lisans";
  const active = $("#sa_tabs .nav-link.active");
  if(active?.dataset.bsTarget?.includes("envanter")) atama_turu = "envanter";
  else if(active?.dataset.bsTarget?.includes("yazici")) atama_turu = "yazici";

  const val = el => (el?.value || "").trim();
  const valOrNull = el => {
    const v = val(el);
    return v ? v : null;
  };

  const payload = {
    stock_id: stockValue,
    atama_turu,
    miktar: Number($("#sa_miktar")?.value||1) || 1,
    notlar: valOrNull($("#sa_not")),
  };

  if(atama_turu === "lisans"){
    const lisansAdi = val($("#sa_license_name"));
    if(!lisansAdi){ showBanner("Lisans adı giriniz.", "warning"); return; }
    payload.license_form = {
      lisans_adi: lisansAdi,
      lisans_anahtari: valOrNull($("#sa_license_key")),
      sorumlu_personel: valOrNull($("#sa_license_person")),
      bagli_envanter_no: valOrNull($("#sa_license_inventory")),
      mail_adresi: valOrNull($("#sa_license_mail")),
      ifs_no: valOrNull($("#sa_license_ifs")),
    };
  } else if(atama_turu === "envanter"){
    const envNo = val($("#sa_inv_no"));
    if(!envNo){ showBanner("Envanter numarası giriniz.", "warning"); return; }
    payload.envanter_form = {
      envanter_no: envNo,
      bilgisayar_adi: valOrNull($("#sa_inv_pc")),
      fabrika: valOrNull($("#sa_inv_factory")),
      departman: valOrNull($("#sa_inv_department")),
      sorumlu_personel: valOrNull($("#sa_inv_person")),
      kullanim_alani: valOrNull($("#sa_inv_usage")),
      seri_no: valOrNull($("#sa_inv_serial")),
      bagli_envanter_no: valOrNull($("#sa_inv_machine")),
      notlar: valOrNull($("#sa_inv_note")),
      ifs_no: valOrNull($("#sa_inv_ifs")),
      marka: valOrNull($("#sa_inv_brand")),
      model: valOrNull($("#sa_inv_model")),
      donanim_tipi: valOrNull($("#sa_inv_hardware")),
    };
  } else {
    const prnNo = val($("#sa_prn_no"));
    if(!prnNo){ showBanner("Yazıcı envanter numarası giriniz.", "warning"); return; }
    payload.printer_form = {
      envanter_no: prnNo,
      marka: valOrNull($("#sa_prn_brand")),
      model: valOrNull($("#sa_prn_model")),
      kullanim_alani: valOrNull($("#sa_prn_usage")),
      ip_adresi: valOrNull($("#sa_prn_ip")),
      mac: valOrNull($("#sa_prn_mac")),
      hostname: valOrNull($("#sa_prn_host")),
      ifs_no: valOrNull($("#sa_prn_ifs")),
      notlar: valOrNull($("#sa_prn_note")),
    };
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
    if (typeof loadStockStatus === "function") {
      loadStockStatus();
    }
    await sa_loadStocks();
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

function sa_setFieldValue(input, value){
  if (!input) return;
  if (input.tagName === 'SELECT') {
    const stringValue = value !== undefined && value !== null ? String(value) : '';
    if (!stringValue) {
      Array.from(input.querySelectorAll('option[data-auto-option="1"]')).forEach(opt => opt.remove());
      input.value = '';
      return;
    }
    let option = Array.from(input.options).find(opt => opt.value === stringValue);
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

function sa_applyAutoData(data, options = {}){
  const { source = null, clearMissing = false, onlySource = false, skipHide = false } = options;
  document.querySelectorAll('[data-auto-key]').forEach(input => {
    if (!input) return;
    const keyAttr = input.dataset.autoKey || '';
    const keys = keyAttr.split(/[|,]/).map(k => k.trim()).filter(Boolean);
    const sources = (input.dataset.autoSource || '').split(',').map(s => s.trim()).filter(Boolean);
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
      sa_setFieldValue(input, value);
    } else if (clearMissing) {
      sa_setFieldValue(input, '');
    }
    if (!skipHide) {
      const container = input.closest('[data-auto-field]');
      if (container) {
        container.classList.toggle('d-none', hasValue);
      }
    }
  });
}

function sa_autoSelectTab(meta){
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

function sa_resetSourceSpecificFields(){
  ['envanter', 'lisans', 'yazici'].forEach(type => {
    sa_applyAutoData({}, { source: type, clearMissing: true, onlySource: true });
  });
}

function sa_fetchSourceDetail(sourceType, sourceId){
  const cacheKey = `${sourceType}:${sourceId}`;
  if (SA_SOURCE_CACHE.has(cacheKey)) {
    return Promise.resolve(SA_SOURCE_CACHE.get(cacheKey));
  }
  const url = `${URL_ASSIGN_SOURCE_DETAIL}?type=${encodeURIComponent(sourceType)}&id=${encodeURIComponent(sourceId)}`;
  return fetch(url, { headers: { Accept: 'application/json' } })
    .then(res => {
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
      return res.json();
    })
    .then(data => {
      SA_SOURCE_CACHE.set(cacheKey, data);
      return data;
    });
}

function sa_fillSourceDetails(meta){
  sa_resetSourceSpecificFields();
  if (!meta || !meta.source_type || !meta.source_id) {
    return;
  }
  const requestId = ++SA_SOURCE_REQUEST_ID;
  sa_fetchSourceDetail(meta.source_type, meta.source_id)
    .then(detail => {
      if (requestId !== SA_SOURCE_REQUEST_ID) return;
      if (detail && detail.data) {
        sa_applyAutoData(detail.data, { source: detail.type, clearMissing: true });
      }
    })
    .catch(err => {
      if (requestId !== SA_SOURCE_REQUEST_ID) return;
      console.error('source detail load failed', err);
    });
}

function sa_updateAutoFields(){
  const meta = SA_SELECTED_STOCK_META || {};
  sa_applyAutoData(meta, { clearMissing: true });
  sa_autoSelectTab(meta);
  sa_fillSourceDetails(meta);
}

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
  return `<tr>
    <td>${item.donanim_tipi || '-'}</td>
    <td>${item.marka || '-'}</td>
    <td>${item.model || '-'}</td>
    <td>${item.ifs_no || '-'}</td>
    <td class="text-end">${item.net_miktar}</td>
    <td>${item.son_islem_ts ? new Date(item.son_islem_ts).toLocaleString('tr-TR', { day:'2-digit', month:'2-digit', year:'numeric', hour:'2-digit', minute:'2-digit', hour12:false }) : '-'}</td>
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

function filterStockTable(){
  const q = document.getElementById('stockSearch')?.value.toLowerCase() || '';
  const activePane = document.querySelector('#stockStatusTabContent .tab-pane.active');
  if (!activePane) return;
  activePane.querySelectorAll('tbody tr').forEach(tr=>{
    if (tr.dataset.emptyRow === '1') {
      tr.style.display = '';
      return;
    }
    tr.style.display = tr.textContent.toLowerCase().includes(q) ? '' : 'none';
  });
}
document.getElementById('stockSearch')?.addEventListener('input', filterStockTable);
document.querySelectorAll('#stockStatusTabs [data-bs-toggle="tab"]').forEach(btn => {
  btn.addEventListener('shown.bs.tab', filterStockTable);
});

// Stok durumu sekmesini yükle
function loadStockStatus() {
  setStockStatusMessage(document.querySelector('#tblStockStatusInventory tbody'), 'Yükleniyor…');
  setStockStatusMessage(document.querySelector('#tblStockStatusLicense tbody'), 'Yükleniyor…');

  fetch(STOCK_STATUS_URL, {
    headers: { Accept: 'application/json' },
    credentials: 'same-origin',
  })
    .then(r => {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    })
    .then(data => {
      const inventoryTbody = document.querySelector('#tblStockStatusInventory tbody');
      const licenseTbody = document.querySelector('#tblStockStatusLicense tbody');
      if (!inventoryTbody || !licenseTbody) return;
      const items = Array.isArray(data) ? data : (data.items || data.rows);
      if (!Array.isArray(items)) {
        setStockStatusMessage(inventoryTbody, 'Veri alınamadı');
        setStockStatusMessage(licenseTbody, 'Veri alınamadı');
        return;
      }

      const inventoryItems = [];
      const licenseItems = [];
      items.forEach(item => {
        const typeRaw = item?.source_type;
        const type = typeof typeRaw === 'string' ? typeRaw.toLowerCase() : '';
        if (type === 'lisans') {
          licenseItems.push(item);
        } else {
          inventoryItems.push(item);
        }
      });

      renderStockStatusTable(inventoryTbody, inventoryItems);
      renderStockStatusTable(licenseTbody, licenseItems);
      filterStockTable();
    })
    .catch(err => {
      console.error('stock status load failed', err);
      const inventoryTbody = document.querySelector('#tblStockStatusInventory tbody');
      const licenseTbody = document.querySelector('#tblStockStatusLicense tbody');
      setStockStatusMessage(inventoryTbody, 'Veri alınamadı');
      setStockStatusMessage(licenseTbody, 'Veri alınamadı');
    });
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
    const label = item?.source_type
      ? (STOCK_DETAIL_SOURCE_LABELS[item.source_type] || item.source_type)
      : '';
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

document.addEventListener('click', event => {
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
});

// Tab gösterildiğinde yükle
const stockStatusTab = document.getElementById('tab-status');
stockStatusTab?.addEventListener('shown.bs.tab', loadStockStatus);

// Sayfa yüklenirken de bir kez dene
loadStockStatus();
