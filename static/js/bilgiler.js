(function () {
  const MAX_PIN = 3;
  const MAX_FILE_SIZE = 5 * 1024 * 1024;

  function parseErrorMessage(response, fallback) {
    const contentType = response.headers.get("content-type") || "";
    if (contentType.includes("application/json")) {
      return response.json().then((data) => {
        if (data && typeof data.detail === "string") {
          return data.detail;
        }
        if (data && data.detail && data.detail.message) {
          return data.detail.message;
        }
        return fallback;
      });
    }
    return response.text().then((text) => text || fallback);
  }

  function ensurePinnedSection() {
    let section = document.getElementById("pinnedBilgiler");
    if (section) {
      return section;
    }
    const generalSection = document
      .getElementById("bilgiList")
      ?.closest("section");
    if (!generalSection) {
      return null;
    }
    section = document.createElement("section");
    section.id = "pinnedBilgiler";
    section.className = "mb-5";
    section.innerHTML = `
      <div class="d-flex align-items-center gap-2 mb-2">
        <span class="text-uppercase text-muted fw-semibold small">Sabitlenen Bilgiler</span>
        <span class="badge bg-warning text-dark">0/${MAX_PIN}</span>
      </div>
      <div class="row g-3"></div>
    `;
    generalSection.parentElement.insertBefore(section, generalSection);
    return section;
  }

  function updatePinnedBadge(section, countOverride) {
    if (!section) return;
    const badge = section.querySelector(".badge");
    if (!badge) return;
    if (typeof countOverride === "number") {
      badge.textContent = `${countOverride}/${MAX_PIN}`;
      return;
    }
    const total = section.querySelectorAll(".bilgi-card").length;
    badge.textContent = `${total}/${MAX_PIN}`;
  }

  function moveCardToPinned(card, pinCount) {
    const section = ensurePinnedSection();
    if (!section) return;
    const row = section.querySelector(".row");
    if (!row) return;
    row.prepend(card);
    updatePinnedBadge(section, pinCount);
  }

  function moveCardToGeneral(card, pinCount) {
    const list = document.getElementById("bilgiList");
    if (list) {
      list.prepend(card);
    }
    const section = document.getElementById("pinnedBilgiler");
    if (section) {
      const row = section.querySelector(".row");
      if (!row || !row.querySelector(".bilgi-card")) {
        section.remove();
      } else {
        updatePinnedBadge(section, pinCount);
      }
    }
  }

  function applyFilters(filterEl, searchEl) {
    const category = filterEl ? filterEl.value : "";
    const query = searchEl ? searchEl.value.trim().toLowerCase() : "";
    document.querySelectorAll(".bilgi-card").forEach((card) => {
      const cardCategory = card.dataset.category || "";
      const haystack = (card.dataset.search || "").toLowerCase();
      const categoryMatch = !category || cardCategory === category;
      const searchMatch = !query || haystack.includes(query);
      card.classList.toggle("d-none", !(categoryMatch && searchMatch));
    });
  }

  async function handlePin(button) {
    const card = button.closest(".bilgi-card");
    if (!card) return;
    const id = button.dataset.id;
    if (!id) return;
    const pinned = button.dataset.pinned === "true";

    try {
      const response = await fetch(`/bilgiler/${id}/pin`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pin: !pinned }),
      });
      if (!response.ok) {
        const message = await parseErrorMessage(
          response,
          "İşlem tamamlanamadı",
        );
        throw new Error(message);
      }
      const data = await response.json();
      button.dataset.pinned = data.pinned ? "true" : "false";
      const icon = button.querySelector("i");
      const label = button.querySelector("span");
      if (data.pinned) {
        if (icon) icon.classList.add("bi-pin-angle-fill");
        if (icon) icon.classList.remove("bi-pin-angle");
        if (label) label.textContent = "Tutturmayı Kaldır";
        moveCardToPinned(card, data.pin_count);
      } else {
        if (icon) icon.classList.remove("bi-pin-angle-fill");
        if (icon) icon.classList.add("bi-pin-angle");
        if (label) label.textContent = "Tuttur";
        moveCardToGeneral(card, data.pin_count);
      }
    } catch (err) {
      window.alert(err.message || "İşlem tamamlanamadı", {
        variant: "danger",
      });
    }
  }

  async function handleDelete(button) {
    const card = button.closest(".bilgi-card");
    if (!card) return;
    const id = button.dataset.id;
    if (!id) return;
    const confirmed = await window.confirm({
      message: "Bu bilgiyi silmek istediğinizden emin misiniz?",
      confirmLabel: "Sil",
      confirmVariant: "danger",
      title: "Silme Onayı",
    });
    if (!confirmed) return;

    try {
      const response = await fetch(`/bilgiler/${id}`, { method: "DELETE" });
      if (!response.ok) {
        const message = await parseErrorMessage(
          response,
          "Silme işlemi başarısız",
        );
        throw new Error(message);
      }
      card.remove();
      const generalList = document.getElementById("bilgiList");
      if (generalList && !generalList.querySelector(".bilgi-card")) {
        const empty = document.createElement("div");
        empty.className = "col-12";
        empty.innerHTML =
          '<div class="alert alert-info mb-0">Listede bilgi bulunmuyor.</div>';
        generalList.appendChild(empty);
      }
      const pinnedSection = document.getElementById("pinnedBilgiler");
      if (pinnedSection) {
        const hasCard = pinnedSection.querySelector(".bilgi-card");
        if (!hasCard) {
          pinnedSection.remove();
        } else {
          updatePinnedBadge(pinnedSection);
        }
      }
    } catch (err) {
      window.alert(err.message || "Silme işlemi başarısız", {
        variant: "danger",
      });
    }
  }

  function handlePhotoPreview(input, previewWrapper, previewImg, errorBox) {
    const file = input.files && input.files[0];
    if (!file) {
      if (previewWrapper) previewWrapper.classList.add("d-none");
      if (previewImg) previewImg.src = "";
      return;
    }
    if (file.size > MAX_FILE_SIZE) {
      if (errorBox) {
        errorBox.textContent = "Dosya boyutu 5MB sınırını aşıyor.";
        errorBox.classList.remove("d-none");
      } else {
        window.alert("Dosya boyutu 5MB sınırını aşıyor.", {
          variant: "warning",
        });
      }
      input.value = "";
      return;
    }
    const allowed = ["image/jpeg", "image/png", "image/gif"];
    if (file.type && !allowed.includes(file.type)) {
      if (errorBox) {
        errorBox.textContent =
          "Sadece JPG, PNG veya GIF dosyaları yükleyebilirsiniz.";
        errorBox.classList.remove("d-none");
      } else {
        window.alert("Sadece JPG, PNG veya GIF dosyaları yükleyebilirsiniz.", {
          variant: "warning",
        });
      }
      input.value = "";
      return;
    }
    if (errorBox) errorBox.classList.add("d-none");
    const reader = new FileReader();
    reader.onload = (ev) => {
      if (previewImg) previewImg.src = ev.target.result;
      if (previewWrapper) previewWrapper.classList.remove("d-none");
    };
    reader.readAsDataURL(file);
  }

  function bindForm(form, errorBox, previewWrapper, previewImg) {
    if (!form) return;
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      if (errorBox) {
        errorBox.classList.add("d-none");
        errorBox.textContent = "";
      }
      const formData = new FormData(form);
      try {
        const response = await fetch("/bilgiler/ekle", {
          method: "POST",
          body: formData,
        });
        if (!response.ok) {
          const message = await parseErrorMessage(
            response,
            "Kaydetme sırasında bir hata oluştu",
          );
          throw new Error(message);
        }
        const modalEl = document.getElementById("bilgiModal");
        if (modalEl && window.bootstrap) {
          const modal = window.bootstrap.Modal.getOrCreateInstance(modalEl);
          modal.hide();
        }
        form.reset();
        if (previewWrapper) previewWrapper.classList.add("d-none");
        if (previewImg) previewImg.src = "";
        window.location.reload();
      } catch (err) {
        if (errorBox) {
          errorBox.textContent =
            err.message || "Kaydetme sırasında bir hata oluştu";
          errorBox.classList.remove("d-none");
        } else {
          window.alert(err.message || "Kaydetme sırasında bir hata oluştu", {
            variant: "danger",
          });
        }
      }
    });
  }

  window.initBilgiPage = function initBilgiPage(options = {}) {
    const filterEl = document.getElementById("kategoriFilter");
    const searchEl = document.getElementById("bilgiSearch");
    const form = document.getElementById("bilgiForm");
    const formError = document.getElementById("bilgiFormError");
    const photoInput = document.getElementById("bilgiPhotoInput");
    const previewWrapper = document.getElementById("bilgiPhotoPreviewWrapper");
    const previewImg = document.getElementById("bilgiPhotoPreview");

    if (filterEl) {
      filterEl.value = options.kategori || "";
      filterEl.addEventListener("change", () =>
        applyFilters(filterEl, searchEl),
      );
    }
    if (searchEl) {
      searchEl.value = options.search || "";
      searchEl.addEventListener("input", () =>
        applyFilters(filterEl, searchEl),
      );
    }
    applyFilters(filterEl, searchEl);

    if (photoInput) {
      photoInput.addEventListener("change", () =>
        handlePhotoPreview(photoInput, previewWrapper, previewImg, formError),
      );
    }

    bindForm(form, formError, previewWrapper, previewImg);

    document.addEventListener("click", (e) => {
      const pinBtn = e.target.closest(".bilgi-pin-btn");
      if (pinBtn) {
        e.preventDefault();
        handlePin(pinBtn).then(() => applyFilters(filterEl, searchEl));
        return;
      }
      const deleteBtn = e.target.closest(".bilgi-delete-btn");
      if (deleteBtn) {
        e.preventDefault();
        handleDelete(deleteBtn).then(() => applyFilters(filterEl, searchEl));
      }
    });
  };
})();
