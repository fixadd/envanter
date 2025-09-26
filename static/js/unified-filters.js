(() => {
  const API_DISTINCT_PREFIX = "/api/lookup/distinct/";

  function normaliseValue(value) {
    if (value === null || value === undefined) return "";
    return String(value).trim();
  }

  function normaliseForCompare(value) {
    return normaliseValue(value).toLowerCase();
  }

  function buildColumnIndexMap(tableEl) {
    if (!tableEl) return {};
    const map = {};
    const headers = tableEl.querySelectorAll("thead th");
    headers.forEach((th, idx) => {
      const field = th.dataset.field;
      if (field) {
        map[field] = idx;
      }
    });
    return map;
  }

  function getOptionLabel(selectEl, value) {
    if (!selectEl) return value;
    const option = Array.from(selectEl.options).find(
      (opt) => opt.value === value,
    );
    return option ? option.textContent : value;
  }

  async function populateDistinctValues(
    selectId,
    entity,
    column,
    options = {},
  ) {
    const selectEl = document.getElementById(selectId);
    if (!selectEl) return;
    const { placeholder = "Tümü", includeEmpty = true, distinctUrl } = options;
    const endpoint =
      distinctUrl ||
      `${API_DISTINCT_PREFIX}${encodeURIComponent(entity)}/${encodeURIComponent(column)}`;
    try {
      const response = await fetch(endpoint);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const data = await response.json();
      const values = Array.isArray(data) ? data : [];
      const fragment = document.createDocumentFragment();
      if (includeEmpty) {
        const emptyOpt = document.createElement("option");
        emptyOpt.value = "";
        emptyOpt.textContent = placeholder;
        fragment.appendChild(emptyOpt);
      }
      values
        .map((item) =>
          typeof item === "object" ? (item.value ?? item.text ?? "") : item,
        )
        .filter((item) => item !== null && item !== undefined && item !== "")
        .forEach((item) => {
          const opt = document.createElement("option");
          opt.value = item;
          opt.textContent = item;
          fragment.appendChild(opt);
        });
      selectEl.innerHTML = "";
      selectEl.appendChild(fragment);
    } catch (error) {
      console.warn("populateDistinctValues failed", { entity, column, error });
    }
  }

  class UnifiedFilterSystem {
    constructor(options = {}) {
      this.options = Object.assign(
        {
          tableSelector: "table",
          searchInputId: null,
          filters: [],
          filterButtonId: "filterBtn",
          clearButtonId: "clearFilterBtn",
          activeFiltersContainerId: "activeFilterBadges",
          activeFiltersSectionId: "activeFiltersSection",
        },
        options,
      );

      this.table =
        typeof this.options.tableSelector === "string"
          ? document.querySelector(this.options.tableSelector)
          : this.options.tableSelector;
      this.tbodyRows = this.table
        ? Array.from(this.table.querySelectorAll("tbody tr"))
        : [];
      this.columnIndexMap = buildColumnIndexMap(this.table);
      this.searchInput = this.options.searchInputId
        ? document.getElementById(this.options.searchInputId)
        : null;
      this.filterButton = this.options.filterButtonId
        ? document.getElementById(this.options.filterButtonId)
        : null;
      this.clearButton = this.options.clearButtonId
        ? document.getElementById(this.options.clearButtonId)
        : null;
      this.activeFiltersContainer = this.options.activeFiltersContainerId
        ? document.getElementById(this.options.activeFiltersContainerId)
        : null;
      this.activeFiltersSection = this.options.activeFiltersSectionId
        ? document.getElementById(this.options.activeFiltersSectionId)
        : null;

      this.filters = (this.options.filters || [])
        .map((filter) => {
          const element = document.getElementById(filter.id);
          if (!element) return null;
          return Object.assign({}, filter, { element });
        })
        .filter(Boolean);

      this.advancedFilters = [];
      this._bindEvents();
      this.applyFilters();
    }

    _bindEvents() {
      if (this.searchInput) {
        this.searchInput.addEventListener("input", () => this.applyFilters());
      }

      this.filters.forEach((filter) => {
        const eventName =
          filter.element.tagName === "SELECT" ? "change" : "input";
        filter.element.addEventListener(eventName, () => this.applyFilters());
      });

      if (this.filterButton) {
        this.filterButton.addEventListener("click", (event) => {
          if (this.advancedFilterModal) {
            event.preventDefault();
            this.advancedFilterModal.open();
          } else {
            this.applyFilters();
          }
        });
      }

      if (this.clearButton) {
        this.clearButton.addEventListener("click", (event) => {
          event.preventDefault();
          this.clearFilters();
        });
      }

      if (this.activeFiltersContainer) {
        this.activeFiltersContainer.addEventListener("click", (event) => {
          const badge = event.target.closest("[data-filter-id]");
          if (!badge) return;
          const filterId = badge.dataset.filterId;
          const filterType = badge.dataset.filterType || "simple";
          if (filterType === "search") {
            if (this.searchInput) {
              this.searchInput.value = "";
            }
          } else if (filterType === "advanced") {
            this.advancedFilters = this.advancedFilters.filter(
              (f) => f.id !== filterId,
            );
            if (this.advancedFilterModal) {
              this.advancedFilterModal.setCurrentFilters(this.advancedFilters);
            }
          } else {
            const filter = this.filters.find((item) => item.id === filterId);
            if (filter) {
              if (filter.element.tagName === "SELECT") {
                filter.element.selectedIndex = 0;
              } else {
                filter.element.value = "";
              }
            }
          }
          this.applyFilters();
        });
      }
    }

    registerAdvancedFilter(modalInstance) {
      if (!modalInstance) return;
      this.advancedFilterModal = modalInstance;
      modalInstance.setApplyCallback((filters) => {
        this.setAdvancedFilters(filters);
      });
      modalInstance.setResetCallback(() => {
        this.clearAdvancedFilters();
      });
      modalInstance.setCurrentFilters(this.advancedFilters);
    }

    setAdvancedFilters(filters = []) {
      this.advancedFilters = Array.isArray(filters) ? filters : [];
      if (this.advancedFilterModal) {
        this.advancedFilterModal.setCurrentFilters(this.advancedFilters);
      }
      this.applyFilters();
    }

    clearAdvancedFilters() {
      this.advancedFilters = [];
      if (this.advancedFilterModal) {
        this.advancedFilterModal.setCurrentFilters([]);
      }
      this.applyFilters();
    }

    clearFilters() {
      if (this.searchInput) {
        this.searchInput.value = "";
      }
      this.filters.forEach((filter) => {
        if (filter.element.tagName === "SELECT") {
          filter.element.selectedIndex = 0;
        } else {
          filter.element.value = "";
        }
      });
      this.clearAdvancedFilters();
    }

    _getFilterValue(element) {
      if (!element) return "";
      if (element.tagName === "SELECT") {
        return normaliseValue(element.value);
      }
      return normaliseValue(element.value);
    }

    _getRowValue(row, field) {
      if (!row) return "";
      const directAttr = row.getAttribute(`data-${field}`);
      if (directAttr !== null && directAttr !== undefined) {
        return normaliseValue(directAttr);
      }
      const index = this.columnIndexMap[field];
      if (index === undefined) return "";
      const cell = row.children[index];
      if (!cell) return "";
      return normaliseValue(cell.textContent);
    }

    _matchRowValue(rowValue, filterValue) {
      if (!filterValue) return true;
      if (!rowValue) return false;
      return normaliseForCompare(rowValue) === normaliseForCompare(filterValue);
    }

    applyFilters() {
      const searchValue = this.searchInput
        ? normaliseForCompare(this.searchInput.value)
        : "";

      const activeSimpleFilters = this.filters
        .map((filter) => {
          const value = this._getFilterValue(filter.element);
          if (!value) return null;
          const displayValue = getOptionLabel(filter.element, value);
          return {
            id: filter.id,
            label: filter.label || filter.id,
            columnField: filter.columnField,
            value,
            displayValue,
          };
        })
        .filter(Boolean);

      const activeFilters = [...activeSimpleFilters, ...this.advancedFilters];

      this.tbodyRows.forEach((row) => {
        const rowText = normaliseForCompare(row.textContent || "");
        let visible = true;

        if (searchValue) {
          visible = rowText.includes(searchValue);
        }

        if (visible) {
          for (const filter of activeFilters) {
            const rowValue = this._getRowValue(
              row,
              filter.columnField || filter.field,
            );
            if (!this._matchRowValue(rowValue, filter.value)) {
              visible = false;
              break;
            }
          }
        }

        row.classList.toggle("d-none", !visible);
      });

      this._renderBadges({
        searchValue,
        activeSimpleFilters,
        advancedFilters: this.advancedFilters,
      });
    }

    _renderBadges({ searchValue, activeSimpleFilters, advancedFilters }) {
      if (
        !this.activeFiltersContainer &&
        !this.activeFiltersSection &&
        !this.clearButton
      ) {
        return;
      }
      const badges = [];

      if (searchValue) {
        badges.push({
          id: "__search__",
          label: "Arama",
          displayValue: this.searchInput ? this.searchInput.value : "",
          type: "search",
        });
      }

      activeSimpleFilters.forEach((filter) => {
        badges.push({
          id: filter.id,
          label: filter.label,
          displayValue: filter.displayValue,
          type: "simple",
        });
      });

      advancedFilters.forEach((filter) => {
        badges.push({
          id: filter.id,
          label: filter.label,
          displayValue: filter.displayValue || filter.value,
          type: "advanced",
        });
      });

      if (this.activeFiltersContainer) {
        this.activeFiltersContainer.innerHTML = "";
        if (badges.length === 0) {
          const empty = document.createElement("span");
          empty.className = "text-muted small";
          empty.textContent = "Aktif filtre yok";
          this.activeFiltersContainer.appendChild(empty);
        } else {
          badges.forEach((badge) => {
            const badgeEl = document.createElement("span");
            badgeEl.className = "filter-badge";
            badgeEl.dataset.filterId = badge.id;
            badgeEl.dataset.filterType = badge.type;
            badgeEl.innerHTML = `
              <span class="filter-badge__label">${badge.label}:</span>
              <span class="filter-badge__value">${badge.displayValue}</span>
              <button type="button" class="filter-badge__remove" aria-label="Filtreyi temizle">
                <i class="bi bi-x"></i>
              </button>
            `;
            this.activeFiltersContainer.appendChild(badgeEl);
          });
        }
      }

      const hasActive = badges.length > 0;
      if (this.activeFiltersSection) {
        this.activeFiltersSection.classList.toggle("d-none", !hasActive);
      }
      if (this.clearButton) {
        this.clearButton.classList.toggle("d-none", !hasActive);
      }
    }
  }

  class AdvancedFilterModal {
    constructor(options = {}) {
      this.options = Object.assign(
        {
          modalId: null,
          formId: null,
          triggerId: "filterBtn",
          columns: [],
          distinctUrl: null,
        },
        options,
      );
      this.modalEl = this.options.modalId
        ? document.getElementById(this.options.modalId)
        : null;
      this.formEl = this.options.formId
        ? document.getElementById(this.options.formId)
        : null;
      this.rowsContainer = this.formEl
        ? this.formEl.querySelector("#filterRows")
        : null;
      this.triggerEl = this.options.triggerId
        ? document.getElementById(this.options.triggerId)
        : null;
      this.columns = this.options.columns || [];
      this.distinctUrl = this.options.distinctUrl || null;
      this.currentFilters = [];
      this.applyCallback = null;
      this.resetCallback = null;
      this.rowCounter = 0;

      this.modalInstance =
        this.modalEl && window.bootstrap
          ? bootstrap.Modal.getOrCreateInstance(this.modalEl)
          : null;

      this._bindEvents();
    }

    _bindEvents() {
      if (this.triggerEl) {
        this.triggerEl.addEventListener("click", (event) => {
          event.preventDefault();
          this.open();
        });
      }

      if (this.formEl) {
        this.formEl.addEventListener("submit", (event) => {
          event.preventDefault();
          const filters = this._collectFilters();
          this.currentFilters = filters;
          if (this.applyCallback) {
            this.applyCallback(filters);
          }
          this.close();
        });

        this.formEl.addEventListener("click", (event) => {
          const addBtn = event.target.closest("[data-filter-add]");
          const removeBtn = event.target.closest("[data-filter-remove]");
          if (addBtn) {
            event.preventDefault();
            this._appendRow();
          }
          if (removeBtn) {
            event.preventDefault();
            const row = event.target.closest(".filter-row-shell");
            if (row) {
              row.remove();
            }
            this._ensureAtLeastOneRow();
          }
        });

        this.formEl.addEventListener("change", (event) => {
          const select = event.target.closest("[data-filter-column]");
          if (select) {
            const row = select.closest(".filter-row-shell");
            this._populateRowValues(row, select.value);
          }
        });
      }
    }

    open() {
      if (!this.modalEl || !this.rowsContainer) return;
      this._renderFromCurrentFilters();
      if (this.modalInstance) {
        this.modalInstance.show();
      }
    }

    close() {
      if (this.modalInstance) {
        this.modalInstance.hide();
      }
    }

    setApplyCallback(callback) {
      this.applyCallback = callback;
    }

    setResetCallback(callback) {
      this.resetCallback = callback;
    }

    setCurrentFilters(filters = []) {
      this.currentFilters = Array.isArray(filters) ? filters : [];
    }

    clear() {
      this.currentFilters = [];
      if (typeof this.resetCallback === "function") {
        this.resetCallback();
      }
    }

    _renderFromCurrentFilters() {
      if (!this.rowsContainer) return;
      this.rowsContainer.innerHTML = "";
      if (this.currentFilters.length === 0) {
        this._appendRow();
      } else {
        this.currentFilters.forEach((filter) => {
          this._appendRow(
            filter.field || filter.columnField,
            filter.value,
            filter.displayValue,
          );
        });
      }
      this._ensureAtLeastOneRow();
    }

    _ensureAtLeastOneRow() {
      if (!this.rowsContainer) return;
      if (this.rowsContainer.children.length === 0) {
        this._appendRow();
      }
    }

    _createRowElement() {
      const row = document.createElement("div");
      row.className = "filter-row-shell";
      row.dataset.rowId = `filter-row-${this.rowCounter++}`;
      const columnOptions = this.columns
        .map(
          (col) =>
            `<option value="${col.field}" data-column-label="${col.name}">${col.name}</option>`,
        )
        .join("");
      row.innerHTML = `
        <select class="form-select form-select-sm" data-filter-column>
          ${columnOptions}
        </select>
        <select class="form-select form-select-sm" data-filter-value>
          <option value="">Seçiniz</option>
        </select>
        <div class="filter-row-shell__actions">
          <button class="btn btn-outline-primary btn-sm" data-filter-add type="button">
            <i class="bi bi-plus-lg"></i>
          </button>
          <button class="btn btn-outline-danger btn-sm" data-filter-remove type="button">
            <i class="bi bi-dash-lg"></i>
          </button>
        </div>
      `;
      return row;
    }

    async _populateRowValues(row, field, presetValue) {
      if (!row) return;
      const valueSelect = row.querySelector("[data-filter-value]");
      if (!valueSelect) return;
      valueSelect.innerHTML = '<option value="">Seçiniz</option>';
      if (!field) return;
      const column = this.columns.find((col) => col.field === field);
      if (!column) return;
      const urlTemplate = this.options.distinctUrl || "";
      const endpoint = urlTemplate
        ? urlTemplate.replace("__COL__", encodeURIComponent(field))
        : `${API_DISTINCT_PREFIX}${encodeURIComponent(field)}`;
      try {
        const response = await fetch(endpoint);
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        const data = await response.json();
        const values = Array.isArray(data) ? data : [];
        values
          .map((item) =>
            typeof item === "object" ? (item.value ?? item.text ?? "") : item,
          )
          .filter((item) => item !== null && item !== undefined && item !== "")
          .forEach((value) => {
            const option = document.createElement("option");
            option.value = value;
            option.textContent = value;
            valueSelect.appendChild(option);
          });
        if (presetValue) {
          valueSelect.value = presetValue;
        }
      } catch (error) {
        console.warn("AdvancedFilterModal: distinct fetch failed", {
          field,
          error,
        });
      }
    }

    _appendRow(field, presetValue) {
      if (!this.rowsContainer) return;
      const row = this._createRowElement();
      this.rowsContainer.appendChild(row);
      if (field) {
        const columnSelect = row.querySelector("[data-filter-column]");
        if (columnSelect) {
          columnSelect.value = field;
        }
        this._populateRowValues(row, field, presetValue);
      } else {
        const columnSelect = row.querySelector("[data-filter-column]");
        this._populateRowValues(row, columnSelect ? columnSelect.value : null);
      }
    }

    _collectFilters() {
      if (!this.rowsContainer) return [];
      const filters = [];
      Array.from(
        this.rowsContainer.querySelectorAll(".filter-row-shell"),
      ).forEach((row, index) => {
        const columnSelect = row.querySelector("[data-filter-column]");
        const valueSelect = row.querySelector("[data-filter-value]");
        const field = columnSelect ? columnSelect.value : "";
        const value = valueSelect ? valueSelect.value : "";
        if (!field || !value) return;
        const column = this.columns.find((col) => col.field === field);
        const label = column ? column.name : field;
        const displayValue = getOptionLabel(valueSelect, value) || value;
        filters.push({
          id: `${field}-${value}-${index}`,
          field,
          columnField: field,
          label,
          value,
          displayValue,
        });
      });
      return filters;
    }
  }

  window.populateDistinctValues = populateDistinctValues;
  window.UnifiedFilterSystem = UnifiedFilterSystem;
  window.AdvancedFilterModal = AdvancedFilterModal;
})();
