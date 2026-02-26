"""
Backfill paid_at timestamps for SalePayment and RepairPayment records that don't have them.
This ensures all payments appear correctly in daily sales reports.
"""
import sys
sys.path.insert(0, '/app')

from app import create_app
from app.extensions import db
from app.models.sales import SalePayment, Sale
from app.models.repair import RepairPayment
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = create_app()

def backfill_sale_payments():
    """Set paid_at to sale.created_at for SalePayment records missing paid_at"""
    with app.app_context():
        # Find all SalePayment records without paid_at
        payments_missing_timestamp = SalePayment.query.filter(
            SalePayment.paid_at.is_(None)
        ).all()
        
        if not payments_missing_timestamp:
            logger.info("✓ All SalePayment records already have paid_at timestamps")
            return
        
        logger.info(f"Found {len(payments_missing_timestamp)} SalePayment records missing paid_at")
        
        for payment in payments_missing_timestamp:
            sale = Sale.query.get(payment.sale_id)
            if sale and sale.created_at:
                # Use sale.created_at as the payment timestamp (fallback to when sale was created)
                payment.paid_at = sale.created_at
                logger.info(f"  Payment {payment.id} (Sale {payment.sale_id}): set paid_at to {sale.created_at}")
            else:
                logger.warning(f"  Payment {payment.id}: could not find associated sale")
        
        db.session.commit()
        logger.info(f"✓ Successfully backfilled {len(payments_missing_timestamp)} SalePayment records")

def backfill_repair_payments():
    """Set paid_at to device.created_at for RepairPayment records missing paid_at"""
    try:
        with app.app_context():
            from app.models.repair import Device
            
            # Find all RepairPayment records without paid_at
            payments_missing_timestamp = RepairPayment.query.filter(
                RepairPayment.paid_at.is_(None)
            ).all()
            
            if not payments_missing_timestamp:
                logger.info("✓ All RepairPayment records already have paid_at timestamps")
                return
            
            logger.info(f"Found {len(payments_missing_timestamp)} RepairPayment records missing paid_at")
            
            for payment in payments_missing_timestamp:
                device = Device.query.get(payment.device_id)
                if device and device.created_at:
                    # Use device.created_at as the payment timestamp
                    payment.paid_at = device.created_at
                    logger.info(f"  Payment {payment.id} (Device {payment.device_id}): set paid_at to {device.created_at}")
                else:
                    logger.warning(f"  Payment {payment.id}: could not find associated device")
            
            db.session.commit()
            logger.info(f"✓ Successfully backfilled {len(payments_missing_timestamp)} RepairPayment records")
    except Exception as e:
        logger.warning(f"RepairPayment backfill skipped (table may not exist): {e}")

if __name__ == '__main__':
    logger.info("Starting payment timestamp backfill...")
    backfill_sale_payments()
    backfill_repair_payments()
    logger.info("✓ Backfill complete!")
