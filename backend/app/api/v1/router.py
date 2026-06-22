from __future__ import annotations

from fastapi import APIRouter

from app.integrations.crm.router import router as crm_admin_router
from app.modules.analytics.router import router as analytics_router
from app.modules.applicants.router import router as applicants_router
from app.modules.applications.router import router as applications_router
from app.modules.audit.router import router as audit_router
from app.modules.auth.router import router as auth_router
from app.modules.consulting.router import router as consulting_router
from app.modules.contracts.router import router as contracts_router
from app.modules.dictionaries.router import router as dictionaries_router
from app.modules.files.router import router as files_router
from app.modules.international_admissions.router import router as international_router
from app.modules.leads.router import router as leads_router
from app.modules.payments.router import router as payments_router
from app.modules.programs.router import router as programs_router
from app.modules.referrals.router import router as referrals_router
from app.modules.regions.router import router as regions_router
from app.modules.users.router import router as users_router

api_router = APIRouter()


@api_router.get("/ping", tags=["meta"])
async def ping() -> dict[str, str]:
    return {"status": "ok"}


api_router.include_router(auth_router,         prefix="/auth",         tags=["auth"])
api_router.include_router(users_router,        prefix="/users",        tags=["users"])
api_router.include_router(applicants_router,   prefix="/applicants",   tags=["applicants"])
api_router.include_router(applications_router, prefix="/applications", tags=["applications"])
api_router.include_router(programs_router,     prefix="/programs",     tags=["programs"])
api_router.include_router(regions_router,      prefix="/regions",      tags=["regions"])
api_router.include_router(contracts_router,    prefix="/contracts",    tags=["contracts"])
api_router.include_router(payments_router,     prefix="/payments",     tags=["payments"])
api_router.include_router(dictionaries_router, prefix="/dictionaries", tags=["dictionaries"])
api_router.include_router(audit_router,        prefix="/audit",        tags=["audit"])
api_router.include_router(files_router,        prefix="/files",        tags=["files"])
api_router.include_router(leads_router,        prefix="/leads",        tags=["leads"])
api_router.include_router(consulting_router,   prefix="/consulting-agencies", tags=["consulting"])
api_router.include_router(referrals_router,    prefix="/referrals",    tags=["referrals"])
api_router.include_router(analytics_router,    prefix="/analytics",    tags=["analytics"])
api_router.include_router(crm_admin_router,    prefix="/integrations/crm", tags=["integrations"])
api_router.include_router(international_router, prefix="/international-admissions", tags=["international-admissions"])
