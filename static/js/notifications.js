(() => {
  const alertModalEl = document.getElementById("globalAlertModal");
  const confirmModalEl = document.getElementById("globalConfirmModal");
  if (!alertModalEl || !confirmModalEl) return;

  const alertModal = new bootstrap.Modal(alertModalEl);
  const confirmModal = new bootstrap.Modal(confirmModalEl);

  const alertTitleEl = document.getElementById("globalAlertTitle");
  const alertBodyEl = document.getElementById("globalAlertBody");
  const alertHeaderEl = alertModalEl.querySelector(".modal-header");
  const alertOkBtn = document.getElementById("globalAlertOk");

  const confirmTitleEl = document.getElementById("globalConfirmTitle");
  const confirmBodyEl = document.getElementById("globalConfirmBody");
  const confirmHeaderEl = confirmModalEl.querySelector(".modal-header");
  const confirmCancelBtn = document.getElementById("globalConfirmCancel");
  const confirmOkBtn = document.getElementById("globalConfirmOk");

  const toastContainer = document.getElementById("globalToastContainer");

  const VARIANT_DEFAULTS = {
    primary: "Bilgi",
    secondary: "Bilgi",
    success: "Başarılı",
    danger: "Hata",
    warning: "Uyarı",
    info: "Bilgi",
    light: "Bilgi",
    dark: "Bilgi",
  };

  const HEADER_VARIANT_CLASSES = Object.keys(VARIANT_DEFAULTS).map(
    (variant) => `text-bg-${variant}`,
  );

  function detectVariant(message) {
    const text = (message == null ? "" : String(message)).toLowerCase();
    if (!text) return "primary";
    if (/başarı|tamamlandı|kaydedildi|oldu/.test(text)) return "success";
    if (/uyarı|dikkat|emin misiniz|onay/.test(text)) return "warning";
    if (
      /hata|başarısız|geçersiz|olmadı|silinemez|sınırı aşıyor|fail/.test(text)
    )
      return "danger";
    return "primary";
  }

  function setButtonVariant(button, variant, fallback = "primary") {
    if (!button) return;
    const finalVariant =
      variant && VARIANT_DEFAULTS[variant] ? variant : fallback;
    button.className = `btn btn-${finalVariant}`;
  }

  function setHeaderVariant(header, variant, fallback = "primary") {
    if (!header) return;
    header.classList.remove(...HEADER_VARIANT_CLASSES);
    const finalVariant =
      variant && VARIANT_DEFAULTS[variant] ? variant : fallback;
    header.classList.add(`text-bg-${finalVariant}`);
  }

  function setModalBody(element, message) {
    if (!element) return;
    const text = message == null ? "" : String(message);
    element.innerHTML = "";
    const lines = text.split(/\r?\n/);
    lines.forEach((line, index) => {
      if (index) element.appendChild(document.createElement("br"));
      element.appendChild(document.createTextNode(line));
    });
  }

  function resolveOnHide(modalEl, callback) {
    const handler = () => {
      modalEl.removeEventListener("hidden.bs.modal", handler);
      callback();
    };
    modalEl.addEventListener("hidden.bs.modal", handler);
  }

  window.showAlert = function showAlert(message, options = {}) {
    const resolvedVariant = options.variant || detectVariant(message);
    const { title, okLabel = "Tamam" } = options;
    alertTitleEl.textContent =
      title || VARIANT_DEFAULTS[resolvedVariant] || "Bilgi";
    alertOkBtn.textContent = okLabel;
    setButtonVariant(alertOkBtn, resolvedVariant, "primary");
    setHeaderVariant(alertHeaderEl, resolvedVariant, "primary");
    setModalBody(alertBodyEl, message);
    return new Promise((resolve) => {
      resolveOnHide(alertModalEl, resolve);
      alertModal.show();
    });
  };

  const nativeAlert = window.alert ? window.alert.bind(window) : null;

  window.alert = (message, options = {}) => {
    if (!alertModalEl) {
      nativeAlert?.(message);
      return undefined;
    }
    const opts =
      typeof options === "string"
        ? { variant: options }
        : { ...(options || {}) };
    window.showAlert(message, opts);
    return undefined;
  };

  window.showToast = function showToast(message, options = {}) {
    if (!toastContainer) return;
    const resolvedVariant = options.variant || detectVariant(message);
    const { title = "", delay = 5000 } = options;
    const effectiveVariant = VARIANT_DEFAULTS[resolvedVariant]
      ? resolvedVariant
      : "primary";
    const toastEl = document.createElement("div");
    toastEl.className = `toast text-bg-${effectiveVariant} border-0`;
    toastEl.setAttribute("role", "status");
    toastEl.setAttribute("aria-live", "polite");
    toastEl.setAttribute("aria-atomic", "true");
    toastEl.innerHTML = `
      <div class="toast-header text-bg-${effectiveVariant} border-0">
        <strong class="me-auto">${title || VARIANT_DEFAULTS[effectiveVariant] || "Bilgi"}</strong>
        <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Kapat"></button>
      </div>
      <div class="toast-body"></div>
    `;
    const body = toastEl.querySelector(".toast-body");
    setModalBody(body, message);
    toastContainer.appendChild(toastEl);
    const toast = new bootstrap.Toast(toastEl, { delay });
    toastEl.addEventListener("hidden.bs.toast", () => {
      toast.dispose();
      toastEl.remove();
    });
    toast.show();
    return toast;
  };

  window.showConfirm = function showConfirm(message, options = {}) {
    const opts =
      typeof message === "object" ? { ...message } : { ...options, message };
    const {
      message: finalMessage = "",
      title = "Onay",
      confirmLabel = "Evet",
      cancelLabel = "İptal",
      confirmVariant = "primary",
      cancelVariant = "secondary",
    } = opts;

    confirmTitleEl.textContent = title;
    confirmOkBtn.textContent = confirmLabel;
    confirmCancelBtn.textContent = cancelLabel;
    setButtonVariant(confirmOkBtn, confirmVariant, "primary");
    setButtonVariant(confirmCancelBtn, cancelVariant, "secondary");
    const headerVariant = opts.headerVariant || confirmVariant;
    setHeaderVariant(confirmHeaderEl, headerVariant, "primary");
    setModalBody(confirmBodyEl, finalMessage);

    return new Promise((resolve) => {
      const cleanup = () => {
        confirmOkBtn.removeEventListener("click", onOk);
        confirmCancelBtn.removeEventListener("click", onCancel);
        confirmModalEl.removeEventListener("hidden.bs.modal", onCancel);
      };

      const onOk = () => {
        cleanup();
        confirmModal.hide();
        resolve(true);
      };

      const onCancel = () => {
        cleanup();
        resolve(false);
      };

      confirmOkBtn.addEventListener("click", onOk, { once: true });
      confirmCancelBtn.addEventListener("click", onCancel, { once: true });
      confirmModalEl.addEventListener("hidden.bs.modal", onCancel, {
        once: true,
      });

      confirmModal.show();
    });
  };

  window.handleConfirm = function handleConfirm(trigger, event, options = {}) {
    if (event) event.preventDefault();
    const opts =
      typeof options === "string" ? { message: options } : { ...options };
    if (!opts.message) {
      opts.message =
        trigger?.getAttribute("data-confirm-message") || "Onaylıyor musunuz?";
    }
    window.showConfirm(opts).then((confirmed) => {
      if (!confirmed) return;
      if (typeof opts.onConfirm === "function") {
        opts.onConfirm.call(trigger);
        return;
      }
      const targetForm = trigger?.form || trigger?.closest?.("form");
      if (targetForm && trigger?.type === "submit") {
        if (typeof targetForm.requestSubmit === "function") {
          targetForm.requestSubmit(trigger);
        } else {
          targetForm.submit();
        }
        return;
      }
      const href = trigger?.getAttribute?.("href");
      if (href) {
        const target = trigger.getAttribute("target");
        if (target && target !== "_self") {
          window.open(href, target);
        } else {
          window.location.href = href;
        }
        return;
      }
      const submitTarget = opts.submitTarget
        ? document.querySelector(opts.submitTarget)
        : null;
      if (submitTarget && typeof submitTarget.submit === "function") {
        submitTarget.submit();
      }
    });
    return false;
  };

  const nativeConfirm = window.confirm ? window.confirm.bind(window) : null;

  function resolveToPromise(result) {
    return typeof Promise === "function" ? Promise.resolve(result) : result;
  }

  window.confirm = function confirmOverride(message, options = {}) {
    if (!confirmModalEl) {
      return resolveToPromise(nativeConfirm ? nativeConfirm(message) : true);
    }
    const opts =
      typeof message === "object" ? { ...message } : { ...options, message };
    if (!opts.message) {
      opts.message = message == null ? "" : String(message);
    }
    return window.showConfirm(opts);
  };

  window.confirm.native = nativeConfirm;
  window.confirmAsync = window.confirm;

  window.notify = {
    success(message, options = {}) {
      return window.showToast(message, { ...options, variant: "success" });
    },
    info(message, options = {}) {
      return window.showToast(message, { ...options, variant: "info" });
    },
    warning(message, options = {}) {
      return window.showToast(message, { ...options, variant: "warning" });
    },
    danger(message, options = {}) {
      return window.showToast(message, { ...options, variant: "danger" });
    },
    error(message, options = {}) {
      return window.showToast(message, { ...options, variant: "danger" });
    },
  };
})();
