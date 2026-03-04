# Sales Item Revocation - Quick Reference

## What's New?

Your sales system now has **granular item management** instead of just invoice-level deletion:

### 1. **Individual Product Revocation** ✓
- Revoke specific items without losing the entire sale
- Perfect for fixing mistakes (wrong product, damaged item, customer rejection, etc.)
- Automatically restores stock for revoked items

### 2. **Itemized Sales View** ✓
- Sales list now shows what products are in each sale
- First 3 items visible with "+X more" indicator
- See product names, quantities, and amounts at a glance

### 3. **Audit Trail** ✓
- Complete history of all revocations
- Timestamps, reasons, and who made changes
- View original vs. current invoice totals
- Visual timeline of changes

## How to Use It

### Revoke an Item from a Sale

1. Open a processed sale from **Sales > Sales History**
2. View the invoice
3. Find the item to revoke and click the red ⊘ button
4. Enter reason for revocation (e.g., "Customer rejected", "Damaged in shipping")
5. Click "Revoke Item" to confirm
6. Sale automatically updates:
   - New total calculated
   - Stock is restored
   - Item moves to "Revoked Items" section

### View Revocation History

1. On an invoice with revoked items, click **"Revocation History"** button
2. View complete audit trail:
   - What was revoked
   - When and by whom
   - Why it was revoked
   - Summary of original vs. current amounts

### See Itemized Products in Sales List

1. Go to **Sales > Sales History**
2. Look at the "Items" column
3. See products and quantities inline
4. Revoked items shown with a count badge

## What Happens When You Revoke an Item?

✓ Item is marked as revoked (not deleted - history preserved)  
✓ Stock is automatically restored  
✓ Sale total is recalculated  
✓ Sale status updates if needed  
✓ Reason is recorded for audit trail  
✓ Username and timestamp are logged  

## Example Scenarios

### Scenario 1: Wrong Item Added
- Customer ordered "Monitor" but you added "Keyboard" by mistake
- Revoke the Keyboard item with reason: "Wrong item - will add correct product"
- Sale total adjusts
- Stock for Keyboard restored
- Can then manually add Monitor or create new line item

### Scenario 2: Damaged Product
- Item arrived damaged or customer found defect
- Revoke item with reason: "Product defective - customer returning"
- Stock restored for return/replacement
- Sale reflects what customer actually received
- Keeps transaction record for accounting

### Scenario 3: Quantity Adjustment
- Created sale with 5 units, customer only wants 3
- Revoke the items (qty 2) with reason: "Customer requested quantity reduction"
- Sale adjusts to 3 units
- Remaining stock corrected
- Invoice accurately reflects what was sold

## Permission Levels

Only **ADMIN** and **SALES** users can:
- Revoke items
- View revocation history
- See revoke options on invoices

Walk-in and other roles cannot revoke items.

## Technical Details

### Database Changes
- Added 3 columns to track revocation status
- Migration: `add_revocation_to_sale_items.py`
- Run `flask db upgrade` to apply

### New Endpoints
- `POST /sales/<id>/item/<id>/revoke` - Revoke an item
- `GET /sales/<id>/items-summary` - Get item details (JSON)
- `GET /sales/<id>/revocation-history` - View audit trail

### Files Modified
- [app/models/sales.py](app/models/sales.py) - Added revocation model
- [app/blueprints/sales/routes.py](app/blueprints/sales/routes.py) - New endpoints
- [templates/sales/invoice.html](templates/sales/invoice.html) - Revoke UI
- [templates/sales/sales_list.html](templates/sales/sales_list.html) - Enhanced view
- [templates/sales/revocation_history.html](templates/sales/revocation_history.html) - New

### New Files
- [migrations/versions/add_revocation_to_sale_items.py](migrations/versions/add_revocation_to_sale_items.py)
- [templates/sales/revocation_history.html](templates/sales/revocation_history.html)

## Key Benefits

1. **No More Invoice Deletion** - Fix mistakes without losing the entire transaction
2. **Better Accountability** - Audit trail shows what happened and who did it
3. **Accurate Inventory** - Stock automatically managed when items revoked
4. **Financial Records** - Original amounts preserved for reconciliation
5. **Flexible Management** - Handle complex scenarios (damaged goods, wrong items, returns)
6. **Compliance** - Complete history for regulatory/audit requirements

## Deployment Steps

1. **Backup Database** - Always backup before migrations
   ```bash
   # Create backup
   ```

2. **Apply Migration**
   ```bash
   flask db upgrade
   ```

3. **Test in Development**
   - Create a test sale
   - Try revoking an item
   - Check stock restoration
   - View revocation history

4. **Deploy to Production**
   - Follow your standard deployment process
   - Notify users of new feature
   - Provide training if needed

## FAQ

**Q: Can I un-revoke an item?**  
A: Current version doesn't support this, but the data structure allows for future implementation. Contact dev team if needed.

**Q: What if I revoke all items from a sale?**  
A: The sale status becomes "VOID" and total becomes ₱0.00. Original record preserved for history.

**Q: Does revoking affect payment tracking?**  
A: No, existing payments stay recorded. You may need to adjust if sale status changes.

**Q: Can customers see revoked items?**  
A: No, only staff with ADMIN/SALES role see revocation details.

**Q: What about duplicate invoices?**  
A: Revocation tracks item-level changes, so invoice number remains unique even with revocations.

**Q: Does this affect reports?**  
A: Reports use active items only, so revoked items automatically excluded from most calculations.

## Support

For issues or questions:
1. Check the detailed guide: [SALES_ITEM_REVOCATION_GUIDE.md](SALES_ITEM_REVOCATION_GUIDE.md)
2. Review Implementation Guide for technical details
3. Contact development team with specifics

---

**Version:** 1.0  
**Date Implemented:** March 4, 2026  
**Status:** Production Ready
