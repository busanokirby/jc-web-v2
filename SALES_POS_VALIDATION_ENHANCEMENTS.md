# POS Validation Enhancements (Retain Input on Errors)

**Date**: March 5, 2026

When the POS form encountered validation errors (empty cart, invalid quantity, insufficient stock, etc.) the previous implementation redirected back to `/pos`. This caused the entire form — items, customer, discount, notes, etc. — to be wiped out, forcing the user to re-enter everything.

### Goals

- Warn user about the problem instead of losing their data
- Preserve all entered values on validation failures
- Restore the cart & form state when errors occur

### Changes

1. **Backend (`sales/routes.py`)**
   
   - Built `products_json` early and helper `render_pos_with_data()` to centralize rendering logic.
   - On every validation failure or exception during POST, call `render_pos_with_data(**preload)` instead of redirecting.
   - Preload dictionary collects all submitted form values (items JSON, customer, discount, payment amount, notes, deposit/claim flags, department details).
   - Added preload in stock-out exception path as well.   - Ensure the `customer_id` value is always included in the preload so the selected customer is preserved after an error.
2. **Frontend (`templates/sales/pos.html`)**

   - Inject `window.preloaded_*` JavaScript variables using Jinja.
   - Restore the cart, customer selection, discount, payment amount, notes, deposit/claim checkboxes, department/new-department inputs on page load.
   - Show restored items immediately by calling `updateCart()`.
   - Adjust department toggling logic after restoring the department ID.
   - Preloaded restoration happens before reprocessed-item handling, so both features work seamlessly.

   Example snippet added at top of script:
   ```js
   window.preloaded_items_json = {{ preloaded_items_json|tojson(default='null') }};
   // ... other preload vars ...
   
   let cart = [];
   const products = JSON.parse(document.getElementById('products-data').textContent);
   // restore preloaded cart
   if (window.preloaded_items_json) {
       /* parse and push items */
       updateCart();
   }
   ```

3. **Behavior**

   - User fills cart and form, then triggers an error (e.g. stock shortage).
   - Flash message appears at top of page but the form remains populated exactly as before.
   - User can correct the offending item/field and resubmit.

### Testing Checklist

- [ ] Try submitting an empty cart → flash + data retained (cart still empty though)
- [ ] Enter item with qty zero → flash + cart preserved
- [ ] Enter item quantity exceeding stock → flash + cart preserved
- [ ] Simulate stock_out raising `StockError` (e.g. product with negative stock) → flash + cart preserved
- [ ] Force JSON decode error (malformed items JSON) → flash + cart preserved
- [ ] Choose deposit and claim simultaneously → flash + form preserved
- [ ] Verify department/new-department fields restored properly after reload

### Notes

This solution avoids duplication by rendering the template with the same context used for GET requests. It does not add any session storage or temporary DB state. The `preloaded_*` variables are ephemeral, only used when re-rendering as part of a POST error.

Feel free to extend the preload list if more fields are added later.
