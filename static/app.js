const searchInput = document.getElementById("searchInput");
const clearBtn = document.getElementById("clearBtn");
const categoryFilter = document.getElementById("categoryFilter");
const resultsEl = document.getElementById("results");
const loadingEl = document.getElementById("loading");
const emptyEl = document.getElementById("emptyState");
const countEl = document.getElementById("resultCount");
const modal = document.getElementById("modal");

let debounceTimer = null;
const DEBOUNCE_MS = 400;

async function doSearch() {
    const query = searchInput.value.trim();
    const category = categoryFilter.value;

    loadingEl.classList.add("active");
    resultsEl.innerHTML = "";
    emptyEl.style.display = "none";

    try {
        let url;
        if (category) {
            url = `/api/category/${encodeURIComponent(category)}`;
        } else {
            url = `/api/search?q=${encodeURIComponent(query)}&limit=60`;
        }

        const resp = await fetch(url);
        const data = await resp.json();
        const items = data.items || [];

        loadingEl.classList.remove("active");

        if (items.length === 0) {
            emptyEl.style.display = "";
            countEl.textContent = "0 results";
            return;
        }

        countEl.textContent = query || category
            ? `${items.length} result${items.length !== 1 ? "s" : ""}`
            : `${data.total || items.length} items`;

        renderCards(items);
    } catch (err) {
        loadingEl.classList.remove("active");
        resultsEl.innerHTML = `<p style="color:red;padding:20px;">Search error: ${err.message}</p>`;
    }
}

function renderCards(items) {
    resultsEl.innerHTML = "";
    const frag = document.createDocumentFragment();

    items.forEach(item => {
        const card = document.createElement("div");
        card.className = "card";
        card.addEventListener("click", () => openModal(item));

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

        const name = document.createElement("div");
        name.className = "card-name";
        name.textContent = item.name;
        body.appendChild(name);

        if (item.category) {
            const cat = document.createElement("span");
            cat.className = "card-cat";
            cat.textContent = item.category;
            body.appendChild(cat);
        }

        card.appendChild(body);
        frag.appendChild(card);
    });

    resultsEl.appendChild(frag);
}

function openModal(item) {
    document.getElementById("modalName").textContent = item.name;
    document.getElementById("modalCategory").textContent = item.category || "";
    document.getElementById("modalCategory").style.display = item.category ? "" : "none";

    const img = document.getElementById("modalImg");
    if (item.thumb_file) {
        img.src = `/thumbnails/${item.thumb_file}`;
        img.alt = item.name;
        img.style.display = "";
    } else {
        img.style.display = "none";
    }

    const extraEl = document.getElementById("modalExtra");
    extraEl.innerHTML = "";
    if (item.extra && Object.keys(item.extra).length > 0) {
        Object.entries(item.extra).forEach(([key, val]) => {
            let display = escHtml(val);
            if (key === "Price" && val) {
                const num = parseFloat(val);
                if (!isNaN(num)) display = "$" + num.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
            }
            const row = document.createElement("div");
            row.className = "extra-row";
            row.innerHTML = `<span class="extra-label">${escHtml(key)}</span><span>${display}</span>`;
            extraEl.appendChild(row);
        });
    }

    modal.style.display = "";
    document.body.style.overflow = "hidden";
}

function closeModal() {
    modal.style.display = "none";
    document.body.style.overflow = "";
}

function escHtml(str) {
    const d = document.createElement("div");
    d.textContent = str;
    return d.innerHTML;
}

searchInput.addEventListener("input", () => {
    clearBtn.classList.toggle("visible", searchInput.value.length > 0);
    categoryFilter.value = "";
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(doSearch, DEBOUNCE_MS);
});

clearBtn.addEventListener("click", () => {
    searchInput.value = "";
    clearBtn.classList.remove("visible");
    doSearch();
});

categoryFilter.addEventListener("change", () => {
    searchInput.value = "";
    clearBtn.classList.remove("visible");
    doSearch();
});

modal.querySelector(".modal-backdrop").addEventListener("click", closeModal);
modal.querySelector(".modal-close").addEventListener("click", closeModal);
document.addEventListener("keydown", e => {
    if (e.key === "Escape") closeModal();
});

async function loadCategories() {
    try {
        const resp = await fetch("/api/categories");
        const data = await resp.json();
        (data.categories || []).forEach(cat => {
            const opt = document.createElement("option");
            opt.value = cat;
            opt.textContent = cat;
            categoryFilter.appendChild(opt);
        });
    } catch (_) {}
}

loadCategories();
doSearch();
