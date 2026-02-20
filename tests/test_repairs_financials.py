from decimal import Decimal

from app.models.repair import Device
from app.extensions import db
from app.services.financials import recompute_repair_financials


def test_zero_cost_repair_defaults_pending(app, logged_in_client):
    """Repairs with total_cost == 0 should be Pending unless charge_waived is True."""
    with app.app_context():
        d = Device(ticket_number='T-ZERO-001', customer_id=1, device_type='accessory', issue_description='no charge')
        # no fees set -> total_cost == 0
        recompute_repair_financials(d)
        db.session.add(d)
        db.session.commit()

        assert d.total_cost == Decimal('0.00')
        assert d.balance_due == Decimal('0.00')
        # important: not auto-marked as Paid
        assert d.payment_status == 'Pending'


def test_waived_charge_still_marked_paid(app, logged_in_client):
    """If charge_waived is True the repair remains Paid (existing behavior)."""
    with app.app_context():
        d = Device(ticket_number='T-WAIVED-001', customer_id=1, device_type='accessory', issue_description='waived')
        d.charge_waived = True
        recompute_repair_financials(d)
        db.session.add(d)
        db.session.commit()

        assert d.total_cost == Decimal('0.00')
        assert d.balance_due == Decimal('0.00')
        assert d.payment_status == 'Paid'
