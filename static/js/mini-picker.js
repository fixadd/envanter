(function () {
  // ENTITY eşlemesi: endpoint + opsiyonel bağımlılık (dependsOn)
  const MAP = {
    kullanim_alani: {
      title: "KULLANIM ALANI",
      endpoint: "/api/picker/kullanim_alani",
    },
    lisans_adi: { title: "LİSANS ADI", endpoint: "/api/picker/lisans_adi" },
    fabrika: { title: "FABRİKA", endpoint: "/api/picker/fabrika" },
    donanim_tipi: {
      title: "DONANIM TİPİ",
      endpoint: "/api/picker/donanim_tipi",
    },
    marka: { title: "MARKA", endpoint: "/api/picker/marka" },
    departman: { title: "DEPARTMAN", endpoint: "/api/picker/kullanim_alani" }, // ürün ekledeki kullanım alanı
    sorumlu_personel: {
      title: "SORUMLU PERSONEL",
      endpoint: "/api/picker/kullanici",
      allowAdd: false,
      allowDelete: false,
    },
    bilgi_kategori: {
      title: "BİLGİ KATEGORİSİ",
      endpoint: "/api/picker/bilgi_kategori",
    },

    // MODEL marka'ya bağlı: GET'te ?marka_id=.. gönder, POST'ta parent_id olarak geç
    model: {
      title: "MODEL",
      endpoint: "/api/picker/model",
      dependsOn: { hiddenId: "marka", param: "marka_id" },
    },
  };

  const $m = document.getElementById("picker-modal");
  const $title = document.getElementById("picker-title");
  const $search = document.getElementById("picker-search");
  const $add = document.getElementById("picker-add");
  const $list = document.getElementById("picker-list");
  const $close = document.querySelector(".picker-close");
  const $cancel = document.getElementById("picker-cancel");

  if (!$m || !$title || !$search || !$add || !$list || !$close || !$cancel) {
    console.warn("[mini-picker] Modal öğeleri bulunamadı.");
    return;
  }

  // Aktif seçim bağlamı
  let current = {
    entity: null,
    endpoint: null,
    hidden: null,
    display: null,
    chip: null,
    extra: {},
    parentId: null,
    allowAdd: true,
    allowDelete: true,
    storeAs: "id",
    dependsOnId: null,
    parentParam: null,
  };

  function getDependencyParams(entity, options) {
    const meta = MAP[entity];
    const depMeta = meta && meta.dependsOn;
    const dependsOnId =
      (options && options.parentOverride) || (depMeta && depMeta.hiddenId);
    const paramName =
      (options && options.parentParam) || (depMeta && depMeta.param);
    if (!dependsOnId) {
      return {
        extra: {},
        parentId: null,
        dependsOnId: null,
        paramName,
      };
    }
    const depHidden = document.getElementById(dependsOnId);
    if (!depHidden || !depHidden.value) {
      return { extra: null, parentId: null, dependsOnId, paramName };
    }
    const parentValue = depHidden.value;
    const extra = paramName ? { [paramName]: parentValue } : {};
    return {
      extra,
      parentId: parentValue,
      dependsOnId,
      paramName,
    };
  }

  function resolveStoreStrategy(hiddenEl, override) {
    const candidate = override || (hiddenEl && hiddenEl.dataset.store);
    return candidate === "text" ? "text" : "id";
  }

  function openModal(entity, hiddenEl, displayEl, chipEl, options = {}) {
    const meta = MAP[entity] || {
      title: entity.toUpperCase(),
      endpoint: `/api/picker/${entity}`,
    };

    const dep = getDependencyParams(entity, options);
    if (dep.extra === null) {
      alert("Önce bağlı alanı seçin (örn. önce MARKA seçin).");
      return;
    }

    current = {
      entity,
      endpoint: meta.endpoint,
      hidden: hiddenEl || null,
      display: displayEl || null,
      chip: chipEl || null,
      extra: dep.extra || {},
      parentId: dep.parentId || null,
      allowAdd: meta.allowAdd !== false,
      allowDelete: meta.allowDelete !== false,
      storeAs: resolveStoreStrategy(hiddenEl, options.storeAs),
      dependsOnId: dep.dependsOnId || null,
      parentParam: dep.paramName || null,
    };

    $title.textContent = `${meta.title} seçin`;
    $search.value = "";
    $list.innerHTML = "";
    $m.hidden = false;
    $m.style.display = "flex";

    $add.style.display = current.allowAdd ? "" : "none";
    updateAddState();
    load("");
    $search.focus();
  }

  function updateAddState() {
    $add.disabled = !current.allowAdd || $search.value.trim().length === 0;
  }

  async function load(q) {
    const url = new URL(current.endpoint, location.origin);
    if (q) url.searchParams.set("q", q);
    Object.entries(current.extra || {}).forEach(([k, v]) =>
      url.searchParams.set(k, v),
    );
    const res = await fetch(url, { headers: { Accept: "application/json" } });
    const data = (await res.json()) || [];
    render(data);
  }

  function render(items) {
    if (!items.length) {
      $list.innerHTML = '<div class="picker-empty">Kayıt bulunamadı.</div>';
      return;
    }
    $list.innerHTML = items
      .map(
        (r) => `
      <div class="picker-row" data-id="${r.id}" data-text="${r.text}">
        <p class="picker-name">${r.text}</p>
        <div class="picker-actions">
          <button type="button" class="picker-select">Seç</button>
          ${current.allowDelete ? '<button type="button" class="picker-del" title="Sil">–</button>' : ""}
        </div>
      </div>`,
      )
      .join("");
  }

  function closeModal() {
    $m.style.display = "none";
    $m.hidden = true;
    $list.innerHTML = "";
    $search.value = "";
    current = {
      entity: null,
      endpoint: null,
      hidden: null,
      display: null,
      chip: null,
      extra: {},
      parentId: null,
      allowAdd: true,
      allowDelete: true,
      storeAs: "id",
      dependsOnId: null,
      parentParam: null,
    };
  }

  function dispatchChange(detail) {
    if (current.hidden) {
      current.hidden.dispatchEvent(
        new CustomEvent("picker:change", { bubbles: true, detail }),
      );
    }
    if (current.display) {
      current.display.dispatchEvent(
        new CustomEvent("picker:change", { bubbles: true, detail }),
      );
    }
  }

  // Arama + Ekle
  $search.addEventListener("input", (e) => {
    updateAddState();
    load(e.target.value.trim());
  });
  $search.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !$add.disabled) {
      e.preventDefault();
      addItem();
    }
  });

  $add.addEventListener("click", addItem);

  async function addItem() {
    if (!current.allowAdd) return;
    const text = $search.value.trim();
    if (!text) return;

    // POST body: { text, parent_id? }
    const body = { text };
    if (current.parentId) body.parent_id = current.parentId;

    const res = await fetch(current.endpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify(body),
    });

    if (res.ok) {
      const created = await res.json(); // {id, text}
      // otomatik seç
      const storedValue =
        current.storeAs === "text" ? created.text : created.id;
      if (current.hidden) {
        current.hidden.value = storedValue;
        current.hidden.dataset.id = created.id;
        current.hidden.dataset.text = created.text;
      }
      if (current.display) current.display.value = created.text;
      if (current.chip) {
        current.chip.textContent = created.text;
        current.chip.classList.remove("d-none");
      }
      dispatchChange({
        id: created.id,
        text: created.text,
        entity: current.entity,
        storedAs: current.storeAs,
      });
      closeModal();
    } else if (res.status === 409) {
      alert("Bu kayıt zaten var.");
    } else {
      alert("Ekleme başarısız!");
    }
  }

  // Liste seçim/silme
  $list.addEventListener("click", async (e) => {
    const row = e.target.closest(".picker-row");
    if (!row) return;

    if (e.target.classList.contains("picker-select")) {
      const detail = {
        id: row.dataset.id || "",
        text: row.dataset.text || "",
        entity: current.entity,
        storedAs: current.storeAs,
      };
      const storedValue = current.storeAs === "text" ? detail.text : detail.id;
      if (current.hidden) {
        current.hidden.value = storedValue || "";
        current.hidden.dataset.id = detail.id;
        current.hidden.dataset.text = detail.text;
      }
      if (current.display) current.display.value = detail.text;
      if (current.chip) {
        current.chip.textContent = detail.text;
        current.chip.classList.remove("d-none");
      }
      dispatchChange(detail);
      closeModal();
    } else if (e.target.classList.contains("picker-del")) {
      if (!current.allowDelete) return;
      if (!confirm("Silinsin mi?")) return;
      const url = `${current.endpoint}/${encodeURIComponent(row.dataset.id)}`;
      const delRes = await fetch(url, { method: "DELETE" });
      if (delRes.ok) {
        row.remove();
        if (!$list.children.length)
          $list.innerHTML = '<div class="picker-empty">Kayıt bulunamadı.</div>';
      } else {
        alert("Silme başarısız!");
      }
    }
  });

  $close.onclick = $cancel.onclick = closeModal;
  $m.addEventListener("click", (e) => {
    if (e.target === $m) closeModal();
  });

  // ≡ butonlarını bağla (admin/kullanıcı fark etmez; kapsayıcı id’ni değiştir)
  document
    .querySelectorAll(
      "#admin-urun-ekle .pick-btn, #urun-ekle .pick-btn, .inventory-edit-modal .pick-btn",
    )
    .forEach((btn) => {
      btn.addEventListener("click", () => {
        const entity = btn.dataset.entity;
        if (!entity) return;
        const hiddenId = btn.dataset.target || entity;
        const displayId = btn.dataset.display || null;
        const chipKey = btn.dataset.chip || hiddenId || entity;
        const hidden = hiddenId ? document.getElementById(hiddenId) : null;
        const display = displayId ? document.getElementById(displayId) : null;
        const chip = chipKey
          ? document.querySelector(`.pick-chip[data-for="${chipKey}"]`)
          : null;
        openModal(entity, hidden, display, chip, {
          parentOverride: btn.dataset.parent || null,
          parentParam: btn.dataset.parentParam || null,
          storeAs: btn.dataset.store || null,
        });
      });
    });

  // Sayfaya sonradan eklenen lookup-display inputları için tıklama delegasyonu
  document.addEventListener("click", (e) => {
    const input = e.target.closest("input.lookup-display");
    if (!input) return;
    const entity =
      input.dataset.entity ||
      (input.id ? input.id.replace("_display", "") : null);
    if (!entity) return;
    const hiddenId = input.dataset.target || entity;
    const chipKey = input.dataset.chip || hiddenId || entity;
    const hidden = hiddenId ? document.getElementById(hiddenId) : null;
    const chip = chipKey
      ? document.querySelector(`.pick-chip[data-for="${chipKey}"]`)
      : null;
    openModal(entity, hidden, input, chip, {
      parentOverride: input.dataset.parent || null,
      parentParam: input.dataset.parentParam || null,
      storeAs: input.dataset.store || null,
    });
  });

  // Dışarıdan çağrılabilsin
  window.__openPickerModal = openModal;
})();
