(function(){

  // ENTITY eşlemesi: endpoint + opsiyonel bağımlılık (dependsOn)
  const MAP = {
    kullanim_alani: { title: "KULLANIM ALANI", endpoint: "/api/picker/kullanim_alani" },
    lisans_adi:     { title: "LİSANS ADI",     endpoint: "/api/picker/lisans_adi"     },
    fabrika:        { title: "FABRİKA",        endpoint: "/api/picker/fabrika"        },
    donanim_tipi:   { title: "DONANIM TİPİ",   endpoint: "/api/picker/donanim_tipi"   },
    marka:          { title: "MARKA",          endpoint: "/api/picker/marka"          },

    // MODEL marka'ya bağlı: GET'te ?marka_id=.. gönder, POST'ta parent_id olarak geç
    model:          { title: "MODEL",          endpoint: "/api/picker/model",
                      dependsOn: { hiddenId: "marka", param: "marka_id" } },
  };

  const $m      = document.getElementById('picker-modal');
  const $title  = document.getElementById('picker-title');
  const $search = document.getElementById('picker-search');
  const $add    = document.getElementById('picker-add');
  const $list   = document.getElementById('picker-list');
  const $close  = document.querySelector('.picker-close');
  const $cancel = document.getElementById('picker-cancel');

  let current = { entity:null, endpoint:null, hidden:null, chip:null, extra:{} };

  function getDependencyParams(entity){
    const meta = MAP[entity];
    if(!meta || !meta.dependsOn) return { extra: {}, parentId: null };
    const dep = meta.dependsOn;
    const depHidden = document.getElementById(dep.hiddenId);
    if(!depHidden || !depHidden.value) return { extra: null, parentId: null }; // bağımlı ama seçilmemiş
    return { extra: { [dep.param]: depHidden.value }, parentId: depHidden.value };
  }

  function openModal(entity, hiddenEl, chipEl){
    const meta = MAP[entity] || { title: entity.toUpperCase(), endpoint: `/api/picker/${entity}` };

    const dep = getDependencyParams(entity);
    if(dep.extra === null){
      alert("Önce bağlı alanı seçin (örn. önce MARKA seçin).");
      return;
    }

    current = {
      entity,
      endpoint: meta.endpoint,
      hidden: hiddenEl,
      chip: chipEl || null,
      extra: dep.extra || {},
      parentId: dep.parentId || null,
    };

    $title.textContent = `${meta.title} seçin`;
    $search.value = ''; $list.innerHTML = '';
    $m.hidden = false; $m.style.display = 'flex';

    updateAddState();
    load('');
    $search.focus();
  }

  function updateAddState(){
    $add.disabled = ($search.value.trim().length === 0);
  }

  async function load(q){
    const url = new URL(current.endpoint, location.origin);
    if(q) url.searchParams.set('q', q);
    Object.entries(current.extra || {}).forEach(([k,v]) => url.searchParams.set(k, v));
    const res = await fetch(url, { headers:{ Accept:'application/json' } });
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
      </div>`).join('');
  }

  function closeModal(){
    $m.style.display='none'; $m.hidden=true;
    $list.innerHTML=''; $search.value='';
    current = { entity:null, endpoint:null, hidden:null, chip:null, extra:{} };
  }

  // Arama + Ekle
  $search.addEventListener('input', (e)=>{ updateAddState(); load(e.target.value.trim()); });
  $search.addEventListener('keydown', (e)=>{ if(e.key === 'Enter' && !$add.disabled) { e.preventDefault(); addItem(); } });

  $add.addEventListener('click', addItem);

  async function addItem(){
    const text = $search.value.trim();
    if(!text) return;

    // POST body: { text, parent_id? }
    const body = { text };
    if(current.parentId) body.parent_id = current.parentId;

    const res = await fetch(current.endpoint, {
      method:'POST',
      headers:{ 'Content-Type':'application/json', 'Accept':'application/json' },
      body: JSON.stringify(body)
    });

    if(res.ok){
      const created = await res.json(); // {id, text}
      // otomatik seç
      if(current.hidden) current.hidden.value = created.id;
      if(current.chip){ current.chip.textContent = created.text; current.chip.classList.remove('d-none'); }
      closeModal();
    }else if(res.status === 409){
      alert('Bu kayıt zaten var.');
    }else{
      alert('Ekleme başarısız!');
    }
  }

  // Liste seçim/silme
  $list.addEventListener('click', async (e)=>{
    const row = e.target.closest('.picker-row'); if(!row) return;

    if(e.target.classList.contains('picker-select')){
      if(current.hidden) current.hidden.value = row.dataset.id;
      if(current.chip){ current.chip.textContent = row.dataset.text; current.chip.classList.remove('d-none'); }
      closeModal();
    }else if(e.target.classList.contains('picker-del')){
      if(!confirm('Silinsin mi?')) return;
      const url = `${current.endpoint}/${encodeURIComponent(row.dataset.id)}`;
      const delRes = await fetch(url, { method:'DELETE' });
      if(delRes.ok){
        row.remove();
        if(!$list.children.length) $list.innerHTML = `<div class="picker-empty">Kayıt bulunamadı.</div>`;
      }else{
        alert('Silme başarısız!');
      }
    }
  });

  $close.onclick = $cancel.onclick = closeModal;
  $m.addEventListener('click', e=>{ if(e.target === $m) closeModal(); });

  // ≡ butonlarını bağla (admin/kullanıcı fark etmez; kapsayıcı id’ni değiştir)
  document.querySelectorAll('#admin-urun-ekle .pick-btn, #urun-ekle .pick-btn').forEach(btn=>{
    btn.addEventListener('click', ()=>{
      const entity = btn.dataset.entity;
      const hidden = document.getElementById(entity);
      const chip   = document.querySelector(`.pick-chip[data-for="${entity}"]`);
      openModal(entity, hidden, chip);
    });
  });

})();
