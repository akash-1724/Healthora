import os
import random
import zipfile
import json
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


def seed_drugs_and_batches(db: Session, his_data: dict[str, list[list[str]]]):
    if db.query(Drug).count() == 0:
        drug_rows = his_data.get("Drug", [])[1:]
        if not drug_rows:
            drug_rows = [
                ["1", "Aspirin Ecosprin", "Acetylsalicylic Acid", "Tablet", "75mg", "OTC", "1"],
                ["2", "Atorva-20", "Atorvastatin", "Tablet", "20mg", "Schedule H", "3"],
                ["6", "Dolo 650", "Paracetamol", "Tablet", "650mg", "OTC", "1"],
                ["7", "Actrapid", "Insulin (Human)", "Injection", "100 IU/ml", "Schedule H", "6"],
            ]

        db.add_all(
            [
                Drug(
                    drug_id=int(float(row[0])),
                    drug_name=row[1],
                    generic_name=row[2],
                    formulation=row[3],
                    strength=row[4],
                    schedule_type=row[5],
                    is_active=True,
                    low_stock_threshold=50,
                )
                for row in drug_rows
                if len(row) >= 6
            ]
        )
        db.commit()

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
        db.commit()


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

    if db.query(DrugBatch).count() == 0:
        batch_rows = his_data.get("Drug_Batch", [])[1:]
        if not batch_rows:
            batch_rows = [
                ["1", "1", "B2025-001", "46096", "1.25", "1.75", "850"],
                ["3", "2", "B2025-003", "46235", "6.5", "9.75", "380"],
                ["11", "6", "B2025-011", "46154", "1.8", "2.52", "780"],
                ["13", "7", "B2025-013", "46327", "350.00", "525.00", "210"],
            ]

        supplier_ids = [s.supplier_id for s in db.query(Supplier).order_by(Supplier.supplier_id.asc()).all()]
        prepared_batches = []
        for idx, row in enumerate(batch_rows):
            if len(row) < 7:
                continue
            prepared_batches.append(
                DrugBatch(
                    batch_id=int(float(row[0])),
                    drug_id=int(float(row[1])),
                    batch_no=row[2],
                    expiry_date=excel_date_to_date(row[3]) or date.today(),
                    purchase_price=float(row[4]),
                    selling_price=float(row[5]),
                    quantity_available=int(float(row[6])),
                    supplier_id=supplier_ids[idx % len(supplier_ids)] if supplier_ids else None,
                    is_expired=False,
                )
            )

        db.add_all(prepared_batches)
        db.commit()

    supplier_ids = [s.supplier_id for s in db.query(Supplier).order_by(Supplier.supplier_id.asc()).all()]
    if supplier_ids:
        batches_without_supplier = db.query(DrugBatch).filter(DrugBatch.supplier_id.is_(None)).order_by(DrugBatch.batch_id.asc()).all()
        for idx, batch in enumerate(batches_without_supplier):
            batch.supplier_id = supplier_ids[idx % len(supplier_ids)]
        if batches_without_supplier:
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
    his_data = load_his_data()
    seed_roles(db, his_data)
    seed_users(db, his_data)
    seed_patients(db, his_data)
    seed_suppliers(db, his_data)
    seed_drugs_and_batches(db, his_data)
    seed_operational_history(db)
    sync_postgres_sequences(db)
