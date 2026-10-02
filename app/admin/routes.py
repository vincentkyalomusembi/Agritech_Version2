from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.admin.schema import (
    AdminCountyItem,
    AdminExpertCreate,
    AdminExpertUpdate,
    AdminFieldOfficerCreate,
    AdminFieldOfficerResponse,
    AdminFarmerActiveUpdate,
    AdminFarmerDetail,
    AdminFarmerListItem,
    AdminOverview,
    AdminRequestItem,
    AdminRequestPatch,
    AvailabilityUpdate,
    PageFarmers,
    PageGeneric,
    PagePricing,
    PageQuotes,
    PageRequests,
    PageStaff,
    PageExperts,
    QuotePreviewResponse,
    RequoteRequest,
)
from app.advisory.schema import AdvisoryCreate, AdvisoryResponse, AdvisoryUpdate
from app.advisory.service import AdvisoryService
from app.audit.service import write_audit
from app.database.sessions import get_db
from app.expert_requests.model import RequestStatus
from app.experts.model import ExpertType
from app.experts.schema import ExpertResponse
from app.experts.services.expert_service import ExpertService
from app.market_prices.schema import MarketPriceResponse
from app.market_prices.service import MarketPriceService
from app.pricing.schema import PricingRuleCreate, PricingRuleResponse, QuoteResponse
from app.products.schema import ProductCreate, ProductResponse, ProductUpdate
from app.products.service import ProductService
from app.staff.dependencies import get_current_staff, require_roles
from app.staff.model import StaffRole, StaffUser
from app.staff.repository import StaffRepository
from app.staff.schema import StaffCreate, StaffResponse, StaffUpdate
from app.staff.service import StaffService
from app.admin.service import AdminService
from app.counties.repository import CountyRepository

router = APIRouter(prefix="/admin", tags=["Admin"])


def _svc(db: Session) -> AdminService:
    return AdminService(db)


def _officer_expert_id(staff: StaffUser) -> UUID | None:
    if staff.role == StaffRole.OFFICER:
        return staff.expert_id
    return None


@router.get("/overview", response_model=AdminOverview)
def admin_overview(
    staff: StaffUser = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    return _svc(db).overview()


@router.get("/farmers", response_model=PageFarmers)
def admin_farmers(
    search: str | None = None,
    county_id: UUID | None = None,
    size_class: str | None = None,
    is_active: bool | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    staff: StaffUser = Depends(require_roles(StaffRole.PLATFORM_ADMIN)),
    db: Session = Depends(get_db),
):
    items, total = _svc(db).list_farmers(
        search=search,
        county_id=county_id,
        size_class=size_class,
        is_active=is_active,
        limit=limit,
        offset=offset,
    )
    return PageFarmers(items=items, total=total, limit=limit, offset=offset)


@router.get("/farmers/{farmer_id}", response_model=AdminFarmerDetail)
def admin_farmer_detail(
    farmer_id: UUID,
    staff: StaffUser = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    show_full = staff.role == StaffRole.PLATFORM_ADMIN
    if staff.role == StaffRole.OFFICER:
        # Officer may open a farmer who appears on an assigned request.
        from app.expert_requests.model import ExpertRequest
        linked = (
            db.query(ExpertRequest)
            .filter(
                ExpertRequest.farmer_id == farmer_id,
                ExpertRequest.expert_id == staff.expert_id,
            )
            .first()
        )
        if linked is None:
            from fastapi import HTTPException
            raise HTTPException(status_code=403, detail="Farmer is not on an assigned request.")
        show_full = False
    return _svc(db).farmer_detail(farmer_id, show_full_id=show_full)


@router.patch("/farmers/{farmer_id}", response_model=AdminFarmerListItem)
def admin_farmer_active(
    farmer_id: UUID,
    payload: AdminFarmerActiveUpdate,
    staff: StaffUser = Depends(require_roles(StaffRole.PLATFORM_ADMIN)),
    db: Session = Depends(get_db),
):
    return _svc(db).set_farmer_active(farmer_id, payload.is_active, staff)


@router.get("/staff", response_model=PageStaff)
def admin_list_staff(
    _: StaffUser = Depends(require_roles(StaffRole.PLATFORM_ADMIN)),
    db: Session = Depends(get_db),
):
    items = [StaffResponse.model_validate(row) for row in StaffRepository(db).list_all()]
    return PageStaff(items=items, total=len(items), limit=len(items), offset=0)


@router.post("/staff", response_model=StaffResponse, status_code=201)
def admin_create_staff(
    payload: StaffCreate,
    staff: StaffUser = Depends(require_roles(StaffRole.PLATFORM_ADMIN)),
    db: Session = Depends(get_db),
):
    created = StaffService(db).create(payload)
    write_audit(
        db,
        action="staff.create",
        entity="staff_user",
        entity_id=created.id,
        actor_id=staff.id,
        commit=True,
    )
    return created


@router.patch("/staff/{staff_id}", response_model=StaffResponse)
def admin_update_staff(
    staff_id: UUID,
    payload: StaffUpdate,
    actor: StaffUser = Depends(require_roles(StaffRole.PLATFORM_ADMIN)),
    db: Session = Depends(get_db),
):
    updated = StaffService(db).update(staff_id, payload)
    write_audit(
        db,
        action="staff.update",
        entity="staff_user",
        entity_id=staff_id,
        actor_id=actor.id,
        commit=True,
    )
    return updated


@router.get("/counties", response_model=list[AdminCountyItem])
def admin_counties(
    _: StaffUser = Depends(require_roles(StaffRole.PLATFORM_ADMIN)),
    db: Session = Depends(get_db),
):
    return [
        AdminCountyItem(id=row.id, name=row.name)
        for row in CountyRepository(db).list_all()
    ]


@router.post("/field-officers", response_model=AdminFieldOfficerResponse, status_code=201)
def admin_create_field_officer(
    payload: AdminFieldOfficerCreate,
    staff: StaffUser = Depends(require_roles(StaffRole.PLATFORM_ADMIN)),
    db: Session = Depends(get_db),
):
    return _svc(db).create_field_officer(payload, staff)


@router.get("/experts", response_model=PageExperts)
def admin_experts(
    county_id: UUID | None = None,
    expert_type: ExpertType | None = None,
    is_available: bool | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _: StaffUser = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    result = ExpertService(db).list_experts(
        county_id=county_id,
        expert_type=expert_type,
        is_available=is_available,
        limit=limit,
        offset=offset,
    )
    return PageExperts(items=result.items, total=result.total, limit=limit, offset=offset)


@router.post("/experts", response_model=ExpertResponse, status_code=201)
def admin_create_expert(
    payload: AdminExpertCreate,
    staff: StaffUser = Depends(require_roles(StaffRole.PLATFORM_ADMIN)),
    db: Session = Depends(get_db),
):
    return _svc(db).create_expert(payload, staff)


@router.patch("/experts/{expert_id}", response_model=ExpertResponse)
def admin_update_expert(
    expert_id: UUID,
    payload: AdminExpertUpdate,
    staff: StaffUser = Depends(require_roles(StaffRole.PLATFORM_ADMIN)),
    db: Session = Depends(get_db),
):
    return _svc(db).update_expert(expert_id, payload, staff)


@router.get("/expert-requests", response_model=PageRequests)
def admin_requests(
    status: RequestStatus | None = None,
    county_id: UUID | None = None,
    expert_id: UUID | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    staff: StaffUser = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    items, total = _svc(db).list_requests(
        status_filter=status,
        county_id=county_id,
        expert_id=expert_id,
        assigned_only_expert_id=_officer_expert_id(staff),
        limit=limit,
        offset=offset,
    )
    return PageRequests(items=items, total=total, limit=limit, offset=offset)


@router.get("/expert-requests/{request_id}", response_model=AdminRequestItem)
def admin_request_detail(
    request_id: UUID,
    staff: StaffUser = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    return _svc(db).get_request(request_id, assigned_only_expert_id=_officer_expert_id(staff))


@router.patch("/expert-requests/{request_id}")
def admin_patch_request(
    request_id: UUID,
    payload: AdminRequestPatch,
    staff: StaffUser = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    return _svc(db).patch_request(
        request_id,
        payload,
        actor=staff,
        officer_expert_id=_officer_expert_id(staff),
    )


@router.get("/products", response_model=list[ProductResponse])
def admin_products(
    active_only: bool = False,
    _: StaffUser = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    return ProductService(db).get_all(active_only=active_only)


@router.post("/products", response_model=ProductResponse, status_code=201)
def admin_create_product(
    payload: ProductCreate,
    staff: StaffUser = Depends(require_roles(StaffRole.PLATFORM_ADMIN)),
    db: Session = Depends(get_db),
):
    created = ProductService(db).create(payload)
    write_audit(db, action="product.create", entity="product", entity_id=created.id, actor_id=staff.id, commit=True)
    return created


@router.patch("/products/{product_id}", response_model=ProductResponse)
def admin_update_product(
    product_id: UUID,
    payload: ProductUpdate,
    staff: StaffUser = Depends(require_roles(StaffRole.PLATFORM_ADMIN)),
    db: Session = Depends(get_db),
):
    updated = ProductService(db).update(product_id, payload)
    write_audit(db, action="product.update", entity="product", entity_id=product_id, actor_id=staff.id, commit=True)
    return updated


@router.get("/advisories", response_model=list[AdvisoryResponse])
def admin_advisories(
    active_only: bool = False,
    _: StaffUser = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    return AdvisoryService(db).get_all(active_only=active_only)


@router.post("/advisories", response_model=AdvisoryResponse, status_code=201)
def admin_create_advisory(
    payload: AdvisoryCreate,
    staff: StaffUser = Depends(require_roles(StaffRole.PLATFORM_ADMIN)),
    db: Session = Depends(get_db),
):
    created = AdvisoryService(db).create(payload)
    write_audit(db, action="advisory.create", entity="advisory", entity_id=created.id, actor_id=staff.id, commit=True)
    return created


@router.patch("/advisories/{advisory_id}", response_model=AdvisoryResponse)
def admin_update_advisory(
    advisory_id: UUID,
    payload: AdvisoryUpdate,
    staff: StaffUser = Depends(require_roles(StaffRole.PLATFORM_ADMIN)),
    db: Session = Depends(get_db),
):
    updated = AdvisoryService(db).update(advisory_id, payload)
    write_audit(db, action="advisory.update", entity="advisory", entity_id=advisory_id, actor_id=staff.id, commit=True)
    return updated


@router.get("/market-prices", response_model=list[MarketPriceResponse])
def admin_market_prices(
    _: StaffUser = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    return MarketPriceService(db).get_all()


@router.post("/market-prices/scrape")
def admin_scrape_prices(
    staff: StaffUser = Depends(require_roles(StaffRole.PLATFORM_ADMIN)),
    db: Session = Depends(get_db),
):
    result = MarketPriceService(db).scrape_and_store()
    write_audit(db, action="market.scrape", entity="market_price", actor_id=staff.id, commit=True)
    return {"message": "KAMIS scrape completed.", **result}


@router.get("/quotes", response_model=PageQuotes)
def admin_quotes(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _: StaffUser = Depends(require_roles(StaffRole.PLATFORM_ADMIN)),
    db: Session = Depends(get_db),
):
    items, total = _svc(db).list_quotes(limit, offset)
    return PageQuotes(items=items, total=total, limit=limit, offset=offset)


@router.get("/quotes/preview", response_model=QuotePreviewResponse)
def admin_quote_preview(
    acres: float = 0,
    cattle: int = 0,
    goats: int = 0,
    sheep: int = 0,
    poultry: int = 0,
    _: StaffUser = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    return _svc(db).preview_quote(acres, cattle, goats, sheep, poultry)


@router.post("/farmers/{farmer_id}/requote", response_model=QuoteResponse)
def admin_requote(
    farmer_id: UUID,
    payload: RequoteRequest,
    staff: StaffUser = Depends(require_roles(StaffRole.PLATFORM_ADMIN)),
    db: Session = Depends(get_db),
):
    return _svc(db).requote(farmer_id, payload.reason, staff)


@router.get("/pricing", response_model=PagePricing)
def admin_pricing(
    _: StaffUser = Depends(require_roles(StaffRole.PLATFORM_ADMIN)),
    db: Session = Depends(get_db),
):
    items = [PricingRuleResponse.model_validate(row) for row in _svc(db).list_pricing_rules()]
    return PagePricing(items=items, total=len(items), limit=len(items), offset=0)


@router.post("/pricing", response_model=PricingRuleResponse, status_code=201)
def admin_create_pricing(
    payload: PricingRuleCreate,
    staff: StaffUser = Depends(require_roles(StaffRole.PLATFORM_ADMIN)),
    db: Session = Depends(get_db),
):
    return PricingRuleResponse.model_validate(_svc(db).create_pricing_rule(payload, staff))


@router.get("/subscriptions", response_model=PageGeneric)
def admin_subscriptions(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _: StaffUser = Depends(require_roles(StaffRole.PLATFORM_ADMIN)),
    db: Session = Depends(get_db),
):
    items, total = _svc(db).list_subscriptions(limit, offset)
    return PageGeneric(items=items, total=total, limit=limit, offset=offset)


@router.get("/sms-sessions", response_model=PageGeneric)
def admin_sms_sessions(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _: StaffUser = Depends(require_roles(StaffRole.PLATFORM_ADMIN)),
    db: Session = Depends(get_db),
):
    items, total = _svc(db).list_sms_sessions(limit, offset)
    return PageGeneric(items=items, total=total, limit=limit, offset=offset)


@router.get("/audit", response_model=PageGeneric)
def admin_audit(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _: StaffUser = Depends(require_roles(StaffRole.PLATFORM_ADMIN)),
    db: Session = Depends(get_db),
):
    items, total = _svc(db).list_audit(limit, offset)
    return PageGeneric(items=items, total=total, limit=limit, offset=offset)


@router.patch("/me/availability", response_model=ExpertResponse)
def officer_availability(
    payload: AvailabilityUpdate,
    staff: StaffUser = Depends(require_roles(StaffRole.OFFICER, StaffRole.PLATFORM_ADMIN)),
    db: Session = Depends(get_db),
):
    if staff.expert_id is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Staff user is not linked to an expert.")
    return _svc(db).update_expert(
        staff.expert_id,
        AdminExpertUpdate(is_available=payload.is_available),
        staff,
    )
