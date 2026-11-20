from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from payroll.models import Department, UserProfile, Employee, SalaryPayment


class FinancePayrollSystemTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Create department
        self.dept = Department.objects.create(
            name="Finance Operations",
            code="DEP-FIN",
            budget=Decimal("1000000.00")
        )

        # Create Manager
        self.manager_user = User.objects.create_user(
            username="manager_test",
            password="password123",
            first_name="Finance",
            last_name="Director"
        )
        UserProfile.objects.create(user=self.manager_user, role="MANAGER")

        # Create Employee
        self.emp_user = User.objects.create_user(
            username="emp_test",
            password="password123",
            first_name="John",
            last_name="Doe"
        )
        UserProfile.objects.create(user=self.emp_user, role="EMPLOYEE")
        self.employee = Employee.objects.create(
            user=self.emp_user,
            emp_code="FIN-TEST-01",
            department=self.dept,
            designation="Accountant",
            basic_salary=Decimal("50000.00"),
            hra=Decimal("15000.00"),
            medical_allowance=Decimal("2000.00"),
            conveyance_allowance=Decimal("1000.00"),
            pf_deduction=Decimal("3000.00"),
            tax_deduction=Decimal("4000.00"),
            bank_name="HDFC Bank",
            account_number="1234567890"
        )

    def test_manager_portal_access(self):
        """Test that the 1st URL (/manager/) loads for Manager user."""
        self.client.login(username="manager_test", password="password123")
        response = self.client.get(reverse("manager_portal"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Manager dashboard")
        self.assertContains(response, "FIN-TEST-01")

    def test_employee_cannot_access_manager_portal(self):
        """Test that Employee users are cleanly redirected without 'Access Denied' errors."""
        self.client.login(username="emp_test", password="password123")
        response = self.client.get(reverse("manager_portal"), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(reverse("manager_login"), response.redirect_chain[0][0])
        self.assertNotContains(response, "Access restricted")
        self.assertNotContains(response, "Access Denied")

    def test_unauthenticated_manager_portal_has_no_access_denied_error(self):
        """Opening manager portal when not logged in must cleanly show manager login without any Access error."""
        response = self.client.get(reverse("manager_portal"), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(reverse("manager_login"), response.redirect_chain[0][0])
        self.assertNotContains(response, "Access restricted")
        self.assertNotContains(response, "Access Denied")

    def test_manager_portal_login_flow(self):
        """Test signing into manager portal with valid manager credentials."""
        response = self.client.post(reverse("manager_login"), {
            "username": "manager_test",
            "password": "password123"
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Welcome back, Finance Manager")
        self.assertContains(response, "Manager dashboard")

    def test_employee_portal_access(self):
        """Test that the 2nd URL (/employee/) loads for Employee user."""
        self.client.login(username="emp_test", password="password123")
        response = self.client.get(reverse("employee_portal"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Welcome, John Doe")
        self.assertContains(response, "My details")
        self.assertContains(response, "Attendance, November 2026")
        self.assertContains(response, "My payslips")

    def test_manager_cannot_access_employee_portal(self):
        """Test that Manager users are strictly blocked from accessing the Employee Portal."""
        self.client.login(username="manager_test", password="password123")
        response = self.client.get(reverse("employee_portal"))
        # Should redirect to employee_login because manager has no employee profile
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("employee_login"), response.url)

    def test_process_monthly_salary_payment(self):
        """Test paying salary to an employee for a specific month and year."""
        self.client.login(username="manager_test", password="password123")

        # Execute salary payment for month=11, year=2026
        response = self.client.post(reverse("process_single_payment"), {
            "employee_id": self.employee.id,
            "month": 11,
            "year": 2026,
            "bonus": "2000.00",
            "payment_method": "DIRECT_DEPOSIT",
            "remarks": "Monthly test salary payout"
        })
        self.assertEqual(response.status_code, 302)

        # Verify payment in database
        payment = SalaryPayment.objects.filter(employee=self.employee, month=11, year=2026).first()
        self.assertIsNotNone(payment)
        self.assertEqual(payment.status, "PAID")
        expected_net = self.employee.net_salary + Decimal("2000.00")
        self.assertEqual(payment.net_paid, expected_net)
        self.assertTrue(payment.transaction_id.startswith("FIN-TXN-202611-"))

    def test_prevent_duplicate_monthly_payment(self):
        """Ensure an employee cannot be paid twice for the exact same month/year."""
        self.client.login(username="manager_test", password="password123")

        # 1st Payment
        self.client.post(reverse("process_single_payment"), {
            "employee_id": self.employee.id,
            "month": 11,
            "year": 2026,
            "bonus": "0.00",
        })
        # Attempt 2nd Payment for the same month/year
        self.client.post(reverse("process_single_payment"), {
            "employee_id": self.employee.id,
            "month": 11,
            "year": 2026,
            "bonus": "0.00",
        })
        # Should only have 1 payment record
        count = SalaryPayment.objects.filter(employee=self.employee, month=11, year=2026).count()
        self.assertEqual(count, 1)

    def test_printable_payslip_view(self):
        """Test that official salary slip generates correctly."""
        # Create payment
        payment = SalaryPayment.objects.create(
            employee=self.employee,
            month=10,
            year=2026,
            basic_salary=self.employee.basic_salary,
            allowances=self.employee.total_allowances,
            deductions=self.employee.total_deductions,
            bonus=Decimal("0.00"),
            net_paid=self.employee.net_salary,
            status="PAID",
            transaction_id="FIN-TXN-202610-TEST-001",
            paid_by=self.manager_user
        )

        self.client.login(username="emp_test", password="password123")
        response = self.client.get(reverse("view_payslip", args=[payment.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "MONTHLY SALARY SLIP")
        self.assertContains(response, payment.transaction_id)

    def test_employee_payroll_detail_api(self):
        """Test API endpoint returning full payroll record when clicking an employee."""
        self.client.login(username="manager_test", password="password123")
        url = reverse("employee_payroll_detail_api", args=[self.employee.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["emp_code"], "FIN-TEST-01")
        self.assertEqual(data["full_name"], "John Doe")
        self.assertIn("salary_structure", data)
        self.assertIn("payments", data)
        self.assertEqual(data["salary_structure"]["basic_salary"], 50000.0)

    def test_employee_profile_view(self):
        """Test that /employee/profile/ displays employee personal, job, and banking data."""
        self.client.login(username="emp_test", password="password123")
        response = self.client.get(reverse("employee_profile"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "My profile")
        self.assertContains(response, "FIN-TEST-01")
        self.assertContains(response, "Employment & Contact Details")
        self.assertContains(response, "Banking & Statutory Identifiers")

    def test_employee_attendance_view(self):
        """Test that /employee/attendance/ displays relevant attendance stats and calendar."""
        self.client.login(username="emp_test", password="password123")
        response = self.client.get(reverse("employee_attendance"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Attendance records")
        self.assertContains(response, "Daily Attendance Log")
        self.assertContains(response, "Leave Balances & Compliance")

    def test_employee_payslips_view(self):
        """Test that /employee/payslips/ displays the archive of salary statements."""
        SalaryPayment.objects.create(
            employee=self.employee,
            month=10,
            year=2026,
            basic_salary=self.employee.basic_salary,
            allowances=self.employee.total_allowances,
            deductions=self.employee.total_deductions,
            bonus=Decimal("0.00"),
            net_paid=self.employee.net_salary,
            status="PAID",
            transaction_id="FIN-TXN-202610-TEST-002",
            paid_by=self.manager_user
        )
        self.client.login(username="emp_test", password="password123")
        response = self.client.get(reverse("employee_payslips"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "My payslips")
        self.assertContains(response, "Official Remuneration Document Archive")
        self.assertContains(response, "FIN-TXN-202610-TEST-002")

    def test_official_payslip_document_letter_format(self):
        """Test that payslip renders as an official document letter with amount in words."""
        payment = SalaryPayment.objects.create(
            employee=self.employee,
            month=11,
            year=2026,
            basic_salary=self.employee.basic_salary,
            allowances=self.employee.total_allowances,
            deductions=self.employee.total_deductions,
            bonus=Decimal("0.00"),
            net_paid=Decimal("62000.00"),
            status="PAID",
            transaction_id="FIN-TXN-202611-TEST-003",
            paid_by=self.manager_user
        )
        self.client.login(username="emp_test", password="password123")
        response = self.client.get(reverse("view_payslip", args=[payment.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SALARY ADVICE LETTER")
        self.assertContains(response, "Indian Rupees Sixty Two Thousand Only")
        self.assertContains(response, "FinCorp Global Enterprises Pvt. Ltd.")
        self.assertContains(response, "OFFICIALLY AUDITED & CERTIFIED")

    def test_manager_employees_directory(self):
        """Test that /manager/employees/ displays visual employee roster with View buttons."""
        self.client.login(username="manager_test", password="password123")
        response = self.client.get(reverse("manager_employees"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Employee Directory")
        self.assertContains(response, "Visual Staff Directory")
        self.assertContains(response, "FIN-TEST-01")
        self.assertContains(response, "View")

    def test_manager_employee_detail_page(self):
        """Test that clicking View opens separate page with comprehensive profile, daily attendance, and detailed payroll."""
        self.client.login(username="manager_test", password="password123")
        response = self.client.get(reverse("manager_employee_detail_page", args=[self.employee.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "1. Comprehensive Employee Profile")
        self.assertContains(response, "2. Daily Attendance Records")
        self.assertContains(response, "3. Detailed Payroll & Compensation Information")
        self.assertContains(response, "FIN-TEST-01")
        self.assertContains(response, "John Doe")
        self.assertContains(response, "November 2026 Attendance Calendar")
        self.assertContains(response, "Daily Swipe & Presence Log")

    def test_manager_attendance_view(self):
        """Test that /manager/attendance/ displays organizational attendance standing."""
        self.client.login(username="manager_test", password="password123")
        response = self.client.get(reverse("manager_attendance"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Attendance")
        self.assertContains(response, "Staff Attendance Roster")

    def test_manager_payroll_view(self):
        """Test that /manager/payroll/ displays monthly salary disbursement management."""
        self.client.login(username="manager_test", password="password123")
        response = self.client.get(reverse("manager_payroll"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Payroll")
        self.assertContains(response, "Monthly salary payout")
