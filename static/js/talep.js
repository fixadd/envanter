// /static/js/talep.js
(function () {
  const modal = document.getElementById("talepModal");
  const tableBody = () => document.querySelector("#rowsTable tbody");
  const addRowBtn = () => document.getElementById("btnAddRow");

  // Basit cache
  const cache = {};

  async function getLookup(name) {
    if (cache[name]) return cache[name];
    const r = await fetch(`/api/lookup/${name}`);
    if (!r.ok) return [];
    const data = await r.json(); // [{id, adi}]
    cache[name] = data;
    return data;
  }

  async function getModelsByBrand(brandId) {
    const key = `model_${brandId}`;
    if (cache[key]) return cache[key];
    const r = await fetch(`/api/lookup/model?marka_id=${encodeURIComponent(brandId)}`);
    if (!r.ok) return [];
    const data = await r.json(); // [{id, adi}]
    cache[key] = data;
    return data;
  }

  function optionHtml(arr, placeholder = "Seçiniz…") {
    const head = `<option value="">${placeholder}</option>`;
    if (!Array.isArray(arr) || !arr.length) return head + `<option value="">Seçenek yok</option>`;
    return head + arr.map(x => `<option value="${x.id}">${x.adi}</option>`).join("");
  }

  function rowTemplate() {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>
        <select class="form-select sel-donanim" required></select>
      </td>
      <td>
        <input type="number" min="1" value="1" class="form-control inp-miktar" required>
      </td>
      <td>
        <select class="form-select sel-marka"></select>
      </td>
      <td>
        <select class="form-select sel-model" disabled>
          <option value="">Seçiniz…</option>
        </select>
      </td>
      <td>
        <input type="text" class="form-control inp-aciklama" placeholder="Açıklama">
      </td>
      <td class="text-end">
        <button type="button" class="btn btn-outline-danger btn-sm btn-remove">Sil</button>
      </td>
    `;
    return tr;
  }

  async function fillStaticLookups(tr) {
    const donanimSel = tr.querySelector(".sel-donanim");
    const markaSel = tr.querySelector(".sel-marka");
    const modelSel = tr.querySelector(".sel-model");

    const [donanimlar, markalar] = await Promise.all([
      getLookup("donanim_tipi"),
      getLookup("marka"),
    ]);

    donanimSel.innerHTML = optionHtml(donanimlar);
    markaSel.innerHTML = optionHtml(markalar);
    modelSel.innerHTML = `<option value="">Seçiniz…</option>`;
    modelSel.disabled = true;
  }

  async function onBrandChange(tr, brandId) {
    const modelSel = tr.querySelector(".sel-model");
    if (!brandId) {
      modelSel.innerHTML = `<option value="">Seçiniz…</option>`;
      modelSel.disabled = true;
      return;
    }
    modelSel.disabled = true;
    modelSel.innerHTML = `<option>Yükleniyor…</option>`;
    const modeller = await getModelsByBrand(brandId);
    modelSel.innerHTML = optionHtml(modeller);
    modelSel.disabled = !modeller.length;
  }

  async function addRow() {
    const tr = rowTemplate();
    tableBody().appendChild(tr);
    await fillStaticLookups(tr);

    // Eventler
    tr.querySelector(".sel-marka").addEventListener("change", (e) => {
      onBrandChange(tr, e.target.value);
    });
    tr.querySelector(".btn-remove").addEventListener("click", () => {
      tr.remove();
    });
  }

  // Modal açıldığında ilk satırı garanti ekle
  modal?.addEventListener("shown.bs.modal", async () => {
    if (!tableBody().children.length) {
      await addRow();
    }
  });

  // Satır ekle butonu
  document.addEventListener("click", async (e) => {
    if (e.target?.id === "btnAddRow") {
      await addRow();
    }
  });

  // Form submit
  document.addEventListener("submit", async (e) => {
    const form = e.target;
    if (form?.id !== "talepForm") return;
    e.preventDefault();

    const ifs_no = document.getElementById("ifs_no").value.trim();
    const lines = [];
    tableBody().querySelectorAll("tr").forEach((tr) => {
      const donanim_tipi_id = Number(tr.querySelector(".sel-donanim").value || 0);
      const miktar = Number(tr.querySelector(".inp-miktar").value || 0);
      const marka_id = Number(tr.querySelector(".sel-marka").value || 0);
      const model_id = Number(tr.querySelector(".sel-model").value || 0);
      const aciklama = tr.querySelector(".inp-aciklama").value.trim() || null;

      if (donanim_tipi_id && miktar > 0) {
        lines.push({ donanim_tipi_id, miktar, marka_id, model_id, aciklama });
      }
    });

    if (!lines.length) {
      alert("En az bir satır doldurun.");
      return;
    }

    try {
      const r = await fetch("/api/talep/ekle", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ifs_no, lines }),
      });
      if (!r.ok) throw new Error(await r.text());
      bootstrap.Modal.getInstance(modal)?.hide();
      window.location.reload();
    } catch (err) {
      console.error(err);
      alert("Talep kaydedilemedi.");
    }
  });
})();

