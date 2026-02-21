from fastapi import APIRouter

from app.api.v1.accessioning import router as accessioning_router
from app.api.v1.audit import router as audit_router
from app.api.v1.auth import router as auth_router
from app.api.v1.clients import router as clients_router
from app.api.v1.files import router as files_router
from app.api.v1.health import router as health_router
from app.api.v1.invoices import router as invoices_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.orders import router as orders_router
from app.api.v1.packages import router as packages_router
from app.api.v1.payments import router as payments_router
from app.api.v1.phlebotomists import router as phlebotomists_router
from app.api.v1.pricing import router as pricing_router
from app.api.v1.reconciliation import router as reconciliation_router
from app.api.v1.reports import router as reports_router
from app.api.v1.zones import locality_router, nsa_router, pincode_router, zone_router
from app.api.v1.zones import router as zones_router

router = APIRouter()

router.include_router(health_router)
router.include_router(auth_router)
router.include_router(clients_router)
router.include_router(phlebotomists_router)
router.include_router(zones_router)
router.include_router(zone_router)
router.include_router(pincode_router)
router.include_router(locality_router)
router.include_router(nsa_router)
router.include_router(orders_router)
router.include_router(packages_router)
router.include_router(pricing_router)
router.include_router(accessioning_router)
router.include_router(invoices_router)
router.include_router(payments_router)
router.include_router(notifications_router)
router.include_router(reconciliation_router)
router.include_router(reports_router)
router.include_router(files_router)
router.include_router(audit_router)
