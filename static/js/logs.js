// Simple search & action filtering for logs page
(function () {
  function setupFilter(inputId, tableSelector, actionSelectId) {
    const input = document.getElementById(inputId);
    const actionSel = document.getElementById(actionSelectId);
    if (!input && !actionSel) return;
    const rows = document.querySelectorAll(`${tableSelector} tbody tr`);

    function apply() {
      const q = input ? input.value.toLowerCase() : "";
      const act = actionSel ? actionSel.value : "";
      rows.forEach((row) => {
        const text = row.textContent.toLowerCase();
        const actionCell = row.querySelector('td[data-action]');
        const action = actionCell ? actionCell.getAttribute('data-action') : "";
        const matchText = !q || text.includes(q);
        const matchAction = !act || action === act;
        row.classList.toggle('d-none', !(matchText && matchAction));
      });
    }

    if (input) input.addEventListener('input', apply);
    if (actionSel) actionSel.addEventListener('change', apply);
  }

  document.addEventListener('DOMContentLoaded', () => {
    setupFilter('searchUserLogs', '#userlogs', 'filterUserAction');
    setupFilter('searchInventoryLogs', '#inventorylogs', 'filterInventoryAction');
  });
})();
