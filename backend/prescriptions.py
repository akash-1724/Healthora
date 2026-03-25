from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_
from sqlalchemy.orm import Session

from audit import log_action
from database import get_db
from deps import get_current_user, require_permission
from models import DispensingRecord, Drug, DrugBatch, Patient, Prescription, PrescriptionItem, User
from schemas import (
    DispensingRecordCreate,
    DispensingRecordRead,
    PrescriptionCreate,
    PrescriptionItemRead,
    PrescriptionRead,
)

router = APIRouter(prefix="/api", tags=["prescriptions"])


def to_prescription_read(rx: Prescription) -> PrescriptionRead:
    return PrescriptionRead(
        prescription_id=rx.prescription_id,
        patient_id=rx.patient_id,
        patient_name=rx.patient.name if rx.patient else "",
        doctor_name=rx.doctor_name,
        diagnosis=rx.diagnosis,
        notes=rx.notes,
        status=rx.status,
        created_by_username=rx.created_by.username if rx.created_by else None,
        created_at=rx.created_at,
        items=[
            PrescriptionItemRead(
                item_id=item.item_id,
                drug_id=item.drug_id,
                drug_name=item.drug.drug_name if item.drug else "",
                dosage=item.dosage,
                duration=item.duration,
                quantity_prescribed=item.quantity_prescribed,
            )
            for item in rx.items
        ],
    )


def to_dispensing_read(rec: DispensingRecord) -> DispensingRecordRead:
    return DispensingRecordRead(
        record_id=rec.record_id,
        prescription_id=rec.prescription_id,
        patient_id=rec.patient_id,
        patient_name=rec.patient.name if rec.patient else "",
        batch_id=rec.batch_id,
        drug_name=rec.batch.drug.drug_name if rec.batch else "",
        batch_no=rec.batch.batch_no if rec.batch else "",
        quantity_dispensed=rec.quantity_dispensed,
        dispensed_by_username=rec.dispensed_by.username if rec.dispensed_by else "",
        dispensed_at=rec.dispensed_at,
        notes=rec.notes,
    )


# ─── Prescriptions ───────────────────────────────────────────────────────────

@router.get("/prescriptions", response_model=list[PrescriptionRead], dependencies=[Depends(require_permission("view_prescriptions"))])
def list_prescriptions(skip: int = 0, limit: int = 50, patient_id: int | None = None, db: Session = Depends(get_db)):
    q = db.query(Prescription)
    if patient_id is not None:
        q = q.filter(Prescription.patient_id == patient_id)
    prescriptions = q.order_by(Prescription.prescription_id.desc()).offset(skip).limit(limit).all()
    return [to_prescription_read(rx) for rx in prescriptions]


@router.get("/prescriptions/{prescription_id}", response_model=PrescriptionRead, dependencies=[Depends(require_permission("view_prescriptions"))])
def get_prescription(prescription_id: int, db: Session = Depends(get_db)):
    rx = db.query(Prescription).filter(Prescription.prescription_id == prescription_id).first()
    if not rx:
        raise HTTPException(status_code=404, detail="Prescription not found")
    return to_prescription_read(rx)


@router.post("/prescriptions", response_model=PrescriptionRead, dependencies=[Depends(require_permission("add_prescriptions"))])
def create_prescription(payload: PrescriptionCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    patient = db.query(Patient).filter(Patient.patient_id == payload.patient_id, Patient.is_archived.is_(False)).first()
    if not patient:
        raise HTTPException(status_code=400, detail="Patient not found or archived")

    if not payload.items:
        raise HTTPException(status_code=400, detail="Prescription must have at least one item")

    rx = Prescription(
        patient_id=payload.patient_id,
        doctor_name=(current_user.full_name or current_user.username),
        diagnosis=payload.diagnosis,
        notes=payload.notes,
        status="open",
        created_by_user_id=current_user.user_id,
    )
    db.add(rx)
    db.flush()

    for item in payload.items:
        drug = db.query(Drug).filter(Drug.drug_id == item.drug_id, Drug.is_active.is_(True)).first()
        if not drug:
            raise HTTPException(status_code=400, detail=f"Drug id {item.drug_id} not found or inactive")
        db.add(PrescriptionItem(
            prescription_id=rx.prescription_id,
            drug_id=item.drug_id,
            dosage=item.dosage,
            duration=item.duration,
            quantity_prescribed=item.quantity_prescribed,
        ))

    log_action(db, "create_prescription", actor_user_id=current_user.user_id, target_table="prescriptions", target_id=rx.prescription_id)
    db.commit()
    db.refresh(rx)
    return to_prescription_read(rx)


@router.post("/dispensing/dispatch/{prescription_id}", response_model=list[DispensingRecordRead], dependencies=[Depends(require_permission("dispense_drugs"))])
def dispatch_prescription(prescription_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rx = db.query(Prescription).filter(Prescription.prescription_id == prescription_id).first()
    if not rx:
        raise HTTPException(status_code=404, detail="Prescription not found")
    if rx.status != "open":
        raise HTTPException(status_code=400, detail="Only active prescriptions can be dispatched")
    if not rx.items:
        raise HTTPException(status_code=400, detail="Prescription has no items")

    records: list[DispensingRecord] = []
    for item in rx.items:
        required_qty = max(1, item.quantity_prescribed or 1)
        batch = (
            db.query(DrugBatch)
            .filter(
                and_(
                    DrugBatch.drug_id == item.drug_id,
                    DrugBatch.is_expired.is_(False),
                    DrugBatch.quantity_available >= required_qty,
                )
            )
            .order_by(DrugBatch.expiry_date.asc(), DrugBatch.batch_id.asc())
            .first()
        )
        if not batch:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient active stock for drug_id {item.drug_id}",
            )

        batch.quantity_available -= required_qty
        record = DispensingRecord(
            prescription_id=rx.prescription_id,
            patient_id=rx.patient_id,
            batch_id=batch.batch_id,
            quantity_dispensed=required_qty,
            dispensed_by_user_id=current_user.user_id,
            notes="dispatched",
        )
        db.add(record)
        db.flush()
        records.append(record)

    rx.status = "dispensed"
    log_action(
        db,
        "dispatch_prescription",
        actor_user_id=current_user.user_id,
        target_table="prescriptions",
        target_id=rx.prescription_id,
        detail={"items": len(records)},
    )
    db.commit()
    for record in records:
        db.refresh(record)
    return [to_dispensing_read(record) for record in records]


@router.patch("/prescriptions/{prescription_id}/cancel", response_model=PrescriptionRead, dependencies=[Depends(require_permission("add_prescriptions"))])
def cancel_prescription(prescription_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rx = db.query(Prescription).filter(Prescription.prescription_id == prescription_id).first()
    if not rx:
        raise HTTPException(status_code=404, detail="Prescription not found")
    if rx.status != "open":
        raise HTTPException(status_code=400, detail="Only open prescriptions can be cancelled")
    rx.status = "cancelled"
    log_action(db, "cancel_prescription", actor_user_id=current_user.user_id, target_table="prescriptions", target_id=prescription_id)
    db.commit()
    db.refresh(rx)
    return to_prescription_read(rx)


# ─── Dispensing ──────────────────────────────────────────────────────────────

@router.get("/dispensing", response_model=list[DispensingRecordRead], dependencies=[Depends(require_permission("view_dispensing"))])
def list_dispensing(skip: int = 0, limit: int = 50, patient_id: int | None = None, db: Session = Depends(get_db)):
    q = db.query(DispensingRecord)
    if patient_id is not None:
        q = q.filter(DispensingRecord.patient_id == patient_id)
    records = q.order_by(DispensingRecord.dispensed_at.desc()).offset(skip).limit(limit).all()
    return [to_dispensing_read(r) for r in records]


@router.post("/dispensing", response_model=DispensingRecordRead, dependencies=[Depends(require_permission("dispense_drugs"))])
def dispense_drug(payload: DispensingRecordCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Validate patient
    patient = db.query(Patient).filter(Patient.patient_id == payload.patient_id, Patient.is_archived.is_(False)).first()
    if not patient:
        raise HTTPException(status_code=400, detail="Patient not found or archived")

    # Validate batch
    batch = db.query(DrugBatch).filter(DrugBatch.batch_id == payload.batch_id).first()
    if not batch:
        raise HTTPException(status_code=400, detail="Batch not found")
    if batch.is_expired:
        raise HTTPException(status_code=400, detail="Cannot dispense from an expired batch")
    if batch.quantity_available < payload.quantity_dispensed:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient stock: available {batch.quantity_available}, requested {payload.quantity_dispensed}",
        )

    # Validate prescription linkage
    if payload.prescription_id:
        rx = db.query(Prescription).filter(Prescription.prescription_id == payload.prescription_id).first()
        if not rx or rx.status == "cancelled":
            raise HTTPException(status_code=400, detail="Invalid or cancelled prescription")

    # Decrement stock
    batch.quantity_available -= payload.quantity_dispensed

    record = DispensingRecord(
        prescription_id=payload.prescription_id,
        patient_id=payload.patient_id,
        batch_id=payload.batch_id,
        quantity_dispensed=payload.quantity_dispensed,
        dispensed_by_user_id=current_user.user_id,
        notes=payload.notes,
    )
    db.add(record)
    db.flush()

    # Mark prescription as dispensed if linked
    if payload.prescription_id:
        rx = db.query(Prescription).filter(Prescription.prescription_id == payload.prescription_id).first()
        if rx:
            rx.status = "dispensed"

    log_action(
        db,
        "dispense_drug",
        actor_user_id=current_user.user_id,
        target_table="dispensing_records",
        target_id=record.record_id,
        detail={
            "batch_id": payload.batch_id,
            "drug_name": batch.drug.drug_name,
            "quantity_dispensed": payload.quantity_dispensed,
            "patient_id": payload.patient_id,
        },
    )
    db.commit()
    db.refresh(record)
    return to_dispensing_read(record)
