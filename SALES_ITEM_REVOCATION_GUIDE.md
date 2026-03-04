# Sales Item Revocation Feature - Implementation Guide

## Overview
This implementation adds the ability to revoke (remove) individual products from processed sales without deleting the entire invoice. This addresses the efficiency issue when mistakes are made in sales - users can now remove just the problematic items instead of losing the entire transaction record.

## Key Features Added

### 1. **Individual Item Revocation**
   - Revoke specific products from a sale one at a time
   - Maintain audit trail with timestamp, reason, and who revoked it
   - Stock is automatically restored for revoked items
   - Sale totals are recalculated automatically

### 2. **Enhanced Sales Item Model**
   - Added revocation tracking fields:
     - `revoked_at`: Timestamp when item was revoked
     - `revoke_reason`: Text field to document why the item was revoked
     - `revoked_by`: Username of who performed the revocation
   - Added `is_revoked` property to check revocation status
   - Added `revoke()` method for soft-deletion with audit trail

### 3. **Improved Sales Management**
   - Sales list now shows itemized products (up to 3 visible, with "+X more" indicator)
   - Separate display of active vs. revoked items on the invoice
   - Badge showing count of revoked items
   - Full product details in sales list tooltip

### 4. **Revocation UI**
   - Revoke buttons on individual items (visible only to ADMIN and SALES roles)
   - Modal dialog for entering revocation reason
   - Confirmation with impact summary
   - Real-time page reload after successful revocation

### 5. **Audit Trail & History**
   - New `/sales/<sale_id>/revocation-history` endpoint
   - Dedicated template showing:
     - Timeline of all revocations
     - Product details for each revoked item
     - Revocation reason and timestamp
     - Who performed each revocation
     - Summary of total amounts revoked vs. current invoice total
     - Comparison between original and current invoice amounts

## Technical Implementation

### Database Changes
**Migration: `add_revocation_to_sale_items.py`**
- Adds 3 nullable columns to `sale_item` table:
  - `revoked_at` (DateTime)
  - `revoke_reason` (Text)
  - `revoked_by` (String)

### Model Changes
**File: `app/models/sales.py`**

**Sale Model - New Methods:**
```python
@property
def active_items() -> List[SaleItem]:
    """Return only non-revoked items"""

@property
def revoked_items() -> List[SaleItem]:
    """Return only revoked items"""

def calculate_totals_excluding_revoked():
    """Calculate new subtotal and total excluding revoked items"""
```

**SaleItem Model - New Fields & Methods:**
```python
revoked_at = db.Column(db.DateTime, nullable=True)
revoke_reason = db.Column(db.Text, nullable=True)
revoked_by = db.Column(db.String(100), nullable=True)

@property
def is_revoked() -> bool:
    """Check if this item has been revoked"""

def revoke(reason: str = None, revoked_by: str = None):
    """Mark this item as revoked with audit trail"""
```

### Backend Routes
**File: `app/blueprints/sales/routes.py`**

**New Endpoints:**

1. **POST `/sales/<sale_id>/item/<item_id>/revoke`**
   - Revokes a single sale item
   - Restores stock automatically
   - Recalculates sale totals
   - Returns JSON response with success status
   - Only accessible to ADMIN and SALES roles

2. **GET `/sales/<sale_id>/items-summary`**
   - Returns JSON summary of all items (active and revoked)
   - Includes separate counts and subtotals
   - Used for AJAX operations

3. **GET `/sales/<sale_id>/revocation-history`**
   - Renders audit trail page
   - Shows all revocations with full details
   - Displays timeline and impact analysis

### Template Changes

**File: `templates/sales/invoice.html`**
- Added revoke buttons for each item (print-hidden)
- Separate section for revoked items
- Revoked items shown in faded, de-emphasized style
- Modal dialog for entering revocation reason
- Link to revocation history if items are revoked
- JavaScript handling for revocation workflow

**File: `templates/sales/sales_list.html`**
- Enhanced items column to show itemized products
- Displays first 3 products with "+X more" for additional items
- Added badge for revoked item count
- Products shown with quantities

**New File: `templates/sales/revocation_history.html`**
- Comprehensive audit trail view
- Summary cards showing revocation statistics
- Detailed table with full item information
- Visual timeline of revocations
- Comparison of original vs. current invoice totals

## Usage Workflow

### For End Users (ADMIN/SALES)

1. **View Sale Invoice**
   - Navigate to Sales > Sales History
   - Click on a sale to view invoice
   - Revoke buttons appear at the end of each item row

2. **Revoke an Item**
   - Click the red revoke button (⊘) next to the item
   - Modal opens with item details
   - Enter reason for revocation (e.g., "Customer rejected", "Damaged")
   - Click "Revoke Item" to confirm
   - Page reloads and shows revoked item in separate section

3. **View Revocation History**
   - If sale has revoked items, click "Revocation History" button
   - View timeline of all revocations
   - See who revoked what and when
   - Compare original vs. current totals

4. **Sales List Enhanced View**
   - Sales list now shows product names and quantities
   - Hover over item badge shows product details
   - Revoke count badge visible if items were revoked

## Business Logic

### Sale Recalculation
When an item is revoked:
1. Item is soft-deleted (marked with `revoked_at` timestamp)
2. Stock is restored using existing `stock_in()` function
3. Sale subtotal is recalculated excluding revoked items
4. Sale total = new subtotal - discount
5. Sale status updated based on new total:
   - If all items revoked → VOID
   - If new total = payments received → PAID
   - Otherwise → PARTIAL

### Audit Trail
Each revocation records:
- Timestamp of revocation
- Reason provided by user
- Username of who performed revocation
- Original item details preserved for history

### Stock Management
- Stock automatically restored when item revoked
- Reference type: "REVOCATION"
- Notes include invoice number and revocation reason
- Maintains inventory accuracy

## Data Integrity

### Soft Deletion Approach
- Items are NOT deleted but marked as revoked
- Preserves complete history for auditing
- Allows future "un-revocation" if needed
- Maintains referential integrity

### Reversibility
While the current implementation doesn't include "un-revocation", the data structure supports it:
- Revocation data can be cleared to restore item
- Stock can be reversed if needed
- This can be added in future if required

## API Responses

### Revoke Item Response
```json
{
  "success": true,
  "message": "Item revoked: Product Name (qty: 2)",
  "data": {
    "item_id": 123,
    "product_name": "Computer Monitor",
    "qty_revoked": 2,
    "amount_saved": 8999.99,
    "new_sale_total": 15000.00,
    "new_sale_status": "PARTIAL"
  }
}
```

### Items Summary Response
```json
{
  "invoice_no": "INV-2026-001",
  "active_items": [...],
  "revoked_items": [...],
  "active_count": 3,
  "revoked_count": 1,
  "active_subtotal": 15000.00,
  "revoked_subtotal": 8999.99,
  "original_total": 24000.00,
  "current_total": 15000.00,
  "sale_status": "PARTIAL"
}
```

## Security Considerations

- Revocation only available to ADMIN and SALES roles
- All revocations logged with username
- Reason documentation enforced
- No bulk revocation (prevents accidents)
- Each revocation requires deliberate action

## Database Migration

Run the migration to add the new columns:
```bash
flask db upgrade
```

## Future Enhancements

1. **Bulk Item Operations**
   - Remove multiple items at once
   - Batch reason entry

2. **Item Re-addition**
   - "Un-revoke" functionality
   - Restore previously revoked items

3. **Reason Categories**
   - Pre-defined revocation reasons
   - Better analytics

4. **Notifications**
   - Alert customer when items revoked
   - Email notifications to staff

5. **Permission Levels**
   - Different permissions for different user types
   - Approval workflow for high-value revocations

## Testing Recommendations

1. **Functional Testing**
   - Revoke items from various sale states (PAID, PARTIAL, etc.)
   - Verify stock restoration
   - Check sale status updates
   - Confirm audit trail recording

2. **Edge Cases**
   - Revoke all items (sale becomes VOID)
   - Revoke service items (no stock)
   - Revoke from already-paid sale
   - Multiple revocations in sequence

3. **UI Testing**
   - Modal appears correctly
   - Revoke buttons visible to right roles
   - Print function excludes revoke buttons
   - Responsive design on mobile

4. **Audit Trail**
   - Verify timestamps accurate
   - Check usernames recorded correctly
   - Confirm reasons preserved
   - Validate timeline display

## Integration Notes

- Works seamlessly with existing payment tracking
- Compatible with credit claims system
- Maintains financial reconciliation accuracy
- Does not affect existing reports (uses active items only)
- Stock system integration via existing `stock_in()` function

## Performance Considerations

- Uses soft-deletion (no joins needed for history)
- Efficient query with `is_revoked` property filter
- Minimal database overhead
- No impact on invoice printing performance
