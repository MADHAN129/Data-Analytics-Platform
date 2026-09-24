import sys
import datetime
from app.database import SessionLocal
from app.models.connection import DatabaseConnection
from app.services.connection_service import get_connector, sync_schema

def seed_oracle(connector):
    print("--- Seeding Oracle Database ---")
    conn = connector.connect()
    cur = conn.cursor()

    # Drop existing tables if they exist
    tables_to_drop = ["COMPANY_FINANCIALS", "SALES_RECORDS", "PROJECTS", "EMPLOYEES", "DEPARTMENTS"]
    for t in tables_to_drop:
        try:
            cur.execute(f"DROP TABLE {t} CASCADE CONSTRAINTS")
            print(f"Dropped {t}")
        except Exception:
            pass

    # 1. DEPARTMENTS
    cur.execute("""
    CREATE TABLE DEPARTMENTS (
        department_id NUMBER PRIMARY KEY,
        department_name VARCHAR2(100) NOT NULL,
        manager_name VARCHAR2(100),
        location VARCHAR2(100),
        budget NUMBER(15, 2),
        headcount NUMBER
    )
    """)

    departments_data = [
        (1, 'Engineering', 'Alexander Wright', 'San Francisco, CA', 4500000.00, 48),
        (2, 'Product Management', 'Sophia Martinez', 'New York, NY', 1800000.00, 15),
        (3, 'Sales & Marketing', 'Marcus Vance', 'Chicago, IL', 3200000.00, 35),
        (4, 'Finance & Operations', 'Elena Rostova', 'Boston, MA', 1500000.00, 18),
        (5, 'Human Resources', 'David Kim', 'Austin, TX', 950000.00, 12),
        (6, 'Customer Success', 'Jessica Taylor', 'Denver, CO', 1200000.00, 22),
    ]

    for d in departments_data:
        cur.execute(
            "INSERT INTO DEPARTMENTS (department_id, department_name, manager_name, location, budget, headcount) VALUES (:1, :2, :3, :4, :5, :6)",
            d
        )

    # 2. EMPLOYEES
    cur.execute("""
    CREATE TABLE EMPLOYEES (
        employee_id NUMBER PRIMARY KEY,
        first_name VARCHAR2(50) NOT NULL,
        last_name VARCHAR2(50) NOT NULL,
        email VARCHAR2(100) UNIQUE,
        job_title VARCHAR2(100),
        department_id NUMBER REFERENCES DEPARTMENTS(department_id),
        salary NUMBER(12, 2),
        hire_date DATE,
        performance_score NUMBER(3, 2),
        city VARCHAR2(50)
    )
    """)

    employees_data = [
        (101, 'Liam', 'Chen', 'liam.chen@company.com', 'Senior Software Engineer', 1, 145000.00, datetime.date(2021, 3, 15), 4.8, 'San Francisco'),
        (102, 'Emma', 'Watson', 'emma.watson@company.com', 'Lead DevOps Engineer', 1, 155000.00, datetime.date(2020, 6, 1), 4.9, 'San Francisco'),
        (103, 'Noah', 'Patel', 'noah.patel@company.com', 'Data Scientist', 1, 138000.00, datetime.date(2022, 1, 10), 4.5, 'San Francisco'),
        (104, 'Olivia', 'Davis', 'olivia.davis@company.com', 'Frontend Developer', 1, 120000.00, datetime.date(2022, 8, 22), 4.6, 'Austin'),
        (105, 'Lucas', 'Mendoza', 'lucas.mendoza@company.com', 'Backend Architect', 1, 168000.00, datetime.date(2019, 11, 4), 4.9, 'San Francisco'),
        (106, 'Ava', 'Johnson', 'ava.johnson@company.com', 'Principal Product Manager', 2, 160000.00, datetime.date(2020, 2, 18), 4.7, 'New York'),
        (107, 'Ethan', 'Brown', 'ethan.brown@company.com', 'Technical Product Manager', 2, 132000.00, datetime.date(2021, 9, 5), 4.4, 'New York'),
        (108, 'Mia', 'Wilson', 'mia.wilson@company.com', 'UI/UX Product Designer', 2, 115000.00, datetime.date(2023, 2, 1), 4.6, 'New York'),
        (109, 'James', 'Miller', 'james.miller@company.com', 'Enterprise Account Executive', 3, 125000.00, datetime.date(2020, 8, 14), 4.8, 'Chicago'),
        (110, 'Charlotte', 'Taylor', 'charlotte.taylor@company.com', 'VP Global Sales', 3, 210000.00, datetime.date(2018, 5, 20), 4.9, 'Chicago'),
        (111, 'Benjamin', 'Anderson', 'benjamin.a@company.com', 'Marketing Campaign Lead', 3, 105000.00, datetime.date(2022, 4, 11), 4.3, 'Chicago'),
        (112, 'Amelia', 'Thomas', 'amelia.thomas@company.com', 'Senior Financial Analyst', 4, 118000.00, datetime.date(2021, 1, 25), 4.7, 'Boston'),
        (113, 'Henry', 'Jackson', 'henry.jackson@company.com', 'Operations Controller', 4, 142000.00, datetime.date(2019, 7, 30), 4.6, 'Boston'),
        (114, 'Harper', 'White', 'harper.white@company.com', 'People Operations Director', 5, 135000.00, datetime.date(2020, 10, 12), 4.8, 'Austin'),
        (115, 'Evelyn', 'Harris', 'evelyn.harris@company.com', 'Technical Recruiter', 5, 92000.00, datetime.date(2023, 5, 1), 4.2, 'Austin'),
        (116, 'Daniel', 'Martin', 'daniel.martin@company.com', 'Customer Success Director', 6, 130000.00, datetime.date(2021, 6, 18), 4.7, 'Denver'),
        (117, 'Abigail', 'Clark', 'abigail.clark@company.com', 'Enterprise Support Specialist', 6, 88000.00, datetime.date(2022, 11, 7), 4.5, 'Denver'),
    ]

    for e in employees_data:
        cur.execute(
            "INSERT INTO EMPLOYEES (employee_id, first_name, last_name, email, job_title, department_id, salary, hire_date, performance_score, city) VALUES (:1, :2, :3, :4, :5, :6, :7, :8, :9, :10)",
            e
        )

    # 3. PROJECTS
    cur.execute("""
    CREATE TABLE PROJECTS (
        project_id NUMBER PRIMARY KEY,
        project_name VARCHAR2(100) NOT NULL,
        department_id NUMBER REFERENCES DEPARTMENTS(department_id),
        budget NUMBER(15, 2),
        spent NUMBER(15, 2),
        status VARCHAR2(50),
        start_date DATE,
        end_date DATE
    )
    """)

    projects_data = [
        (201, 'AI Analytics Core Engine', 1, 850000.00, 620000.00, 'In Progress', datetime.date(2025, 1, 15), datetime.date(2025, 12, 31)),
        (202, 'NextGen Cloud Migration', 1, 1200000.00, 1150000.00, 'Completed', datetime.date(2024, 3, 1), datetime.date(2025, 2, 28)),
        (203, 'Mobile Dashboard App v2', 2, 450000.00, 310000.00, 'In Progress', datetime.date(2025, 4, 1), datetime.date(2025, 10, 31)),
        (204, 'Global Enterprise CRM Rollout', 3, 600000.00, 580000.00, 'Completed', datetime.date(2024, 6, 15), datetime.date(2025, 1, 15)),
        (205, 'Automated Billing & ERP Sync', 4, 350000.00, 210000.00, 'In Progress', datetime.date(2025, 2, 1), datetime.date(2025, 8, 30)),
        (206, 'Talent Acquisition & Portal', 5, 180000.00, 175000.00, 'Completed', datetime.date(2024, 9, 1), datetime.date(2025, 3, 31)),
    ]

    for p in projects_data:
        cur.execute(
            "INSERT INTO PROJECTS (project_id, project_name, department_id, budget, spent, status, start_date, end_date) VALUES (:1, :2, :3, :4, :5, :6, :7, :8)",
            p
        )

    # 4. SALES_RECORDS
    cur.execute("""
    CREATE TABLE SALES_RECORDS (
        sale_id NUMBER PRIMARY KEY,
        client_name VARCHAR2(100) NOT NULL,
        product_name VARCHAR2(100),
        category VARCHAR2(50),
        region VARCHAR2(50),
        units_sold NUMBER,
        unit_price NUMBER(10, 2),
        total_revenue NUMBER(15, 2),
        sale_date DATE,
        sales_rep_id NUMBER REFERENCES EMPLOYEES(employee_id)
    )
    """)

    sales_data = [
        (3001, 'Acme Global Corp', 'Enterprise Analytics License', 'Software', 'North America', 10, 25000.00, 250000.00, datetime.date(2025, 1, 10), 109),
        (3002, 'Starlight Financial', 'Cloud AI Data Platform', 'Cloud Services', 'North America', 5, 45000.00, 225000.00, datetime.date(2025, 1, 24), 110),
        (3003, 'Hyperion Retail Group', 'Real-Time Insights Dashboard', 'Software', 'Europe', 8, 18000.00, 144000.00, datetime.date(2025, 2, 5), 109),
        (3004, 'Apex Health Technologies', 'Enterprise Security & Compliance', 'Security', 'North America', 12, 15000.00, 180000.00, datetime.date(2025, 2, 18), 110),
        (3005, 'Nordic Logistics AB', 'Fleet Analytics Module', 'Software', 'Europe', 15, 12000.00, 180000.00, datetime.date(2025, 3, 2), 109),
        (3006, 'Pacific Telecom', 'High-Volume Stream Engine', 'Cloud Services', 'Asia-Pacific', 4, 60000.00, 240000.00, datetime.date(2025, 3, 19), 110),
        (3007, 'Vertex Media Group', 'Audience Analytics Suite', 'Software', 'North America', 20, 9500.00, 190000.00, datetime.date(2025, 4, 4), 109),
        (3008, 'Quantum BioLabs', 'Cloud AI Data Platform', 'Cloud Services', 'North America', 6, 45000.00, 270000.00, datetime.date(2025, 4, 22), 110),
        (3009, 'Atlas Industrial Systems', 'IoT Edge Analytics', 'Hardware/Software', 'Europe', 25, 8000.00, 200000.00, datetime.date(2025, 5, 11), 109),
        (3010, 'Zenith Capital Management', 'Predictive Trading Analytics', 'Software', 'North America', 3, 75000.00, 225000.00, datetime.date(2025, 5, 29), 110),
    ]

    for s in sales_data:
        cur.execute(
            "INSERT INTO SALES_RECORDS (sale_id, client_name, product_name, category, region, units_sold, unit_price, total_revenue, sale_date, sales_rep_id) VALUES (:1, :2, :3, :4, :5, :6, :7, :8, :9, :10)",
            s
        )

    # 5. COMPANY_FINANCIALS
    cur.execute("""
    CREATE TABLE COMPANY_FINANCIALS (
        financial_id NUMBER PRIMARY KEY,
        fiscal_year NUMBER,
        quarter VARCHAR2(10),
        revenue NUMBER(15, 2),
        operating_expenses NUMBER(15, 2),
        net_profit NUMBER(15, 2),
        profit_margin_pct NUMBER(5, 2)
    )
    """)

    financials_data = [
        (401, 2024, 'Q1', 4200000.00, 3100000.00, 1100000.00, 26.19),
        (402, 2024, 'Q2', 4800000.00, 3350000.00, 1450000.00, 30.21),
        (403, 2024, 'Q3', 5300000.00, 3600000.00, 1700000.00, 32.08),
        (404, 2024, 'Q4', 6100000.00, 3950000.00, 2150000.00, 35.25),
        (405, 2025, 'Q1', 5800000.00, 3800000.00, 2000000.00, 34.48),
        (406, 2025, 'Q2', 6500000.00, 4100000.00, 2400000.00, 36.92),
    ]

    for f in financials_data:
        cur.execute(
            "INSERT INTO COMPANY_FINANCIALS (financial_id, fiscal_year, quarter, revenue, operating_expenses, net_profit, profit_margin_pct) VALUES (:1, :2, :3, :4, :5, :6, :7)",
            f
        )

    conn.commit()
    cur.close()
    connector.close()
    print("Oracle Company Data seeded successfully!")

def seed_postgres(connector):
    print("--- Seeding PostgreSQL Database ---")
    conn = connector.connect()
    cur = conn.cursor()

    cur.execute("DROP TABLE IF EXISTS company_financials CASCADE;")
    cur.execute("DROP TABLE IF EXISTS sales_records CASCADE;")
    cur.execute("DROP TABLE IF EXISTS projects CASCADE;")
    cur.execute("DROP TABLE IF EXISTS employees CASCADE;")
    cur.execute("DROP TABLE IF EXISTS departments CASCADE;")

    # 1. departments
    cur.execute("""
    CREATE TABLE departments (
        department_id SERIAL PRIMARY KEY,
        department_name VARCHAR(100) NOT NULL,
        manager_name VARCHAR(100),
        location VARCHAR(100),
        budget NUMERIC(15, 2),
        headcount INT
    );
    """)

    departments_data = [
        (1, 'Engineering', 'Alexander Wright', 'San Francisco, CA', 4500000.00, 48),
        (2, 'Product Management', 'Sophia Martinez', 'New York, NY', 1800000.00, 15),
        (3, 'Sales & Marketing', 'Marcus Vance', 'Chicago, IL', 3200000.00, 35),
        (4, 'Finance & Operations', 'Elena Rostova', 'Boston, MA', 1500000.00, 18),
        (5, 'Human Resources', 'David Kim', 'Austin, TX', 950000.00, 12),
        (6, 'Customer Success', 'Jessica Taylor', 'Denver, CO', 1200000.00, 22),
    ]
    cur.executemany(
        "INSERT INTO departments (department_id, department_name, manager_name, location, budget, headcount) VALUES (%s, %s, %s, %s, %s, %s);",
        departments_data
    )

    # 2. employees
    cur.execute("""
    CREATE TABLE employees (
        employee_id INT PRIMARY KEY,
        first_name VARCHAR(50) NOT NULL,
        last_name VARCHAR(50) NOT NULL,
        email VARCHAR(100) UNIQUE,
        job_title VARCHAR(100),
        department_id INT REFERENCES departments(department_id),
        salary NUMERIC(12, 2),
        hire_date DATE,
        performance_score NUMERIC(3, 2),
        city VARCHAR(50)
    );
    """)

    employees_data = [
        (101, 'Liam', 'Chen', 'liam.chen@company.com', 'Senior Software Engineer', 1, 145000.00, datetime.date(2021, 3, 15), 4.8, 'San Francisco'),
        (102, 'Emma', 'Watson', 'emma.watson@company.com', 'Lead DevOps Engineer', 1, 155000.00, datetime.date(2020, 6, 1), 4.9, 'San Francisco'),
        (103, 'Noah', 'Patel', 'noah.patel@company.com', 'Data Scientist', 1, 138000.00, datetime.date(2022, 1, 10), 4.5, 'San Francisco'),
        (104, 'Olivia', 'Davis', 'olivia.davis@company.com', 'Frontend Developer', 1, 120000.00, datetime.date(2022, 8, 22), 4.6, 'Austin'),
        (105, 'Lucas', 'Mendoza', 'lucas.mendoza@company.com', 'Backend Architect', 1, 168000.00, datetime.date(2019, 11, 4), 4.9, 'San Francisco'),
        (106, 'Ava', 'Johnson', 'ava.johnson@company.com', 'Principal Product Manager', 2, 160000.00, datetime.date(2020, 2, 18), 4.7, 'New York'),
        (107, 'Ethan', 'Brown', 'ethan.brown@company.com', 'Technical Product Manager', 2, 132000.00, datetime.date(2021, 9, 5), 4.4, 'New York'),
        (108, 'Mia', 'Wilson', 'mia.wilson@company.com', 'UI/UX Product Designer', 2, 115000.00, datetime.date(2023, 2, 1), 4.6, 'New York'),
        (109, 'James', 'Miller', 'james.miller@company.com', 'Enterprise Account Executive', 3, 125000.00, datetime.date(2020, 8, 14), 4.8, 'Chicago'),
        (110, 'Charlotte', 'Taylor', 'charlotte.taylor@company.com', 'VP Global Sales', 3, 210000.00, datetime.date(2018, 5, 20), 4.9, 'Chicago'),
        (111, 'Benjamin', 'Anderson', 'benjamin.a@company.com', 'Marketing Campaign Lead', 3, 105000.00, datetime.date(2022, 4, 11), 4.3, 'Chicago'),
        (112, 'Amelia', 'Thomas', 'amelia.thomas@company.com', 'Senior Financial Analyst', 4, 118000.00, datetime.date(2021, 1, 25), 4.7, 'Boston'),
        (113, 'Henry', 'Jackson', 'henry.jackson@company.com', 'Operations Controller', 4, 142000.00, datetime.date(2019, 7, 30), 4.6, 'Boston'),
        (114, 'Harper', 'White', 'harper.white@company.com', 'People Operations Director', 5, 135000.00, datetime.date(2020, 10, 12), 4.8, 'Austin'),
        (115, 'Evelyn', 'Harris', 'evelyn.harris@company.com', 'Technical Recruiter', 5, 92000.00, datetime.date(2023, 5, 1), 4.2, 'Austin'),
        (116, 'Daniel', 'Martin', 'daniel.martin@company.com', 'Customer Success Director', 6, 130000.00, datetime.date(2021, 6, 18), 4.7, 'Denver'),
        (117, 'Abigail', 'Clark', 'abigail.clark@company.com', 'Enterprise Support Specialist', 6, 88000.00, datetime.date(2022, 11, 7), 4.5, 'Denver'),
    ]
    cur.executemany(
        "INSERT INTO employees (employee_id, first_name, last_name, email, job_title, department_id, salary, hire_date, performance_score, city) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);",
        employees_data
    )

    # 3. projects
    cur.execute("""
    CREATE TABLE projects (
        project_id INT PRIMARY KEY,
        project_name VARCHAR(100) NOT NULL,
        department_id INT REFERENCES departments(department_id),
        budget NUMERIC(15, 2),
        spent NUMERIC(15, 2),
        status VARCHAR(50),
        start_date DATE,
        end_date DATE
    );
    """)

    projects_data = [
        (201, 'AI Analytics Core Engine', 1, 850000.00, 620000.00, 'In Progress', datetime.date(2025, 1, 15), datetime.date(2025, 12, 31)),
        (202, 'NextGen Cloud Migration', 1, 1200000.00, 1150000.00, 'Completed', datetime.date(2024, 3, 1), datetime.date(2025, 2, 28)),
        (203, 'Mobile Dashboard App v2', 2, 450000.00, 310000.00, 'In Progress', datetime.date(2025, 4, 1), datetime.date(2025, 10, 31)),
        (204, 'Global Enterprise CRM Rollout', 3, 600000.00, 580000.00, 'Completed', datetime.date(2024, 6, 15), datetime.date(2025, 1, 15)),
        (205, 'Automated Billing & ERP Sync', 4, 350000.00, 210000.00, 'In Progress', datetime.date(2025, 2, 1), datetime.date(2025, 8, 30)),
        (206, 'Talent Acquisition & Portal', 5, 180000.00, 175000.00, 'Completed', datetime.date(2024, 9, 1), datetime.date(2025, 3, 31)),
    ]
    cur.executemany(
        "INSERT INTO projects (project_id, project_name, department_id, budget, spent, status, start_date, end_date) VALUES (%s, %s, %s, %s, %s, %s, %s, %s);",
        projects_data
    )

    # 4. sales_records
    cur.execute("""
    CREATE TABLE sales_records (
        sale_id INT PRIMARY KEY,
        client_name VARCHAR(100) NOT NULL,
        product_name VARCHAR(100),
        category VARCHAR(50),
        region VARCHAR(50),
        units_sold INT,
        unit_price NUMERIC(10, 2),
        total_revenue NUMERIC(15, 2),
        sale_date DATE,
        sales_rep_id INT REFERENCES employees(employee_id)
    );
    """)

    sales_data = [
        (3001, 'Acme Global Corp', 'Enterprise Analytics License', 'Software', 'North America', 10, 25000.00, 250000.00, datetime.date(2025, 1, 10), 109),
        (3002, 'Starlight Financial', 'Cloud AI Data Platform', 'Cloud Services', 'North America', 5, 45000.00, 225000.00, datetime.date(2025, 1, 24), 110),
        (3003, 'Hyperion Retail Group', 'Real-Time Insights Dashboard', 'Software', 'Europe', 8, 18000.00, 144000.00, datetime.date(2025, 2, 5), 109),
        (3004, 'Apex Health Technologies', 'Enterprise Security & Compliance', 'Security', 'North America', 12, 15000.00, 180000.00, datetime.date(2025, 2, 18), 110),
        (3005, 'Nordic Logistics AB', 'Fleet Analytics Module', 'Software', 'Europe', 15, 12000.00, 180000.00, datetime.date(2025, 3, 2), 109),
        (3006, 'Pacific Telecom', 'High-Volume Stream Engine', 'Cloud Services', 'Asia-Pacific', 4, 60000.00, 240000.00, datetime.date(2025, 3, 19), 110),
        (3007, 'Vertex Media Group', 'Audience Analytics Suite', 'Software', 'North America', 20, 9500.00, 190000.00, datetime.date(2025, 4, 4), 109),
        (3008, 'Quantum BioLabs', 'Cloud AI Data Platform', 'Cloud Services', 'North America', 6, 45000.00, 270000.00, datetime.date(2025, 4, 22), 110),
        (3009, 'Atlas Industrial Systems', 'IoT Edge Analytics', 'Hardware/Software', 'Europe', 25, 8000.00, 200000.00, datetime.date(2025, 5, 11), 109),
        (3010, 'Zenith Capital Management', 'Predictive Trading Analytics', 'Software', 'North America', 3, 75000.00, 225000.00, datetime.date(2025, 5, 29), 110),
    ]
    cur.executemany(
        "INSERT INTO sales_records (sale_id, client_name, product_name, category, region, units_sold, unit_price, total_revenue, sale_date, sales_rep_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);",
        sales_data
    )

    # 5. company_financials
    cur.execute("""
    CREATE TABLE company_financials (
        financial_id INT PRIMARY KEY,
        fiscal_year INT,
        quarter VARCHAR(10),
        revenue NUMERIC(15, 2),
        operating_expenses NUMERIC(15, 2),
        net_profit NUMERIC(15, 2),
        profit_margin_pct NUMERIC(5, 2)
    );
    """)

    financials_data = [
        (401, 2024, 'Q1', 4200000.00, 3100000.00, 1100000.00, 26.19),
        (402, 2024, 'Q2', 4800000.00, 3350000.00, 1450000.00, 30.21),
        (403, 2024, 'Q3', 5300000.00, 3600000.00, 1700000.00, 32.08),
        (404, 2024, 'Q4', 6100000.00, 3950000.00, 2150000.00, 35.25),
        (405, 2025, 'Q1', 5800000.00, 3800000.00, 2000000.00, 34.48),
        (406, 2025, 'Q2', 6500000.00, 4100000.00, 2400000.00, 36.92),
    ]
    cur.executemany(
        "INSERT INTO company_financials (financial_id, fiscal_year, quarter, revenue, operating_expenses, net_profit, profit_margin_pct) VALUES (%s, %s, %s, %s, %s, %s, %s);",
        financials_data
    )

    cur.close()
    connector.close()
    print("PostgreSQL Company Data seeded successfully!")

def main():
    db = SessionLocal()
    conns = db.query(DatabaseConnection).all()
    for c in conns:
        connector = get_connector(c)
        if c.connection_type == 'oracle':
            try:
                seed_oracle(connector)
                sync_schema(db, c.id)
                print(f"Schema synced for {c.name}")
            except Exception as e:
                print(f"Failed to seed Oracle: {e}")
        elif c.connection_type == 'postgresql':
            try:
                seed_postgres(connector)
                sync_schema(db, c.id)
                print(f"Schema synced for {c.name}")
            except Exception as e:
                print(f"Failed to seed Postgres: {e}")

if __name__ == '__main__':
    main()
