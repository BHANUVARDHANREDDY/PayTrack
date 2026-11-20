import uuid
from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=15, unique=True)
    budget = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.code})"


class UserProfile(models.Model):
    ROLE_CHOICES = (
        ("MANAGER", "Finance Manager"),
        ("EMPLOYEE", "Finance Employee"),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="EMPLOYEE")
    phone = models.CharField(max_length=20, blank=True)

    def is_manager(self):
        return self.role == "MANAGER"

    def is_employee(self):
        return self.role == "EMPLOYEE"

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - {self.get_role_display()}"


class Employee(models.Model):
    STATUS_CHOICES = (
        ("ACTIVE", "Active"),
        ("ON_LEAVE", "On Leave"),
        ("RESIGNED", "Resigned"),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="employee_profile")
    emp_code = models.CharField(max_length=20, unique=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name="employees")
    designation = models.CharField(max_length=100)
    joining_date = models.DateField(default=timezone.now)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="ACTIVE")
    attendance_percentage = models.PositiveSmallIntegerField(default=95)
    present_days = models.PositiveSmallIntegerField(default=13)
    leave_days = models.PositiveSmallIntegerField(default=1)
    absent_days = models.PositiveSmallIntegerField(default=1)

    # Banking & Tax Details
    bank_name = models.CharField(max_length=100, default="State Bank of India")
    account_number = models.CharField(max_length=30)
    ifsc_code = models.CharField(max_length=20, default="SBIN0001001")
    pan_number = models.CharField(max_length=20, blank=True)

    # Salary Structure (Monthly Base)
    basic_salary = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("50000.00"))
    hra = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("15000.00"), verbose_name="House Rent Allowance")
    medical_allowance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("3000.00"))
    conveyance_allowance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("2000.00"))

    # Monthly Deductions
    pf_deduction = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("3600.00"), verbose_name="Provident Fund (PF)")
    tax_deduction = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("4500.00"), verbose_name="Income Tax (TDS)")
    other_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        ordering = ["emp_code"]

    def __str__(self):
        return f"{self.emp_code} - {self.user.get_full_name() or self.user.username} ({self.designation})"

    @property
    def full_name(self):
        return self.user.get_full_name() or self.user.username

    @property
    def work_email(self):
        return self.user.email or f"{self.user.username}@example.com"

    @property
    def total_allowances(self):
        return (self.hra or Decimal("0")) + (self.medical_allowance or Decimal("0")) + (self.conveyance_allowance or Decimal("0"))

    @property
    def gross_salary(self):
        return (self.basic_salary or Decimal("0")) + self.total_allowances

    @property
    def total_deductions(self):
        return (self.pf_deduction or Decimal("0")) + (self.tax_deduction or Decimal("0")) + (self.other_deductions or Decimal("0"))

    @property
    def net_salary(self):
        net = self.gross_salary - self.total_deductions
        return max(net, Decimal("0.00"))

    def get_payment_for_month(self, month, year):
        return self.salary_payments.filter(month=month, year=year).first()

    def is_paid_for_month(self, month, year):
        return self.salary_payments.filter(month=month, year=year, status="PAID").exists()


class SalaryPayment(models.Model):
    MONTH_NAMES = {
        1: "January", 2: "February", 3: "March", 4: "April",
        5: "May", 6: "June", 7: "July", 8: "August",
        9: "September", 10: "October", 11: "November", 12: "December"
    }

    STATUS_CHOICES = (
        ("PAID", "Paid"),
        ("PENDING", "Pending"),
        ("FAILED", "Failed"),
    )

    PAYMENT_METHOD_CHOICES = (
        ("DIRECT_DEPOSIT", "Direct Bank Transfer"),
        ("NEFT_RTGS", "NEFT / RTGS"),
        ("CHEQUE", "Company Cheque"),
    )

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="salary_payments")
    month = models.PositiveSmallIntegerField()
    year = models.PositiveIntegerField()
    payment_date = models.DateField(default=timezone.now)

    # Financial snapshots at the time of payment
    basic_salary = models.DecimalField(max_digits=12, decimal_places=2)
    allowances = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    deductions = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    bonus = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    net_paid = models.DecimalField(max_digits=12, decimal_places=2)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PAID")
    payment_method = models.CharField(max_length=30, choices=PAYMENT_METHOD_CHOICES, default="DIRECT_DEPOSIT")
    transaction_id = models.CharField(max_length=64, unique=True)
    paid_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="authorized_payments")
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-year", "-month", "-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["employee", "month", "year"], name="unique_monthly_salary_per_employee")
        ]

    def __str__(self):
        return f"{self.employee.emp_code} - {self.get_month_name()} {self.year} (₹{self.net_paid})"

    def get_month_name(self):
        return self.MONTH_NAMES.get(self.month, str(self.month))

    @property
    def month_year_label(self):
        return f"{self.get_month_name()} {self.year}"

    @classmethod
    def generate_transaction_id(cls, emp_code, year, month):
        random_suffix = uuid.uuid4().hex[:6].upper()
        return f"FIN-TXN-{year}{str(month).zfill(2)}-{emp_code}-{random_suffix}"


class ReimbursementClaim(models.Model):
    CATEGORY_CHOICES = (
        ("TRAVEL", "Travel & Fuel"),
        ("OFFICE", "Office & Equipment"),
        ("MEALS", "Client Meetings & Meals"),
        ("HEALTH", "Medical Reimbursement"),
        ("OTHER", "Other Operational Expense"),
    )

    STATUS_CHOICES = (
        ("PENDING", "Pending Approval"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
    )

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="claims")
    title = models.CharField(max_length=150)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default="TRAVEL")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    claim_date = models.DateField(default=timezone.now)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    description = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_claims")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.employee.emp_code} - {self.title} (₹{self.amount}) [{self.status}]"
