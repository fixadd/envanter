(function () {
  function go(url) {
    window.location.href = url;
  }

  // Detay (göz)
  document.addEventListener("click", function (e) {
    const btn = e.target.closest(".js-view");
    if (!btn) return;
    const { entity, id } = btn.dataset;
    if (!entity || !id) return;
    go(`/${entity}/${id}`);
  });

  // İşlemler select
  document.addEventListener("change", function (e) {
    const sel = e.target.closest(".js-actions");
    if (!sel) return;
    const { entity, id } = sel.dataset;
    const val = sel.value;
    if (!entity || !id || !val) return;

    // Tek tip URL şeması:
    // assign -> /{entity}/{id}/assign
    // edit   -> /{entity}/{id}/edit
    // stock  -> /{entity}/{id}/stock
    // scrap  -> /{entity}/{id}/scrap
    if (val === "fault" && window.Faults) {
      window.Faults.openMarkModal(entity, {
        entityId: Number.isNaN(Number(id)) ? id : Number(id),
        entityKey: sel.dataset.entityKey || "",
        deviceNo: sel.dataset.device || "",
        title: sel.dataset.title || "",
      });
      sel.value = "";
      return;
    }
    if (val === "repair" && window.Faults) {
      window.Faults.openRepairModal(entity, {
        entityId: Number.isNaN(Number(id)) ? id : Number(id),
        entityKey: sel.dataset.entityKey || "",
        deviceNo: sel.dataset.device || "",
      });
      sel.value = "";
      return;
    }

    const map = {
      assign: "assign",
      edit: "edit",
      stock: "stock",
      scrap: "scrap",
    };
    if (map[val]) {
      const url = `/${entity}/${id}/${map[val]}`;
      if (val === "edit" && window.openModal) {
        const selectedOption = sel.options[sel.selectedIndex];
        const title = (
          sel.dataset.editModalTitle ||
          selectedOption?.text ||
          ""
        ).trim();
        const size = sel.dataset.editModalSize || "lg";
        openModal(`${url}?modal=1`, title, { size });
      } else {
        go(url);
      }
    }
    sel.value = "";
  });

  // Eğer tüm satır tıklanıyorsa iptal etmek istersen:
  document.addEventListener("click", function (e) {
    const rowLink = e.target.closest(".js-row-link");
    if (
      rowLink &&
      !e.target.closest(".js-view") &&
      !e.target.closest(".js-actions")
    ) {
      e.stopPropagation();
      e.preventDefault();
    }
  });
})();
