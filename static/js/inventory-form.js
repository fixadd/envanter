(function (global) {
  const optionCache = new Map();

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function normalisePickerItems(data) {
    if (!Array.isArray(data)) return [];
    return data
      .map((item) => {
        if (typeof item === "string") {
          const value = item.trim();
          if (!value) return null;
          return { id: value, text: value };
        }
        if (!item || typeof item !== "object") return null;
        const text =
          item.text ||
          item.name ||
          item.label ||
          item.value ||
          item.ad ||
          item.adi ||
          "";
        const id = item.id ?? text;
        if (!text) return null;
        return { id, text };
      })
      .filter(Boolean);
  }

  async function fetchPickerItems(url) {
    const cacheKey = url;
    if (optionCache.has(cacheKey)) {
      return optionCache.get(cacheKey);
    }
    try {
      const res = await fetch(url, { headers: { Accept: "application/json" } });
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
      const payload = await res.json();
      const items = normalisePickerItems(payload);
      optionCache.set(cacheKey, items);
      return items;
    } catch (error) {
      console.warn("fetchPickerItems failed", { url, error });
      optionCache.set(cacheKey, []);
      return [];
    }
  }

  function ensureChoices(select) {
    if (!select) return null;
    if (select._choices) return select._choices;
    if (
      global._selects &&
      typeof global._selects.makeSearchableSelect === "function"
    ) {
      const inst = global._selects.makeSearchableSelect(select);
      return inst;
    }
    return null;
  }

  async function loadOptions(select, url, options = {}) {
    if (!select) return [];
    const { placeholder = "Seçiniz...", fallbackUrl } = options;
    let items = await fetchPickerItems(url);
    if (!items.length && fallbackUrl) {
      items = await fetchPickerItems(fallbackUrl);
    }

    const inst = ensureChoices(select);

    if (inst) {
      inst.clearStore();
      const data = [];
      if (placeholder !== null) {
        data.push({
          value: "",
          label: placeholder,
          disabled: false,
          selected: false,
        });
      }
      items.forEach((item) => {
        data.push({
          value: item.text,
          label: item.text,
          customProperties: { dataId: item.id ?? "" },
        });
      });
      inst.setChoices(data, "value", "label", true);
      inst.setChoiceByValue("");
      // Choices doesn't preserve customProperties on the native options, so sync manually
      const nativeOptions = Array.from(select.options);
      nativeOptions.forEach((option, index) => {
        if (index === 0 && placeholder !== null) {
          delete option.dataset.id;
          return;
        }
        const item = items[index - (placeholder !== null ? 1 : 0)];
        if (!item) return;
        if (item.id !== undefined && item.id !== null && item.id !== "") {
          option.dataset.id = item.id;
        } else {
          delete option.dataset.id;
        }
      });
    } else {
      const placeholderOption =
        placeholder === null
          ? ""
          : `<option value=\"\">${escapeHtml(placeholder)}</option>`;
      const optionsHtml = items
        .map((item) => {
          const dataId =
            item.id !== undefined && item.id !== null
              ? ` data-id=\"${escapeHtml(item.id)}\"`
              : "";
          return `<option value=\"${escapeHtml(item.text)}\"${dataId}>${escapeHtml(
            item.text,
          )}</option>`;
        })
        .join("");
      select.innerHTML = placeholderOption + optionsHtml;
    }

    return items;
  }

  function setSelectedByText(select, text) {
    if (!select) return null;
    const target = (text ?? "").trim();
    if (!target) {
      select.value = "";
      if (select._choices) {
        select._choices.setChoiceByValue("");
      }
      return null;
    }
    const options = Array.from(select.options);
    let match = options.find(
      (option) => (option.value || "").trim() === target,
    );
    if (!match) {
      match = options.find(
        (option) =>
          (option.textContent || "").trim().toLowerCase() ===
          target.toLowerCase(),
      );
    }
    if (match) {
      select.value = match.value;
      if (select._choices) {
        select._choices.setChoiceByValue(match.value);
      } else {
        options.forEach((option) => {
          option.selected = option === match;
        });
      }
      return match;
    }

    const newOption = new Option(target, target, true, true);
    select.add(newOption);
    if (select._choices) {
      select._choices.setChoices(
        [
          {
            value: target,
            label: target,
            selected: true,
          },
        ],
        "value",
        "label",
        false,
      );
    }
    return newOption;
  }

  function getDatasetId(option) {
    if (!option) return "";
    return option.dataset?.id || option.getAttribute("data-id") || "";
  }

  function disableSelect(select, placeholderText) {
    if (!select) return;
    if (placeholderText !== undefined) {
      const html = `<option value=\"\">${escapeHtml(placeholderText)}</option>`;
      if (select._choices) {
        select._choices.clearStore();
        select._choices.setChoices(
          [
            {
              value: "",
              label: placeholderText,
              disabled: false,
              selected: true,
            },
          ],
          "value",
          "label",
          true,
        );
      } else {
        select.innerHTML = html;
      }
    }
    select.value = "";
    if (select._choices) {
      select._choices.setChoiceByValue("");
      select._choices.disable();
    }
    select.disabled = true;
  }

  function enableSelect(select) {
    if (!select) return;
    select.disabled = false;
    if (select._choices) {
      select._choices.enable();
    }
  }

  async function initializeInventoryForm(config = {}) {
    const mode = config.mode || "create";
    const selectors = {
      fabrika: mode === "edit" ? "edit_fabrika" : "fabrika",
      departman: mode === "edit" ? "edit_departman" : "departman",
      donanim_tipi: mode === "edit" ? "edit_donanim_tipi" : "donanim_tipi",
      sorumlu_personel:
        mode === "edit" ? "edit_sorumlu_personel" : "sorumlu_personel",
      marka: mode === "edit" ? "edit_marka" : "marka",
      model: mode === "edit" ? "edit_model" : "model",
      kullanim_alani: mode === "edit" ? "edit_kullanim_alani" : null,
      ...config.selectors,
    };

    const values = config.values || {};

    const fabrikaSelect = selectors.fabrika
      ? document.getElementById(selectors.fabrika)
      : null;
    const departmanSelect = selectors.departman
      ? document.getElementById(selectors.departman)
      : null;
    const donanimSelect = selectors.donanim_tipi
      ? document.getElementById(selectors.donanim_tipi)
      : null;
    const sorumluSelect = selectors.sorumlu_personel
      ? document.getElementById(selectors.sorumlu_personel)
      : null;
    const markaSelect = selectors.marka
      ? document.getElementById(selectors.marka)
      : null;
    const modelSelect = selectors.model
      ? document.getElementById(selectors.model)
      : null;
    const kullanimSelect = selectors.kullanim_alani
      ? document.getElementById(selectors.kullanim_alani)
      : null;

    if (modelSelect && !modelSelect.options.length) {
      disableSelect(modelSelect, "Önce marka seçiniz...");
    }

    await loadOptions(fabrikaSelect, "/api/picker/fabrika");
    setSelectedByText(fabrikaSelect, values.fabrika);

    await loadOptions(departmanSelect, "/api/picker/kullanim_alani", {
      fallbackUrl: "/inventory/assign/sources?type=departman",
    });
    setSelectedByText(departmanSelect, values.departman);

    await loadOptions(donanimSelect, "/api/picker/donanim_tipi");
    setSelectedByText(donanimSelect, values.donanim_tipi || values.donanim);

    await loadOptions(sorumluSelect, "/api/picker/kullanici");
    setSelectedByText(sorumluSelect, values.sorumlu_personel || values.sorumlu);

    if (global._selects && selectors.sorumlu_personel) {
      global._selects.enableRemoteSearch(
        selectors.sorumlu_personel,
        "/api/picker/kullanici",
        () => ({}),
        (r) => ({ value: r.text, label: r.text }),
      );
    }

    if (kullanimSelect) {
      await loadOptions(kullanimSelect, "/api/picker/kullanim_alani");
      setSelectedByText(
        kullanimSelect,
        values.kullanim_alani || values.kullanim,
      );
    }

    const brandItems = await loadOptions(markaSelect, "/api/picker/marka");
    setSelectedByText(markaSelect, values.marka);

    function findBrandId() {
      if (!markaSelect) return "";
      const option = markaSelect.options[markaSelect.selectedIndex];
      let brandId = getDatasetId(option);
      if (!brandId && markaSelect.value) {
        const match = brandItems.find(
          (item) => item.text === markaSelect.value,
        );
        if (match) brandId = match.id;
      }
      return brandId;
    }

    async function populateModels(brandId, selectedModelText) {
      if (!modelSelect) return;
      if (!brandId) {
        disableSelect(modelSelect, "Önce marka seçiniz...");
        return;
      }
      enableSelect(modelSelect);
      const query = new URLSearchParams({ marka_id: brandId });
      await loadOptions(modelSelect, `/api/picker/model?${query.toString()}`);
      setSelectedByText(modelSelect, selectedModelText);
    }

    await populateModels(findBrandId(), values.model);

    if (markaSelect) {
      markaSelect.addEventListener("change", async () => {
        const brandId = findBrandId();
        await populateModels(brandId, "");
      });
    }
  }

  global.inventoryForm = {
    initializeInventoryForm,
    loadOptions,
    fetchPickerItems,
    normalisePickerItems,
    setSelectedByText,
  };
})(window);
