(function () {
  const modals = new Map();

  function getModal(id) {
    if (!modals.has(id)) {
      const el = document.getElementById(id);
      if (!el) return null;
      modals.set(id, el);
    }
    return modals.get(id);
  }

  function openModal(id) {
    const modal = getModal(id);
    if (!modal) return;
    modal.removeAttribute("hidden");
    modal.setAttribute("aria-hidden", "false");
    document.body.classList.add("modal-open");
    const firstInput = modal.querySelector("input, select, textarea, button");
    if (firstInput) {
      setTimeout(() => firstInput.focus(), 10);
    }
  }

  function closeModal(id) {
    const modal = getModal(id);
    if (!modal) return;
    modal.setAttribute("hidden", "");
    modal.setAttribute("aria-hidden", "true");
    if (![...modals.values()].some((el) => !el.hasAttribute("hidden"))) {
      document.body.classList.remove("modal-open");
    }
  }

  document.addEventListener("click", (event) => {
    const openTrigger = event.target.closest("[data-open]");
    if (openTrigger) {
      event.preventDefault();
      openModal(openTrigger.getAttribute("data-open"));
      return;
    }

    const closeTrigger = event.target.closest("[data-close]");
    if (closeTrigger) {
      event.preventDefault();
      const modal = closeTrigger.closest("[data-modal]");
      if (modal && modal.id) closeModal(modal.id);
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      const opened = [...modals.values()].find(
        (el) => !el.hasAttribute("hidden"),
      );
      if (opened) {
        closeModal(opened.id);
      }
    }
  });

  window.appModals = { open: openModal, close: closeModal };
})();
