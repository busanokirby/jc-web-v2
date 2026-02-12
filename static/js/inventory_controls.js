document.addEventListener('DOMContentLoaded', function () {
    // Quick add stepper
    const qaInc = document.getElementById('qa-inc');
    const qaDec = document.getElementById('qa-dec');
    const qaStock = document.getElementById('qa-stock');
    const qaForm = document.getElementById('quick-add-form');

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
});