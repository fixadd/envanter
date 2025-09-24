// static/js/refdata.js

// Basit fetch yardımcıları
async function apiGet(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

async function apiPost(url, body) {
  const r = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

async function apiPut(url, body) {
  const r = await fetch(url, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

async function apiDelete(url) {
  const r = await fetch(url, { method: "DELETE" });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

// /api/ref/{entity} —> kendi tablosuna yaz
async function addRef(entity, name, brandId = null) {
  const payload = { name: (name || "").trim() };
  if (!payload.name) throw new Error("İsim boş olamaz.");
  if (entity === "model") {
    if (!brandId) throw new Error("Model eklemek için marka seçin.");
    payload.brand_id = parseInt(brandId, 10);
  }
  return apiPost(`/api/ref/${entity}`, payload);
}

// /api/lookup/{entity} —> tablodan oku
async function fetchList(entity, extraParams = {}) {
  const usp = new URLSearchParams(extraParams);
  return apiGet(`/api/lookup/${entity}?${usp.toString()}`);
}

// Liste render
function renderList(containerEl, rows) {
  containerEl.innerHTML =
    rows?.length
      ? rows
          .map(
            (r) =>
              `<li class="list-group-item d-flex justify-content-between align-items-center gap-2">
               <span class="flex-grow-1">${r.name ?? r.ad ?? r.adi ?? r.text ?? ""}</span>
               <div class="btn-group btn-group-sm">
                 <button class="btn btn-outline-secondary ref-edit" data-id="${r.id}">Düzenle</button>
                 <button class="btn btn-danger ref-delete" data-id="${r.id}">Sil</button>
               </div>
             </li>`,
          )
          .join("")
      : '<li class="list-group-item text-muted">Kayıt yok</li>';
}

// Marka select'ini doldur (model kartı için)
async function fillBrandSelect(selectEl) {
  const rows = await fetchList("marka");
  const opts = ['<option value="">Marka seçiniz…</option>'].concat(
    rows.map(
      (r) =>
        `<option value="${r.id}">${r.name ?? r.ad ?? r.adi ?? r.text}</option>`,
    ),
  );
  selectEl.innerHTML = opts.join("");

  // Choices.js ile aramalı hale getir
  if (window.Choices) {
    if (!selectEl._choicesInstance) {
      selectEl._choicesInstance = new Choices(selectEl, {
        searchEnabled: true,
        placeholder: true,
        placeholderValue: "Marka seçiniz…",
        shouldSort: true,
        itemSelectText: "",
        noResultsText: "Sonuç yok",
        noChoicesText: "Seçenek yok",
        allowHTML: false,
      });
    } else {
      const inst = selectEl._choicesInstance;
      inst.clearStore();
      inst.setChoices(
        rows.map((r) => ({
          value: r.id,
          label: r.name ?? r.ad ?? r.adi ?? r.text,
        })),
        "value",
        "label",
        true,
      );
    }
  }
}

async function refreshCard(card) {
  const entity = card.dataset.entity;
  const listEl = card.querySelector(".ref-list");
  if (!listEl) return;

  if (entity === "model") {
    const brandSel = card.querySelector(".ref-brand");
    const brandId = brandSel?.value ? brandSel.value : "";
    if (!brandId) {
      renderList(listEl, []); // Marka seçilmeden model listesi gösterilmesin
      return;
    }
    const rows = await fetchList("model", { marka_id: brandId });
    renderList(listEl, rows);
    return;
  }

  const rows = await fetchList(entity);
  renderList(listEl, rows);
}

function bindCard(card) {
  const entity = card.dataset.entity;
  const input = card.querySelector(".ref-input");
  const addBtn = card.querySelector(".ref-add");
  const listEl = card.querySelector(".ref-list");

  if (!addBtn) return;

  if (input && listEl) {
    // Mevcut detaylı kart yapısı

    // Model kartı: önce Marka select’ini doldur ve değişimde listeyi yenile
    if (entity === "model") {
      const brandSel = card.querySelector(".ref-brand");
      if (brandSel) {
        fillBrandSelect(brandSel)
          .then(() => refreshCard(card))
          .catch(console.error);
        brandSel.addEventListener("change", () => refreshCard(card));
      }
    }

    // Ekle
    addBtn.addEventListener("click", async () => {
      const name = (input.value || "").trim();
      if (!name) {
        input.focus();
        return;
      }

      try {
        if (entity === "model") {
          const brandSel = card.querySelector(".ref-brand");
          const brandId =
            brandSel?.value ? parseInt(brandSel.value, 10) : null;
          if (!brandId) {
            alert("Lütfen önce marka seçin.");
            return;
          }
          await addRef("model", name, brandId);
        } else {
          await addRef(entity, name);
        }
        input.value = "";
        await refreshCard(card);
      } catch (e) {
        alert("Kaydedilemedi: " + (e?.message || e));
      }
    });

    // Enter ile ekleme
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") addBtn.click();
    });

    if (listEl) {
      listEl.addEventListener("click", async (e) => {
        const editBtn = e.target.closest(".ref-edit");
        if (editBtn) {
          const id = editBtn.dataset.id;
          if (!id) return;
          const rowEl = editBtn.closest("li");
          const currentText = rowEl
            ? rowEl.querySelector("span")?.textContent?.trim()
            : "";
          const name = prompt("Yeni adı girin", currentText || "");
          if (!name) return;
          try {
            await apiPut(`/api/ref/${entity}/${id}`, { name });
            await refreshCard(card);
          } catch (err) {
            alert("Güncellenemedi: " + (err?.message || err));
          }
          return;
        }

        const btn = e.target.closest(".ref-delete");
        if (!btn) return;
        const id = btn.dataset.id;
        if (!id) return;
        try {
          await apiDelete(`/api/ref/${entity}/${id}`);
          await refreshCard(card);
        } catch (err) {
          alert("Silinemedi: " + (err?.message || err));
        }
      });
    }
  } else {
    // Sade satır: prompt ile değer al
    addBtn.addEventListener("click", async () => {
      const name = prompt("Yeni değer girin");
      if (!name) return;
      try {
        await addRef(entity, name);
        alert("Kaydedildi");
      } catch (e) {
        alert("Kaydedilemedi: " + (e?.message || e));
      }
    });
  }
}

// Sayfa giriş noktası
function initRefAdmin() {
  document.querySelectorAll(".ref-card[data-entity]").forEach((card) => {
    bindCard(card);
    refreshCard(card).catch(console.error);
  });

  const toggleBtn = document.getElementById("toggleRefLists");
  if (toggleBtn) {
    toggleBtn.addEventListener("click", () => {
      document.querySelectorAll(".ref-list").forEach((list) => {
        list.classList.toggle("d-none");
      });
    });
  }
}

window.initRefAdmin = initRefAdmin;
