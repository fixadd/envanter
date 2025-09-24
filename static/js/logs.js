// Simple search & action filtering for logs page
(function () {
  function setupFilter(inputId, tableSelector, selectId, dataAttr) {
    const input = document.getElementById(inputId);
    const select = document.getElementById(selectId);
    if (!input && !select) return;
    const rows = document.querySelectorAll(`${tableSelector} tbody tr`);

    function apply() {
      const q = input ? input.value.toLowerCase() : "";
      const selVal = select ? select.value : "";
      rows.forEach((row) => {
        const text = row.textContent.toLowerCase();
        let attrVal = "";
        if (select && dataAttr) {
          const cell = row.querySelector(`[${dataAttr}]`);
          attrVal = cell ? cell.getAttribute(dataAttr) : "";
        }
        const matchText = !q || text.includes(q);
        const matchSelect = !selVal || attrVal === selVal;
        row.classList.toggle("d-none", !(matchText && matchSelect));
      });
    }

    if (input) input.addEventListener("input", apply);
    if (select) select.addEventListener("change", apply);
  }

  document.addEventListener("DOMContentLoaded", () => {
    setupFilter("searchUserLogs", "#userlogs", "filterUserName", "data-user");
    setupFilter(
      "searchInventoryLogs",
      "#inventorylogs",
      "filterInventoryNo",
      "data-inv",
    );
  });
})();
