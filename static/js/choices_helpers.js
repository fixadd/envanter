// static/js/choices_helpers.js

// -------- Helpers ----------
async function getJSON(url, opts = {}) {
  const r = await fetch(url, opts);
  if (!r.ok) {
    const err = new Error(await r.text());
    err.status = r.status;
    throw err;
  }
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
    itemSelectText: "",
    placeholder: true,
    placeholderValue: placeholder,
    shouldSort: true,
    allowHTML: false,
  });
  selectEl._choicesInstance = inst;
  return inst;
}

function setChoicesSafe(selectEl, items, replaceAll = true, placeholderOpt) {
  const inst = ensureChoices(
    selectEl,
    placeholderOpt?.placeholderValue || "Seçiniz…",
  );
  if (!inst) return;

  try {
    inst.clearStore?.();
  } catch (_) {}
  try {
    inst.clearChoices?.();
  } catch (_) {}

  inst.setChoices(
    Array.isArray(items) ? items : [],
    "value",
    "label",
    replaceAll,
  );
}

async function fillChoices({
  endpoint,
  selectId,
  params = {},
  placeholder = "Seçiniz…",
  signal,
}) {
  const sel = document.getElementById(selectId);
  if (!sel) return;
  const p = { ...params };
  if (endpoint.includes("/api/lookup/model")) delete p.marka;
  const usp = new URLSearchParams();
  Object.entries(p).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") usp.append(k, v);
  });
  if (endpoint.includes("/api/lookup/model") && !usp.has("marka_id")) return;
  const url = endpoint + (usp.toString() ? "?" + usp : "");
  let data = [];
  try {
    data = await getJSON(url, { signal });
  } catch (e) {
    if (e.status === 422) {
      if (window.showAlert) {
        window.showAlert("Lütfen önce marka seçiniz.", {
          variant: "warning",
          title: "Eksik Seçim",
        });
      } else {
        alert("Marka seçiniz");
      }
      return;
    }
    if (e.name === "AbortError") return;
    throw e;
  }

  const choices = (Array.isArray(data) ? data : []).map((item) => {
    if (item == null) {
      return { value: "", label: "" };
    }
    if (typeof item === "string" || typeof item === "number") {
      const text = String(item);
      return { value: text, label: text };
    }
    const value = item.id ?? item.value ?? (item.text != null ? item.text : "");
    const label =
      item.name ??
      item.text ??
      item.ad ??
      item.adi ??
      item.label ??
      (value !== undefined && value !== null ? String(value) : "");
    return { value, label };
  });
  setChoicesSafe(sel, choices, true, { placeholderValue: placeholder });
}

function bindBrandToModel(brandSelectId, modelSelectId) {
  const brandSel = document.getElementById(brandSelectId);
  const modelSel = document.getElementById(modelSelectId);
  if (!brandSel || !modelSel) return;

  setChoicesSafe(
    modelSel,
    [{ value: "", label: "Önce marka seçiniz…", disabled: true }],
    true,
    { placeholderValue: "Önce marka seçiniz…" },
  );

  let aborter;
  brandSel.addEventListener("change", async () => {
    const brandId = brandSel.value;
    if (aborter) aborter.abort();
    if (!brandId) {
      setChoicesSafe(
        modelSel,
        [{ value: "", label: "Önce marka seçiniz…", disabled: true }],
        true,
        { placeholderValue: "Önce marka seçiniz…" },
      );
      return;
    }
    aborter = new AbortController();
    await fillChoices({
      endpoint: "/api/lookup/model",
      selectId: modelSelectId,
      params: { marka_id: brandId },
      placeholder: "Model seçiniz…",
      signal: aborter.signal,
    });
  });
}

function initPersonelChoices(selectId, placeholder = "Personel seçiniz…") {
  const sel = document.getElementById(selectId);
  if (!sel) return;
  const curr = Array.from(sel.options).map((o) => ({
    value: o.value,
    label: o.textContent,
  }));
  setChoicesSafe(sel, curr, true, { placeholderValue: placeholder });
}

async function initBagliEnvanterChoices(
  selectId,
  tableSelector = 'table tbody a[href^="/inventory/"]',
  endpoint = "/api/lookup/inventory-no",
) {
  const sel = document.getElementById(selectId);
  if (!sel) return;
  const placeholder = { placeholderValue: "Envanter no seçiniz…" };

  async function fromEndpoint() {
    const rows = await getJSON(endpoint);
    const choices = rows.map((x) => ({
      value: x.no ?? x.name ?? x.id,
      label: x.no ?? x.name ?? String(x.id),
    }));
    setChoicesSafe(sel, choices, true, placeholder);
  }

  function fromTable() {
    const links = document.querySelectorAll(tableSelector);
    const uniq = new Set();
    links.forEach((a) => {
      const t = (a.textContent || "").trim();
      if (t) uniq.add(t);
    });
    const choices = Array.from(uniq)
      .sort()
      .map((no) => ({ value: no, label: no }));
    setChoicesSafe(
      sel,
      choices.length
        ? choices
        : [{ value: "", label: "Kayıt yok", disabled: true }],
      true,
      placeholder,
    );
  }

  try {
    await fromEndpoint();
  } catch {
    fromTable();
  }
}

window.choicesHelper = {
  fillChoices,
  bindBrandToModel,
  initPersonelChoices,
  initBagliEnvanterChoices,
};

// Not: Bu dosya Choices’in bazı sürümlerinde clearStore olmayan duruma da dayanıklıdır.
