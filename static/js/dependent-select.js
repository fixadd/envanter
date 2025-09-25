// Marka -> Model gibi bağımlı select'ler için genel çözüm
document.querySelectorAll("select[data-depends]").forEach((target) => {
  const source = document.querySelector(target.dataset.depends);
  const baseUrl = target.dataset.url || "/api/lookup/model?marka=";
  if (!source) return;

  const fill = async () => {
    const val = source.value;
    target.innerHTML = "<option>Yükleniyor…</option>";
    if (!val) {
      target.innerHTML = '<option value="">Seçiniz…</option>';
      return;
    }
    const r = await fetch(baseUrl + encodeURIComponent(val));
    const list = await r.json();
    target.innerHTML =
      '<option value="">Seçiniz…</option>' +
      list.map((x) => `<option>${x}</option>`).join("");
  };
  source.addEventListener("change", fill);
});
