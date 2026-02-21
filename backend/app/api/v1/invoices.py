"""Invoice API endpoints — task 9.5."""

from __future__ import annotations

import io
import uuid
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_active_user, require_roles
from app.core.database import get_db
from app.models.invoices import Invoice, InvoiceLineItem, InvoiceStatus
from app.models.orders import Order, OrderStatus
from app.models.users import User, UserRole
from app.schemas.invoice import (
    InvoiceCreate,
    InvoiceListResponse,
    InvoiceResponse,
    MarkPaidRequest,
)

router = APIRouter(prefix="/invoices", tags=["invoices"])


def _generate_invoice_number() -> str:
    """Generate a unique invoice number like INV-20260222-XXXX."""
    now = datetime.utcnow()
    short_id = uuid.uuid4().hex[:6].upper()
    return f"INV-{now.strftime('%Y%m%d')}-{short_id}"


@router.post(
    "/generate",
    response_model=InvoiceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_invoice(
    payload: InvoiceCreate,
    user: User = Depends(require_roles("super_admin", "city_admin")),
    db: AsyncSession = Depends(get_db),
):
    """Generate an invoice for a client for a date range."""
    # Fetch completed orders in the date range for this client
    stmt = select(Order).where(
        Order.client_id == payload.client_id,
        Order.status == OrderStatus.COMPLETED,
        Order.appointment_date >= payload.date_from,
        Order.appointment_date <= payload.date_to,
    )
    result = await db.execute(stmt)
    orders = result.scalars().all()

    if not orders:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No completed orders found for the given client and date range",
        )

    # Build line items and compute subtotal
    line_items = []
    subtotal = 0.0
    for order in orders:
        amount = float(order.amount)
        subtotal += amount
        line_items.append(
            InvoiceLineItem(
                order_id=order.id,
                description=f"Order {order.booking_id}",
                amount=amount,
            )
        )

    tax_amount = 0.0  # Tax can be configured later
    total = subtotal + tax_amount

    invoice = Invoice(
        client_id=payload.client_id,
        invoice_number=_generate_invoice_number(),
        date_from=payload.date_from,
        date_to=payload.date_to,
        subtotal=subtotal,
        tax_amount=tax_amount,
        total=total,
        status=InvoiceStatus.PENDING,
        line_items=line_items,
    )
    db.add(invoice)
    await db.commit()
    await db.refresh(invoice)

    # Reload with line_items
    stmt = (
        select(Invoice)
        .options(selectinload(Invoice.line_items))
        .where(Invoice.id == invoice.id)
    )
    result = await db.execute(stmt)
    invoice = result.scalar_one()

    return invoice


@router.get("", response_model=InvoiceListResponse)
async def list_invoices(
    client_id: uuid.UUID | None = Query(None),
    invoice_status: str | None = Query(None, alias="status"),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List invoices with filters. Admins see all, client_user sees own client's."""
    stmt = select(Invoice)
    count_stmt = select(func.count(Invoice.id))

    # RBAC: client_user can only see their own client's invoices
    if user.role == UserRole.CLIENT_USER:
        if not hasattr(user, "client_id") or not user.client_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Client user has no associated client",
            )
        stmt = stmt.where(Invoice.client_id == user.client_id)
        count_stmt = count_stmt.where(Invoice.client_id == user.client_id)
    elif user.role == UserRole.PHLEBOTOMIST:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )

    if client_id:
        stmt = stmt.where(Invoice.client_id == client_id)
        count_stmt = count_stmt.where(Invoice.client_id == client_id)
    if invoice_status:
        stmt = stmt.where(Invoice.status == invoice_status)
        count_stmt = count_stmt.where(Invoice.status == invoice_status)
    if date_from:
        stmt = stmt.where(Invoice.date_from >= date_from)
        count_stmt = count_stmt.where(Invoice.date_from >= date_from)
    if date_to:
        stmt = stmt.where(Invoice.date_to <= date_to)
        count_stmt = count_stmt.where(Invoice.date_to <= date_to)

    total = (await db.execute(count_stmt)).scalar() or 0
    stmt = stmt.order_by(Invoice.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(stmt)
    invoices = result.scalars().all()

    return InvoiceListResponse(items=invoices, total=total)


@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: uuid.UUID,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get invoice detail with line items."""
    stmt = (
        select(Invoice)
        .options(selectinload(Invoice.line_items))
        .where(Invoice.id == invoice_id)
    )
    result = await db.execute(stmt)
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found"
        )

    # RBAC check for client_user
    if user.role == UserRole.CLIENT_USER:
        user_client_id = getattr(user, "client_id", None)
        if user_client_id != invoice.client_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )

    return invoice


@router.get("/{invoice_id}/pdf")
async def get_invoice_pdf(
    invoice_id: uuid.UUID,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate PDF for an invoice."""
    stmt = (
        select(Invoice)
        .options(selectinload(Invoice.line_items))
        .where(Invoice.id == invoice_id)
    )
    result = await db.execute(stmt)
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found"
        )

    # RBAC check for client_user
    if user.role == UserRole.CLIENT_USER:
        user_client_id = getattr(user, "client_id", None)
        if user_client_id != invoice.client_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )

    # Try to generate PDF with reportlab
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import cm
        from reportlab.pdfgen import canvas

        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=A4)
        width, height = A4

        # Header
        c.setFont("Helvetica-Bold", 18)
        c.drawString(2 * cm, height - 2 * cm, "INVOICE")

        c.setFont("Helvetica", 11)
        c.drawString(2 * cm, height - 3 * cm, f"Invoice #: {invoice.invoice_number}")
        c.drawString(
            2 * cm,
            height - 3.5 * cm,
            f"Period: {invoice.date_from} to {invoice.date_to}",
        )
        c.drawString(
            2 * cm,
            height - 4 * cm,
            f"Status: {getattr(invoice.status, 'value', invoice.status)}",
        )

        # Table header
        y = height - 5.5 * cm
        c.setFont("Helvetica-Bold", 10)
        c.drawString(2 * cm, y, "Description")
        c.drawString(14 * cm, y, "Amount")
        y -= 0.6 * cm
        c.line(2 * cm, y, 19 * cm, y)
        y -= 0.5 * cm

        # Line items
        c.setFont("Helvetica", 10)
        for item in invoice.line_items:
            c.drawString(2 * cm, y, str(item.description)[:60])
            c.drawRightString(19 * cm, y, f"{float(item.amount):.2f}")
            y -= 0.5 * cm
            if y < 3 * cm:
                c.showPage()
                y = height - 2 * cm

        # Totals
        y -= 0.5 * cm
        c.line(2 * cm, y, 19 * cm, y)
        y -= 0.6 * cm
        c.setFont("Helvetica-Bold", 10)
        c.drawString(12 * cm, y, "Subtotal:")
        c.drawRightString(19 * cm, y, f"{float(invoice.subtotal):.2f}")
        y -= 0.5 * cm
        c.drawString(12 * cm, y, "Tax:")
        c.drawRightString(19 * cm, y, f"{float(invoice.tax_amount):.2f}")
        y -= 0.5 * cm
        c.setFont("Helvetica-Bold", 12)
        c.drawString(12 * cm, y, "Total:")
        c.drawRightString(19 * cm, y, f"{float(invoice.total):.2f}")

        c.save()
        buf.seek(0)

        return StreamingResponse(
            buf,
            media_type="application/pdf",
            headers={
                "Content-Disposition": (
                    f'attachment; filename="{invoice.invoice_number}.pdf"'
                )
            },
        )
    except ImportError:
        # reportlab not available — return JSON stub
        return {
            "note": (
                "PDF generation is stubbed" " — install reportlab for full PDF support"
            ),
            "invoice_number": invoice.invoice_number,
            "client_id": str(invoice.client_id),
            "date_from": str(invoice.date_from),
            "date_to": str(invoice.date_to),
            "subtotal": float(invoice.subtotal),
            "tax_amount": float(invoice.tax_amount),
            "total": float(invoice.total),
            "status": getattr(invoice.status, "value", invoice.status),
            "line_items": [
                {
                    "description": li.description,
                    "amount": float(li.amount),
                    "order_id": str(li.order_id),
                }
                for li in invoice.line_items
            ],
        }


@router.put("/{invoice_id}/mark-paid", response_model=InvoiceResponse)
async def mark_invoice_paid(
    invoice_id: uuid.UUID,
    payload: MarkPaidRequest,
    user: User = Depends(require_roles("super_admin", "city_admin")),
    db: AsyncSession = Depends(get_db),
):
    """Mark an invoice as paid with a payment reference."""
    stmt = (
        select(Invoice)
        .options(selectinload(Invoice.line_items))
        .where(Invoice.id == invoice_id)
    )
    result = await db.execute(stmt)
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found"
        )

    if invoice.status == InvoiceStatus.PAID:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invoice is already paid",
        )

    invoice.status = InvoiceStatus.PAID
    invoice.payment_ref = payload.payment_ref
    invoice.paid_at = func.now()

    await db.commit()
    await db.refresh(invoice)

    # Reload with line_items
    stmt = (
        select(Invoice)
        .options(selectinload(Invoice.line_items))
        .where(Invoice.id == invoice.id)
    )
    result = await db.execute(stmt)
    invoice = result.scalar_one()

    return invoice
