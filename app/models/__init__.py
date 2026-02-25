"""
Database models package
"""
# Base model used to give all declarative models a permissive constructor
from app.models.base import BaseModel

from app.models.user import User
from app.models.settings import Setting
from app.models.customer import Customer
from app.models.repair import Device, Technician, DeviceAssignment, RepairPartUsed
from app.models.inventory import Category, Product, StockMovement
from app.models.sales import Sale, SaleItem, SalePayment
from app.models.email_config import SMTPSettings, EmailReport

__all__ = [
    'User', 'Setting',
    'Customer',
    'Device', 'Technician', 'DeviceAssignment', 'RepairPartUsed',
    'Category', 'Product', 'StockMovement',
    'Sale', 'SaleItem', 'SalePayment',
    'SMTPSettings', 'EmailReport'
]