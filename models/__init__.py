"""ORM models.

Every model is imported here so that ``Base.metadata`` is complete after a
single ``import app.models``. Without this, ``create_all`` would emit only the
tables that happened to have been imported already.
"""

from app.models.base import Base
from app.models.check_in import CheckIn
from app.models.expense import Expense
from app.models.life_event import LifeEvent
from app.models.user import User

__all__ = ["Base", "CheckIn", "Expense", "LifeEvent", "User"]
