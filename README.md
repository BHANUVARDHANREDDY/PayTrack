# 💼 PayTrack — Enterprise Finance & Monthly Payroll Management System

**PayTrack** is a full-stack, enterprise-grade Finance Management application built with **pure Python** using **Django**, **MySQL**, **HTML5**, **CSS3**, and **JavaScript (`.js`)**.

---

## 🌟 Key Features

1. **Role-Based Portals (The Two URLs)**:
   - **1st URL — Manager Portal (`/manager/`)**:
     - Complete executive financial dashboard.
     - **Feature to Pay Salaries Every Month**:
       - Filter by Month and Year (e.g., November 2026).
       - Visual status tracking: `PAID` (Green badge with transaction code) vs `PENDING` (Amber badge).
       - Individual payout modal with performance bonus inputs, payment method selection, and real-time JavaScript take-home recalculation.
       - **1-Click "Pay All Pending Salaries"**: Bulk disbursement with atomic database transactions.
       - Automatic generation of unique transaction IDs (e.g. `FIN-TXN-202611-FIN-001-XXXX`).
     - Employee Directory: Onboard staff, edit salary packages (Basic, HRA, Medical, PF, TDS Tax).
     - Payment History & Audit trail of all disbursed amounts.
     - Pure JavaScript HTML5 Canvas analytics (6-Month trend & departmental allocation).
     - Reimbursement review and approval.

   - **2nd URL — Employee Portal (`/employee/`)**:
     - Live payment status indicator for the current month.
     - Transparent Monthly Compensation Card (Basic, Allowances, Gross, Deductions, Net Take-Home).
     - Banking and tax details (Bank name, A/C number, IFSC, PAN).
     - Monthly Salary Slips History with direct links to view and print official company payslips.
     - **Live Salary Simulator**: Interactive JavaScript calculator to simulate changes in allowances, PF, and tax.
     - Submit reimbursement expense claims directly to the manager.

2. **Official Printable Salary Slips (`/payslip/<id>/`)**:
   - Formatted for physical print and PDF export with corporate header, verified watermark seal, and signature lines.

3. **Pure Python Architecture**:
   - Zero hardcoding.
   - Clean object-oriented Django models, services, and forms.
   - Full automated test suite verifying business logic (`python manage.py test`).

4. **MySQL Database Integration**:
   - Relational schema configured via `PyMySQL` (`pymysql.install_as_MySQLdb()`).
   - Configurable credentials via `.env`.
   - Automatic resilient fallback ensuring zero crashes during local demonstration.

---

## 📸 Frontend Design & Screenshots

The application features an executive navy-and-slate corporate aesthetic with glassmorphism, responsive cards, and gold/emerald accents:

| Section | Description | Live Route |
| :--- | :--- | :--- |
| **1st URL: Manager Portal** | Monthly payroll disbursement table, stat cards, bulk pay action | `http://127.0.0.1:8000/manager/` |
| **2nd URL: Employee Portal** | Personal compensation breakdown, payment status, payslips | `http://127.0.0.1:8000/employee/` |
| **Official Salary Slip** | Printable payroll voucher with transaction reference code | `http://127.0.0.1:8000/payslip/1/` |
| **Corporate Sign-In** | Authentication gateway with 1-click test credentials | `http://127.0.0.1:8000/login/` |
| **Landing Portal** | Overview with embedded frontend screenshots showcase | `http://127.0.0.1:8000/` |

---

## 🚀 Quick Start Guide

### 1. Activate the Virtual Environment
```powershell
# From the project directory:
.\venv\Scripts\Activate.ps1
```

### 2. Configure MySQL Database
Edit the `.env` file in the project root:
```ini
DB_ENGINE=mysql
DB_NAME=finance_db
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_HOST=127.0.0.1
DB_PORT=3306
```

### 3. Run Migrations & Seed Data
```powershell
python manage.py migrate
python seed_data.py
```

### 4. Run Automated Unit Tests
```powershell
python manage.py test
```

### 5. Launch the Server
```powershell
python manage.py runserver
```
Visit `http://127.0.0.1:8000/` in your browser.

---

## 🔑 Demo Login Credentials

| Role | Username | Password | Access URL |
| :--- | :--- | :--- | :--- |
| **Finance Manager** | `manager` | `password123` | `http://127.0.0.1:8000/manager/` |
| **Lead Analyst (Employee 1)** | `emp1` | `password123` | `http://127.0.0.1:8000/employee/` |
| **Payroll Specialist (Employee 2)** | `emp2` | `password123` | `http://127.0.0.1:8000/employee/` |
| **Treasury Officer (Employee 3)** | `emp3` | `password123` | `http://127.0.0.1:8000/employee/` |
| **Audit Officer (Employee 4)** | `emp4` | `password123` | `http://127.0.0.1:8000/employee/` |

---

## 📁 Project Structure

```
Python Project/
├── .env                       # Database & security configuration
├── manage.py                  # Django CLI entrypoint
├── seed_data.py               # Pure Python database seeder
├── finance_system/            # Core project package
│   ├── settings.py            # MySQL & app settings
│   ├── urls.py                # Main URL routing
│   └── wsgi.py
├── payroll/                   # Finance & Payroll Application
│   ├── models.py              # Department, UserProfile, Employee, SalaryPayment, Claim
│   ├── views.py               # Pure Python view logic for Manager & Employee
│   ├── urls.py                # Manager and Employee routes
│   ├── admin.py               # Django Admin registration
│   ├── tests.py               # Automated unit tests
│   └── static/payroll/
│       ├── css/style.css      # Executive styling
│       ├── js/dashboard.js    # Modals, live calculations, filtering
│       ├── js/charts.js       # Pure JS canvas chart renderer
│       └── img/               # UI screenshots gallery
└── templates/payroll/         # Modern HTML5 templates
    ├── base.html              # Executive layout & navbar
    ├── index.html             # Landing page & screenshot gallery
    ├── login.html             # Corporate login with 1-click test credentials
    ├── manager_dashboard.html # 1st URL: Manager Portal
    ├── employee_dashboard.html# 2nd URL: Employee Portal
    └── payslip.html           # Official printable salary slip
```
