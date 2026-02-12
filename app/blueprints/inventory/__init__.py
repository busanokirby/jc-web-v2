from flask import Blueprint

inventory_bp = Blueprint("inventory", __name__)

from . import routes  # noqa
# Extra inventory routes for Phase 2
from . import extra_routes  # noqa