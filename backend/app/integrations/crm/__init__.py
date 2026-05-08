"""CRM integration package.

This admission system DOES NOT implement CRM features.
It only sends lead/applicant events to an external CRM via HTTP API.

Public surface:
    - CrmClient: thin HTTP client (auth, retry, error handling)
    - schemas: outbound payloads (ApplicantLead, ApplicantUpdate, ...)
    - events: helpers to fire CRM events from services
"""

from app.integrations.crm.client import CrmClient, CrmError, CrmResult

__all__ = ["CrmClient", "CrmError", "CrmResult"]
