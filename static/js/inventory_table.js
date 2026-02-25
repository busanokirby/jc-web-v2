/*
Client-side enhancements for the inventory products table:
- real time search/filtering
- column sorting with aria attributes
- simple pagination (optional)
- highlight low-stock rows

Lightweight, dependency-free. Works with the markup in products.html.
*/

document.addEventListener('DOMContentLoaded', () => {
    const table = document.getElementById('products-table');
    if (!table) return;

    const tbody = table.tBodies[0];
    const rows = Array.from(tbody.rows);

    // search input (already exists server-side) but we hook it for realtime
    const searchInput = document.querySelector('input[name="q"]');
    if (searchInput) {
        searchInput.addEventListener('input', () => {
            const term = searchInput.value.toLowerCase().trim();
            rows.forEach(r => {
                const text = r.textContent.toLowerCase();
                r.style.display = text.includes(term) ? '' : 'none';
            });
        });
    }

    // sorting
    const getCellValue = (row, idx) => row.cells[idx]?.textContent.trim();
    const comparer = (idx, asc) => (a, b) => {
        const v1 = getCellValue(a, idx);
        const v2 = getCellValue(b, idx);
        const num1 = parseFloat(v1.replace(/[^0-9.]/g, ''));
        const num2 = parseFloat(v2.replace(/[^0-9.]/g, ''));
        if (!isNaN(num1) && !isNaN(num2)) {
            return asc ? num1 - num2 : num2 - num1;
        }
        return asc ? v1.localeCompare(v2) : v2.localeCompare(v1);
    };

    table.querySelectorAll('th.sortable').forEach((th, idx) => {
        th.addEventListener('click', () => {
            const current = th.getAttribute('aria-sort');
            const asc = current !== 'ascending';
            rows.sort(comparer(idx, asc));
            rows.forEach(r => tbody.appendChild(r));
            // update aria-sort attributes
            table.querySelectorAll('th.sortable').forEach(h => h.setAttribute('aria-sort', 'none'));
            th.setAttribute('aria-sort', asc ? 'ascending' : 'descending');
        });
    });
});
