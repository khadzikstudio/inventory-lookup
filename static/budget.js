const searchInput = document.getElementById("searchInput");
const clearBtn = document.getElementById("clearBtn");
const resultsEl = document.getElementById("results");
const loadingEl = document.getElementById("loading");
const emptyEl = document.getElementById("emptyState");
const daysInput = document.getElementById("daysInput");
const budgetInput = document.getElementById("budgetInput");
const selectedListEl = document.getElementById("selectedList");
const selectedCountEl = document.getElementById("selectedCount");
const subtotalDayEl = document.getElementById("subtotalDay");
const grandTotalEl = document.getElementById("grandTotal");
const budgetStatusEl = document.getElementById("budgetStatus");
const dropZoneEl = document.getElementById("dropZone");
const exportBtn = document.getElementById("exportBtn");

const selectedItems = new Map();
const searchResultsById = new Map();
let debounceTimer = null;

function parseMoney(value) {
    const n = parseFloat(value);
    return Number.isFinite(n) ? n : 0;
}

function money(value) {
    return "$" + value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function getPrice(item) {
    return parseMoney(item?.extra?.Price || 0);
}

function escHtml(str) {
    const d = document.createElement("div");
    d.textContent = str == null ? "" : String(str);
    return d.innerHTML;
}

async function doSearch() {
    const query = searchInput.value.trim();
    loadingEl.classList.add("active");
    resultsEl.innerHTML = "";
    emptyEl.style.display = "none";
    searchResultsById.clear();

    try {
        const resp = await fetch(`/api/search?q=${encodeURIComponent(query)}&limit=120`);
        const data = await resp.json();
        const items = data.items || [];
        loadingEl.classList.remove("active");

        if (!items.length) {
            emptyEl.style.display = "";
            return;
        }

        renderResults(items);
    } catch (err) {
        loadingEl.classList.remove("active");
        resultsEl.innerHTML = `<p style="color:red;padding:20px;">Search error: ${escHtml(err.message)}</p>`;
    }
}

function renderResults(items) {
    resultsEl.innerHTML = "";
    const frag = document.createDocumentFragment();

    items.forEach(item => {
        searchResultsById.set(item.id, item);

        const card = document.createElement("div");
        card.className = "card";
        card.dataset.itemId = String(item.id);
        card.draggable = true;
        card.addEventListener("dragstart", e => {
            e.dataTransfer.setData("text/item-id", String(item.id));
            e.dataTransfer.effectAllowed = "copy";
        });

        if (item.thumb_file) {
            const img = document.createElement("img");
            img.className = "card-img";
            img.loading = "lazy";
            img.src = `/thumbnails/${item.thumb_file}`;
            img.alt = item.name;
            img.onerror = function () {
                this.outerHTML = `<div class="card-img no-img">No image</div>`;
            };
            card.appendChild(img);
        } else {
            const placeholder = document.createElement("div");
            placeholder.className = "card-img no-img";
            placeholder.textContent = "No image";
            card.appendChild(placeholder);
        }

        const body = document.createElement("div");
        body.className = "card-body";
        body.innerHTML = `<div class="card-name">${escHtml(item.name)}</div>`;
        card.appendChild(body);

        const actions = document.createElement("div");
        actions.className = "card-actions";
        actions.innerHTML = `<span class="mini-price">${money(getPrice(item))} / day</span>`;

        const addBtn = document.createElement("button");
        addBtn.className = "add-btn";
        addBtn.textContent = "Add";
        addBtn.addEventListener("click", () => addItem(item));
        actions.appendChild(addBtn);
        card.appendChild(actions);

        frag.appendChild(card);
    });

    resultsEl.appendChild(frag);
}

function addItem(item) {
    const existing = selectedItems.get(item.id);
    if (existing) {
        existing.qty += 1;
    } else {
        selectedItems.set(item.id, { item, qty: 1 });
    }
    renderSelected();
}

function removeItem(id) {
    selectedItems.delete(id);
    renderSelected();
}

function renderSelected() {
    selectedListEl.innerHTML = "";
    const days = Math.max(1, parseInt(daysInput.value || "1", 10));
    let subtotalDay = 0;
    let grandTotal = 0;

    selectedItems.forEach((entry, id) => {
        const unit = getPrice(entry.item);
        const lineDay = unit * entry.qty;
        const lineTotal = lineDay * days;
        subtotalDay += lineDay;
        grandTotal += lineTotal;

        const row = document.createElement("div");
        row.className = "selected-item";

        const imgHtml = entry.item.thumb_file
            ? `<img src="/thumbnails/${escHtml(entry.item.thumb_file)}" alt="${escHtml(entry.item.name)}" draggable="true">`
            : `<div class="card-img no-img" style="width:56px;height:56px;">No image</div>`;

        row.innerHTML = `
            ${imgHtml}
            <div class="item-meta">
                <div class="item-name">${escHtml(entry.item.name)}</div>
                <div class="item-price">${money(unit)} / day</div>
            </div>
            <div>
                <div class="item-controls">
                    <input type="number" min="1" value="${entry.qty}" data-qty-id="${id}">
                    <button class="remove-btn" data-remove-id="${id}">Remove</button>
                </div>
                <div class="item-total">${money(lineTotal)}</div>
            </div>
        `;

        selectedListEl.appendChild(row);
    });

    selectedCountEl.textContent = String(selectedItems.size);
    subtotalDayEl.textContent = money(subtotalDay);
    grandTotalEl.textContent = money(grandTotal);
    updateBudgetStatus(grandTotal);
}

function updateBudgetStatus(total) {
    const budget = parseMoney(budgetInput.value);
    budgetStatusEl.className = "budget-status";

    if (budget <= 0) {
        budgetStatusEl.textContent = "No budget target set.";
        return;
    }

    const ratio = total / budget;
    if (total <= budget) {
        const remain = budget - total;
        budgetStatusEl.classList.add(ratio > 0.9 ? "warn" : "good");
        budgetStatusEl.textContent = `${ratio > 0.9 ? "Near budget" : "On budget"} - ${money(remain)} remaining`;
    } else {
        const over = total - budget;
        budgetStatusEl.classList.add("over");
        budgetStatusEl.textContent = `Over budget by ${money(over)}`;
    }
}

function exportCsv() {
    const days = Math.max(1, parseInt(daysInput.value || "1", 10));
    if (!selectedItems.size) {
        alert("Add at least one item before exporting.");
        return;
    }

    const lines = [
        ["Item", "Qty", "Price Per Day", "Days", "Line Total"],
    ];

    selectedItems.forEach(entry => {
        const unit = getPrice(entry.item);
        const total = unit * entry.qty * days;
        lines.push([
            entry.item.name,
            String(entry.qty),
            unit.toFixed(2),
            String(days),
            total.toFixed(2),
        ]);
    });

    const csv = lines
        .map(cols => cols.map(c => `"${String(c).replace(/"/g, "\"\"")}"`).join(","))
        .join("\n");

    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "budget-build.csv";
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
}

searchInput.addEventListener("input", () => {
    clearBtn.classList.toggle("visible", searchInput.value.length > 0);
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(doSearch, 300);
});

clearBtn.addEventListener("click", () => {
    searchInput.value = "";
    clearBtn.classList.remove("visible");
    doSearch();
});

daysInput.addEventListener("input", renderSelected);
budgetInput.addEventListener("input", renderSelected);
exportBtn.addEventListener("click", exportCsv);

selectedListEl.addEventListener("input", e => {
    const id = parseInt(e.target.dataset.qtyId || "", 10);
    if (!id || !selectedItems.has(id)) return;
    const qty = Math.max(1, parseInt(e.target.value || "1", 10));
    selectedItems.get(id).qty = qty;
    renderSelected();
});

selectedListEl.addEventListener("click", e => {
    const id = parseInt(e.target.dataset.removeId || "", 10);
    if (!id) return;
    removeItem(id);
});

dropZoneEl.addEventListener("dragover", e => {
    e.preventDefault();
    dropZoneEl.classList.add("active");
});

dropZoneEl.addEventListener("dragleave", () => {
    dropZoneEl.classList.remove("active");
});

dropZoneEl.addEventListener("drop", e => {
    e.preventDefault();
    dropZoneEl.classList.remove("active");
    const id = parseInt(e.dataTransfer.getData("text/item-id") || "", 10);
    if (!id) return;
    const item = searchResultsById.get(id);
    if (item) addItem(item);
});

doSearch();
