"""
Feature flag utilities for checking system toggles
"""
from app.models.settings import Setting


def is_pos_enabled():
    """Check if POS module is enabled"""
    return Setting.get_bool('POS_ENABLED', default=True)


def is_sales_can_edit_inventory():
    """Check if SALES role can edit inventory"""
    return Setting.get_bool('SALES_CAN_EDIT_INVENTORY', default=True)


def is_tech_can_view_details():
    """Check if TECH role can view details"""
    return Setting.get_bool('TECH_CAN_VIEW_DETAILS', default=True)


def get_all_feature_flags():
    """Get all feature flags as dictionary"""
    return {
        'POS_ENABLED': is_pos_enabled(),
        'SALES_CAN_EDIT_INVENTORY': is_sales_can_edit_inventory(),
        'TECH_CAN_VIEW_DETAILS': is_tech_can_view_details()
    }