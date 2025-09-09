// static/js/choices_helpers.js

// -------- Helpers ----------
async function getJSON(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

function ensureChoices(selectEl, placeholder = "Seçiniz…") {
  if (!window.Choices) {
    console.warn("Choices.js yüklü değil!");
    return null;
  }
  if (!selectEl) return null;
  if (selectEl._choicesInstance) return selectEl._choicesInstance;

  const inst = new Choices(selectEl, {
    searchEnabled: true,
    itemSelectText: '',
    placeholder: true,
    placeholderValue: placeholder,
    shouldSort: true,
    allowHTML: false
  });
  selectEl._choicesInstance = inst;
  return inst;
}

function setChoicesSafe(selectEl, items, replaceAll = true, placeholderOpt) {
  const inst = ensureChoices(selectEl, placeholderOpt?.placeholderValue || "Seçiniz…");
  if (!inst) return;

  try { inst.clearStore?.(); } catch (_) {}
  try { inst.clearChoices?.(); } catch (_) {}

  inst.setChoices(Array.isArray(items) ? items : [], 'value', 'label', replaceAll);
}

async function fillChoices({ endpoint, selectId, params = {}, placeholder = "Seçiniz…" }) {
  const sel = document.getElementById(selectId);
  if (!sel) return;
  const usp = new URLSearchParams(params);
  const data = await getJSON(endpoint + (usp.toString() ? "?" + usp : ""));

  const choices = data.map(x => ({
    value: x.id,
    label: x.name ?? x.ad ?? x.adi ?? x.text
  }));
  setChoicesSafe(sel, choices, true, { placeholderValue: placeholder });
}

function bindBrandToModel(brandSelectId, modelSelectId) {
  const brandSel = document.getElementById(brandSelectId);
  const modelSel = document.getElementById(modelSelectId);
  if (!brandSel || !modelSel) return;

  setChoicesSafe(modelSel,
    [{ value: "", label: "Önce marka seçiniz…", disabled: true }],
    true, { placeholderValue: "Önce marka seçiniz…" });

  brandSel.addEventListener("change", async () => {
    const brandId = brandSel.value;
    if (!brandId) {
      setChoicesSafe(modelSel,
        [{ value: "", label: "Önce marka seçiniz…", disabled: true }],
        true, { placeholderValue: "Önce marka seçiniz…" });
      return;
    }
    await fillChoices({
      endpoint: "/api/lookup/model",
      selectId: modelSelectId,
      params: { marka_id: brandId },
      placeholder: "Model seçiniz…"
    });
  });
}

function initPersonelChoices(selectId, placeholder = "Personel seçiniz…") {
  const sel = document.getElementById(selectId);
  if (!sel) return;
  const curr = Array.from(sel.options).map(o => ({ value: o.value, label: o.textContent }));
  setChoicesSafe(sel, curr, true, { placeholderValue: placeholder });
}

async function initBagliEnvanterChoices(selectId, tableSelector = 'table tbody a[href^="/inventory/"]', endpoint = '/api/lookup/inventory-no') {
  const sel = document.getElementById(selectId);
  if (!sel) return;
  const placeholder = { placeholderValue: "Envanter no seçiniz…" };

  async function fromEndpoint() {
    const rows = await getJSON(endpoint);
    const choices = rows.map(x => ({
      value: x.no ?? x.name ?? x.id,
      label: x.no ?? x.name ?? String(x.id)
    }));
    setChoicesSafe(sel, choices, true, placeholder);
  }

  function fromTable() {
    const links = document.querySelectorAll(tableSelector);
    const uniq = new Set();
    links.forEach(a => { const t = (a.textContent || '').trim(); if (t) uniq.add(t); });
    const choices = Array.from(uniq).sort().map(no => ({ value: no, label: no }));
    setChoicesSafe(sel, choices.length ? choices : [{ value: "", label: "Kayıt yok", disabled: true }], true, placeholder);
  }

  try { await fromEndpoint(); } catch { fromTable(); }
}

window.choicesHelper = {
  fillChoices,
  bindBrandToModel,
  initPersonelChoices,
  initBagliEnvanterChoices
};


// Not: Bu dosya Choices’in bazı sürümlerinde clearStore olmayan duruma da dayanıklıdır.
