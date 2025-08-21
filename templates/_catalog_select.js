<script>
/**
 * basitSelectDoldur({
 *   selectId: "fabrika_select",
 *   url: "/catalog/factories",
 *   hiddenName: "fabrika",            // Form POST’unda backend’in beklediği alan
 *   placeholder: "Seçiniz…"
 * })
 */
async function basitSelectDoldur({selectId, url, hiddenName, placeholder="Seçiniz…"}) {
  const sel = document.getElementById(selectId);
  sel.innerHTML = "";
  const ph = document.createElement("option");
  ph.value = ""; ph.textContent = placeholder;
  sel.appendChild(ph);

  const data = await fetch(url).then(r => r.json()).catch(()=>[]);
  data.forEach(item => {
    const opt = document.createElement("option");
    opt.value = item.id;
    opt.textContent = item.name;
    sel.appendChild(opt);
  });

  // Seçilen label'ı gizli input olarak forma bas
  const form = sel.closest("form");
  let hid = form.querySelector(`input[name="${hiddenName}"]`);
  if (!hid) {
    hid = document.createElement("input");
    hid.type = "hidden";
    hid.name = hiddenName;
    form.appendChild(hid);
  }
  sel.addEventListener("change", () => {
    const txt = sel.options[sel.selectedIndex]?.textContent || "";
    hid.value = txt;                   // backend yine string alanı alır (örn. fabrika)
  });
}

/**
 * bağımlıSelectDoldur({
 *   ustSelectId: "marka_select",
 *   altSelectId: "model_select",
 *   altUrlBuilder: (brandId)=>`/catalog/models?brand_id=${brandId}`,
 *   altHiddenName: "model",       // örn. envanter/model veya yazıcı_modeli karşılığı
 * })
 */
function bağımlıSelectDoldur({ustSelectId, altSelectId, altUrlBuilder, altHiddenName, altPlaceholder="Seçiniz…"}) {
  const upper = document.getElementById(ustSelectId);
  const lower = document.getElementById(altSelectId);

  upper.addEventListener("change", async () => {
    lower.innerHTML = "";
    const ph = document.createElement("option");
    ph.value = ""; ph.textContent = upper.value ? altPlaceholder : "Önce üst seçimi yapın…";
    lower.appendChild(ph);
    lower.disabled = !upper.value;
    if (!upper.value) return;

    const data = await fetch(altUrlBuilder(upper.value)).then(r=>r.json()).catch(()=>[]);
    data.forEach(item => {
      const opt = document.createElement("option");
      opt.value = item.id;
      opt.textContent = item.name;
      lower.appendChild(opt);
    });

    // alt seçimin metnini gizli inputa bas
    const form = lower.closest("form");
    let hid = form.querySelector(`input[name="${altHiddenName}"]`);
    if (!hid) { hid = document.createElement("input"); hid.type="hidden"; hid.name=altHiddenName; form.appendChild(hid); }
    lower.addEventListener("change", ()=> {
      const txt = lower.options[lower.selectedIndex]?.textContent || "";
      hid.value = txt;
    });
  });
}
</script>
