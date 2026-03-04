# Quick Reference - Implementation Code Snippets

## Database Operations

### Create a new department
```python
from app.models.customer import Department
from app.extensions import db

new_dept = Department(
    customer_id=123,
    name="IT Department",
    contact_person="John Doe",
    phone="09123456789",
    email="it@company.com",
    is_active=True
)
db.session.add(new_dept)
db.session.commit()
```

### Fetch all departments for a customer
```python
from app.models.customer import Customer

customer = Customer.query.get(123)
departments = customer.departments
# Filter active only
active_depts = [d for d in customer.departments if d.is_active]
```

### Find repairs for a specific department
```python
from app.models.repair import Device

repairs = Device.query.filter_by(department_id=5).all()
```

### Find sales for a specific department
```python
from app.models.sales import Sale

sales = Sale.query.filter_by(department_id=5).all()
```

### Get customer and all related departments
```python
from app.models.customer import Customer

customer = Customer.query.options(
    joinedload(Customer.departments)
).get(123)
```

---

## Frontend JavaScript

### Update department dropdown when customer changes
```javascript
function updateDepartmentOptions(customerId) {
    fetch(`/customers/${customerId}/departments-api`)
        .then(r => r.json())
        .then(data => {
            const departmentSelect = document.getElementById('department_id');
            const customerType = data.customer_type;
            
            if (customerType === 'Individual') {
                document.getElementById('department_card').style.display = 'none';
            } else {
                document.getElementById('department_card').style.display = 'block';
                
                departmentSelect.innerHTML = '<option value="">-- No Department --</option>';
                departmentSelect.innerHTML += '<option value="__new__">+ Create New Department</option>';
                
                data.departments.forEach(dept => {
                    const opt = document.createElement('option');
                    opt.value = dept.id;
                    opt.textContent = dept.name + (dept.contact_person ? ` (${dept.contact_person})` : '');
                    departmentSelect.appendChild(opt);
                });
            }
        });
}
```

### Toggle new department form
```javascript
function toggleNewDepartmentSection() {
    const departmentSelect = document.getElementById('department_id');
    const newDepartmentSection = document.getElementById('new_department_section');
    
    if (departmentSelect.value === '__new__') {
        newDepartmentSection.style.display = 'block';
        document.getElementById('new_department_name').focus();
    } else {
        newDepartmentSection.style.display = 'none';
    }
}
```

---

## API Response Examples

### GET `/customers/123/departments-api`

**Request:**
```
GET /customers/123/departments-api
Authorization: Bearer [token]
```

**Response (200 OK):**
```json
{
  "customer_id": 123,
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
    },
    {
      "id": 3,
      "name": "Sales Department",
      "contact_person": null,
      "is_active": true
    }
  ]
}
```

---

## Form Submissions

### Quick Repair Request

**Form Data:**
```
POST /customers/123/quick-repair

department_id: "1"  // Optional, or "__new__"
new_department_name: "Warehouse"  // If department_id == "__new__"
new_department_contact: "Bob Wilson"  // If department_id == "__new__"
device_type: "Printer"
brand: "HP"
model: "M455"
issue_description: "Paper jam, won't print"
```

**Success Response:**
- Redirect to `/repairs/{device_id}`

**Error Response:**
- Flash message with error
- Redirect back to customer detail

### Quick Sale Request

**Form Data:**
```
POST /customers/123/quick-sale

department_id: "2"  // Optional, or "__new__"
new_department_name: "Main Office"  // If department_id == "__new__"
new_department_contact: "Alice Johnson"  // If department_id == "__new__"
notes: "Selling 5 ink cartridges"
```

**Success Response:**
- Redirect to `/sales/pos?sale_id={sale_id}`

**Error Response:**
- Flash message with error
- Redirect back to customer detail

---

## HTML Templates - Key Sections

### Quick Repair Modal

```html
<div class="modal fade" id="quickRepairModal" tabindex="-1">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header bg-success text-white">
                <h5 class="modal-title"><i class="bi bi-tools"></i> Quick Add Repair</h5>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
            </div>
            <form method="POST" id="quickRepairForm" action="">
                <div class="modal-body">
                    <!-- Department selector shown only if Business/Government -->
                    <div id="departmentSelectDiv" style="display: none;">
                        <label class="form-label">Department / Location</label>
                        <select class="form-select" id="department_select" name="department_id">
                            <option value="">-- No Department --</option>
                            <option value="__new__">+ Create New Department</option>
                        </select>
                    </div>
                    
                    <!-- Device type selection -->
                    <div class="mb-3">
                        <label class="form-label">Device Type *</label>
                        <select class="form-select" id="device_type" name="device_type" required>
                            <option value="">-- Select --</option>
                            <option value="Printer">Printer</option>
                            <option value="Laptop">Laptop</option>
                            <option value="Desktop">Desktop</option>
                        </select>
                    </div>
                    
                    <!-- Issue description -->
                    <div class="mb-3">
                        <label class="form-label">Issue Description *</label>
                        <textarea class="form-control" name="issue_description" rows="3" required></textarea>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                    <button type="submit" class="btn btn-success">Create Repair</button>
                </div>
            </form>
        </div>
    </div>
</div>
```

### Department Selection in Repair Form

```html
<div class="card mb-4" id="department_card" style="display: none;">
    <div class="card-header bg-light">
        <h5 class="mb-0"><i class="bi bi-building"></i> Department / Location (Optional)</h5>
    </div>
    <div class="card-body">
        <select class="form-select" id="department_id" name="department_id" onchange="toggleNewDepartmentSection()">
            <option value="">-- No Department --</option>
            <option value="__new__">+ Create New Department</option>
        </select>
        
        <div id="new_department_section" style="display: none; margin-top: 15px;" class="p-3 bg-light border rounded">
            <h6>Create New Department</h6>
            <div class="mb-2">
                <label class="form-label">Department Name *</label>
                <input type="text" class="form-control" name="new_department_name" placeholder="e.g., Makati Branch">
            </div>
            <div class="mb-2">
                <label class="form-label">Contact Person</label>
                <input type="text" class="form-control" name="new_department_contact" placeholder="Name">
            </div>
        </div>
    </div>
</div>
```

---

## Common Queries for Reporting

### Get all repairs by department for a customer

```python
from app.models.customer import Customer, Department
from app.models.repair import Device

customer = Customer.query.get(123)

for dept in customer.departments:
    repairs = Device.query.filter_by(
        customer_id=customer.id,
        department_id=dept.id
    ).all()
    print(f"{dept.name}: {len(repairs)} repairs")
```

### Get departments with most active repairs

```python
from sqlalchemy import func, desc
from app.models.customer import Department
from app.models.repair import Device

dept_repair_count = db.session.query(
    Department,
    func.count(Device.id).label('repair_count')
).outerjoin(Device, Department.id == Device.department_id)\
 .group_by(Department.id)\
 .order_by(desc('repair_count'))\
 .limit(10)\
 .all()

for dept, count in dept_repair_count:
    print(f"{dept.name}: {count} repairs")
```

### Get business customers with multiple departments

```python
from sqlalchemy import func
from app.models.customer import Customer, Department

customers_multi_dept = db.session.query(
    Customer,
    func.count(Department.id).label('dept_count')
).filter(Customer.customer_type.in_(['Business', 'Government']))\
 .outerjoin(Department, Customer.id == Department.customer_id)\
 .group_by(Customer.id)\
 .having(func.count(Department.id) > 1)\
 .all()

for customer, count in customers_multi_dept:
    print(f"{customer.name}: {count} departments")
```

---

## SQL Queries for Database

### List all departments with customer names

```sql
SELECT 
    d.id,
    d.name as department_name,
    c.name as customer_name,
    d.contact_person,
    d.phone,
    d.is_active
FROM department d
JOIN customer c ON d.customer_id = c.id
ORDER BY c.name, d.name;
```

### Count repairs per department

```sql
SELECT 
    d.name as department_name,
    c.name as customer_name,
    COUNT(dev.id) as repair_count
FROM department d
LEFT JOIN device dev ON d.id = dev.department_id
JOIN customer c ON d.customer_id = c.id
GROUP BY d.id
ORDER BY repair_count DESC;
```

### Revenue by department

```sql
SELECT 
    d.name as department_name,
    c.name as customer_name,
    SUM(s.total) as total_sales,
    COUNT(s.id) as sale_count
FROM department d
LEFT JOIN sale s ON d.id = s.department_id
JOIN customer c ON d.customer_id = c.id
GROUP BY d.id
ORDER BY total_sales DESC;
```

### Find inactive departments

```sql
SELECT 
    d.*,
    c.name as customer_name,
    COUNT(dev.id) as repair_count
FROM department d
JOIN customer c ON d.customer_id = c.id
LEFT JOIN device dev ON d.id = dev.department_id
WHERE d.is_active = 0
GROUP BY d.id;
```

---

## Model Relationships

### Customer → Department Relationship
```python
# From customer:
customer.departments  # List of Department objects

# From department:
department.customer  # Parent Customer object
```

### Device (Repair) → Department Relationship
```python
# From device:
device.department  # Parent Department object (nullable)

# From department:
department.devices  # List of Device objects
```

### Sale → Department Relationship
```python
# From sale:
sale.department  # Parent Department object (nullable)

# From department:
department.sales  # List of Sale objects
```

---

## Validation Examples

### Check if customer is Business/Government

```python
def supports_departments(customer):
    return customer.customer_type in ('Business', 'Government')

# Usage:
if supports_departments(customer):
    # Show department UI
    pass
```

### Validate department belongs to customer

```python
def validate_department_ownership(customer_id, department_id):
    dept = Department.query.get(department_id)
    if not dept or dept.customer_id != customer_id:
        raise ValueError("Department does not belong to this customer")

# Usage:
try:
    validate_department_ownership(customer.id, dept_id)
except ValueError as e:
    flash(str(e), "danger")
```

### Check if department is being used

```python
def get_department_usage(department_id):
    repair_count = Device.query.filter_by(department_id=department_id).count()
    sale_count = Sale.query.filter_by(department_id=department_id).count()
    return {
        "repairs": repair_count,
        "sales": sale_count,
        "total": repair_count + sale_count
    }

# Usage:
usage = get_department_usage(dept.id)
if usage['total'] > 0:
    # Department is in use, mark inactive instead of deleting
    dept.is_active = False
else:
    # Safe to delete
    db.session.delete(dept)
```

---

## Error Handling

### Department Creation Error

```python
try:
    dept = Department(
        customer_id=customer_id,
        name=dept_name,
        contact_person=contact_person
    )
    db.session.add(dept)
    db.session.commit()
except Exception as e:
    db.session.rollback()
    flash(f"Error creating department: {str(e)}", "danger")
    return redirect(url_for("customers.customer_detail", customer_id=customer_id))
```

### Department Validation

```python
def validate_department_creation(customer_id, dept_name):
    if not dept_name or not dept_name.strip():
        return False, "Department name is required"
    
    if len(dept_name) > 200:
        return False, "Department name too long (max 200 characters)"
    
    customer = Customer.query.get(customer_id)
    if not customer:
        return False, "Customer not found"
    
    if customer.customer_type == "Individual":
        return False, "Individual customers cannot have departments"
    
    return True, "Valid"
```

---

## Testing Examples

### Test Department Creation

```python
def test_create_department(client, business_customer):
    response = client.post(
        f'/customers/{business_customer.id}/quick-repair',
        data={
            'department_id': '__new__',
            'new_department_name': 'Test Department',
            'new_department_contact': 'Test Person',
            'device_type': 'Printer',
            'issue_description': 'Test issue'
        },
        follow_redirects=True
    )
    assert response.status_code == 200
    
    dept = Department.query.filter_by(name='Test Department').first()
    assert dept is not None
    assert dept.customer_id == business_customer.id
```

### Test Quick Repair

```python
def test_quick_repair(client, customer):
    response = client.post(
        f'/customers/{customer.id}/quick-repair',
        data={
            'device_type': 'Laptop',
            'brand': 'Dell',
            'model': 'XPS',
            'issue_description': 'Screen flickering'
        },
        follow_redirects=True
    )
    assert response.status_code == 200
    
    device = Device.query.filter_by(customer_id=customer.id).first()
    assert device is not None
    assert device.device_type == 'Laptop'
    assert device.department_id is None  # Individual customer
```

---

This reference guide covers the most common operations and patterns used in the department system implementation.
