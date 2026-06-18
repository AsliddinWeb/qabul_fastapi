"""All PostgreSQL ENUM types used across the schema.

Defined here (not in modules) because:
  - several tables share the same enum (e.g. ContractType in contracts + parties),
  - Alembic needs a single source of truth to avoid duplicate CREATE TYPE.

Each enum's `name=` kwarg in `sa.Enum(...)` MUST match the `value` attribute
defined here, so the on-disk type name is stable across migrations.

NOTE: `pg_enum()` below configures SQLAlchemy to use the Python enum's `.value`
(lowercase strings like "draft") for the on-disk Postgres ENUM. Without
`values_callable`, SQLAlchemy would default to `.name` ("DRAFT") which
mismatches our `server_default=Enum.MEMBER.value` and our API/Pydantic schema.
"""

from __future__ import annotations

from enum import Enum
from typing import TypeVar

from sqlalchemy import Enum as SAEnum

E = TypeVar("E", bound=Enum)


def pg_enum(enum_cls: type[E], name: str, *, create_type: bool = True) -> SAEnum:
    """Build a SQLAlchemy ENUM column type that stores Python `.value` strings."""
    return SAEnum(
        enum_cls,
        name=name,
        native_enum=True,
        create_type=create_type,
        values_callable=lambda c: [e.value for e in c],  # type: ignore[arg-type]
    )


class UserRole(str, Enum):
    SUPERADMIN = "superadmin"
    ADMIN = "admin"
    OPERATOR = "operator"
    DIRECTOR = "director"
    ACCOUNTANT = "accountant"
    APPLICANT = "applicant"


class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"


class OtpPurpose(str, Enum):
    LOGIN = "login"
    REGISTER = "register"
    RESET = "reset"


class ApplicantStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    ENROLLED = "enrolled"


class ApplicantContactStatus(str, Enum):
    """CRM-style follow-up state, manually set by operators.

    Separate from ApplicantStatus (which mirrors application lifecycle).
    Lets the team mark stages BEFORE/AFTER the application itself —
    e.g. they talked to the candidate but no application is in yet, or
    a contracted candidate stopped responding.
    """

    NEW = "new"                  # Default — abituriyent yangi ro'yxatga olindi
    CONTACTED = "contacted"      # Operator gaplashdi
    INTERESTED = "interested"    # Qiziqyapti — keyingi muloqotni kutyapti
    LOST = "lost"                # Yo'qotildi (pul yetmadi / boshqa OTM tanladi)
    ENROLLED = "enrolled"        # O'qishga kirdi (shartnoma imzolanganda avto)


class ApplicationStatus(str, Enum):
    """Match old Django values verbatim."""

    PENDING = "topshirildi"
    REVIEW = "korib_chiqilmoqda"
    ACCEPTED = "qabul_qilindi"
    REJECTED = "rad_etildi"


class AdmissionType(str, Enum):
    """1-kurs (yangi qabul), perevod, 2-mutaxassislik, yoki magistratura.

    SECOND_SPEC ("ikkinchi_mutaxassislik") — admitted to a SECOND
    Bachelor's track on top of an existing Bachelor's degree. Always
    starts at kurs 2 (the 1st-year general courses are credit-
    transferred from the prior degree), and only kunduzgi form is
    offered.

    MAGISTRATURA ("magistratura") — Master's degree applicant.
    Requires a Bachelor's diploma (same row as SECOND_SPEC carries,
    `is_for_second_specialization=True`). Kunduzgi-only. Only
    education_levels named "Magistr" are eligible programs.
    """

    REGULAR = "yangi_qabul"
    TRANSFER = "perevod"
    SECOND_SPEC = "ikkinchi_mutaxassislik"
    MAGISTRATURA = "magistratura"


class ContractType(str, Enum):
    TWO_PARTY = "two_party"
    THREE_PARTY = "three_party"


class ContractStatus(str, Enum):
    DRAFT = "draft"
    SIGNED = "signed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class PartyRole(str, Enum):
    UNIVERSITY = "university"
    STUDENT = "student"
    SPONSOR = "sponsor"
    PARENT = "parent"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    REFUNDED = "refunded"


class Language(str, Enum):
    UZ = "uz"
    RU = "ru"
    EN = "en"


class LeadStatus(str, Enum):
    OPEN = "open"      # in funnel
    WON = "won"        # converted to Application
    LOST = "lost"      # dropped (with reason)
