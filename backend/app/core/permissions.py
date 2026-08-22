"""RBAC: roles + permissions + ownership helpers.

Permissions are stable string constants (`<resource>.<action>`).
Each role maps to a set of permissions; checks happen at the FastAPI dep layer
(`require_permission`) and inside service layers (ownership).
"""

from __future__ import annotations

from enum import Enum
from uuid import UUID

from app.db.enums import UserRole as Role


class Permission(str, Enum):
    # Users
    USERS_LIST = "users.list"
    USERS_READ = "users.read"
    USERS_CREATE = "users.create"
    USERS_UPDATE = "users.update"
    USERS_DELETE = "users.delete"
    USERS_RESET_PASSWORD = "users.reset_password"

    # Applicants — split into self vs other
    APPLICANTS_READ_SELF = "applicants.read_self"
    APPLICANTS_WRITE_SELF = "applicants.write_self"
    APPLICANTS_LIST = "applicants.list"
    APPLICANTS_READ = "applicants.read"
    APPLICANTS_WRITE = "applicants.write"
    APPLICANTS_STATUS = "applicants.status"
    APPLICANTS_CREATE_BY_OPERATOR = "applicants.create_by_operator"

    # Applications (a specific applicant's submission to a program offering)
    APPLICATIONS_CREATE_SELF = "applications.create_self"
    APPLICATIONS_READ_SELF = "applications.read_self"
    APPLICATIONS_WITHDRAW_SELF = "applications.withdraw_self"
    APPLICATIONS_LIST = "applications.list"
    APPLICATIONS_READ = "applications.read"
    APPLICATIONS_REVIEW = "applications.review"

    # Programs / branches / education levels / education forms
    PROGRAMS_READ = "programs.read"
    PROGRAMS_WRITE = "programs.write"

    # Geo (countries / regions / districts)
    REGIONS_READ = "regions.read"
    REGIONS_WRITE = "regions.write"

    # Diploms catalog (education_types / institution_types / courses)
    DIPLOMS_READ = "diploms.read"
    DIPLOMS_WRITE = "diploms.write"

    # Dictionaries
    DICTIONARIES_READ = "dictionaries.read"
    DICTIONARIES_WRITE = "dictionaries.write"

    # Contracts
    CONTRACTS_READ = "contracts.read"
    CONTRACTS_CREATE = "contracts.create"
    CONTRACTS_SIGN = "contracts.sign"
    CONTRACT_TEMPLATES_READ = "contract_templates.read"
    CONTRACT_TEMPLATES_WRITE = "contract_templates.write"

    # Payments
    PAYMENTS_READ = "payments.read"
    PAYMENTS_CREATE = "payments.create"
    PAYMENTS_CONFIRM = "payments.confirm"
    PAYMENTS_FAIL = "payments.fail"
    PAYMENTS_REFUND = "payments.refund"

    # Audit
    AUDIT_READ = "audit.read"

    # Reports
    REPORTS_VIEW = "reports.view"
    REPORTS_FINANCIAL = "reports.financial"

    # Integrations admin (CRM queue / DLQ management)
    INTEGRATIONS_ADMIN = "integrations.admin"

    # Leads (CRM funnel)
    LEADS_LIST = "leads.list"
    LEADS_READ = "leads.read"
    LEADS_CREATE = "leads.create"
    LEADS_UPDATE = "leads.update"
    LEADS_MOVE = "leads.move"
    LEADS_ASSIGN = "leads.assign"
    LEADS_CONVERT = "leads.convert"
    LEADS_LOSE = "leads.lose"
    LEADS_DELETE = "leads.delete"
    LEADS_SETTINGS = "leads.settings"  # pipelines/stages/sources/lost-reasons CRUD

    # Editable marketing landing content (hero, stats, texts, partners, images).
    LANDING_MANAGE = "landing.manage"

    # International admissions — separate funnel for non-resident
    # applicants, managed via /admin/international-admissions.
    INTL_ADMISSIONS_LIST   = "intl_admissions.list"
    INTL_ADMISSIONS_READ   = "intl_admissions.read"
    INTL_ADMISSIONS_MANAGE = "intl_admissions.manage"  # advance/reject/notes
    INTL_ADMISSIONS_DELETE = "intl_admissions.delete"


# ---------- Role groups (kept for legacy `require_roles` usage) ----------
STAFF_ROLES = {Role.SUPERADMIN, Role.ADMIN, Role.OPERATOR, Role.DIRECTOR, Role.ACCOUNTANT}
ADMIN_ROLES = {Role.SUPERADMIN, Role.ADMIN}
ALL_ROLES = set(Role)


# ---------- Role → Permissions matrix ----------
_P = Permission

ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.SUPERADMIN: frozenset(Permission),  # all permissions
    Role.ADMIN: frozenset({
        _P.USERS_LIST, _P.USERS_READ, _P.USERS_CREATE,
        _P.USERS_UPDATE, _P.USERS_DELETE, _P.USERS_RESET_PASSWORD,

        _P.APPLICANTS_LIST, _P.APPLICANTS_READ, _P.APPLICANTS_WRITE,
        _P.APPLICANTS_STATUS, _P.APPLICANTS_CREATE_BY_OPERATOR,

        _P.APPLICATIONS_LIST, _P.APPLICATIONS_READ, _P.APPLICATIONS_REVIEW,

        _P.PROGRAMS_READ, _P.PROGRAMS_WRITE,
        _P.REGIONS_READ, _P.REGIONS_WRITE,
        _P.DIPLOMS_READ, _P.DIPLOMS_WRITE,
        _P.DICTIONARIES_READ, _P.DICTIONARIES_WRITE,

        _P.CONTRACTS_READ, _P.CONTRACTS_CREATE, _P.CONTRACTS_SIGN,
        _P.CONTRACT_TEMPLATES_READ, _P.CONTRACT_TEMPLATES_WRITE,

        _P.PAYMENTS_READ,

        _P.AUDIT_READ, _P.REPORTS_VIEW, _P.REPORTS_FINANCIAL,
        _P.INTEGRATIONS_ADMIN, _P.LANDING_MANAGE,

        _P.LEADS_LIST, _P.LEADS_READ, _P.LEADS_CREATE, _P.LEADS_UPDATE,
        _P.LEADS_MOVE, _P.LEADS_ASSIGN, _P.LEADS_CONVERT, _P.LEADS_LOSE,
        _P.LEADS_DELETE, _P.LEADS_SETTINGS,

        # International admissions — full manage rights
        _P.INTL_ADMISSIONS_LIST, _P.INTL_ADMISSIONS_READ,
        _P.INTL_ADMISSIONS_MANAGE, _P.INTL_ADMISSIONS_DELETE,
    }),
    Role.OPERATOR: frozenset({
        _P.APPLICANTS_LIST, _P.APPLICANTS_READ, _P.APPLICANTS_WRITE,
        _P.APPLICANTS_CREATE_BY_OPERATOR,
        _P.APPLICATIONS_LIST, _P.APPLICATIONS_READ, _P.APPLICATIONS_REVIEW,
        _P.PROGRAMS_READ, _P.REGIONS_READ, _P.DIPLOMS_READ, _P.DICTIONARIES_READ,
        _P.CONTRACTS_READ, _P.CONTRACTS_CREATE, _P.CONTRACTS_SIGN,
        _P.CONTRACT_TEMPLATES_READ,
        _P.PAYMENTS_READ,

        # Operators handle the funnel — full lead lifecycle except settings/delete.
        _P.LEADS_LIST, _P.LEADS_READ, _P.LEADS_CREATE, _P.LEADS_UPDATE,
        _P.LEADS_MOVE, _P.LEADS_ASSIGN, _P.LEADS_CONVERT, _P.LEADS_LOSE,
    }),
    Role.DIRECTOR: frozenset({
        _P.USERS_LIST, _P.USERS_READ,
        _P.APPLICANTS_LIST, _P.APPLICANTS_READ,
        _P.APPLICATIONS_LIST, _P.APPLICATIONS_READ,
        _P.PROGRAMS_READ, _P.REGIONS_READ, _P.DIPLOMS_READ, _P.DICTIONARIES_READ,
        _P.CONTRACTS_READ, _P.CONTRACT_TEMPLATES_READ,
        _P.PAYMENTS_READ,
        _P.REPORTS_VIEW, _P.REPORTS_FINANCIAL,
        _P.AUDIT_READ,

        _P.LEADS_LIST, _P.LEADS_READ,

        # International admissions — read-only for the director.
        _P.INTL_ADMISSIONS_LIST, _P.INTL_ADMISSIONS_READ,
    }),
    Role.ACCOUNTANT: frozenset({
        _P.APPLICANTS_LIST, _P.APPLICANTS_READ,
        _P.APPLICATIONS_LIST, _P.APPLICATIONS_READ,
        _P.PROGRAMS_READ, _P.REGIONS_READ, _P.DIPLOMS_READ, _P.DICTIONARIES_READ,
        # Accountants may issue contracts on applications (system + billing PDF),
        # same as operators/admins.
        _P.CONTRACTS_READ, _P.CONTRACTS_CREATE, _P.CONTRACTS_SIGN, _P.CONTRACT_TEMPLATES_READ,
        _P.PAYMENTS_READ, _P.PAYMENTS_CREATE,
        _P.PAYMENTS_CONFIRM, _P.PAYMENTS_FAIL, _P.PAYMENTS_REFUND,
        _P.REPORTS_FINANCIAL,
    }),
    Role.APPLICANT: frozenset({
        _P.APPLICANTS_READ_SELF, _P.APPLICANTS_WRITE_SELF,
        _P.APPLICATIONS_CREATE_SELF, _P.APPLICATIONS_READ_SELF, _P.APPLICATIONS_WITHDRAW_SELF,
        _P.PROGRAMS_READ, _P.REGIONS_READ, _P.DIPLOMS_READ, _P.DICTIONARIES_READ,
        _P.CONTRACTS_READ,  # own only — enforced at service layer
    }),
}


# ---------- Helpers ----------
def has_permission(role: Role, perm: Permission) -> bool:
    return perm in ROLE_PERMISSIONS.get(role, frozenset())


def has_any(role: Role, *perms: Permission) -> bool:
    granted = ROLE_PERMISSIONS.get(role, frozenset())
    return any(p in granted for p in perms)


def has_all(role: Role, *perms: Permission) -> bool:
    granted = ROLE_PERMISSIONS.get(role, frozenset())
    return all(p in granted for p in perms)


def permissions_for(role: Role) -> frozenset[Permission]:
    return ROLE_PERMISSIONS.get(role, frozenset())


# ---------- Ownership helpers ----------
def is_self_applicant(current_user_id: UUID, applicant_user_id: UUID) -> bool:
    return current_user_id == applicant_user_id


def can_access_applicant(role: Role, current_user_id: UUID, applicant_user_id: UUID) -> bool:
    """Staff with applicants.read OR the applicant themselves."""
    if has_permission(role, Permission.APPLICANTS_READ):
        return True
    return role == Role.APPLICANT and current_user_id == applicant_user_id


__all__ = [
    "Role",
    "Permission",
    "ROLE_PERMISSIONS",
    "STAFF_ROLES",
    "ADMIN_ROLES",
    "ALL_ROLES",
    "has_permission",
    "has_any",
    "has_all",
    "permissions_for",
    "is_self_applicant",
    "can_access_applicant",
]
