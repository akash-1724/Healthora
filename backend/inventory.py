from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from deps import get_current_user, require_permission
from models import Drug, DrugBatch, Patient, User
from schemas import (
    DrugBatchCreate,
    DrugBatchRead,
    DrugCreate,
    DrugRead,
    DrugUpdate,
    InventoryUpdate,
    PatientCreate,
    PatientRead,
    PatientUpdate,
)

router = APIRouter(prefix="/api", tags=["inventory"])


def to_batch_read(batch: DrugBatch) -> DrugBatchRead:
    return DrugBatchRead(
        batch_id=batch.batch_id,
        drug_id=batch.drug_id,
        drug_name=batch.drug.drug_name,
        batch_no=batch.batch_no,
        expiry_date=batch.expiry_date,
        purchase_price=float(batch.purchase_price),
        selling_price=float(batch.selling_price),
        quantity_available=batch.quantity_available,
        is_expired=batch.is_expired,
    )


def to_patient_read(patient: Patient, creator_username: str | None = None) -> PatientRead:
    return PatientRead(
        patient_id=patient.patient_id,
        name=patient.name,
        address=patient.address,
        gender=patient.gender,
        contact=patient.contact,
        dob=patient.dob,
        created_by_user_id=patient.created_by_user_id,
        created_by=creator_username,
        created_at=patient.created_at,
        is_archived=patient.is_archived,
    )


def to_drug_read(drug: Drug, total_quantity: int = 0, active_batches: int = 0) -> DrugRead:
    return DrugRead(
        drug_id=drug.drug_id,
        drug_name=drug.drug_name,
        generic_name=drug.generic_name,
        formulation=drug.formulation,
        strength=drug.strength,
        schedule_type=drug.schedule_type,
        is_active=drug.is_active,
        low_stock_threshold=drug.low_stock_threshold,
        total_quantity=total_quantity,
        active_batches=active_batches,
    )


@router.get("/inventory", response_model=list[DrugBatchRead], dependencies=[Depends(require_permission("view_inventory"))])
def get_inventory(db: Session = Depends(get_db)):
    batches = db.query(DrugBatch).join(Drug).order_by(DrugBatch.batch_id.asc()).all()
    return [to_batch_read(batch) for batch in batches]


@router.get("/drugs", response_model=list[DrugRead], dependencies=[Depends(require_permission("view_drugs"))])
def list_drugs(db: Session = Depends(get_db)):
    drugs = db.query(Drug).order_by(Drug.drug_id.asc()).all()
    batches = db.query(DrugBatch).all()
    stats: dict[int, tuple[int, int]] = {}
    for batch in batches:
        total_qty, active_count = stats.get(batch.drug_id, (0, 0))
        total_qty += batch.quantity_available
        if not batch.is_expired and batch.quantity_available > 0:
            active_count += 1
        stats[batch.drug_id] = (total_qty, active_count)
    return [to_drug_read(drug, *(stats.get(drug.drug_id, (0, 0)))) for drug in drugs]


@router.post("/drugs", response_model=DrugRead, dependencies=[Depends(require_permission("add_drug"))])
def add_drug(payload: DrugCreate, db: Session = Depends(get_db)):
    max_drug = db.query(Drug.drug_id).order_by(Drug.drug_id.desc()).first()
    next_drug_id = (max_drug[0] if max_drug else 0) + 1
    drug = Drug(
        drug_id=next_drug_id,
        drug_name=payload.drug_name,
        generic_name=payload.generic_name,
        formulation=payload.formulation,
        strength=payload.strength,
        schedule_type=payload.schedule_type,
        low_stock_threshold=payload.low_stock_threshold,
        is_active=True,
    )
    db.add(drug)
    db.commit()
    db.refresh(drug)
    return to_drug_read(drug)


@router.put("/drugs/{drug_id}", response_model=DrugRead, dependencies=[Depends(require_permission("add_drug"))])
def update_drug(drug_id: int, payload: DrugUpdate, db: Session = Depends(get_db)):
    drug = db.query(Drug).filter(Drug.drug_id == drug_id).first()
    if not drug:
        raise HTTPException(status_code=404, detail="Drug not found")

    if payload.drug_name is not None:
        drug.drug_name = payload.drug_name
    if payload.generic_name is not None:
        drug.generic_name = payload.generic_name
    if payload.formulation is not None:
        drug.formulation = payload.formulation
    if payload.strength is not None:
        drug.strength = payload.strength
    if payload.schedule_type is not None:
        drug.schedule_type = payload.schedule_type
    if payload.low_stock_threshold is not None:
        drug.low_stock_threshold = payload.low_stock_threshold
    if payload.is_active is not None:
        drug.is_active = payload.is_active

    db.commit()
    db.refresh(drug)
    related = db.query(DrugBatch).filter(DrugBatch.drug_id == drug.drug_id).all()
    total_qty = sum(row.quantity_available for row in related)
    active_count = sum(1 for row in related if not row.is_expired and row.quantity_available > 0)
    return to_drug_read(drug, total_qty, active_count)


@router.patch("/drugs/{drug_id}/disable", response_model=DrugRead, dependencies=[Depends(require_permission("add_drug"))])
def disable_drug(drug_id: int, db: Session = Depends(get_db)):
    drug = db.query(Drug).filter(Drug.drug_id == drug_id).first()
    if not drug:
        raise HTTPException(status_code=404, detail="Drug not found")
    drug.is_active = False
    db.commit()
    db.refresh(drug)
    related = db.query(DrugBatch).filter(DrugBatch.drug_id == drug.drug_id).all()
    total_qty = sum(row.quantity_available for row in related)
    active_count = sum(1 for row in related if not row.is_expired and row.quantity_available > 0)
    return to_drug_read(drug, total_qty, active_count)


@router.post("/drug-batches", response_model=DrugBatchRead, dependencies=[Depends(require_permission("add_batch"))])
def add_batch(payload: DrugBatchCreate, db: Session = Depends(get_db)):
    drug = db.query(Drug).filter(Drug.drug_id == payload.drug_id).first()
    if not drug:
        raise HTTPException(status_code=400, detail="Invalid drug_id")

    exists = db.query(DrugBatch).filter(DrugBatch.batch_no == payload.batch_no).first()
    if exists:
        raise HTTPException(status_code=400, detail="batch_no already exists")

    max_batch = db.query(DrugBatch.batch_id).order_by(DrugBatch.batch_id.desc()).first()
    next_batch_id = (max_batch[0] if max_batch else 0) + 1

    batch = DrugBatch(
        batch_id=next_batch_id,
        drug_id=payload.drug_id,
        batch_no=payload.batch_no,
        expiry_date=payload.expiry_date,
        purchase_price=payload.purchase_price,
        selling_price=payload.selling_price,
        quantity_available=payload.quantity_available,
        is_expired=False,
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)
    return to_batch_read(batch)


@router.patch("/drug-batches/{batch_id}/mark-expired", response_model=DrugBatchRead, dependencies=[Depends(require_permission("add_batch"))])
def mark_batch_expired(batch_id: int, db: Session = Depends(get_db)):
    batch = db.query(DrugBatch).filter(DrugBatch.batch_id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    batch.is_expired = True
    db.commit()
    db.refresh(batch)
    return to_batch_read(batch)


@router.put("/inventory/{batch_id}", response_model=DrugBatchRead, dependencies=[Depends(require_permission("update_inventory"))])
def update_inventory(batch_id: int, payload: InventoryUpdate, db: Session = Depends(get_db)):
    batch = db.query(DrugBatch).filter(DrugBatch.batch_id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    batch.quantity_available = payload.quantity_available
    db.commit()
    db.refresh(batch)
    return to_batch_read(batch)


@router.get("/patients", response_model=list[PatientRead], dependencies=[Depends(require_permission("view_patients"))])
def list_patients(db: Session = Depends(get_db)):
    patients = db.query(Patient).filter(Patient.is_archived.is_(False)).order_by(Patient.patient_id.asc()).all()
    creator_ids = {row.created_by_user_id for row in patients if row.created_by_user_id is not None}
    creators = db.query(User).filter(User.user_id.in_(creator_ids)).all() if creator_ids else []
    creator_map = {user.user_id: user.username for user in creators}
    return [to_patient_read(row, creator_map.get(row.created_by_user_id)) for row in patients]


@router.post("/patients", response_model=PatientRead, dependencies=[Depends(require_permission("add_patients"))])
def add_patient(payload: PatientCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    max_patient = db.query(Patient.patient_id).order_by(Patient.patient_id.desc()).first()
    next_patient_id = (max_patient[0] if max_patient else 10000) + 1
    patient = Patient(
        patient_id=next_patient_id,
        name=payload.name,
        address=payload.address,
        gender=payload.gender,
        contact=payload.contact,
        dob=payload.dob,
        created_by_user_id=current_user.user_id,
        is_archived=False,
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return to_patient_read(patient, current_user.username)


@router.put("/patients/{patient_id}", response_model=PatientRead, dependencies=[Depends(require_permission("view_patients"))])
def edit_patient(patient_id: int, payload: PatientUpdate, db: Session = Depends(get_db)):
    patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    if payload.name is not None:
        patient.name = payload.name
    if payload.address is not None:
        patient.address = payload.address
    if payload.gender is not None:
        patient.gender = payload.gender
    if payload.contact is not None:
        patient.contact = payload.contact
    if payload.dob is not None:
        patient.dob = payload.dob
    db.commit()
    db.refresh(patient)
    creator = db.query(User).filter(User.user_id == patient.created_by_user_id).first() if patient.created_by_user_id else None
    return to_patient_read(patient, creator.username if creator else None)


@router.patch("/patients/{patient_id}/archive", response_model=PatientRead, dependencies=[Depends(require_permission("view_patients"))])
def archive_patient(patient_id: int, db: Session = Depends(get_db)):
    patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    patient.is_archived = True
    db.commit()
    db.refresh(patient)
    creator = db.query(User).filter(User.user_id == patient.created_by_user_id).first() if patient.created_by_user_id else None
    return to_patient_read(patient, creator.username if creator else None)


@router.get("/ai-report", dependencies=[Depends(require_permission("view_ai_report"))])
def ai_report_stub():
    return {"message": "Coming soon"}


def count_expiry_risk(batches: list[DrugBatch]) -> int:
    today = date.today()
    return sum(1 for row in batches if not row.is_expired and 0 <= (row.expiry_date - today).days <= 60)


@router.get("/dashboard-summary", dependencies=[Depends(require_permission("view_dashboard_summary"))])
def dashboard_summary(db: Session = Depends(get_db)):
    batches = db.query(DrugBatch).all()
    usable_stock = sum(row.quantity_available for row in batches if not row.is_expired)
    total_stock = len(batches)
    expiry_risk = count_expiry_risk(batches)

    drugs = db.query(Drug).all()
    by_drug = {}
    for row in batches:
        by_drug[row.drug_id] = by_drug.get(row.drug_id, 0) + row.quantity_available
    low_stock_alerts = sum(1 for drug in drugs if by_drug.get(drug.drug_id, 0) < drug.low_stock_threshold)

    total_patients = db.query(Patient).filter(Patient.is_archived.is_(False)).count()
    return {
        "usable_stock": usable_stock,
        "total_stock": total_stock,
        "expiry_risk": expiry_risk,
        "low_stock_alerts": low_stock_alerts,
        "total_patients": total_patients,
    }
