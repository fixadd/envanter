(function () {
  const form = document.getElementById("licenseAddForm");
  if (!form) return;

  form.addEventListener("submit", () => {
    if (form.dataset.submitting === "true") {
      return;
    }
    form.dataset.submitting = "true";
    const submitButton = form.querySelector('button[type="submit"]');
    if (submitButton) {
      submitButton.disabled = true;
      submitButton.dataset.originalText = submitButton.innerHTML;
      submitButton.innerHTML = "Kaydediliyor...";
    }
  });
})();
