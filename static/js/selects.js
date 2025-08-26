// static/js/selects.js
const selects = {};

function makeSearchableSelect(el, placeholder="Seçiniz…") {
  if (el._choices) return el._choices;
  const inst = new Choices(el, {
    searchEnabled: true,
    shouldSort: true,
    allowHTML: false,
    itemSelectText: "",
    placeholder: true,
    placeholderValue: placeholder,
    searchPlaceholderValue: "Ara...",
    noResultsText: "Sonuç yok",
    noChoicesText: "Seçenek yok",
  });
  el._choices = inst;
  return inst;
}

async function fillChoices({ endpoint, selectId, params={}, placeholder="Seçiniz…", keepValue=false }) {
  const el = document.getElementById(selectId);
  if (!el) return;
  let inst = selects[selectId];
  if (!inst) { inst = makeSearchableSelect(el, placeholder); selects[selectId] = inst; }
  const usp = new URLSearchParams(params);
  const res = await fetch(`${endpoint}?${usp.toString()}`);
  const data = res.ok ? await res.json() : [];
  const current = keepValue ? el.value : null;
  inst.clearStore();
  inst.setChoices(data.map(r => ({ value: r.id, label: r.text ?? r.ad ?? r.name })), 'value', 'label', true);
  if (keepValue && current) inst.setChoiceByValue(current);
}

async function bindMarkaModel(markaSelectId, modelSelectId) {
  const markaEl = document.getElementById(markaSelectId);
  const modelEl = document.getElementById(modelSelectId);
  if (!markaEl || !modelEl) return;
  const modelInst = selects[modelSelectId] || makeSearchableSelect(modelEl, "Model seçiniz…");
  selects[modelSelectId] = modelInst;

  async function updateModels() {
    const m = markaEl.value;
    if (!m) { modelInst.clearStore(); modelEl.disabled = true; return; }
    modelEl.disabled = false;
    await fillChoices({ endpoint: "/api/lookup/model", selectId: modelSelectId, params: { marka_id: m }, placeholder: "Model seçiniz…" });
  }
  markaEl.addEventListener("change", updateModels);
  await updateModels();
}

function debounce(fn, d=300){ let t; return (...a)=>{ clearTimeout(t); t=setTimeout(()=>fn(...a), d); }; }
function enableRemoteSearch(selectId, endpoint, extraParamsFn=()=>({})) {
  const inst = selects[selectId]; if (!inst) return;
  const input = inst.input?.element; if (!input) return;
  input.addEventListener("input", debounce(async ()=>{
    const q = input.value.trim();
    await fillChoices({ endpoint, selectId, params: { q, ...extraParamsFn() }, keepValue: false });
  }, 300));
}

document.addEventListener("DOMContentLoaded", () => {
  if (window.SKIP_SELECT_ENHANCE) return;
  document.querySelectorAll("select").forEach(el => {
    if (el.dataset.noSearch !== undefined) return;
    const inst = makeSearchableSelect(el);
    if (el.id) selects[el.id] = inst;
  });
});

window._selects = { fillChoices, bindMarkaModel, enableRemoteSearch, makeSearchableSelect };
