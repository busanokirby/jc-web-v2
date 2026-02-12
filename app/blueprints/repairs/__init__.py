from flask import Blueprint

repairs_bp = Blueprint("repairs", __name__)

from . import routes  # noqa