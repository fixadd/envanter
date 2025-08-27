(function(){
  const MAP = {
    kullanim_alani: { title: "KULLANIM ALANI", endpoint: "/api/picker/kullanim_alani" },
    lisans_adi:     { title: "LİSANS ADI",     endpoint: "/api/picker/lisans_adi"     },
    fabrika:        { title: "FABRİKA",        endpoint: "/api/picker/fabrika"        },
    donanim_tipi:   { title: "DONANIM TİPİ",   endpoint: "/api/picker/donanim_tipi"   },
    marka:          { title: "MARKA",          endpoint: "/api/picker/marka"          },
    model:          { title: "MODEL",          endpoint: "/api/picker/model",
                      dependsOn: { hiddenId: "marka", param: "marka_id" } },
  };

  const $m      = document.getElementById('picker-modal');
  const $title  = document.getElementById('picker-title');
  const $search = document.getElementById('picker-search');
  const $list   = document.getElementById('picker-list');
  const $close  = document.querySelector('.picker-close');
  const $cancel = document.getElementById('picker-cancel');

  let current = { entity:null, endpoint:null, hidden:null, chip:null, extra:{} };

  function getDependencyParams(entity){
    const meta = MAP[entity];
    if(!meta || !meta.dependsOn) return {};
    const dep = meta.dependsOn;
    const depHidden = document.getElementById(dep.hiddenId);
    if(!depHidden || !depHidden.value) return null;
    return { [dep.param]: depHidden.value };
  }

  function openModal(entity, hiddenEl, chipEl){
    const meta = MAP[entity] || { title: entity.toUpperCase(), endpoint: `/api/picker/${entity}` };
    const extraParams = getDependencyParams(entity);
    if(extraParams === null){
      alert("Önce MARKA seçin.");
      return;
    }
    current = { entity, endpoint: meta.endpoint, hidden: hiddenEl, chip: chipEl || null, extra: extraParams || {} };

    $title.textContent = `${meta.title} seçin`;
    $search.value = ''; $list.innerHTML = '';
    $m.hidden = false; $m.style.display = 'flex';
    load('');
    $search.focus();
  }

  async function load(q){
    const url = new URL(current.endpoint, location.origin);
    if(q) url.searchParams.set('q', q);
    Object.entries(current.extra || {}).forEach(([k,v]) => url.searchParams.set(k, v));

    const res = await fetch(url, { headers:{Accept:'application/json'} });
    const data = (await res.json()) || [];
    render(data);
  }

  function render(items){
    if(!items.length){ $list.innerHTML = `<div class="picker-empty">Kayıt bulunamadı.</div>`; return; }
    $list.innerHTML = items.map(r=>`
      <div class="picker-row" data-id="${r.id}" data-text="${r.text}">
        <p class="picker-name">${r.text}</p>
        <div class="picker-actions">
          <button type="button" class="picker-select">Seç</button>
          <button type="button" class="picker-del" title="Sil">–</button>
        </div>
      </div>
    `).join('');
  }

  function closeModal(){
    $m.style.display='none'; $m.hidden=true; $list.innerHTML=''; $search.value='';
    current = { entity:null, endpoint:null, hidden:null, chip:null, extra:{} };
  }

  $search.oninput = e => load(e.target.value.trim());
  $list.onclick = async e => {
    const row = e.target.closest('.picker-row'); if(!row) return;
    if(e.target.classList.contains('picker-select')){
      if(current.hidden) current.hidden.value = row.dataset.id;
      if(current.chip){ current.chip.textContent = row.dataset.text; current.chip.classList.remove('d-none'); }
      closeModal();
    }else if(e.target.classList.contains('picker-del')){
      if(!confirm('Silinsin mi?')) return;
      const del = await fetch(`${current.endpoint}/${encodeURIComponent(row.dataset.id)}`, {method:'DELETE'});
      if(del.ok){
        row.remove();
        if(!$list.children.length) $list.innerHTML = `<div class="picker-empty">Kayıt bulunamadı.</div>`;
      }else{ alert('Silme başarısız!'); }
    }
  };
  $close.onclick = $cancel.onclick = closeModal;
  $m.addEventListener('click', e => { if(e.target === $m) closeModal(); });

  function bindPickButtons(root){
    const container = typeof root === 'string' ? document.querySelector(root) : root;
    if(!container) return;
    container.querySelectorAll('.pick-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const entity = btn.dataset.entity;
        const hidden = document.getElementById(entity);
        const chip   = container.querySelector(`.pick-chip[data-for="${entity}"]`);
        openModal(entity, hidden, chip);
      });
    });
  }

  window.bindPickButtons = bindPickButtons;
  window.openModal = openModal;
})();
