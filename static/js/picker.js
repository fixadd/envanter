(function(){
  const modal  = document.getElementById("pickerModal");
  const title  = document.getElementById("pickerTitle");
  const search = document.getElementById("pickerSearch");
  const list   = document.getElementById("pickerList");
  const newIn  = document.getElementById("pickerNewName");
  const addBtn = document.getElementById("pickerAddBtn");

  let current = { entity:null, targetText:null, targetId:null, markaGetter:null, label:"Seç" };

  function openModal({entity, label, targetTextId, targetHiddenId, markaGetter}){
    current.entity = entity;
    current.label  = label || "Seç";
    current.targetText = document.getElementById(targetTextId);
    current.targetId   = document.getElementById(targetHiddenId);
    current.markaGetter= markaGetter || null;

    title.textContent = `${current.label}`;
    search.value = current.targetText?.value || "";
    newIn.value  = "";
    list.innerHTML = "";

    modal.style.display = "block";
    doSearch();
  }
  function closeModal(){ modal.style.display = "none"; }

  async function doSearch(){
    const params = new URLSearchParams({ q: search.value.trim() });
    if (current.entity === "model" && typeof current.markaGetter === "function"){
      const mid = current.markaGetter();
      if (mid) params.append("marka_id", mid);
    }
    const r = await fetch(`/api/lookup/${current.entity}?` + params.toString());
    const data = r.ok ? await r.json() : [];
    list.innerHTML = data.map(x =>
      `<button type="button" class="list-group-item list-group-item-action" data-id="${x.id}" data-ad="${x.text ?? x.ad ?? x.name}">${x.text ?? x.ad ?? x.name}</button>`
    ).join("");
    [...list.children].forEach(btn=>{
      btn.addEventListener("click", ()=>{
        current.targetText.value = btn.dataset.ad;
        if (current.targetId) current.targetId.value   = btn.dataset.id;
        closeModal();
      });
    });
  }
  function debounce(fn, d=250){ let t; return (...a)=>{ clearTimeout(t); t=setTimeout(()=>fn(...a), d); }; }
  search.addEventListener("input", debounce(doSearch, 200));
  modal.querySelectorAll("[data-close]").forEach(b=> b.addEventListener("click", closeModal));

  addBtn.addEventListener("click", async ()=>{
    const ad = newIn.value.trim();
    if (!ad) return;
    const body = { ad };
    if (current.entity === "model" && typeof current.markaGetter === "function"){
      const mid = current.markaGetter();
      if (!mid){ alert("Önce Marka seçin."); return; }
      body.marka_id = parseInt(mid);
    }
    const r = await fetch(`/api/ref/${current.entity}`, {
      method: "POST", headers: { "Content-Type":"application/json" }, body: JSON.stringify(body)
    });
    if (!r.ok){ alert("Kaydedilemedi"); return; }
    const data = await r.json();
    current.targetText.value = data.text ?? data.ad ?? data.name;
    if (current.targetId) current.targetId.value   = data.id;
    closeModal();
  });

  // Dışarı aç
  window.openPicker = openModal;
})();
