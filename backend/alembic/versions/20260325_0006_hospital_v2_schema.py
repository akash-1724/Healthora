"""Add hospital v2 operational schema tables

Revision ID: 20260325_0006
Revises: 20260310_0005
Create Date: 2026-03-25 12:00:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "20260325_0006"
down_revision: Union[str, Sequence[str], None] = "20260310_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS hospital (
            hospital_id SERIAL PRIMARY KEY,
            name VARCHAR(255),
            registration_no VARCHAR(100),
            address TEXT,
            contact_no VARCHAR(20)
        );

        CREATE TABLE IF NOT EXISTS department (
            department_id SERIAL PRIMARY KEY,
            hospital_id INT REFERENCES hospital(hospital_id),
            name VARCHAR(255),
            department_code VARCHAR(50)
        );

        CREATE TABLE IF NOT EXISTS role (
            role_id SERIAL PRIMARY KEY,
            role_name VARCHAR(100)
        );

        CREATE TABLE IF NOT EXISTS "User" (
            user_id SERIAL PRIMARY KEY,
            username VARCHAR(100),
            password VARCHAR(255),
            role_id INT REFERENCES role(role_id),
            department_id INT REFERENCES department(department_id),
            is_active BOOLEAN,
            created_at TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS patient (
            patient_id SERIAL PRIMARY KEY,
            hospital_id INT REFERENCES hospital(hospital_id),
            first_name VARCHAR(100),
            last_name VARCHAR(100),
            dob DATE,
            gender VARCHAR(10),
            blood_group VARCHAR(5),
            contact_no VARCHAR(20)
        );

        CREATE TABLE IF NOT EXISTS doctor (
            doctor_id SERIAL PRIMARY KEY,
            name VARCHAR(255),
            specialization VARCHAR(100),
            registration_no VARCHAR(100),
            department_id INT REFERENCES department(department_id)
        );

        CREATE TABLE IF NOT EXISTS encounter (
            encounter_id SERIAL PRIMARY KEY,
            patient_id INT REFERENCES patient(patient_id),
            doctor_id INT REFERENCES doctor(doctor_id),
            department_id INT REFERENCES department(department_id),
            encounter_type VARCHAR(50),
            admission_date TIMESTAMP,
            discharge_date TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS manufacturer (
            manufacturer_id SERIAL PRIMARY KEY,
            name VARCHAR(255),
            license_no VARCHAR(100),
            address TEXT
        );

        CREATE TABLE IF NOT EXISTS drug (
            drug_id SERIAL PRIMARY KEY,
            drug_name VARCHAR(255),
            generic_name VARCHAR(255),
            formulation VARCHAR(100),
            strength VARCHAR(50),
            schedule_type VARCHAR(50),
            manufacturer_id INT REFERENCES manufacturer(manufacturer_id)
        );

        CREATE TABLE IF NOT EXISTS drug_batch (
            batch_id SERIAL PRIMARY KEY,
            drug_id INT REFERENCES drug(drug_id),
            batch_no VARCHAR(100),
            expiry_date DATE,
            purchase_price DECIMAL(10, 2),
            selling_price DECIMAL(10, 2),
            quantity_available INT
        );

        CREATE TABLE IF NOT EXISTS pharmacy_store (
            store_id SERIAL PRIMARY KEY,
            hospital_id INT REFERENCES hospital(hospital_id),
            store_name VARCHAR(255)
        );

        CREATE TABLE IF NOT EXISTS store_inventory (
            store_inventory_id SERIAL PRIMARY KEY,
            store_id INT REFERENCES pharmacy_store(store_id),
            batch_id INT REFERENCES drug_batch(batch_id),
            quantity INT
        );

        CREATE TABLE IF NOT EXISTS supplier (
            supplier_id SERIAL PRIMARY KEY,
            name VARCHAR(255),
            license_no VARCHAR(100),
            contact_details TEXT
        );

        CREATE TABLE IF NOT EXISTS purchase_order (
            po_id SERIAL PRIMARY KEY,
            supplier_id INT REFERENCES supplier(supplier_id),
            order_date DATE,
            status VARCHAR(50)
        );

        CREATE TABLE IF NOT EXISTS purchase_order_item (
            po_item_id SERIAL PRIMARY KEY,
            po_id INT REFERENCES purchase_order(po_id),
            drug_id INT REFERENCES drug(drug_id),
            quantity_ordered INT,
            unit_cost DECIMAL(10, 2)
        );

        CREATE TABLE IF NOT EXISTS stock_transaction (
            transaction_id SERIAL PRIMARY KEY,
            batch_id INT REFERENCES drug_batch(batch_id),
            store_id INT REFERENCES pharmacy_store(store_id),
            transaction_type VARCHAR(50),
            quantity INT,
            transaction_date TIMESTAMP,
            user_id INT REFERENCES "User"(user_id)
        );

        CREATE TABLE IF NOT EXISTS prescription (
            prescription_id SERIAL PRIMARY KEY,
            encounter_id INT REFERENCES encounter(encounter_id),
            doctor_id INT REFERENCES doctor(doctor_id),
            prescription_date TIMESTAMP,
            status VARCHAR(50)
        );

        CREATE TABLE IF NOT EXISTS prescription_detail (
            prescription_item_id SERIAL PRIMARY KEY,
            prescription_id INT REFERENCES prescription(prescription_id),
            drug_id INT REFERENCES drug(drug_id),
            dosage VARCHAR(100),
            frequency VARCHAR(100),
            duration_days INT,
            quantity_prescribed INT
        );

        CREATE TABLE IF NOT EXISTS dispense (
            dispense_id SERIAL PRIMARY KEY,
            prescription_id INT REFERENCES prescription(prescription_id),
            pharmacist_id INT REFERENCES "User"(user_id),
            store_id INT REFERENCES pharmacy_store(store_id),
            dispense_date TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS dispense_item (
            dispense_item_id SERIAL PRIMARY KEY,
            dispense_id INT REFERENCES dispense(dispense_id),
            batch_id INT REFERENCES drug_batch(batch_id),
            quantity_dispensed INT
        );

        CREATE TABLE IF NOT EXISTS pharmacy_bill (
            bill_id SERIAL PRIMARY KEY,
            patient_id INT REFERENCES patient(patient_id),
            encounter_id INT REFERENCES encounter(encounter_id),
            total_amount DECIMAL(10, 2),
            payment_status VARCHAR(50),
            bill_date TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS pharmacy_bill_item (
            bill_item_id SERIAL PRIMARY KEY,
            bill_id INT REFERENCES pharmacy_bill(bill_id),
            drug_id INT REFERENCES drug(drug_id),
            quantity INT,
            unit_price DECIMAL(10, 2),
            total_price DECIMAL(10, 2)
        );

        CREATE TABLE IF NOT EXISTS controlled_drug_log (
            log_id SERIAL PRIMARY KEY,
            drug_id INT REFERENCES drug(drug_id),
            batch_id INT REFERENCES drug_batch(batch_id),
            patient_id INT REFERENCES patient(patient_id),
            doctor_id INT REFERENCES doctor(doctor_id),
            pharmacist_id INT REFERENCES "User"(user_id),
            quantity INT,
            date_time TIMESTAMP
        );
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS controlled_drug_log;
        DROP TABLE IF EXISTS pharmacy_bill_item;
        DROP TABLE IF EXISTS pharmacy_bill;
        DROP TABLE IF EXISTS dispense_item;
        DROP TABLE IF EXISTS dispense;
        DROP TABLE IF EXISTS prescription_detail;
        DROP TABLE IF EXISTS prescription;
        DROP TABLE IF EXISTS stock_transaction;
        DROP TABLE IF EXISTS purchase_order_item;
        DROP TABLE IF EXISTS purchase_order;
        DROP TABLE IF EXISTS supplier;
        DROP TABLE IF EXISTS store_inventory;
        DROP TABLE IF EXISTS pharmacy_store;
        DROP TABLE IF EXISTS drug_batch;
        DROP TABLE IF EXISTS drug;
        DROP TABLE IF EXISTS manufacturer;
        DROP TABLE IF EXISTS encounter;
        DROP TABLE IF EXISTS doctor;
        DROP TABLE IF EXISTS patient;
        DROP TABLE IF EXISTS "User";
        DROP TABLE IF EXISTS role;
        DROP TABLE IF EXISTS department;
        DROP TABLE IF EXISTS hospital;
        """
    )
