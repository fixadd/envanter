// static/js/selects.js
const selects = {};

function makeSearchableSelect(el, placeholder = "Seçiniz…") {
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

async function fillChoices({
  endpoint,
  selectId,
  params = {},
  placeholder = "Seçiniz…",
  keepValue = false,
  mapFn,
  signal,
}) {
  const el = document.getElementById(selectId);
  if (!el) return;
  let inst = selects[selectId];
  if (!inst) {
    inst = makeSearchableSelect(el, placeholder);
    selects[selectId] = inst;
  }

  const p = { ...params };
  if (endpoint.includes("/api/lookup/model")) delete p.marka; // tek parametre marka_id

  // Boş parametreleri filtrele
  const usp = new URLSearchParams();
  Object.entries(p).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") usp.append(k, v);
  });

  // Model lookup'larında marka seçimi yoksa istek gönderme
  if (endpoint.includes("/api/lookup/model") && !usp.has("marka_id")) {
    return;
  }

  const res = await fetch(`${endpoint}?${usp.toString()}`, { signal }).catch(
    (e) => {
      if (e.name !== "AbortError") throw e;
    },
  );
  if (!res) return; // abort edilmiş olabilir
  if (res.status === 422) {
    if (window.showAlert) {
      window.showAlert("Lütfen önce marka seçiniz.", { variant: "warning", title: "Eksik Seçim" });
    } else {
      alert("Marka seçiniz");
    }
    return;
  }
  const data = res.ok ? await res.json() : [];
  const current = keepValue ? el.value : null;
  inst.clearStore();
  const map =
    mapFn ||
    ((r) => {
      // Support both object and plain string responses
      if (typeof r === "string") return { value: r, label: r };
      return {
        value: r.id ?? r.value ?? "",
        label: r.name || r.text || r.ad || r.adi || r.label || "",
      };
    });
  inst.setChoices(data.map(map), "value", "label", true);
  if (keepValue && current) inst.setChoiceByValue(current);
}

async function bindMarkaModel(markaSelectId, modelSelectId) {
  const markaEl = document.getElementById(markaSelectId);
  const modelEl = document.getElementById(modelSelectId);
  if (!markaEl || !modelEl) return;
  const modelInst =
    selects[modelSelectId] || makeSearchableSelect(modelEl, "Model seçiniz…");
  selects[modelSelectId] = modelInst;

  let aborter;
  async function updateModels() {
    const m = markaEl.value;
    if (aborter) aborter.abort();
    const parsed = Number.parseInt(m, 10);
    if (!m || Number.isNaN(parsed)) {
      modelInst.clearStore();
      modelInst.disable();
      return;
    }
    modelInst.enable();
    aborter = new AbortController();
    try {
      await fillChoices({
        endpoint: "/api/lookup/model",
        selectId: modelSelectId,
        params: { marka_id: parsed },
        placeholder: "Model seçiniz…",
        signal: aborter.signal,
      });
    } catch (e) {
      if (e.name !== "AbortError") console.error(e);
    }
  }
  markaEl.addEventListener("change", updateModels);
  await updateModels();
}

function debounce(fn, d = 300) {
  let t;
  return (...a) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...a), d);
  };
}
function enableRemoteSearch(
  selectId,
  endpoint,
  extraParamsFn = () => ({}),
  mapFn,
) {
  const inst = selects[selectId];
  if (!inst) return;
  const input = inst.input?.element;
  if (!input) return;
  input.addEventListener(
    "input",
    debounce(async () => {
      const q = input.value.trim();
      const extras = extraParamsFn ? extraParamsFn() : {};
      if (extras === false) return;
      const params = { q, ...(extras || {}) };
      if (params.__skip) {
        return;
      }
      delete params.__skip;
      await fillChoices({
        endpoint,
        selectId,
        params,
        keepValue: false,
        mapFn,
      });
    }, 300),
  );
}

document.addEventListener("DOMContentLoaded", () => {
  if (!window.SKIP_SELECT_ENHANCE) {
    document.querySelectorAll("select").forEach((el) => {
      if (el.dataset.noSearch !== undefined) return;
      const inst = makeSearchableSelect(el);
      if (el.id) selects[el.id] = inst;
    });
  }
});

window._selects = {
  fillChoices,
  bindMarkaModel,
  enableRemoteSearch,
  makeSearchableSelect,
};
