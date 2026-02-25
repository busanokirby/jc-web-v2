#!/usr/bin/env python3
"""
Migration Script: Migrate Repair Payments from Device model to RepairPayment table
Run this AFTER creating the repair_payment table

Usage:
    python scripts/migrate_repair_payments.py

This script:
1. Creates RepairPayment records from Device.deposit_paid fields
2. Validates the migration
3. Provides rollback instructions if needed
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from decimal import Decimal
from datetime import datetime
from flask import Flask
from flask.cli import with_appcontext

def migrate_repair_payments(app):
    """
    Migrate existing repair payments from Device table to RepairPayment table.
    """
    from app.extensions import db
    from app.models.repair import Device
    
    with app.app_context():
        try:
            # Import the new RepairPayment model
            from app.models.repair_payment import RepairPayment
            
            print("🔍 Starting repair payment migration...")
            
            # Find all repairs with deposits
            repairs_with_deposits = Device.query.filter(
                Device.deposit_paid > 0,
                Device.is_archived == True  # Only completed repairs
            ).all()
            
            print(f"Found {len(repairs_with_deposits)} repairs with deposits to migrate")
            
            migrated_count = 0
            failed_count = 0
            skipped_count = 0
            
            for repair in repairs_with_deposits:
                try:
                    # Check if RepairPayment already exists for this device
                    existing = RepairPayment.query.filter_by(
                        device_id=repair.id
                    ).first()
                    
                    if existing:
                        skipped_count += 1
                        print(f"⏭️  Skipping {repair.ticket_number}: RepairPayment already exists")
                        continue
                    
                    # Create RepairPayment from Device data
                    payment = RepairPayment(
                        device_id=repair.id,
                        amount=Decimal(str(repair.deposit_paid)) if repair.deposit_paid else Decimal("0.00"),
                        method="Cash",  # Default method (can be updated later)
                        paid_at=repair.deposit_paid_at or datetime.utcnow(),
                        notes=f"Migrated from Device.deposit_paid (original: {repair.deposit_paid})"
                    )
                    
                    db.session.add(payment)
                    migrated_count += 1
                    
                    if migrated_count % 10 == 0:
                        print(f"  Migrated {migrated_count} records...")
                
                except Exception as e:
                    failed_count += 1
                    print(f"❌ Failed to migrate {repair.ticket_number}: {str(e)}")
            
            # Commit all changes
            db.session.commit()
            
            print(f"\n✅ Migration Complete:")
            print(f"   Migrated: {migrated_count}")
            print(f"   Skipped: {skipped_count}")
            print(f"   Failed: {failed_count}")
            
            # Validation
            print("\n🔍 Validating migration...")
            migrated_payments = RepairPayment.query.count()
            print(f"   Total RepairPayment records: {migrated_payments}")
            
            # Check for consistency
            total_migrated = Decimal("0.00")
            for payment in RepairPayment.query.all():
                total_migrated += Decimal(str(payment.amount))
            
            total_deposits = Decimal("0.00")
            for repair in devices_with_deposits:
                total_deposits += Decimal(str(repair.deposit_paid))
            
            print(f"   Total migrated amount: ₱{float(total_migrated):,.2f}")
            print(f"   Total original deposits: ₱{float(total_deposits):,.2f}")
            
            if total_migrated == total_deposits:
                print("   ✅ Amounts match - migration successful!")
            else:
                print("   ⚠️  Amount mismatch detected!")
            
            return True
        
        except ImportError:
            print("❌ RepairPayment model not found. Create the table first:")
            print("   flask db upgrade")
            return False
        except Exception as e:
            print(f"❌ Migration failed: {str(e)}")
            import traceback
            traceback.print_exc()
            db.session.rollback()
            return False


# ROLLBACK INSTRUCTIONS:
"""
If the migration needs to be rolled back:

1. All RepairPayment records created during migration have 'notes' starting with "Migrated from"
2. Find and delete them:
   
   python
   from app.models.repair_payment import RepairPayment
   from app.extensions import db
   
   payments_to_delete = RepairPayment.query.filter(
       RepairPayment.notes.like('Migrated from%')
   ).all()
   
   for p in payments_to_delete:
       db.session.delete(p)
   
   db.session.commit()
   print(f"Deleted {len(payments_to_delete)} migrated payments")

3. Device.deposit_paid and Device.deposit_paid_at remain unchanged
"""


if __name__ == '__main__':
    from app import create_app
    
    app = create_app()
    
    success = migrate_repair_payments(app)
    sys.exit(0 if success else 1)
