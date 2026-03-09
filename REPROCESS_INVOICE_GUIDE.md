# Invoice Reprocess Feature Guide

## Overview
The **Reprocess Invoice** feature allows administrators to re-handle payments and inventory for existing sales invoices. This is useful when payment processing failed or needs to be redone, or when you need to ensure inventory consistency.

---

## What is Reprocessing?

Reprocessing an invoice means:
- All current sale items will have their stock quantities returned to inventory (stock is restored before the sale record is deleted).
- If stock restoration fails for any item the process will abort and no changes will be made, preventing inventory loss.
1. **Restoring Stock** - All items in the invoice are returned to inventory (as if the sale was reversed)
2. **Clearing Payments** - All existing payment records are removed
3. **Resetting Status** - The sale is marked as PARTIAL, ready for fresh payment processing
4. **Preserving History** - All original transaction data remains in the database for audit purposes

---

## How to Use Reprocess

### Step 1: Open Invoice
1. Navigate to **Sales Management** → **Invoice** or use the sales list
2. Click on the specific invoice you want to reprocess
3. The invoice details page will display

### Step 2: Click Reprocess Button
- In the top-right action bar, click **"Reprocess Invoice"** button (blue info button with refresh icon)
- An admin-only feature - only users with ADMIN or SALES role can see this button

### Step 3: Review Modal
A modal dialog will appear showing:
- Current invoice number and total
- What will happen during reprocessing
- Important use case information
- Warning that this is a significant action

### Step 4: Confirm Reprocess

> **Note:** As part of the reprocessing routine the system will automatically return the quantity of each sold item back into inventory.  This is performed *before* the sale record and payments are removed; if any restoration step fails the operation will stop and you will see an error message so that no stock is lost.

- Click **"Yes, Reprocess Invoice"** button to proceed
- The action will process immediately
- You'll see a success message with details

### Step 5: Fresh Payment Processing
After reprocessing:
- The invoice status becomes **PARTIAL**
- All stock has been restored
- You can now process payments fresh
- Navigate to payment processing or POS to handle payments again

---

## What Gets Restored?

### ✅ Items Restored to Stock
- All **active items** in the invoice (except revoked items)
- **Product stock levels** increase by the original quantity sold
- **Non-service items only** (services don't affect stock)

### ✅ Payments Cleared
- All payment records are **deleted**
- Previous payment history is logged in the system
- You start fresh with $0 paid on the invoice

### ✅ Status Reset
- Sale status → **PARTIAL**
- Credit claim status reset → **False**
- Ready for fresh payment processing

---

## What Does NOT Get Changed?

### 🔒 Preserved Information
- **Revoked items** - Already handled separately, stay revoked
- **Original audit trail** - All original transaction data remains
- **Invoice number** - Stays the same
- **Customer information** - No changes
- **Item prices** - Sales prices remain unchanged
- **Comments/notes** - All notes stay on the invoice

---

## Use Cases

### ✅ When to Reprocess

1. **Payment Processing Failed**
   - POS crashed during payment
   - Payment gateway error occurred
   - Need to re-handle payment from the beginning

2. **Ensure Inventory Consistency**
   - After a partial revocation, ensure stock is correct
   - Reconcile inventory if there was a system issue
   - Clean up after a failed transaction

3. **Customer Request**
   - Customer wants a fresh processing of their purchase
   - Need to adjust payment plan or method
   - Redoing the entire transaction properly

### ❌ When NOT to Reprocess

- You only need to **revoke a single item** → Use "Revoke Item" button instead
- You want to **completely delete** the invoice → Use "Delete Sale" button instead
- Invoice is already **fully paid** and needs nothing changed

---

## Important Warnings

### ⚠️ Before You Reprocess
1. **Verify the need** - Is this really necessary?
2. **Check stock** - Ensure inventory levels are correct before/after
3. **Customer notification** - Consider if customer needs to be informed
4. **Audit trail** - This action will be logged in the system

### ⚠️ After Reprocessing
1. **Re-process payments** - You must now record payment again
2. **Verify stock levels** - Check that inventory was restored correctly
3. **Communicate with customer** - If they need to know about the change
4. **Print new receipt** - If you issued a new printed invoice, print payment receipt

---

## Technical Details

### Backend Route
```
POST /sales/<sale_id>/reprocess
```
- **Auth Required**: Yes (ADMIN or SALES role only)
- **Returns**: JSON with success status and details

### Response Example - Success
```json
{
  "success": true,
  "message": "Invoice reprocessed successfully! 3 items returned to stock (5 units), 1 payment records cleared.",
  "data": {
    "sale_id": 123,
    "invoice_no": "INV-2024-001",
    "items_processed": 3,
    "total_qty_restored": 5,
    "payments_cleared": 1,
    "total_payments_cleared": 500.00,
    "new_status": "PARTIAL"
  }
}
```

### Stock Movement Tracking
- Each reprocessed item creates a stock movement entry
- **Movement Type**: IN (inventory addition)
- **Reference Type**: REPROCESSING
- **Notes**: "Invoice [INV-NO] reprocessing - restored for fresh payment processing"
- Preserved in audit logs for compliance/tracking

---

## Solving Common Issues

### Issue: Reprocess Button Not Visible
**Solution**: You need ADMIN or SALES role to see this button

### Issue: Stock Not Restored After Reprocess
**Solution**: 
- Services don't affect stock, so they won't appear in restoration count
- Check that items were actually in the invoice
- Verify the product is not marked as a service

### Issue: Need to Re-revoke Items
**Solution**: 
- Revoked items are NOT restored during reprocessing
- If you need them restored, you must delete the sale entirely
- Or contact admin for manual database correction

### Issue: Customer Paid But Reprocessed
**Solution**:
- Payment records are cleared, but you need to handle refunds separately
- Document the refund process outside the system
- Create a new payment record when re-processed payment is made

---

## Audit & Compliance

All reprocessing actions are tracked:
- **Who**: Current user (admin/sales staff)
- **When**: Timestamp of reprocessing
- **What**: Invoice number, items affected, stock changes
- **History**: All previous transaction data preserved

For compliance review:
- Check stock movement logs for REPROCESSING references
- Review sale payment history before deletion
- Access audit logs if available in your system

---

## Support

If you have issues with reprocessing:
1. Check this guide for common issues
2. Review the success message for details about what was processed
3. Verify stock levels manually in inventory
4. Contact system administrator if persistent issues occur

---

## Summary

The **Reprocess Invoice** feature is a powerful tool for:
- ✅ Fixing failed payment transactions
- ✅ Ensuring inventory consistency
- ✅ Handling customer requests for fresh processing
- ✅ Maintaining complete audit trails

**Always verify the action is necessary before clicking "Yes, Reprocess Invoice"**

---

*Last Updated: March 5, 2026*
*Feature Version: 1.0*
