"""
Database models package
"""
from app.models.user import User
from app.models.settings import Setting
from app.models.customer import Customer
from app.models.repair import Device, Technician, DeviceAssignment, RepairPartUsed
from app.models.inventory import Category, Product, StockMovement
from app.models.sales import Sale, SaleItem, SalePayment

__all__ = [
    'User', 'Setting',
    'Customer',
    'Device', 'Technician', 'DeviceAssignment', 'RepairPartUsed',
    'Category', 'Product', 'StockMovement',
    'Sale', 'SaleItem', 'SalePayment'
]