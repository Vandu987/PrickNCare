from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.clients import router as clients_router
from app.api.v1.health import router as health_router
from app.api.v1.orders import router as orders_router
from app.api.v1.packages import router as packages_router
from app.api.v1.phlebotomists import router as phlebotomists_router
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
