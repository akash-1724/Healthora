import os
import random
import zipfile
import json
import logging
from pathlib import Path
from datetime import date, datetime, timedelta
from xml.etree import ElementTree as ET

from sqlalchemy import text
from sqlalchemy.orm import Session

from models import (
    AuditLog,
    DispensingRecord,
    Drug,
    DrugBatch,
    Notification,
    Patient,
    Prescription,
    PrescriptionItem,
    PurchaseOrder,
    PurchaseOrderItem,
    Role,
    Supplier,
    User,
)

NS = {
    "m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}

DEFAULT_ROLES = [
    ("system_admin", "System Admin"),
    ("chief_medical_officer", "Chief Medical Officer"),
    ("pharmacy_manager", "Pharmacy Manager"),
    ("senior_pharmacist", "Senior Pharmacist"),
    ("staff_pharmacist", "Staff Pharmacist"),
    ("inventory_clerk", "Inventory Clerk"),
]

ROLE_LABEL_TO_CODE = {
    "System Admin": "system_admin",
    "Chief Medical Officer": "chief_medical_officer",
    "Pharmacy Manager": "pharmacy_manager",
    "Senior Pharmacist": "senior_pharmacist",
    "Staff Pharmacist": "staff_pharmacist",
    "Inventory Clerk": "inventory_clerk",
}

logger = logging.getLogger("healthora.seed")

HOSPITAL_V2_TABLES = [
    '"User"',
    "controlled_drug_log",
    "pharmacy_bill_item",
    "pharmacy_bill",
    "dispense_item",
    "dispense",
    "prescription_detail",
    "prescription",
    "stock_transaction",
    "purchase_order_item",
    "purchase_order",
    "store_inventory",
    "pharmacy_store",
    "drug_batch",
    "supplier",
    "drug",
    "manufacturer",
    "encounter",
    "doctor",
    "patient",
    "department",
    "role",
    "hospital",
]

FALLBACK_DRUG_ROWS = [
    ["1", "Aspirin Ecosprin", "Acetylsalicylic Acid", "Tablet", "75mg", "OTC", "1"],
    ["2", "Atorva-20", "Atorvastatin", "Tablet", "20mg", "Schedule H", "3"],
    ["6", "Dolo 650", "Paracetamol", "Tablet", "650mg", "OTC", "1"],
    ["7", "Actrapid", "Insulin (Human)", "Injection", "100 IU/ml", "Schedule H", "6"],
]

FALLBACK_BATCH_ROWS = [
    ["1", "1", "B2025-001", "46096", "1.25", "1.75", "850"],
    ["3", "2", "B2025-003", "46235", "6.5", "9.75", "380"],
    ["11", "6", "B2025-011", "46154", "1.8", "2.52", "780"],
    ["13", "7", "B2025-013", "46327", "350.00", "525.00", "210"],
]


def _normalize_key(value: str | None) -> str:
    return " ".join((value or "").strip().lower().split())


def _safe_int(value: str | None) -> int | None:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    try:
        return int(float(raw))
    except (TypeError, ValueError):
        return None


def _safe_float(value: str | None) -> float | None:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def excel_date_to_date(value: str | None) -> date | None:
    if not value:
        return None
    return date(1899, 12, 30) + timedelta(days=int(float(value)))


def excel_date_to_datetime(value: str | None) -> datetime:
    if not value:
        return datetime.utcnow()
    return datetime(1899, 12, 30) + timedelta(days=float(value))


def _sheet_rows(sheet_root: ET.Element, shared_strings: list[str]) -> list[list[str]]:
    rows = []
    for row in sheet_root.findall(".//m:sheetData/m:row", NS):
        values = []
        for cell in row.findall("m:c", NS):
            value_node = cell.find("m:v", NS)
            if value_node is None:
                values.append("")
                continue
            raw = value_node.text or ""
            if cell.attrib.get("t") == "s":
                idx = int(raw)
                values.append(shared_strings[idx] if idx < len(shared_strings) else "")
            else:
                values.append(raw)
        if any(val != "" for val in values):
            rows.append(values)
    return rows


def load_his_data() -> dict[str, list[list[str]]]:
    workbook_path = os.getenv("HIS_XLSX_PATH", "/app/HIS (1).xlsx")
    if not os.path.exists(workbook_path):
        return {}

    with zipfile.ZipFile(workbook_path) as archive:
        shared_strings: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            shared_root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            for item in shared_root.findall("m:si", NS):
                shared_strings.append("".join((node.text or "") for node in item.findall(".//m:t", NS)))

        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        rel_map = {node.attrib["Id"]: node.attrib["Target"] for node in rels}

        output: dict[str, list[list[str]]] = {}
        wanted = {"Department", "Role", "User ", "Paitent", "Drug", "Drug_Batch", "Supplier"}
        sheets_node = workbook.find("m:sheets", NS)
        if sheets_node is None:
            return {}
        for sheet in sheets_node:
            name = sheet.attrib["name"]
            if name not in wanted:
                continue
            rid = sheet.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
            target = rel_map[rid]
            path = "xl/" + target if not target.startswith("xl/") else target
            sheet_root = ET.fromstring(archive.read(path))
            output[name] = _sheet_rows(sheet_root, shared_strings)

    return output


def seed_roles(db: Session, his_data: dict[str, list[list[str]]]):
    role_rows = his_data.get("Role", [])
    roles_from_his = []
    if len(role_rows) > 1:
        for row in role_rows[1:]:
            if len(row) < 2:
                continue
            role_label = row[1].strip()
            role_code = ROLE_LABEL_TO_CODE.get(role_label)
            if role_code:
                roles_from_his.append((role_code, role_label))

    role_seed = roles_from_his or DEFAULT_ROLES

    legacy_map = {
        "admin": "system_admin",
        "doctor": "chief_medical_officer",
        "pharmacist": "staff_pharmacist",
    }

    for old_name, new_name in legacy_map.items():
        old_role = db.query(Role).filter(Role.name == old_name).first()
        new_role = db.query(Role).filter(Role.name == new_name).first()
        if old_role:
            if new_role:
                users = db.query(User).filter(User.role_id == old_role.id).all()
                for user in users:
                    user.role_id = new_role.id
                db.delete(old_role)
            else:
                old_role.name = new_name
                old_role.display_name = dict(role_seed)[new_name]
    db.commit()

    for role_name, display_name in role_seed:
        existing = db.query(Role).filter(Role.name == role_name).first()
        if not existing:
            db.add(Role(name=role_name, display_name=display_name))
        else:
            existing.display_name = display_name
    db.commit()


def role_id(db: Session, role_name: str) -> int:
    role = db.query(Role).filter(Role.name == role_name).first()
    if not role:
        raise ValueError(f"Missing role: {role_name}")
    return role.id


def seed_users(db: Session, his_data: dict[str, list[list[str]]]):
    department_map: dict[int, str] = {}
    department_rows = his_data.get("Department", [])
    for row in department_rows[1:]:
        if len(row) < 3:
            continue
        department_map[int(float(row[0]))] = row[2]

    user_rows = his_data.get("User ", [])
    if len(user_rows) > 1:
        for row in user_rows[1:]:
            if len(row) < 7:
                continue
            username = row[1].strip()
            if not username:
                continue
            user_role_id = int(float(row[3])) if row[3] else 5
            role_code = {
                1: "system_admin",
                2: "chief_medical_officer",
                3: "pharmacy_manager",
                4: "senior_pharmacist",
                5: "staff_pharmacist",
                6: "inventory_clerk",
            }.get(user_role_id, "staff_pharmacist")
            dept_name = department_map.get(int(float(row[4])) if row[4] else 103, "Pharmacy")

            existing = db.query(User).filter(User.username == username).first()
            if not existing:
                db.add(
                    User(
                        user_id=int(float(row[0])) if row[0] else None,
                        username=username,
                        password=row[2] or "pass123",
                        role_id=role_id(db, role_code),
                        department=dept_name,
                        is_active=(row[5] or "T") == "T",
                        created_at=excel_date_to_datetime(row[6]),
                    )
                )
            else:
                existing.password = row[2] or existing.password
                existing.role_id = role_id(db, role_code)
                existing.department = dept_name
                existing.is_active = (row[5] or "T") == "T"
    db.commit()

    user_seed = [
        ("sysadmin", "admin", "system_admin", "Administration"),
        ("cmo1", "cmo", "chief_medical_officer", "General Medicine"),
        ("pm1", "manager", "pharmacy_manager", "Pharmacy"),
        ("senior1", "senior", "senior_pharmacist", "Pharmacy"),
        ("staff1", "staff", "staff_pharmacist", "Pharmacy"),
        ("clerk1", "clerk", "inventory_clerk", "Pharmacy"),
    ]

    username_alias_map = {
        "admin": "sysadmin",
        "doctor1": "cmo1",
        "pharmacist1": "staff1",
        "manager1": "pm1",
        "spharm1": "senior1",
        "stpharm1": "staff1",
    }

    for old_username, new_username in username_alias_map.items():
        old_user = db.query(User).filter(User.username == old_username).first()
        if old_user:
            target = db.query(User).filter(User.username == new_username).first()
            if target and target.user_id != old_user.user_id:
                db.delete(old_user)
            else:
                old_user.username = new_username
            db.flush()
    db.commit()

    max_user = db.query(User.user_id).order_by(User.user_id.desc()).first()
    next_user_id = (max_user[0] if max_user else 0) + 1

    for username, password, role_name, department in user_seed:
        existing = db.query(User).filter(User.username == username).first()
        if not existing:
            db.add(
                User(
                    user_id=next_user_id,
                    username=username,
                    password=password,
                    role_id=role_id(db, role_name),
                    department=department,
                    is_active=True,
                )
            )
            next_user_id += 1
        else:
            existing.password = password
            existing.role_id = role_id(db, role_name)
            existing.department = department
            existing.is_active = True
    db.commit()


def seed_patients(db: Session, his_data: dict[str, list[list[str]]]):
    creator_usernames = ["cmo1", "sysadmin", "pm1", "senior1", "staff1", "clerk1"]
    creators = db.query(User).filter(User.username.in_(creator_usernames)).order_by(User.user_id.asc()).all()
    creator_ids = [user.user_id for user in creators]

    def random_creator_sequence(total: int) -> list[int]:
        if not creator_ids or total <= 0:
            return []
        sequence: list[int] = []
        while len(sequence) < total:
            sequence.extend(random.sample(creator_ids, len(creator_ids)))
        return sequence[:total]

    if db.query(Patient).count() > 0:
        existing_rows = db.query(Patient).order_by(Patient.patient_id.asc()).all()
        existing_creator_ids = {row.created_by_user_id for row in existing_rows if row.created_by_user_id is not None}
        if creator_ids and len(existing_creator_ids) <= 1:
            randomized = random_creator_sequence(len(existing_rows))
            for index, row in enumerate(existing_rows):
                row.created_by_user_id = randomized[index]
            db.commit()
        return

    patient_rows = his_data.get("Paitent", [])
    rows = patient_rows[1:]
    if not rows:
        rows = [
            ["10001", "Rahul Menon", "Aluva", "27463", "Urban", "+91-98765-43210", "Male", "O+"],
            ["10002", "Anju Thomas", "Thrissur", "22245", "Rural", "+91-87654-32109", "Female", "A+"],
            ["10003", "Faisal Rahman", "Malappuram", "39661", "Near Water-body", "+91-76543-21098", "Male", "B-"],
            ["10004", "Lakshmi Pillai", "Varkala", "17581", "Rural", "+91-65432-10987", "Female", "AB+"],
        ]

    limit = int(os.getenv("HIS_PATIENT_SEED_LIMIT", "300"))
    to_insert = []
    randomized = random_creator_sequence(len(rows[:limit]))
    for row in rows[:limit]:
        if len(row) < 7:
            continue
        creator_id = randomized[len(to_insert)] if randomized else None
        to_insert.append(
            Patient(
                patient_id=int(float(row[0])),
                name=row[1],
                address=row[2],
                dob=excel_date_to_date(row[3]),
                contact=row[5],
                gender=row[6],
                blood_group=row[7] if len(row) > 7 else None,
                created_by_user_id=creator_id,
                is_archived=False,
            )
        )
    if to_insert:
        db.add_all(to_insert)
        db.commit()


def seed_drugs_and_batches(db: Session, his_data: dict[str, list[list[str]]]) -> dict[int, int]:
    """
    Ensure core drugs exist in an idempotent way and return a source-id -> drug_id map.

    We resolve by business key first (name/generic), not by assuming fixed numeric IDs.
    """
    source_to_drug_id: dict[int, int] = {}

    existing_drugs = db.query(Drug).order_by(Drug.drug_id.asc()).all()
    by_id: dict[int, Drug] = {}
    by_name: dict[str, Drug] = {}
    by_generic: dict[str, Drug] = {}

    def register(drug: Drug):
        by_id[drug.drug_id] = drug
        name_key = _normalize_key(drug.drug_name)
        generic_key = _normalize_key(drug.generic_name)
        if name_key and name_key not in by_name:
            by_name[name_key] = drug
        if generic_key and generic_key not in by_generic:
            by_generic[generic_key] = drug

    for existing in existing_drugs:
        register(existing)

    def ensure_drug(
        source_id: int | None,
        drug_name: str | None,
        generic_name: str | None,
        formulation: str | None,
        strength: str | None,
        schedule_type: str | None,
        threshold: int = 50,
    ) -> Drug:
        name_key = _normalize_key(drug_name)
        generic_key = _normalize_key(generic_name)

        candidate = None
        if name_key:
            candidate = by_name.get(name_key)
        if candidate is None and generic_key:
            candidate = by_generic.get(generic_key)
        if candidate is None and source_id is not None:
            candidate = by_id.get(source_id)

        if candidate is None:
            candidate = Drug(
                drug_name=(drug_name or generic_name or "Unnamed Drug").strip(),
                generic_name=(generic_name or "").strip() or None,
                formulation=(formulation or "").strip() or None,
                strength=(strength or "").strip() or None,
                schedule_type=(schedule_type or "").strip() or None,
                is_active=True,
                low_stock_threshold=max(1, threshold),
            )
            db.add(candidate)
            db.flush()
            register(candidate)
        else:
            if not candidate.generic_name and generic_name:
                candidate.generic_name = generic_name.strip()
            if not candidate.formulation and formulation:
                candidate.formulation = formulation.strip()
            if not candidate.strength and strength:
                candidate.strength = strength.strip()
            if not candidate.schedule_type and schedule_type:
                candidate.schedule_type = schedule_type.strip()
            if not candidate.low_stock_threshold or int(candidate.low_stock_threshold) <= 0:
                candidate.low_stock_threshold = max(1, threshold)
            candidate.is_active = True

        if source_id is not None:
            source_to_drug_id[source_id] = candidate.drug_id
        return candidate

    drug_rows = his_data.get("Drug", [])[1:]
    for row in drug_rows:
        if len(row) < 6:
            continue
        source_id = _safe_int(row[0])
        ensure_drug(
            source_id=source_id,
            drug_name=(row[1] or "").strip(),
            generic_name=(row[2] or "").strip(),
            formulation=(row[3] or "").strip(),
            strength=(row[4] or "").strip(),
            schedule_type=(row[5] or "").strip(),
            threshold=50,
        )

    for row in FALLBACK_DRUG_ROWS:
        source_id = _safe_int(row[0])
        threshold = 80 if _normalize_key(row[1]) == "paracetamol" else 50
        ensure_drug(
            source_id=source_id,
            drug_name=(row[1] or "").strip(),
            generic_name=(row[2] or "").strip(),
            formulation=(row[3] or "").strip(),
            strength=(row[4] or "").strip(),
            schedule_type=(row[5] or "").strip(),
            threshold=threshold,
        )

    canonical_para = db.query(Drug).filter(Drug.drug_name == "Paracetamol").first()
    if not canonical_para:
        canonical_para = Drug(
            drug_name="Paracetamol",
            generic_name="Paracetamol",
            formulation="Tablet",
            strength="500mg",
            schedule_type="OTC",
            is_active=True,
            low_stock_threshold=80,
        )
        db.add(canonical_para)
        db.flush()

    db.commit()
    return source_to_drug_id


def seed_drug_batches(db: Session, his_data: dict[str, list[list[str]]], source_to_drug_id: dict[int, int]):
    supplier_ids = [s.supplier_id for s in db.query(Supplier).order_by(Supplier.supplier_id.asc()).all()]
    if not supplier_ids:
        logger.warning("Skipping drug batch seed because no suppliers exist")
        return

    existing_batches = {batch.batch_no: batch for batch in db.query(DrugBatch).order_by(DrugBatch.batch_id.asc()).all()}
    valid_drug_ids = {row[0] for row in db.query(Drug.drug_id).all()}

    batch_rows = his_data.get("Drug_Batch", [])[1:] or FALLBACK_BATCH_ROWS

    skipped_rows = 0
    try:
        for idx, row in enumerate(batch_rows):
            if len(row) < 7:
                skipped_rows += 1
                continue

            source_drug_id = _safe_int(row[1])
            mapped_drug_id = source_to_drug_id.get(source_drug_id) if source_drug_id is not None else None
            if mapped_drug_id is None and source_drug_id in valid_drug_ids:
                mapped_drug_id = source_drug_id

            if mapped_drug_id not in valid_drug_ids:
                skipped_rows += 1
                continue

            batch_no = (row[2] or "").strip() or f"AUTO-BATCH-{mapped_drug_id}-{idx + 1}"
            expiry_date = excel_date_to_date(row[3]) or (date.today() + timedelta(days=365))
            purchase_price = _safe_float(row[4]) or 1.0
            selling_price = _safe_float(row[5]) or max(1.0, round(purchase_price * 1.2, 2))
            quantity_available = _safe_int(row[6])
            if quantity_available is None:
                quantity_available = 0

            supplier_id = supplier_ids[idx % len(supplier_ids)]
            existing = existing_batches.get(batch_no)
            if existing:
                existing.drug_id = mapped_drug_id
                existing.supplier_id = existing.supplier_id or supplier_id
                if existing.expiry_date is None:
                    existing.expiry_date = expiry_date
                if existing.purchase_price is None:
                    existing.purchase_price = purchase_price
                if existing.selling_price is None:
                    existing.selling_price = selling_price
                if existing.quantity_available is None:
                    existing.quantity_available = quantity_available
            else:
                new_batch = DrugBatch(
                    drug_id=mapped_drug_id,
                    batch_no=batch_no,
                    expiry_date=expiry_date,
                    purchase_price=purchase_price,
                    selling_price=selling_price,
                    quantity_available=quantity_available,
                    supplier_id=supplier_id,
                    is_expired=False,
                )
                db.add(new_batch)
                existing_batches[batch_no] = new_batch

        batches_without_supplier = (
            db.query(DrugBatch).filter(DrugBatch.supplier_id.is_(None)).order_by(DrugBatch.batch_id.asc()).all()
        )
        for idx, batch in enumerate(batches_without_supplier):
            batch.supplier_id = supplier_ids[idx % len(supplier_ids)]

        db.commit()
        if skipped_rows:
            logger.warning("Skipped %d drug batch rows due to invalid/missing drug mapping", skipped_rows)
    except Exception:
        db.rollback()
        logger.exception("Drug batch seeding failed; rolled back pending batch changes")
        raise


def seed_suppliers(db: Session, his_data: dict[str, list[list[str]]]):
    fallback = [
        ("Global Pharma Distributors", "Anoop Mathew", "+91-98112-34567", "sales@globalpharma.in", "Kochi, Kerala"),
        ("Medline Lifesciences", "Reshma Nair", "+91-98220-11446", "contact@medline.in", "Thrissur, Kerala"),
        ("CarePlus Wholesale", "Javed Rahman", "+91-98730-22011", "hello@carepluswholesale.in", "Kozhikode, Kerala"),
        ("Aster Drug Agencies", "Simi Joseph", "+91-99614-77880", "orders@asterdrug.in", "Ernakulam, Kerala"),
        ("Nova Med Supply", "Arun George", "+91-98465-42220", "support@novamed.in", "Palakkad, Kerala"),
        ("Prime Health Traders", "Priya S", "+91-98957-31009", "ops@primehealth.in", "Kannur, Kerala"),
        ("Lifecare Therapeutics", "Nikhil Das", "+91-94471-22008", "info@lifecaretx.in", "Kottayam, Kerala"),
        ("Unity Pharma Network", "Anita Roy", "+91-93882-11773", "connect@unitypharma.in", "Thiruvananthapuram, Kerala"),
    ]

    existing_suppliers = db.query(Supplier).order_by(Supplier.supplier_id.asc()).all()
    if existing_suppliers:
        fallback_by_name = {name: (contact, phone, email, address) for name, contact, phone, email, address in fallback}
        for supplier in existing_suppliers:
            if supplier.name in fallback_by_name:
                contact, phone, email, address = fallback_by_name[supplier.name]
                supplier.contact_person = supplier.contact_person or contact
                supplier.phone = supplier.phone or phone
                supplier.email = supplier.email or email
                supplier.address = supplier.address or address
            supplier.is_active = True
        db.commit()
    else:
        supplier_rows = his_data.get("Supplier", [])[1:]
        suppliers_to_add: list[Supplier] = []

        if supplier_rows:
            for row in supplier_rows[:10]:
                if len(row) < 2:
                    continue
                name = (row[1] or "").strip()
                if not name:
                    continue
                contact_blob = (row[3] if len(row) > 3 else "") or ""
                phone_guess = contact_blob.split("/")[0].strip() if contact_blob else None
                suppliers_to_add.append(
                    Supplier(
                        name=name,
                        contact_person=None,
                        phone=phone_guess,
                        email=None,
                        address=None,
                        is_active=True,
                    )
                )

        if not suppliers_to_add:
            suppliers_to_add = [
                Supplier(name=n, contact_person=c, phone=p, email=e, address=a, is_active=True)
                for n, c, p, e, a in fallback
            ]

        db.add_all(suppliers_to_add)
        db.commit()

def _daterange_points(start_dt: datetime, end_dt: datetime, step_days: int) -> list[datetime]:
    points: list[datetime] = []
    current = start_dt
    while current <= end_dt:
        points.append(current)
        current += timedelta(days=step_days)
    return points


def _ensure_batch_for_drug(db: Session, drug: Drug, supplier_id: int | None, ref_dt: datetime) -> DrugBatch:
    batch = (
        db.query(DrugBatch)
        .filter(DrugBatch.drug_id == drug.drug_id)
        .order_by(DrugBatch.expiry_date.desc())
        .first()
    )
    if batch:
        return batch

    batch = DrugBatch(
        drug_id=drug.drug_id,
        batch_no=f"AUTO-{drug.drug_id}-{ref_dt.strftime('%Y%m%d%H%M%S')}",
        expiry_date=(ref_dt + timedelta(days=540)).date(),
        purchase_price=10.0,
        selling_price=14.5,
        quantity_available=500,
        supplier_id=supplier_id,
        is_expired=False,
    )
    db.add(batch)
    db.flush()
    return batch


def seed_operational_history(db: Session):
    start_dt = datetime(2024, 1, 1, 10, 0, 0)
    end_dt = datetime(2025, 3, 5, 18, 0, 0)

    random.seed(20240301)

    users = db.query(User).order_by(User.user_id.asc()).all()
    patients = db.query(Patient).order_by(Patient.patient_id.asc()).all()
    drugs = db.query(Drug).filter(Drug.is_active.is_(True)).order_by(Drug.drug_id.asc()).all()
    suppliers = db.query(Supplier).filter(Supplier.is_active.is_(True)).order_by(Supplier.supplier_id.asc()).all()

    if not users or not patients or not drugs or not suppliers:
        return

    role_map = {user.user_id: (user.role.name if user.role else "") for user in users}
    doctor_users = [u for u in users if role_map.get(u.user_id) in {"chief_medical_officer", "system_admin"}] or users[:]
    pharmacy_users = [
        u
        for u in users
        if role_map.get(u.user_id) in {"pharmacy_manager", "senior_pharmacist", "staff_pharmacist", "inventory_clerk"}
    ] or users[:]

    span_days = max(1, (end_dt - start_dt).days)
    para_drug = db.query(Drug).filter(Drug.drug_name == "Paracetamol").first()
    para_batch = None
    if para_drug:
        para_batch = _ensure_batch_for_drug(db, para_drug, suppliers[0].supplier_id, datetime(2024, 1, 1, 10, 0, 0))
        if int(para_batch.quantity_available or 0) < 600:
            para_batch.quantity_available = 900

    for idx, supplier in enumerate(suppliers):
        supplier.created_at = start_dt + timedelta(days=int((idx * span_days) / max(1, len(suppliers) - 1)))
    for idx, patient in enumerate(patients):
        patient.created_at = start_dt + timedelta(days=int((idx * span_days) / max(1, len(patients) - 1)))
        if patient.created_by_user_id is None:
            patient.created_by_user_id = random.choice(doctor_users).user_id
    db.commit()

    po_dates = _daterange_points(datetime(2024, 1, 7, 11, 0, 0), datetime(2025, 3, 5, 14, 0, 0), 9)
    existing_po_days = {
        row[0]
        for row in db.execute(
            text(
                "SELECT DATE(created_at) FROM purchase_orders WHERE created_at >= :start_dt AND created_at <= :end_dt"
            ),
            {"start_dt": start_dt, "end_dt": end_dt},
        ).fetchall()
    }

    for dt in po_dates:
        if dt.date() in existing_po_days:
            continue
        supplier = random.choice(suppliers)
        ordered_by = random.choice(pharmacy_users)
        status = random.choices(["received", "pending", "cancelled"], weights=[75, 20, 5], k=1)[0]
        received_at = dt + timedelta(days=random.randint(1, 4)) if status == "received" else None

        po = PurchaseOrder(
            supplier_id=supplier.supplier_id,
            ordered_by_user_id=ordered_by.user_id,
            status=status,
            notes=f"Auto-seeded PO for {supplier.name}",
            created_at=dt,
            received_at=received_at,
        )
        db.add(po)
        db.flush()

        chosen_drugs = random.sample(drugs, k=min(random.randint(2, 4), len(drugs)))
        for drug in chosen_drugs:
            qty_ordered = random.randint(80, 260)
            qty_received = qty_ordered if status == "received" else random.randint(0, max(1, qty_ordered // 3))
            db.add(
                PurchaseOrderItem(
                    po_id=po.po_id,
                    drug_id=drug.drug_id,
                    quantity_ordered=qty_ordered,
                    quantity_received=qty_received,
                    unit_price=round(random.uniform(8.0, 55.0), 2),
                )
            )
            if qty_received > 0:
                batch = _ensure_batch_for_drug(db, drug, supplier.supplier_id, dt)
                batch.quantity_available = max(0, int(batch.quantity_available or 0)) + qty_received

    db.commit()

    if (
        db.execute(text("SELECT COUNT(*) FROM purchase_orders WHERE DATE(created_at)=DATE '2025-03-05'"))
        .scalar_one()
        == 0
    ):
        supplier = random.choice(suppliers)
        ordered_by = random.choice(pharmacy_users)
        po = PurchaseOrder(
            supplier_id=supplier.supplier_id,
            ordered_by_user_id=ordered_by.user_id,
            status="received",
            notes="Auto-seeded PO closing date",
            created_at=datetime(2025, 3, 5, 13, 0, 0),
            received_at=datetime(2025, 3, 5, 17, 0, 0),
        )
        db.add(po)
        db.flush()
        for drug in random.sample(drugs, k=min(3, len(drugs))):
            qty = random.randint(100, 220)
            db.add(
                PurchaseOrderItem(
                    po_id=po.po_id,
                    drug_id=drug.drug_id,
                    quantity_ordered=qty,
                    quantity_received=qty,
                    unit_price=round(random.uniform(8.0, 55.0), 2),
                )
            )
        db.commit()

    rx_dates = _daterange_points(datetime(2024, 1, 3, 9, 30, 0), datetime(2025, 3, 5, 17, 30, 0), 4)
    existing_rx_days = {
        row[0]
        for row in db.execute(
            text("SELECT DATE(created_at) FROM prescriptions WHERE created_at >= :start_dt AND created_at <= :end_dt"),
            {"start_dt": start_dt, "end_dt": end_dt},
        ).fetchall()
    }

    for dt in rx_dates:
        if dt.date() in existing_rx_days:
            continue
        patient = random.choice(patients)
        doctor = random.choice(doctor_users)
        status = random.choices(["dispensed", "open", "cancelled"], weights=[78, 18, 4], k=1)[0]

        prescription = Prescription(
            patient_id=patient.patient_id,
            doctor_name=doctor.full_name or doctor.username,
            diagnosis=random.choice(["Fever", "Viral infection", "Pain", "Hypertension follow-up", "Diabetes follow-up"]),
            notes="Auto-seeded clinical record",
            status=status,
            created_by_user_id=doctor.user_id,
            created_at=dt,
        )
        db.add(prescription)
        db.flush()

        chosen_drugs = random.sample(drugs, k=min(random.randint(1, 3), len(drugs)))
        for drug in chosen_drugs:
            qty_prescribed = random.randint(6, 30)
            db.add(
                PrescriptionItem(
                    prescription_id=prescription.prescription_id,
                    drug_id=drug.drug_id,
                    dosage=random.choice(["1-0-1", "1-1-1", "0-1-1", "1-0-0"]),
                    duration=random.choice(["5 days", "7 days", "10 days", "14 days"]),
                    quantity_prescribed=qty_prescribed,
                )
            )

            if status != "dispensed":
                continue

            batch = (
                db.query(DrugBatch)
                .filter(DrugBatch.drug_id == drug.drug_id)
                .order_by(DrugBatch.expiry_date.asc())
                .first()
            )
            if not batch:
                batch = _ensure_batch_for_drug(db, drug, random.choice(suppliers).supplier_id, dt)

            available = int(batch.quantity_available or 0)
            if available <= 0:
                batch.quantity_available = random.randint(120, 260)
                available = int(batch.quantity_available)

            qty_dispensed = min(qty_prescribed, max(1, random.randint(4, 24)), available)
            batch.quantity_available = max(0, available - qty_dispensed)

            db.add(
                DispensingRecord(
                    prescription_id=prescription.prescription_id,
                    patient_id=patient.patient_id,
                    batch_id=batch.batch_id,
                    quantity_dispensed=qty_dispensed,
                    dispensed_by_user_id=random.choice(pharmacy_users).user_id,
                    dispensed_at=dt + timedelta(hours=random.randint(1, 6)),
                    notes="Auto-seeded dispensing record",
                )
            )

    db.commit()

    if (
        db.execute(text("SELECT COUNT(*) FROM prescriptions WHERE DATE(created_at)=DATE '2025-03-05'"))
        .scalar_one()
        == 0
    ):
        patient = random.choice(patients)
        doctor = random.choice(doctor_users)
        dt = datetime(2025, 3, 5, 11, 45, 0)
        prescription = Prescription(
            patient_id=patient.patient_id,
            doctor_name=doctor.full_name or doctor.username,
            diagnosis="Seasonal fever",
            notes="Auto-seeded closing date prescription",
            status="dispensed",
            created_by_user_id=doctor.user_id,
            created_at=dt,
        )
        db.add(prescription)
        db.flush()
        drug = random.choice(drugs)
        qty = random.randint(10, 24)
        db.add(
            PrescriptionItem(
                prescription_id=prescription.prescription_id,
                drug_id=drug.drug_id,
                dosage="1-0-1",
                duration="7 days",
                quantity_prescribed=qty,
            )
        )
        batch = _ensure_batch_for_drug(db, drug, random.choice(suppliers).supplier_id, dt)
        available = int(batch.quantity_available or 0)
        if available < qty:
            batch.quantity_available = qty + 80
            available = int(batch.quantity_available)
        batch.quantity_available = max(0, available - qty)
        db.add(
            DispensingRecord(
                prescription_id=prescription.prescription_id,
                patient_id=patient.patient_id,
                batch_id=batch.batch_id,
                quantity_dispensed=qty,
                dispensed_by_user_id=random.choice(pharmacy_users).user_id,
                dispensed_at=datetime(2025, 3, 5, 15, 10, 0),
                notes="Auto-seeded closing date dispensing",
            )
        )
        db.commit()

    if para_drug and para_batch:
        para_sales_count = db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM dispensing_records dr
                JOIN drug_batches db ON db.batch_id = dr.batch_id
                JOIN drugs d ON d.drug_id = db.drug_id
                WHERE d.drug_name = 'Paracetamol'
                  AND EXTRACT(YEAR FROM dr.dispensed_at) = 2024
                """
            )
        ).scalar_one()

        if para_sales_count < 12:
            for month in range(1, 13):
                dt = datetime(2024, month, 10, 11, 0, 0)
                patient = random.choice(patients)
                doctor = random.choice(doctor_users)
                dispensed_by = random.choice(pharmacy_users)
                qty = random.randint(8, 20)

                prescription = Prescription(
                    patient_id=patient.patient_id,
                    doctor_name=doctor.full_name or doctor.username,
                    diagnosis="Fever",
                    notes="Auto-seeded Paracetamol monthly sales",
                    status="dispensed",
                    created_by_user_id=doctor.user_id,
                    created_at=dt,
                )
                db.add(prescription)
                db.flush()

                db.add(
                    PrescriptionItem(
                        prescription_id=prescription.prescription_id,
                        drug_id=para_drug.drug_id,
                        dosage="1-0-1",
                        duration="5 days",
                        quantity_prescribed=qty,
                    )
                )

                available = int(para_batch.quantity_available or 0)
                if available < qty:
                    para_batch.quantity_available = qty + 500
                    available = int(para_batch.quantity_available)
                para_batch.quantity_available = max(0, available - qty)

                db.add(
                    DispensingRecord(
                        prescription_id=prescription.prescription_id,
                        patient_id=patient.patient_id,
                        batch_id=para_batch.batch_id,
                        quantity_dispensed=qty,
                        dispensed_by_user_id=dispensed_by.user_id,
                        dispensed_at=dt + timedelta(hours=2),
                        notes="Auto-seeded monthly paracetamol sale",
                    )
                )
            db.commit()

    actions = [
        "create_purchase_order",
        "receive_purchase_order",
        "create_prescription",
        "dispense_drug",
        "update_inventory",
    ]
    log_dates = _daterange_points(datetime(2024, 1, 2, 8, 0, 0), datetime(2025, 3, 5, 20, 0, 0), 3)
    existing_log_days = {
        row[0]
        for row in db.execute(
            text("SELECT DATE(timestamp) FROM audit_logs WHERE timestamp >= :start_dt AND timestamp <= :end_dt"),
            {"start_dt": start_dt, "end_dt": end_dt},
        ).fetchall()
    }
    for dt in log_dates:
        if dt.date() in existing_log_days:
            continue
        actor = random.choice(users)
        action = random.choice(actions)
        target_table = random.choice(["purchase_orders", "prescriptions", "dispensing_records", "drug_batches"])
        db.add(
            AuditLog(
                actor_user_id=actor.user_id,
                action=action,
                target_table=target_table,
                target_id=str(random.randint(1, 5000)),
                detail=json.dumps({"seeded": True, "action": action}),
                ip_address="127.0.0.1",
                timestamp=dt,
            )
        )
    db.commit()

    note_dates = _daterange_points(datetime(2024, 1, 5, 10, 30, 0), datetime(2025, 3, 5, 16, 30, 0), 6)
    note_dates.append(datetime(2025, 3, 5, 16, 30, 0))
    titles = [
        "Low stock warning",
        "Batch nearing expiry",
        "Daily dispensing summary",
        "Purchase order update",
    ]
    existing_note_days = {
        row[0]
        for row in db.execute(
            text("SELECT DATE(created_at) FROM notifications WHERE created_at >= :start_dt AND created_at <= :end_dt"),
            {"start_dt": start_dt, "end_dt": end_dt},
        ).fetchall()
    }
    for dt in note_dates:
        if dt.date() in existing_note_days:
            continue
        recipient = random.choice(users)
        title = random.choice(titles)
        db.add(
            Notification(
                recipient_user_id=recipient.user_id,
                title=title,
                message=f"Auto-seeded notification: {title.lower()}.",
                is_read=dt < datetime(2024, 11, 1, 0, 0, 0),
                created_at=dt,
            )
        )
    db.commit()


def sync_postgres_sequences(db: Session):
    sequence_targets = [
        ("roles", "id"),
        ("users", "user_id"),
        ("patients", "patient_id"),
        ("drugs", "drug_id"),
        ("drug_batches", "batch_id"),
        ("suppliers", "supplier_id"),
        ("purchase_orders", "po_id"),
        ("purchase_order_items", "item_id"),
        ("prescriptions", "prescription_id"),
        ("prescription_items", "item_id"),
        ("dispensing_records", "record_id"),
        ("audit_logs", "log_id"),
        ("notifications", "notification_id"),
    ]
    for table_name, column_name in sequence_targets:
        try:
            db.execute(
                text(
                    f"""
                    SELECT setval(
                        pg_get_serial_sequence('{table_name}', '{column_name}'),
                        COALESCE((SELECT MAX({column_name}) FROM {table_name}), 1),
                        (SELECT COUNT(*) > 0 FROM {table_name})
                    )
                    """
                )
            )
        except Exception:
            pass  # Table may not exist yet on first run before create_all
    db.commit()


def seed_all(db: Session):
    seed_mode = os.getenv("SEED_MODE", "sql_file").strip().lower()
    if seed_mode in {"sql_file", "hospital_sql"}:
        dataset_path = _resolve_hospital_sql_path()
        reset_before_load = os.getenv("HOSPITAL_SQL_RESET", "true").strip().lower() == "true"
        sync_legacy = os.getenv("SYNC_TO_LEGACY_TABLES", "true").strip().lower() == "true"

        if reset_before_load:
            _reset_hospital_sql_tables(db)
        _load_hospital_sql_dataset(db, dataset_path)
        if sync_legacy:
            _sync_legacy_app_tables_from_hospital_sql(db)
            sync_postgres_sequences(db)
        logger.info("Loaded hospital dataset from %s", dataset_path)
        return

    his_data = load_his_data()
    seed_roles(db, his_data)
    seed_users(db, his_data)
    seed_patients(db, his_data)
    source_to_drug_id = seed_drugs_and_batches(db, his_data)
    seed_suppliers(db, his_data)
    seed_drug_batches(db, his_data, source_to_drug_id)
    seed_operational_history(db)
    sync_postgres_sequences(db)


def _resolve_hospital_sql_path() -> str:
    configured_path = os.getenv("HOSPITAL_DATA_SQL_PATH", "").strip()
    candidates = []
    if configured_path:
        candidates.append(Path(configured_path))
    candidates.extend(
        [
            Path("/app/hospital_complete_v2.sql"),
            Path(__file__).resolve().parents[2] / "hospital_complete_v2.sql",
            Path(__file__).resolve().parents[3] / "hospital_complete_v2.sql",
        ]
    )
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return str(candidate)
    raise FileNotFoundError(
        "hospital_complete_v2.sql not found. Set HOSPITAL_DATA_SQL_PATH to the dataset location."
    )


def _reset_hospital_sql_tables(db: Session):
    for table_name in HOSPITAL_V2_TABLES:
        try:
            db.execute(text(f"TRUNCATE TABLE {table_name} RESTART IDENTITY CASCADE"))
        except Exception:
            db.rollback()
    db.commit()


def _load_hospital_sql_dataset(db: Session, sql_file_path: str):
    with open(sql_file_path, "r", encoding="utf-8") as fh:
        sql_text = fh.read()

    normalized_lines = []
    for line in sql_text.splitlines():
        stripped = line.strip().rstrip(";").upper()
        if stripped in {"BEGIN", "COMMIT"}:
            continue
        normalized_lines.append(line)
    executable_sql = "\n".join(normalized_lines)

    connection = db.connection().connection
    cursor = connection.cursor()
    try:
        cursor.execute(executable_sql)
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()


def _sync_legacy_app_tables_from_hospital_sql(db: Session):
    db.execute(text("TRUNCATE TABLE dispensing_records RESTART IDENTITY CASCADE"))
    db.execute(text("TRUNCATE TABLE prescription_items RESTART IDENTITY CASCADE"))
    db.execute(text("TRUNCATE TABLE prescriptions RESTART IDENTITY CASCADE"))
    db.execute(text("TRUNCATE TABLE purchase_order_items RESTART IDENTITY CASCADE"))
    db.execute(text("TRUNCATE TABLE purchase_orders RESTART IDENTITY CASCADE"))
    db.execute(text("TRUNCATE TABLE drug_batches RESTART IDENTITY CASCADE"))
    db.execute(text("TRUNCATE TABLE drugs RESTART IDENTITY CASCADE"))
    db.execute(text("TRUNCATE TABLE patients RESTART IDENTITY CASCADE"))
    db.execute(text("TRUNCATE TABLE suppliers RESTART IDENTITY CASCADE"))
    db.execute(text("TRUNCATE TABLE users RESTART IDENTITY CASCADE"))
    db.execute(text("TRUNCATE TABLE roles RESTART IDENTITY CASCADE"))

    db.execute(
        text(
            """
            INSERT INTO roles (id, name, display_name)
            SELECT
                r.role_id,
                CASE lower(r.role_name)
                    WHEN 'system admin' THEN 'system_admin'
                    WHEN 'chief medical officer' THEN 'chief_medical_officer'
                    WHEN 'pharmacy manager' THEN 'pharmacy_manager'
                    WHEN 'senior pharmacist' THEN 'senior_pharmacist'
                    WHEN 'staff pharmacist' THEN 'staff_pharmacist'
                    WHEN 'inventory clerk' THEN 'inventory_clerk'
                    ELSE regexp_replace(lower(r.role_name), '[^a-z0-9]+', '_', 'g')
                END,
                r.role_name
            FROM role r
            ORDER BY r.role_id
            """
        )
    )

    db.execute(
        text(
            """
            INSERT INTO users (
                user_id,
                username,
                password,
                role_id,
                department,
                is_active,
                failed_login_count,
                must_reset_password,
                created_at
            )
            SELECT
                u.user_id,
                u.username,
                u.password,
                u.role_id,
                COALESCE(d.name, 'Pharmacy') AS department,
                COALESCE(u.is_active, TRUE),
                0,
                FALSE,
                COALESCE(u.created_at, NOW())
            FROM "User" u
            LEFT JOIN department d ON d.department_id = u.department_id
            ORDER BY u.user_id
            """
        )
    )

    db.execute(
        text(
            """
            INSERT INTO suppliers (supplier_id, name, contact_person, phone, email, address, is_active, created_at)
            SELECT
                s.supplier_id,
                s.name,
                NULL,
                split_part(COALESCE(s.contact_details, ''), '/', 1),
                NULLIF(trim(split_part(COALESCE(s.contact_details, ''), '/', 2)), ''),
                s.contact_details,
                TRUE,
                NOW()
            FROM supplier s
            ORDER BY s.supplier_id
            """
        )
    )

    db.execute(
        text(
            """
            INSERT INTO patients (patient_id, name, address, gender, contact, dob, blood_group, created_by_user_id, created_at, is_archived)
            SELECT
                p.patient_id,
                trim(concat_ws(' ', p.first_name, p.last_name)) AS name,
                h.address,
                p.gender,
                p.contact_no,
                p.dob,
                p.blood_group,
                NULL,
                NOW(),
                FALSE
            FROM patient p
            LEFT JOIN hospital h ON h.hospital_id = p.hospital_id
            ORDER BY p.patient_id
            """
        )
    )

    db.execute(
        text(
            """
            INSERT INTO drugs (drug_id, drug_name, generic_name, formulation, strength, schedule_type, is_active, low_stock_threshold)
            SELECT
                d.drug_id,
                d.drug_name,
                d.generic_name,
                d.formulation,
                d.strength,
                d.schedule_type,
                TRUE,
                50
            FROM drug d
            ORDER BY d.drug_id
            """
        )
    )

    db.execute(
        text(
            """
            INSERT INTO drug_batches (batch_id, drug_id, batch_no, expiry_date, purchase_price, selling_price, quantity_available, is_expired, supplier_id)
            SELECT
                b.batch_id,
                b.drug_id,
                b.batch_no,
                b.expiry_date,
                b.purchase_price,
                b.selling_price,
                b.quantity_available,
                (b.expiry_date < CURRENT_DATE),
                NULL
            FROM drug_batch b
            ORDER BY b.batch_id
            """
        )
    )

    db.execute(
        text(
            """
            INSERT INTO purchase_orders (po_id, supplier_id, ordered_by_user_id, status, notes, created_at, received_at)
            SELECT
                po.po_id,
                po.supplier_id,
                NULL,
                COALESCE(po.status, 'pending'),
                NULL,
                COALESCE(po.order_date::timestamp, NOW()),
                NULL
            FROM purchase_order po
            ORDER BY po.po_id
            """
        )
    )

    db.execute(
        text(
            """
            INSERT INTO purchase_order_items (item_id, po_id, drug_id, quantity_ordered, quantity_received, unit_price)
            SELECT
                poi.po_item_id,
                poi.po_id,
                poi.drug_id,
                poi.quantity_ordered,
                0,
                poi.unit_cost
            FROM purchase_order_item poi
            ORDER BY poi.po_item_id
            """
        )
    )

    db.execute(
        text(
            """
            INSERT INTO prescriptions (prescription_id, patient_id, doctor_name, diagnosis, notes, status, created_by_user_id, created_at)
            SELECT
                p.prescription_id,
                e.patient_id,
                COALESCE(d.name, 'Unknown Doctor'),
                NULL,
                NULL,
                COALESCE(p.status, 'open'),
                NULL,
                COALESCE(p.prescription_date, NOW())
            FROM prescription p
            JOIN encounter e ON e.encounter_id = p.encounter_id
            LEFT JOIN doctor d ON d.doctor_id = p.doctor_id
            ORDER BY p.prescription_id
            """
        )
    )

    db.execute(
        text(
            """
            INSERT INTO prescription_items (item_id, prescription_id, drug_id, dosage, duration, quantity_prescribed)
            SELECT
                pd.prescription_item_id,
                pd.prescription_id,
                pd.drug_id,
                trim(concat_ws(' | ', pd.dosage, pd.frequency)),
                CASE
                    WHEN pd.duration_days IS NULL THEN NULL
                    ELSE concat(pd.duration_days::text, ' days')
                END,
                COALESCE(pd.quantity_prescribed, 1)
            FROM prescription_detail pd
            ORDER BY pd.prescription_item_id
            """
        )
    )

    db.execute(
        text(
            """
            INSERT INTO dispensing_records (
                record_id,
                prescription_id,
                patient_id,
                batch_id,
                quantity_dispensed,
                dispensed_by_user_id,
                dispensed_at,
                notes
            )
            SELECT
                di.dispense_item_id,
                d.prescription_id,
                e.patient_id,
                di.batch_id,
                COALESCE(di.quantity_dispensed, 0),
                d.pharmacist_id,
                COALESCE(d.dispense_date, NOW()),
                NULL
            FROM dispense_item di
            JOIN dispense d ON d.dispense_id = di.dispense_id
            JOIN prescription p ON p.prescription_id = d.prescription_id
            JOIN encounter e ON e.encounter_id = p.encounter_id
            ORDER BY di.dispense_item_id
            """
        )
    )

    db.commit()
