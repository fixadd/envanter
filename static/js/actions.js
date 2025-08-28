(function () {
  function go(url) { window.location.href = url; }

  // Detay (göz)
  document.addEventListener('click', function (e) {
    const btn = e.target.closest('.js-view');
    if (!btn) return;
    const { entity, id } = btn.dataset;
    if (!entity || !id) return;
    go(`/${entity}/${id}`);
  });

  // İşlemler select
  document.addEventListener('change', function (e) {
    const sel = e.target.closest('.js-actions');
    if (!sel) return;
    const { entity, id } = sel.dataset;
    const val = sel.value;
    if (!entity || !id || !val) return;

    // Tek tip URL şeması:
    // assign -> /{entity}/{id}/assign
    // edit   -> /{entity}/{id}/edit
    // stock  -> /{entity}/{id}/stock
    // scrap  -> /{entity}/{id}/scrap
    const map = { assign: 'assign', edit: 'edit', stock: 'stock', scrap: 'scrap' };
    if (map[val]) go(`/${entity}/${id}/${map[val]}`);
    sel.value = '';
  });

  // Eğer tüm satır tıklanıyorsa iptal etmek istersen:
  document.addEventListener('click', function (e) {
    const rowLink = e.target.closest('.js-row-link');
    if (rowLink && !e.target.closest('.js-view') && !e.target.closest('.js-actions')) {
      e.stopPropagation();
      e.preventDefault();
    }
  });
})();

// Arama kapalı sadece seçmeli (Choices kullanıyorsan searchEnabled:false)
(function(){
  const initNoSearch = (selId) => {
    const el = document.getElementById(selId);
    if(!el) return;
    if (window.Choices) {
      new Choices(el, { searchEnabled:false, shouldSort:false, itemSelectText:'' });
    }
  };
  initNoSearch('licIslemSelect');
  initNoSearch('prnIslemSelect');
})();
