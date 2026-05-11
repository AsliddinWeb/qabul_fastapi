"""Single import surface for Alembic autogenerate.

Importing this module registers all ORM tables on `Base.metadata`.
Alembic's env.py imports this file once.
"""

# ruff: noqa: F401  -- side-effect imports

from app.modules.applicants import models as applicants_models
from app.modules.applications import models as applications_models
from app.modules.audit import models as audit_models
from app.modules.auth import models as auth_models
from app.modules.consulting import models as consulting_models
from app.modules.contracts import models as contracts_models
from app.modules.dictionaries import models as dictionaries_models
from app.modules.files import models as files_models
from app.modules.leads import models as leads_models
from app.modules.payments import models as payments_models
from app.modules.programs import models as programs_models
from app.modules.referrals import models as referrals_models
from app.modules.regions import models as regions_models
from app.modules.users import models as users_models
