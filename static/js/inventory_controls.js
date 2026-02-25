document.addEventListener('DOMContentLoaded', function () {
    // Quick add stepper
    const qaInc = document.getElementById('qa-inc');
    const qaDec = document.getElementById('qa-dec');
    const qaStock = document.getElementById('qa-stock');
    const qaForm = document.getElementById('quick-add-form');

    // Product form validation
    const productForm = document.getElementById('product-form');
    if (productForm) {
        productForm.addEventListener('submit', function(e) {
            if (!productForm.checkValidity()) {
                e.preventDefault();
                e.stopPropagation();
            }
            productForm.classList.add('was-validated');
        });
    }

    // Category modal (when adding/editing product)
    const addCatBtn = document.getElementById('add-category-btn');
    if (addCatBtn) {
        const catModal = new bootstrap.Modal(document.getElementById('addCategoryModal'));
        addCatBtn.addEventListener('click', () => catModal.show());
        const saveCatBtn = document.getElementById('save-category-btn');
        const newCatName = document.getElementById('new-category-name');
        const addCatAlert = document.getElementById('add-cat-alert');
        saveCatBtn.addEventListener('click', async () => {
            const name = newCatName.value.trim();
            if (!name) {
                addCatAlert.textContent = 'Name is required';
                addCatAlert.style.display = 'block';
                return;
            }
            try {
                const res = await fetch('/inventory/categories/add', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({name})
                });
                const json = await res.json();
                if (!json.success) {
                    addCatAlert.textContent = json.message || 'Error saving category';
                    addCatAlert.style.display = 'block';
                    return;
                }
                // append new option and select it
                const select = document.getElementById('category-select');
                const opt = document.createElement('option');
                opt.value = json.id;
                opt.textContent = json.name;
                opt.selected = true;
                select.appendChild(opt);
                catModal.hide();
                newCatName.value = '';
                addCatAlert.style.display = 'none';
            } catch (err) {
                addCatAlert.textContent = 'Network error';
                addCatAlert.style.display = 'block';
            }
        });
    }

    if (qaInc) {
        qaInc.addEventListener('click', () => {
            qaStock.value = Math.max(0, parseInt(qaStock.value || '0') + 1);
        });
    }
    if (qaDec) {
        qaDec.addEventListener('click', () => {
            qaStock.value = Math.max(0, parseInt(qaStock.value || '0') - 1);
        });
    }

    if (qaForm) {
        qaForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const data = {
                name: document.getElementById('qa-name').value.trim(),
                sku: document.getElementById('qa-sku').value.trim(),
                category_id: document.getElementById('qa-cat').value || null,
                opening_stock: document.getElementById('qa-stock').value || 0
            };
            try {
                const res = await fetch('/inventory/products/add_quick', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                const json = await res.json();
                if (!json.success) {
                    alert(json.message || 'Error adding product');
                    return;
                }
                // Reload the page to simplify UI update
                window.location.reload();
            } catch (err) {
                alert('Error adding product');
            }
        });
    }

    // Adjust buttons
    document.querySelectorAll('.btn-adjust').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            e.preventDefault();
            const productId = btn.dataset.id;
            const delta = parseInt(btn.dataset.delta);
            try {
                const res = await fetch(`/inventory/products/${productId}/adjust`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ delta: delta })
                });
                const json = await res.json();
                if (!json.success) {
                    alert(json.message || 'Error adjusting stock');
                    return;
                }
                const row = document.querySelector(`tr[data-product-id='${productId}']`);
                if (row) {
                    const num = row.querySelector('.stock-number');
                    if (num) {
                        num.textContent = json.stock;
                    } else {
                        // Unexpected structure: log and reload to keep UI consistent
                        console.warn('Expected .stock-number not found, reloading to sync UI');
                        window.location.reload();
                    }
                }
            } catch (err) {
                alert('Error adjusting stock');
            }
        });
    });

    // Delete product buttons (on listing page)
    document.querySelectorAll('.btn-delete-product').forEach(btn => {
        btn.addEventListener('click', async e => {
            e.preventDefault();
            if (!confirm('Delete this product permanently?')) return;
            const productId = btn.dataset.productId;
            try {
                const res = await fetch(`/inventory/products/${productId}/delete`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    body: JSON.stringify({})
                });
                const json = await res.json();
                if (!json.success) {
                    alert(json.message || 'Error deleting product');
                    return;
                }
                // remove row or reload
                const row = document.querySelector(`tr[data-product-id='${productId}']`);
                if (row) {
                    row.remove();
                } else {
                    window.location.reload();
                }
            } catch (err) {
                alert('Network error');
            }
        });
    });
});