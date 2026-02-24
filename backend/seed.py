import os
import random
import zipfile
from datetime import date, datetime, timedelta
from xml.etree import ElementTree as ET

from sqlalchemy import text
from sqlalchemy.orm import Session

from models import Drug, DrugBatch, Patient, Role, User

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
        wanted = {"Department", "Role", "User ", "Paitent", "Drug", "Drug_Batch"}
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

    if db.query(DrugBatch).count() == 0:
        batch_rows = his_data.get("Drug_Batch", [])[1:]
        if not batch_rows:
            batch_rows = [
                ["1", "1", "B2025-001", "46096", "1.25", "1.75", "850"],
                ["3", "2", "B2025-003", "46235", "6.5", "9.75", "380"],
                ["11", "6", "B2025-011", "46154", "1.8", "2.52", "780"],
                ["13", "7", "B2025-013", "46327", "350.00", "525.00", "210"],
            ]

        db.add_all(
            [
                DrugBatch(
                    batch_id=int(float(row[0])),
                    drug_id=int(float(row[1])),
                    batch_no=row[2],
                    expiry_date=excel_date_to_date(row[3]) or date.today(),
                    purchase_price=float(row[4]),
                    selling_price=float(row[5]),
                    quantity_available=int(float(row[6])),
                    is_expired=False,
                )
                for row in batch_rows
                if len(row) >= 7
            ]
        )
        db.commit()


def sync_postgres_sequences(db: Session):
    sequence_targets = [
        ("roles", "id"),
        ("users", "user_id"),
        ("patients", "patient_id"),
        ("drugs", "drug_id"),
        ("drug_batches", "batch_id"),
    ]
    for table_name, column_name in sequence_targets:
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
    db.commit()


def seed_all(db: Session):
    his_data = load_his_data()
    seed_roles(db, his_data)
    seed_users(db, his_data)
    seed_patients(db, his_data)
    seed_drugs_and_batches(db, his_data)
    sync_postgres_sequences(db)
