# Customer Management System Enhancement - Implementation Guide

**Date:** March 4, 2026  
**Version:** 1.0

## Overview

This implementation adds comprehensive enhancements to the customer management system, including:

1. **Department System** - Organize multi-location companies under single customer records
2. **Quick Action Buttons** - Create repairs and sales directly from customer lists
3. **Department-Linked Records** - Repairs and sales are now linked to both customers and departments

---

## Data Model Changes

### 1. New `Department` Model

**Location:** `app/models/customer.py`

```python
class Department(BaseModel, db.Model):
    """Department model for organizing repairs and sales by department within a customer account."""
    __tablename__ = "department"
    
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customer.id"), nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    contact_person = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(100))
    notes = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

**Key Features:**
- One customer can have multiple departments
- Each department tracks contact person and phone
- Departments are soft-deletable via `is_active` flag
- Indexed on `customer_id` for fast lookups

### 2. Updated `Customer` Model

**Changes:**
- Added `departments` relationship with cascade delete
- Accepts Business and Government customer types

### 3. Updated `Device` (Repair) Model

**New Fields:**
```python
department_id = db.Column(db.Integer, db.ForeignKey("department.id"), nullable=True)
```

**Relationships:**
- Optional link to Department
- Maintains backward compatibility (nullable department_id)

### 4. Updated `Sale` Model

**New Fields:**
```python
department_id = db.Column(db.Integer, db.ForeignKey("department.id"), nullable=True)
```

**Relationships:**
- Optional link to Department
- Maintains backward compatibility

---

## Database Migration

**File:** `migrations/versions/add_department_model_9a1b2c3d.py`

Run migration with:
```bash
python -m alembic upgrade head
```

**Creates:**
- `department` table with all fields
- Foreign key constraint from `device` to `department`
- Foreign key constraint from `sale` to `department`
- Index on `department.customer_id`

---

## UI Enhancements

### 1. Customers List Page (`templates/customers/customers.html`)

**New Buttons per Customer:**
- **Add Repair** - Quick repair creation modal
- **Add Sale** - Quick sale creation modal

**Features:**
- Modal pops up with customer pre-selected
- Department selector for Business/Government customers
- Create new department on-the-fly
- Minimal form for quick entry

### 2. Customer Detail Page (`templates/customers/customer_detail.html`)

**New Button Group:**
- **Add Repair** - Opens quick repair modal
- **Add Sale** - Opens quick sale modal

**Enhanced Button Layout:**
- Organized in button groups for better UX
- Color-coded (green for repair, blue for sale)

### 3. Quick Action Modals

#### Quick Repair Modal
- Department selector (for Business/Government only)
- Device type selection
- Brand, Model fields
- Issue description (required)
- New department creation option

#### Quick Sale Modal
- Department selector (for Business/Government only)
- Notes/Item description
- New department creation option
- Creates DRAFT sale record

### 4. Repair Creation Form (`templates/repairs/add_repairs.html`)

**New Department Section:**
- Shows after customer selection
- Only for Business/Government customers
- Display existing departments
- Option to create new department
- Required when creating new department

**JavaScript Enhancements:**
- `updateDepartmentOptions(customerId)` - Fetch and populate departments
- `toggleNewDepartmentSection()` - Show/hide new department form
- Auto-shows/hides department card based on customer type

---

## Backend Routes

### New Routes in Customers Blueprint

#### 1. Quick Repair Creation
```python
@customers_bp.route("/<int:customer_id>/quick-repair", methods=["POST"])
```
- Creates repair with minimal fields
- Handles department creation if needed
- Redirects to repair detail page

#### 2. Quick Sale Creation
```python
@customers_bp.route("/<int:customer_id>/quick-sale", methods=["POST"])
```
- Creates DRAFT sale record
- Handles department creation if needed
- Redirects to POS for adding items

#### 3. Departments API
```python
@customers_bp.route("/<int:customer_id>/departments-api", methods=["GET"])
```
- Returns JSON with customer info and departments
- Used by repair form for dynamic updates
- Returns only active departments

### Modified Routes

#### Repair Creation (`repairs.add_repair`)
- Extracts `department_id` from form
- Creates new Department if needed
- Links repair to department (if specified)

---

## Usage Guide

### For Business/Government Customers

#### Creating a Department:

1. **From Customer Detail:**
   - Click "Add Repair" or "Add Sale"
   - Select "+ Create New Department"
   - Enter department name and contact person
   - Proceed with repair/sale creation

2. **From Repair Creation Form:**
   - Select customer (existing)
   - Department card appears automatically
   - Choose existing department or create new
   - Repair will be linked to selected department

#### Organizing Repairs by Department:

```
ACME Corporation (Customer)
├── IT Department
│   ├── Repair JC-2026-001 (Printer)
│   └── Repair JC-2026-002 (Laptop)
├── HR Department
│   └── Repair JC-2026-003 (Desktop)
└── Main Office
    └── Sale JC-INV-001
```

### For Individual Customers

- Department selector is hidden
- Repairs and sales work exactly as before
- No department assignment needed

---

## Key Features

### 1. Duplicate Prevention
- One company = One customer record
- Multiple departments organize their work
- No more duplicate customer entries

### 2. Quick Entry
- Fast repair creation from customer list
- Minimal required fields
- Full editing available after creation

### 3. Flexible Department Management
- Create departments on-the-fly during data entry
- Add departments later via customer detail page
- Mark departments as inactive without deleting

### 4. Backward Compatibility
- All department fields are optional
- Existing repairs/sales work as before
- Can mix departmentalized and non-departmentalized records

---

## API Response Examples

### GET `/customers/{id}/departments-api`

```json
{
  "customer_id": 1,
  "customer_type": "Business",
  "departments": [
    {
      "id": 1,
      "name": "IT Department",
      "contact_person": "John Doe",
      "is_active": true
    },
    {
      "id": 2,
      "name": "HR Department", 
      "contact_person": "Jane Smith",
      "is_active": true
    }
  ]
}
```

---

## Database Queries

### Find all repairs for a specific department:
```python
repairs = Device.query.filter_by(department_id=dept_id).all()
```

### Find all departments for a customer:
```python
departments = customer.departments
```

### Find dept-specific sales:
```python
sales = Sale.query.filter_by(department_id=dept_id).all()
```

---

## Front-End Interactions

### Modal Data Passing:
- Customer ID passed via `data-customer-id` attribute
- Customer name displayed in modal
- Form action URL updated dynamically

### Department Selection Logic:
```javascript
// Show department section only for Business/Government
if (customerType === 'Business' || customerType === 'Government') {
    departmentCard.style.display = 'block';
}
```

### New Department Creation:
```javascript
if (departmentSelect.value === '__new__') {
    newDepartmentSection.style.display = 'block';
    // User fills in name and contact person
}
```

---

## Migration Checklist

- [ ] Run database migration: `alembic upgrade head`
- [ ] Clear browser cache (template changes)
- [ ] Restart Flask application
- [ ] Test quick repair creation
- [ ] Test quick sale creation
- [ ] Test department creation during repair/sale entry
- [ ] Verify existing repairs/sales still display
- [ ] Test with Business customer type
- [ ] Test with Government customer type
- [ ] Test with Individual customer type

---

## Security Considerations

1. **Role-Based Access:**
   - Quick repair: ADMIN, TECH only
   - Quick sale: ADMIN, SALES only
   - API endpoints check user roles

2. **Department Ownership:**
   - Departments always belong to a customer
   - Can't create department without valid customer_id

3. **Cascading Deletes:**
   - Deleting customer cascades to all departments
   - Deleting department cascades to related repairs/sales
   - Use soft-delete (`is_active`) to preserve data

---

## Future Enhancements

1. **Department User Permissions:**
   - Assign users access to specific departments
   - Granular role-based access control

2. **Department Reports:**
   - Revenue by department
   - Pending repairs per department
   - Department contact history

3. **Bulk Department Operations:**
   - Move repairs between departments
   - Merge departments
   - Archive unused departments

4. **Department Templates:**
   - Create department templates for common structures
   - Auto-populate new customers with default departments

---

## Troubleshooting

### Department selector not showing:
- Verify customer type is 'Business' or 'Government'
- Check browser console for JavaScript errors
- Ensure `updateDepartmentOptions()` is called

### New department not saved:
- Verify `new_department_name` field is required
- Check form submission in browser network tab
- Look for validation errors in logs

### Repairs not linking to department:
- Check `department_id` in database
- Verify migration ran successfully
- Inspect Device model relationships

---

## File Summary

**Models Modified:**
- `app/models/customer.py` - Added Department model
- `app/models/repair.py` - Added department_id field
- `app/models/sales.py` - Added department_id field

**Routes Added:**
- `app/blueprints/customers/routes.py` - 3 new endpoints

**Templates Modified:**
- `templates/customers/customers.html` - Quick action buttons + modals
- `templates/customers/customer_detail.html` - Quick action buttons + modals
- `templates/repairs/add_repairs.html` - Department selection section

**Migration:**
- `migrations/versions/add_department_model_9a1b2c3d.py`

---

## Support

For issues or questions about this implementation:
1. Check the Troubleshooting section above
2. Review browser console for client-side errors
3. Check application logs for server-side errors
4. Verify all files were modified correctly
5. Run database migration to ensure schema is up-to-date
