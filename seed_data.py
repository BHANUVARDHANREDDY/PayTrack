"""
Pure Python Database Seeder matching the exact UI/UX design specifications.
Seeds Manager and Employees (Anita Rao, Ravi Kumar, Sneha Reddy, Imran Khan, Priya Nair).
"""

import os
import django
from decimal import Decimal

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "finance_system.settings")
django.setup()

from django.contrib.auth.models import User
from django.utils import timezone
from payroll.models import Department, UserProfile, Employee, SalaryPayment, ReimbursementClaim


def seed():
    print("🌱 Seeding exact UI/UX matching data...")

    # 1. Departments
    dept_eng, _ = Department.objects.get_or_create(code="ENG", defaults={"name": "Engineering", "budget": Decimal("5000000.00")})
    dept_acc, _ = Department.objects.get_or_create(code="ACC", defaults={"name": "Accounts", "budget": Decimal("3500000.00")})
    dept_hr, _ = Department.objects.get_or_create(code="HR", defaults={"name": "HR", "budget": Decimal("2500000.00")})
    dept_sup, _ = Department.objects.get_or_create(code="SUP", defaults={"name": "Support", "budget": Decimal("2000000.00")})
    dept_sales, _ = Department.objects.get_or_create(code="SAL", defaults={"name": "Sales", "budget": Decimal("4000000.00")})

    # 2. Manager
    mgr_user, _ = User.objects.get_or_create(
        username="manager",
        defaults={
            "email": "manager@financeportal.com",
            "first_name": "Finance",
            "last_name": "Manager",
            "is_staff": True,
            "is_superuser": True
        }
    )
    mgr_user.set_password("password123")
    mgr_user.save()

    UserProfile.objects.update_or_create(user=mgr_user, defaults={"role": "MANAGER", "phone": "+91 9876543210"})
    print("✅ Manager created: username='manager', password='password123'")

    # 3. Exact Employees from the Design Mockup
    # Anita Rao (E-101), Ravi Kumar (E-102), Sneha Reddy (E-103), Imran Khan (E-104), Priya Nair (E-105)
    employees_spec = [
        {
            "username": "anita",
            "first_name": "Anita",
            "last_name": "Rao",
            "email": "anita.rao@example.com",
            "emp_code": "E-101",
            "department": dept_eng,
            "designation": "Python Developer",
            "joining_date": timezone.datetime(2023, 6, 12).date(),
            "attendance": 96,
            "present_days": 13,
            "leave_days": 1,
            "absent_days": 1,
            "basic_salary": Decimal("45000.00"),
            "hra": Decimal("15000.00"),
            "medical_allowance": Decimal("4000.00"),
            "conveyance_allowance": Decimal("2500.00"),
            "pf_deduction": Decimal("2500.00"),
            "tax_deduction": Decimal("2000.00"),
            # Gross: 66,500; Deductions: 4,500; Net: 62,000
        },
        {
            "username": "ravi",
            "first_name": "Ravi",
            "last_name": "Kumar",
            "email": "ravi.kumar@example.com",
            "emp_code": "E-102",
            "department": dept_acc,
            "designation": "Accounts Executive",
            "joining_date": timezone.datetime(2023, 1, 15).date(),
            "attendance": 92,
            "present_days": 12,
            "leave_days": 2,
            "absent_days": 1,
            "basic_salary": Decimal("35000.00"),
            "hra": Decimal("12000.00"),
            "medical_allowance": Decimal("3500.00"),
            "conveyance_allowance": Decimal("2000.00"),
            "pf_deduction": Decimal("2200.00"),
            "tax_deduction": Decimal("1800.00"),
            # Gross: 52,500; Deductions: 4,000; Net: 48,500
        },
        {
            "username": "sneha",
            "first_name": "Sneha",
            "last_name": "Reddy",
            "email": "sneha.reddy@example.com",
            "emp_code": "E-103",
            "department": dept_hr,
            "designation": "HR Specialist",
            "joining_date": timezone.datetime(2023, 3, 1).date(),
            "attendance": 100,
            "present_days": 15,
            "leave_days": 0,
            "absent_days": 0,
            "basic_salary": Decimal("40000.00"),
            "hra": Decimal("13000.00"),
            "medical_allowance": Decimal("3500.00"),
            "conveyance_allowance": Decimal("2500.00"),
            "pf_deduction": Decimal("2200.00"),
            "tax_deduction": Decimal("1800.00"),
            # Gross: 59,000; Deductions: 4,000; Net: 55,000
        },
        {
            "username": "imran",
            "first_name": "Imran",
            "last_name": "Khan",
            "email": "imran.khan@example.com",
            "emp_code": "E-104",
            "department": dept_sup,
            "designation": "Support Engineer",
            "joining_date": timezone.datetime(2023, 9, 10).date(),
            "attendance": 85,
            "present_days": 11,
            "leave_days": 2,
            "absent_days": 2,
            "basic_salary": Decimal("25000.00"),
            "hra": Decimal("9000.00"),
            "medical_allowance": Decimal("3500.00"),
            "conveyance_allowance": Decimal("2000.00"),
            "pf_deduction": Decimal("1800.00"),
            "tax_deduction": Decimal("1500.00"),
            # Gross: 39,500; Deductions: 3,300; Net: 36,200
        },
        {
            "username": "priya",
            "first_name": "Priya",
            "last_name": "Nair",
            "email": "priya.nair@example.com",
            "emp_code": "E-105",
            "department": dept_sales,
            "designation": "Sales Lead",
            "joining_date": timezone.datetime(2023, 5, 5).date(),
            "attendance": 90,
            "present_days": 12,
            "leave_days": 1,
            "absent_days": 2,
            "basic_salary": Decimal("30000.00"),
            "hra": Decimal("10000.00"),
            "medical_allowance": Decimal("3300.00"),
            "conveyance_allowance": Decimal("2000.00"),
            "pf_deduction": Decimal("2000.00"),
            "tax_deduction": Decimal("1500.00"),
            # Gross: 45,300; Deductions: 3,500; Net: 41,800
        },
    ]

    anita_emp = None
    for item in employees_spec:
        user, _ = User.objects.get_or_create(
            username=item["username"],
            defaults={
                "email": item["email"],
                "first_name": item["first_name"],
                "last_name": item["last_name"]
            }
        )
        user.set_password("password123")
        user.email = item["email"]
        user.save()

        UserProfile.objects.update_or_create(user=user, defaults={"role": "EMPLOYEE", "phone": "+91 9988776655"})

        emp, _ = Employee.objects.update_or_create(
            emp_code=item["emp_code"],
            defaults={
                "user": user,
                "department": item["department"],
                "designation": item["designation"],
                "joining_date": item["joining_date"],
                "attendance_percentage": item["attendance"],
                "present_days": item["present_days"],
                "leave_days": item["leave_days"],
                "absent_days": item["absent_days"],
                "basic_salary": item["basic_salary"],
                "hra": item["hra"],
                "medical_allowance": item["medical_allowance"],
                "conveyance_allowance": item["conveyance_allowance"],
                "pf_deduction": item["pf_deduction"],
                "tax_deduction": item["tax_deduction"],
                "bank_name": "HDFC Bank Ltd.",
                "account_number": f"501004{item['emp_code'].replace('-', '')}92",
                "ifsc_code": "HDFC0001002",
                "pan_number": f"ABCDE{item['emp_code'].replace('-', '')}K"
            }
        )
        if item["emp_code"] == "E-101":
            anita_emp = emp
        print(f"✅ Employee {emp.full_name} ({emp.emp_code}): Net Salary ₹{emp.net_salary:,.0f}")

    # 4. Also keep backward compatibility aliases for 'emp1' so any previous login tests work
    emp1_user, _ = User.objects.get_or_create(username="emp1", defaults={"first_name": "Anita", "last_name": "Rao", "email": "anita.rao@example.com"})
    emp1_user.set_password("password123")
    emp1_user.save()

    # 5. Seed exact payslips for Anita Rao as shown in "Employee dashboard.png":
    # October 2026: Gross ₹66,500, Deductions ₹4,500, Net pay ₹62,000, Status Paid
    # September 2026: Gross ₹66,500, Deductions ₹4,500, Net pay ₹62,000, Status Paid
    # August 2026: Gross ₹66,500, Deductions ₹4,500, Net pay ₹62,000, Status Paid
    past_payslips = [
        {"month": 10, "year": 2026, "day": 31},
        {"month": 9, "year": 2026, "day": 30},
        {"month": 8, "year": 2026, "day": 31},
    ]

    for slip in past_payslips:
        txn_id = f"PAY-{slip['year']}{str(slip['month']).zfill(2)}-E101"
        SalaryPayment.objects.update_or_create(
            employee=anita_emp,
            month=slip["month"],
            year=slip["year"],
            defaults={
                "payment_date": timezone.datetime(slip["year"], slip["month"], slip["day"]).date(),
                "basic_salary": anita_emp.basic_salary,
                "allowances": anita_emp.total_allowances,
                "deductions": anita_emp.total_deductions,
                "bonus": Decimal("0.00"),
                "net_paid": anita_emp.net_salary,
                "status": "PAID",
                "payment_method": "DIRECT_DEPOSIT",
                "transaction_id": txn_id,
                "paid_by": mgr_user,
                "remarks": f"Monthly salary disbursement for {SalaryPayment.MONTH_NAMES[slip['month']]} {slip['year']}"
            }
        )

    print("✅ Seeded exact past payslips for Anita Rao (August, September, October 2026)")
    print("🎉 All UI/UX matched data successfully populated!")


if __name__ == "__main__":
    seed()
