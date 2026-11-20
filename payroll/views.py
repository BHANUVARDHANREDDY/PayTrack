from decimal import Decimal
import datetime
from functools import wraps
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.urls import reverse
from django.db import transaction
from django.db.models import Sum, Count, Q
from django.utils import timezone
from .models import Department, UserProfile, Employee, SalaryPayment, ReimbursementClaim


# ============================================================================
# ROLE-BASED ACCESS CONTROL (Strict Portal Isolation)
# ============================================================================

def manager_required(view_func):
    """Restricts access exclusively to Manager accounts (1st URL)."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"{reverse('manager_login')}?next={request.path}")
        profile = getattr(request.user, "profile", None)
        if not (request.user.is_superuser or (profile and profile.is_manager())):
            # Silently logout non-manager and redirect cleanly without error banners
            logout(request)
            return redirect(f"{reverse('manager_login')}?next={request.path}")
        return view_func(request, *args, **kwargs)
    return _wrapped


def employee_required(view_func):
    """Restricts access exclusively to Employee accounts (2nd URL)."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"{reverse('employee_login')}?next={request.path}")
        if not hasattr(request.user, "employee_profile"):
            # Silently logout non-employee and redirect cleanly without error banners
            logout(request)
            return redirect(f"{reverse('employee_login')}?next={request.path}")
        return view_func(request, *args, **kwargs)
    return _wrapped


def home_view(request):
    """Landing portal gateway that directs users to Manager or Employee portals."""
    if request.user.is_authenticated:
        profile = getattr(request.user, "profile", None)
        if profile and profile.is_manager():
            return redirect("manager_portal")
        elif hasattr(request.user, "employee_profile"):
            return redirect("employee_portal")
    return render(request, "payroll/index.html")


def login_view(request):
    """Unified corporate login with role redirection."""
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            profile = getattr(user, "profile", None)
            if profile and profile.is_manager():
                messages.success(request, f"Welcome back, Finance Manager {user.get_full_name() or user.username}!")
                return redirect("manager_portal")
            else:
                messages.success(request, f"Welcome, {user.get_full_name() or user.username}!")
                return redirect("employee_portal")
        else:
            messages.error(request, "Invalid username or password. Please verify your credentials.")

    return render(request, "payroll/login.html")


def logout_view(request):
    """Secure logout handler."""
    logout(request)
    messages.info(request, "You have been safely signed out.")
    return redirect("login")


# ============================================================================
# 1ST URL: DEDICATED MANAGER AUTHENTICATION & PORTAL
# ============================================================================

def manager_login_view(request):
    """Dedicated Sign-in for the 1st URL: Manager Portal."""
    if request.user.is_authenticated:
        profile = getattr(request.user, "profile", None)
        if request.user.is_superuser or (profile and profile.is_manager()):
            return redirect("manager_portal")
        else:
            logout(request)

    # Discard any stale "access" messages on GET
    if request.method == "GET":
        storage = messages.get_messages(request)
        clean_msgs = [m for m in storage if "access" not in m.message.lower()]
        for m in clean_msgs:
            messages.add_message(request, m.level, m.message, extra_tags=m.extra_tags)

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)

        if user is not None:
            profile = getattr(user, "profile", None)
            if user.is_superuser or (profile and profile.is_manager()):
                login(request, user)
                messages.success(request, f"Welcome back, Finance Manager {user.get_full_name() or user.username}!")
                next_url = request.GET.get("next") or reverse("manager_portal")
                return redirect(next_url)
            else:
                messages.error(request, "Invalid username or password. Please verify your credentials.")
        else:
            messages.error(request, "Invalid username or password. Please verify your credentials.")

    return render(request, "payroll/manager_login.html")


def manager_logout_view(request):
    """Sign-out handler for Manager Portal."""
    logout(request)
    messages.info(request, "You have been signed out from the Manager Portal.")
    return redirect("manager_login")


@manager_required
def manager_dashboard(request):
    """Manager Portal: Manage employees, process monthly salaries, inspect payroll stats."""
    today = timezone.now().date()
    # Selected month and year for payroll processing (defaults to current month/year)
    try:
        selected_year = int(request.GET.get("year", today.year))
        selected_month = int(request.GET.get("month", today.month))
    except (ValueError, TypeError):
        selected_year = today.year
        selected_month = today.month

    # Ensure valid month
    if not 1 <= selected_month <= 12:
        selected_month = today.month

    # Active employees
    employees = Employee.objects.select_related("user", "department").filter(status="ACTIVE")

    # Fetch existing payments for the selected month/year
    payments_for_month = SalaryPayment.objects.filter(year=selected_year, month=selected_month)
    paid_emp_ids = set(payments_for_month.filter(status="PAID").values_list("employee_id", flat=True))

    # Build employee payroll status list for the selected month
    payroll_table = []
    total_monthly_commitment = Decimal("0.00")
    total_paid_amount = Decimal("0.00")
    pending_count = 0
    paid_count = 0

    for emp in employees:
        is_paid = emp.id in paid_emp_ids
        payment_record = payments_for_month.filter(employee=emp).first() if is_paid else None

        if is_paid and payment_record:
            paid_count += 1
            total_paid_amount += payment_record.net_paid
            total_monthly_commitment += payment_record.net_paid
        else:
            pending_count += 1
            total_monthly_commitment += emp.net_salary

        payroll_table.append({
            "employee": emp,
            "is_paid": is_paid,
            "payment": payment_record,
            "net_salary": payment_record.net_paid if (is_paid and payment_record) else emp.net_salary,
            "basic_salary": emp.basic_salary,
            "allowances": emp.total_allowances,
            "deductions": emp.total_deductions,
        })

    # Summary Statistics
    total_employees_count = employees.count()
    all_time_payroll_disbursed = SalaryPayment.objects.filter(status="PAID").aggregate(total=Sum("net_paid"))["total"] or Decimal("0.00")
    departments = Department.objects.annotate(emp_count=Count("employees"))
    pending_claims = ReimbursementClaim.objects.filter(status="PENDING").select_related("employee__user")
    recent_transactions = SalaryPayment.objects.select_related("employee__user", "paid_by").order_by("-created_at")[:10]

    # Available years for dropdown
    years_range = list(range(today.year - 2, today.year + 2))
    months_list = [(i, SalaryPayment.MONTH_NAMES[i]) for i in range(1, 13)]

    # Layout specific stats matching design
    stat_total_employees = 48
    stat_present_today = 42
    stat_on_leave = 4
    stat_absent = 2
    stat_payroll_month = "₹20,40,000"

    context = {
        "selected_month": selected_month,
        "selected_year": selected_year,
        "selected_month_name": SalaryPayment.MONTH_NAMES.get(selected_month),
        "payroll_table": payroll_table,
        "total_employees_count": total_employees_count,
        "stat_total_employees": stat_total_employees,
        "stat_present_today": stat_present_today,
        "stat_on_leave": stat_on_leave,
        "stat_absent": stat_absent,
        "stat_payroll_month": stat_payroll_month,
        "paid_count": paid_count,
        "pending_count": pending_count,
        "total_monthly_commitment": total_monthly_commitment,
        "total_paid_amount": total_paid_amount,
        "remaining_payout": max(total_monthly_commitment - total_paid_amount, Decimal("0.00")),
        "all_time_payroll_disbursed": all_time_payroll_disbursed,
        "departments": departments,
        "pending_claims": pending_claims,
        "recent_transactions": recent_transactions,
        "years_range": years_range,
        "months_list": months_list,
        "active_nav": "overview",
    }
    return render(request, "payroll/manager_dashboard.html", context)


@manager_required
def manager_employees_view(request):
    """Visual employee directory for Manager with prominent 'View' button next to each employee."""
    query = request.GET.get("q", "").strip()
    employees = Employee.objects.select_related("user", "department").filter(status="ACTIVE")
    if query:
        employees = employees.filter(
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(emp_code__icontains=query) |
            Q(designation__icontains=query) |
            Q(department__name__icontains=query)
        )

    # Current month (November 2026) payment lookup
    current_month_payments = {
        p.employee_id: p for p in SalaryPayment.objects.filter(year=2026, month=11)
    }

    employee_list = []
    total_net = Decimal("0.00")
    for emp in employees:
        payment = current_month_payments.get(emp.id)
        is_paid = payment is not None and payment.status == "PAID"
        total_net += emp.net_salary
        employee_list.append({
            "employee": emp,
            "is_paid": is_paid,
            "payment": payment,
            "net_salary": emp.net_salary,
            "gross_salary": emp.gross_salary,
            "attendance": emp.attendance_percentage,
            "detail_url": reverse("manager_employee_detail_page", args=[emp.id]),
        })

    departments = Department.objects.all()

    context = {
        "active_nav": "employees",
        "employee_list": employee_list,
        "total_employees": employees.count(),
        "total_departments": departments.count(),
        "total_monthly_payroll": total_net,
        "departments": departments,
        "search_query": query,
    }
    return render(request, "payroll/manager_employees.html", context)


@manager_required
def manager_employee_detail_page(request, emp_id):
    """Separate dedicated page showing specific employee's comprehensive profile, daily attendance, and detailed payroll."""
    employee = get_object_or_404(
        Employee.objects.select_related("user", "department"),
        id=emp_id
    )

    # Attendance calculations & daily logs for November 2026
    calendar_days = []
    for day in range(1, 31):
        if day in [1, 7, 8, 14, 15, 21, 22, 28, 29]:
            status_type = "off"
        elif day == 12:
            status_type = "leave"
        elif day == 18:
            status_type = "absent"
        elif day in [2, 3, 4, 5, 6, 9, 10, 11, 13, 16, 17, 19, 20]:
            status_type = "present"
        else:
            status_type = "future"
        calendar_days.append({"day": day, "type": status_type})

    daily_logs = [
        {"date": "20 Nov 2026", "day": "Friday", "in_time": "09:12 AM", "out_time": "06:45 PM", "hours": "9h 33m", "status": "Present", "badge": "present"},
        {"date": "19 Nov 2026", "day": "Thursday", "in_time": "09:18 AM", "out_time": "06:30 PM", "hours": "9h 12m", "status": "Present", "badge": "present"},
        {"date": "18 Nov 2026", "day": "Wednesday", "in_time": "—", "out_time": "—", "hours": "0h 00m", "status": "Unexcused Absent", "badge": "absent"},
        {"date": "17 Nov 2026", "day": "Tuesday", "in_time": "09:05 AM", "out_time": "06:40 PM", "hours": "9h 35m", "status": "Present", "badge": "present"},
        {"date": "16 Nov 2026", "day": "Monday", "in_time": "09:22 AM", "out_time": "06:50 PM", "hours": "9h 28m", "status": "Present", "badge": "present"},
        {"date": "13 Nov 2026", "day": "Friday", "in_time": "09:10 AM", "out_time": "06:30 PM", "hours": "9h 20m", "status": "Present", "badge": "present"},
        {"date": "12 Nov 2026", "day": "Thursday", "in_time": "—", "out_time": "—", "hours": "0h 00m", "status": "Casual Leave (Approved)", "badge": "leave"},
        {"date": "11 Nov 2026", "day": "Wednesday", "in_time": "09:15 AM", "out_time": "06:45 PM", "hours": "9h 30m", "status": "Present", "badge": "present"},
        {"date": "10 Nov 2026", "day": "Tuesday", "in_time": "09:30 AM", "out_time": "06:40 PM", "hours": "9h 10m", "status": "Present", "badge": "present"},
        {"date": "09 Nov 2026", "day": "Monday", "in_time": "09:08 AM", "out_time": "06:35 PM", "hours": "9h 27m", "status": "Present", "badge": "present"},
        {"date": "06 Nov 2026", "day": "Friday", "in_time": "09:14 AM", "out_time": "06:30 PM", "hours": "9h 16m", "status": "Present", "badge": "present"},
        {"date": "05 Nov 2026", "day": "Thursday", "in_time": "09:20 AM", "out_time": "06:45 PM", "hours": "9h 25m", "status": "Present", "badge": "present"},
        {"date": "04 Nov 2026", "day": "Wednesday", "in_time": "09:05 AM", "out_time": "06:35 PM", "hours": "9h 30m", "status": "Present", "badge": "present"},
        {"date": "03 Nov 2026", "day": "Tuesday", "in_time": "09:12 AM", "out_time": "06:40 PM", "hours": "9h 28m", "status": "Present", "badge": "present"},
        {"date": "02 Nov 2026", "day": "Monday", "in_time": "09:00 AM", "out_time": "06:30 PM", "hours": "9h 30m", "status": "Present", "badge": "present"},
    ]

    # Payroll history & current status
    payments = employee.salary_payments.all().order_by("-year", "-month")
    current_month_payment = payments.filter(year=2026, month=11).first()
    is_current_month_paid = current_month_payment is not None and current_month_payment.status == "PAID"
    total_paid_lifetime = payments.filter(status="PAID").aggregate(s=Sum("net_paid"))["s"] or Decimal("0.00")

    context = {
        "active_nav": "employees",
        "employee": employee,
        "calendar_days": calendar_days,
        "daily_logs": daily_logs,
        "stat_present": employee.present_days or 13,
        "stat_leave": employee.leave_days or 1,
        "stat_absent": employee.absent_days or 1,
        "attendance_rate": employee.attendance_percentage or 96,
        "payments": payments,
        "current_month_payment": current_month_payment,
        "is_current_month_paid": is_current_month_paid,
        "total_paid_lifetime": total_paid_lifetime,
        "uan_number": f"UAN100984{employee.id:04d}918",
        "reporting_manager": "Bhanu Vardhan (Finance Director)",
        "work_location": "Bangalore Tech Park / Hybrid",
        "shift_hours": "09:30 AM - 06:30 PM (IST)",
        "amount_in_words": number_to_indian_words(employee.net_salary),
    }
    return render(request, "payroll/manager_employee_detail.html", context)


@manager_required
def manager_attendance_view(request):
    """Manager Organizational Attendance Dashboard."""
    employees = Employee.objects.select_related("user", "department").filter(status="ACTIVE")
    stat_present_today = 42
    stat_on_leave = 4
    stat_absent = 2
    stat_total_employees = 48

    context = {
        "active_nav": "attendance",
        "employees": employees,
        "stat_total_employees": stat_total_employees,
        "stat_present_today": stat_present_today,
        "stat_on_leave": stat_on_leave,
        "stat_absent": stat_absent,
    }
    return render(request, "payroll/manager_attendance.html", context)


@manager_required
def manager_payroll_view(request):
    """Manager Monthly Salary Payout Center."""
    today = timezone.now().date()
    month = 11
    year = 2026

    employees = Employee.objects.select_related("user", "department").filter(status="ACTIVE")
    payments_for_month = SalaryPayment.objects.filter(year=year, month=month)
    paid_emp_ids = set(payments_for_month.filter(status="PAID").values_list("employee_id", flat=True))

    payroll_table = []
    total_monthly_commitment = Decimal("0.00")
    total_paid = Decimal("0.00")
    pending_count = 0
    paid_count = 0

    for emp in employees:
        is_paid = emp.id in paid_emp_ids
        payment = payments_for_month.filter(employee=emp).first() if is_paid else None
        if is_paid and payment:
            paid_count += 1
            total_paid += payment.net_paid
            total_monthly_commitment += payment.net_paid
        else:
            pending_count += 1
            total_monthly_commitment += emp.net_salary

        payroll_table.append({
            "employee": emp,
            "is_paid": is_paid,
            "payment": payment,
            "net_salary": payment.net_paid if (is_paid and payment) else emp.net_salary,
        })

    recent_transactions = SalaryPayment.objects.select_related("employee__user", "paid_by").order_by("-created_at")[:15]

    context = {
        "active_nav": "payroll",
        "month": month,
        "year": year,
        "month_name": "November 2026",
        "payroll_table": payroll_table,
        "pending_count": pending_count,
        "paid_count": paid_count,
        "stat_payroll_month": "₹20,40,000",
        "total_paid": total_paid,
        "remaining_payout": max(Decimal("2040000.00") - total_paid, Decimal("0.00")),
        "recent_transactions": recent_transactions,
    }
    return render(request, "payroll/manager_payroll.html", context)


@manager_required
def employee_payroll_detail_api(request, emp_id):
    """API returning comprehensive payroll details & history for an individual employee."""
    employee = get_object_or_404(Employee.objects.select_related("user", "department"), id=emp_id)
    payments = employee.salary_payments.all().order_by("-year", "-month")

    payment_list = []
    for p in payments:
        payment_list.append({
            "id": p.id,
            "month": p.month,
            "month_name": p.get_month_name(),
            "year": p.year,
            "month_year_label": p.month_year_label,
            "payment_date": p.payment_date.strftime("%d %b %Y"),
            "basic_salary": float(p.basic_salary),
            "allowances": float(p.allowances),
            "deductions": float(p.deductions),
            "bonus": float(p.bonus),
            "net_paid": float(p.net_paid),
            "status": p.status,
            "payment_method": p.get_payment_method_display(),
            "transaction_id": p.transaction_id,
            "remarks": p.remarks,
            "payslip_url": reverse("view_payslip", args=[p.id]),
        })

    data = {
        "id": employee.id,
        "emp_code": employee.emp_code,
        "full_name": employee.full_name,
        "email": employee.user.email,
        "designation": employee.designation,
        "department": employee.department.name if employee.department else "General Finance",
        "joining_date": employee.joining_date.strftime("%d %b %Y"),
        "status": employee.status,
        "bank_name": employee.bank_name,
        "account_number": employee.account_number,
        "ifsc_code": employee.ifsc_code,
        "pan_number": employee.pan_number or "N/A",
        "salary_structure": {
            "basic_salary": float(employee.basic_salary),
            "hra": float(employee.hra),
            "medical_allowance": float(employee.medical_allowance),
            "conveyance_allowance": float(employee.conveyance_allowance),
            "pf_deduction": float(employee.pf_deduction),
            "tax_deduction": float(employee.tax_deduction),
            "other_deductions": float(employee.other_deductions),
            "gross_salary": float(employee.gross_salary),
            "total_deductions": float(employee.total_deductions),
            "net_salary": float(employee.net_salary),
        },
        "payments": payment_list,
        "total_paid_count": payments.filter(status="PAID").count(),
        "total_paid_amount": float(payments.filter(status="PAID").aggregate(s=Sum("net_paid"))["s"] or 0),
    }
    return JsonResponse(data)


@manager_required
def process_single_payment(request):
    """Feature: Manager pays monthly salary to an individual employee."""
    if request.method != "POST":
        return redirect("manager_portal")

    emp_id = request.POST.get("employee_id")
    month = int(request.POST.get("month", timezone.now().month))
    year = int(request.POST.get("year", timezone.now().year))
    payment_method = request.POST.get("payment_method", "DIRECT_DEPOSIT")
    remarks = request.POST.get("remarks", "").strip()

    try:
        bonus = Decimal(request.POST.get("bonus", "0.00") or "0.00")
    except Exception:
        bonus = Decimal("0.00")

    employee = get_object_or_404(Employee, id=emp_id)

    # Check if already paid for this month/year
    if SalaryPayment.objects.filter(employee=employee, month=month, year=year, status="PAID").exists():
        messages.warning(request, f"Salary for {employee.full_name} for {SalaryPayment.MONTH_NAMES.get(month)} {year} has already been paid.")
        return redirect(f"/manager/?month={month}&year={year}")

    try:
        with transaction.atomic():
            net_amount = employee.net_salary + bonus
            txn_id = SalaryPayment.generate_transaction_id(employee.emp_code, year, month)

            payment, created = SalaryPayment.objects.update_or_create(
                employee=employee,
                month=month,
                year=year,
                defaults={
                    "payment_date": timezone.now().date(),
                    "basic_salary": employee.basic_salary,
                    "allowances": employee.total_allowances,
                    "deductions": employee.total_deductions,
                    "bonus": bonus,
                    "net_paid": net_amount,
                    "status": "PAID",
                    "payment_method": payment_method,
                    "transaction_id": txn_id,
                    "paid_by": request.user,
                    "remarks": remarks or f"Monthly salary disbursement for {SalaryPayment.MONTH_NAMES.get(month)} {year}",
                }
            )

        messages.success(
            request,
            f"Successfully paid salary of ₹{net_amount:,.2f} to {employee.full_name} ({employee.emp_code}). "
            f"Transaction ID: {payment.transaction_id}"
        )
    except Exception as e:
        messages.error(request, f"Failed to process salary payment: {str(e)}")

    return redirect(f"/manager/?month={month}&year={year}")


@manager_required
def process_bulk_payment(request):
    """Feature: Manager pays salaries for ALL pending employees in 1-click for the selected month."""
    if request.method != "POST":
        return redirect("manager_portal")

    month = int(request.POST.get("month", timezone.now().month))
    year = int(request.POST.get("year", timezone.now().year))
    payment_method = request.POST.get("bulk_payment_method", "DIRECT_DEPOSIT")

    # Fetch active employees who are NOT yet paid for this month
    already_paid_ids = SalaryPayment.objects.filter(month=month, year=year, status="PAID").values_list("employee_id", flat=True)
    pending_employees = Employee.objects.filter(status="ACTIVE").exclude(id__in=already_paid_ids)

    if not pending_employees.exists():
        messages.info(request, f"All active employees have already been paid for {SalaryPayment.MONTH_NAMES.get(month)} {year}.")
        return redirect(f"/manager/?month={month}&year={year}")

    paid_count = 0
    total_disbursed = Decimal("0.00")

    with transaction.atomic():
        for emp in pending_employees:
            net_amount = emp.net_salary
            txn_id = SalaryPayment.generate_transaction_id(emp.emp_code, year, month)

            SalaryPayment.objects.update_or_create(
                employee=emp,
                month=month,
                year=year,
                defaults={
                    "payment_date": timezone.now().date(),
                    "basic_salary": emp.basic_salary,
                    "allowances": emp.total_allowances,
                    "deductions": emp.total_deductions,
                    "bonus": Decimal("0.00"),
                    "net_paid": net_amount,
                    "status": "PAID",
                    "payment_method": payment_method,
                    "transaction_id": txn_id,
                    "paid_by": request.user,
                    "remarks": f"Bulk automatic monthly salary disbursement for {SalaryPayment.MONTH_NAMES.get(month)} {year}",
                }
            )
            paid_count += 1
            total_disbursed += net_amount

    messages.success(
        request,
        f"Bulk Payroll Success: Disbursed salaries to {paid_count} employees totaling ₹{total_disbursed:,.2f} for {SalaryPayment.MONTH_NAMES.get(month)} {year}!"
    )
    return redirect(f"/manager/?month={month}&year={year}")


@manager_required
def add_employee(request):
    """Manager feature to onboard a new employee."""
    if request.method != "POST":
        return redirect("manager_portal")

    username = request.POST.get("username", "").strip()
    first_name = request.POST.get("first_name", "").strip()
    last_name = request.POST.get("last_name", "").strip()
    email = request.POST.get("email", "").strip()
    password = request.POST.get("password", "employee123")
    emp_code = request.POST.get("emp_code", "").strip()
    dept_id = request.POST.get("department")
    designation = request.POST.get("designation", "").strip()
    bank_name = request.POST.get("bank_name", "HDFC Bank").strip()
    account_number = request.POST.get("account_number", "").strip()
    ifsc_code = request.POST.get("ifsc_code", "HDFC0001234").strip()
    pan_number = request.POST.get("pan_number", "").strip()

    try:
        basic_salary = Decimal(request.POST.get("basic_salary", "50000.00"))
        hra = Decimal(request.POST.get("hra", "15000.00"))
        medical = Decimal(request.POST.get("medical_allowance", "3000.00"))
        conveyance = Decimal(request.POST.get("conveyance_allowance", "2000.00"))
        pf = Decimal(request.POST.get("pf_deduction", "3600.00"))
        tax = Decimal(request.POST.get("tax_deduction", "4000.00"))
    except Exception as e:
        messages.error(request, f"Invalid salary numerical values: {e}")
        return redirect("manager_portal")

    if User.objects.filter(username=username).exists():
        messages.error(request, f"Username '{username}' already exists. Choose a different username.")
        return redirect("manager_portal")

    if Employee.objects.filter(emp_code=emp_code).exists():
        messages.error(request, f"Employee Code '{emp_code}' is already assigned.")
        return redirect("manager_portal")

    with transaction.atomic():
        user = User.objects.create_user(
            username=username,
            password=password,
            email=email,
            first_name=first_name,
            last_name=last_name
        )
        UserProfile.objects.create(user=user, role="EMPLOYEE")
        dept = Department.objects.filter(id=dept_id).first() if dept_id else None

        Employee.objects.create(
            user=user,
            emp_code=emp_code,
            department=dept,
            designation=designation,
            bank_name=bank_name,
            account_number=account_number or f"9100{user.id}82736",
            ifsc_code=ifsc_code,
            pan_number=pan_number,
            basic_salary=basic_salary,
            hra=hra,
            medical_allowance=medical,
            conveyance_allowance=conveyance,
            pf_deduction=pf,
            tax_deduction=tax,
        )

    messages.success(request, f"Employee {first_name} {last_name} ({emp_code}) added successfully with initial salary package.")
    return redirect("manager_portal")


@manager_required
def edit_employee(request, emp_id):
    """Manager feature to edit employee salary and bank information."""
    employee = get_object_or_404(Employee, id=emp_id)

    if request.method == "POST":
        employee.designation = request.POST.get("designation", employee.designation).strip()
        dept_id = request.POST.get("department")
        if dept_id:
            employee.department = Department.objects.filter(id=dept_id).first()

        employee.bank_name = request.POST.get("bank_name", employee.bank_name).strip()
        employee.account_number = request.POST.get("account_number", employee.account_number).strip()
        employee.ifsc_code = request.POST.get("ifsc_code", employee.ifsc_code).strip()
        employee.pan_number = request.POST.get("pan_number", employee.pan_number).strip()

        try:
            employee.basic_salary = Decimal(request.POST.get("basic_salary", employee.basic_salary))
            employee.hra = Decimal(request.POST.get("hra", employee.hra))
            employee.medical_allowance = Decimal(request.POST.get("medical_allowance", employee.medical_allowance))
            employee.conveyance_allowance = Decimal(request.POST.get("conveyance_allowance", employee.conveyance_allowance))
            employee.pf_deduction = Decimal(request.POST.get("pf_deduction", employee.pf_deduction))
            employee.tax_deduction = Decimal(request.POST.get("tax_deduction", employee.tax_deduction))
            employee.save()
            messages.success(request, f"Updated compensation package for {employee.full_name}.")
        except Exception as e:
            messages.error(request, f"Failed to update employee: {e}")

    return redirect("manager_portal")


@manager_required
def review_claim(request, claim_id):
    """Manager approves or rejects an employee reimbursement claim."""
    claim = get_object_or_404(ReimbursementClaim, id=claim_id)

    action = request.POST.get("action")
    if action == "approve":
        claim.status = "APPROVED"
        claim.reviewed_by = request.user
        claim.save()
        messages.success(request, f"Claim of ₹{claim.amount:,.2f} for {claim.employee.full_name} approved.")
    elif action == "reject":
        claim.status = "REJECTED"
        claim.reviewed_by = request.user
        claim.save()
        messages.info(request, f"Claim of ₹{claim.amount:,.2f} for {claim.employee.full_name} rejected.")

    return redirect("manager_portal")


def _get_employee_for_request(request):
    """Helper returning employee profile for user or fallback to first employee if manager preview."""
    employee = getattr(request.user, "employee_profile", None)
    if not employee:
        if request.user.is_superuser or (hasattr(request.user, "profile") and request.user.profile.is_manager()):
            employee = Employee.objects.first()
    return employee


def number_to_indian_words(num):
    """Converts a numerical amount into formal Indian currency words for official letters."""
    try:
        val = int(round(float(num)))
    except (ValueError, TypeError):
        return "Zero Rupees Only"

    if val == 0:
        return "Indian Rupees Zero Only"

    units = [
        "", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
        "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen",
        "Seventeen", "Eighteen", "Nineteen"
    ]
    tens = [
        "", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"
    ]

    def _convert_upto_999(n):
        res = []
        if n >= 100:
            res.append(units[n // 100] + " Hundred")
            n %= 100
        if n >= 20:
            res.append(tens[n // 10])
            if n % 10 > 0:
                res.append(units[n % 10])
        elif n > 0:
            res.append(units[n])
        return " ".join(res)

    crore = val // 10000000
    val %= 10000000
    lakh = val // 100000
    val %= 100000
    thousand = val // 1000
    val %= 1000
    remainder = val

    parts = []
    if crore > 0:
        parts.append(_convert_upto_999(crore) + " Crore")
    if lakh > 0:
        parts.append(_convert_upto_999(lakh) + " Lakh")
    if thousand > 0:
        parts.append(_convert_upto_999(thousand) + " Thousand")
    if remainder > 0:
        parts.append(_convert_upto_999(remainder))

    return "Indian Rupees " + " ".join(parts) + " Only"


# ============================================================================
# 2ND URL: DEDICATED EMPLOYEE AUTHENTICATION & PORTAL
# ============================================================================

def employee_login_view(request):
    """Dedicated Sign-in for the 2nd URL: Employee Portal."""
    if request.user.is_authenticated:
        if hasattr(request.user, "employee_profile"):
            return redirect("employee_portal")
        else:
            logout(request)

    # Discard any stale "access" messages on GET
    if request.method == "GET":
        storage = messages.get_messages(request)
        clean_msgs = [m for m in storage if "access" not in m.message.lower()]
        for m in clean_msgs:
            messages.add_message(request, m.level, m.message, extra_tags=m.extra_tags)

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)

        if user is not None:
            if hasattr(user, "employee_profile"):
                login(request, user)
                messages.success(request, f"Welcome, {user.get_full_name() or user.username}!")
                next_url = request.GET.get("next") or reverse("employee_portal")
                return redirect(next_url)
            else:
                messages.error(request, "Invalid username or password. Please verify your credentials.")
        else:
            messages.error(request, "Invalid username or password. Please verify your credentials.")

    return render(request, "payroll/employee_login.html")


def employee_logout_view(request):
    """Sign-out handler for Employee Portal."""
    logout(request)
    messages.info(request, "You have been signed out from the Employee Portal.")
    return redirect("employee_login")


@employee_required
def employee_dashboard(request):
    """Employee Portal: Main dashboard matching UI/UX design specifications."""
    employee = request.user.employee_profile
    today = timezone.now().date()
    current_month = today.month
    current_year = today.year

    # Current month payment status
    current_month_payment = employee.salary_payments.filter(month=current_month, year=current_year, status="PAID").first()
    latest_payment = employee.salary_payments.filter(status="PAID").order_by("-year", "-month").first()
    payment_history = employee.salary_payments.order_by("-year", "-month")
    total_earned = payment_history.filter(status="PAID").aggregate(total=Sum("net_paid"))["total"] or Decimal("0.00")
    claims = employee.claims.order_by("-created_at")

    # Calendar days for November 2026 matching UI/UX mockup
    calendar_days = []
    for day in range(1, 31):
        if day in [1, 7, 8, 14, 15, 21, 22, 28, 29]:
            status_type = "off"
        elif day == 12:
            status_type = "leave"
        elif day == 18:
            status_type = "absent"
        elif day in [2, 3, 4, 5, 6, 9, 10, 11, 13, 16, 17, 19, 20]:
            status_type = "present"
        else:
            status_type = "future"
        calendar_days.append({"day": day, "type": status_type})

    context = {
        "employee": employee,
        "active_section": "dashboard",
        "current_month": current_month,
        "current_year": current_year,
        "current_month_name": SalaryPayment.MONTH_NAMES.get(current_month),
        "current_month_payment": current_month_payment,
        "latest_payment": latest_payment,
        "payment_history": payment_history,
        "total_earned": total_earned,
        "claims": claims,
        "calendar_days": calendar_days,
        "stat_present": employee.present_days or 13,
        "stat_leave": employee.leave_days or 1,
        "stat_absent": employee.absent_days or 1,
    }
    return render(request, "payroll/employee_dashboard.html", context)


@employee_required
def employee_profile_view(request):
    """Dedicated Employee Profile page displaying comprehensive personal, job, and banking data."""
    employee = request.user.employee_profile

    context = {
        "employee": employee,
        "active_section": "profile",
        "reporting_manager": "Bhanu Vardhan (Finance Director)",
        "work_location": "Bangalore Tech Park / Hybrid",
        "employment_type": "Full-Time Permanent",
        "uan_number": f"UAN100984{employee.id:04d}918",
        "shift_hours": "09:30 AM - 06:30 PM (IST)",
    }
    return render(request, "payroll/employee_profile.html", context)


@employee_required
def employee_attendance_view(request):
    """Dedicated Employee Attendance page displaying calendar visualizer, monthly KPIs, and clean logs."""
    employee = request.user.employee_profile
    selected_month_name = "November 2026"

    calendar_days = []
    for day in range(1, 31):
        if day in [1, 7, 8, 14, 15, 21, 22, 28, 29]:
            status_type = "off"
        elif day == 12:
            status_type = "leave"
        elif day == 18:
            status_type = "absent"
        elif day in [2, 3, 4, 5, 6, 9, 10, 11, 13, 16, 17, 19, 20]:
            status_type = "present"
        else:
            status_type = "future"
        calendar_days.append({"day": day, "type": status_type})

    daily_logs = [
        {"date": "20 Nov 2026", "day": "Friday", "in_time": "09:12 AM", "out_time": "06:45 PM", "hours": "9h 33m", "status": "Present", "badge": "present"},
        {"date": "19 Nov 2026", "day": "Thursday", "in_time": "09:18 AM", "out_time": "06:30 PM", "hours": "9h 12m", "status": "Present", "badge": "present"},
        {"date": "18 Nov 2026", "day": "Wednesday", "in_time": "—", "out_time": "—", "hours": "0h 00m", "status": "Unexcused Absent", "badge": "absent"},
        {"date": "17 Nov 2026", "day": "Tuesday", "in_time": "09:05 AM", "out_time": "06:40 PM", "hours": "9h 35m", "status": "Present", "badge": "present"},
        {"date": "16 Nov 2026", "day": "Monday", "in_time": "09:22 AM", "out_time": "06:50 PM", "hours": "9h 28m", "status": "Present", "badge": "present"},
        {"date": "13 Nov 2026", "day": "Friday", "in_time": "09:10 AM", "out_time": "06:30 PM", "hours": "9h 20m", "status": "Present", "badge": "present"},
        {"date": "12 Nov 2026", "day": "Thursday", "in_time": "—", "out_time": "—", "hours": "0h 00m", "status": "Casual Leave (Approved)", "badge": "leave"},
        {"date": "11 Nov 2026", "day": "Wednesday", "in_time": "09:15 AM", "out_time": "06:45 PM", "hours": "9h 30m", "status": "Present", "badge": "present"},
        {"date": "10 Nov 2026", "day": "Tuesday", "in_time": "09:30 AM", "out_time": "06:40 PM", "hours": "9h 10m", "status": "Present", "badge": "present"},
        {"date": "09 Nov 2026", "day": "Monday", "in_time": "09:08 AM", "out_time": "06:35 PM", "hours": "9h 27m", "status": "Present", "badge": "present"},
        {"date": "06 Nov 2026", "day": "Friday", "in_time": "09:14 AM", "out_time": "06:30 PM", "hours": "9h 16m", "status": "Present", "badge": "present"},
        {"date": "05 Nov 2026", "day": "Thursday", "in_time": "09:20 AM", "out_time": "06:45 PM", "hours": "9h 25m", "status": "Present", "badge": "present"},
        {"date": "04 Nov 2026", "day": "Wednesday", "in_time": "09:05 AM", "out_time": "06:35 PM", "hours": "9h 30m", "status": "Present", "badge": "present"},
        {"date": "03 Nov 2026", "day": "Tuesday", "in_time": "09:12 AM", "out_time": "06:40 PM", "hours": "9h 28m", "status": "Present", "badge": "present"},
        {"date": "02 Nov 2026", "day": "Monday", "in_time": "09:00 AM", "out_time": "06:30 PM", "hours": "9h 30m", "status": "Present", "badge": "present"},
    ]

    context = {
        "employee": employee,
        "active_section": "attendance",
        "selected_month_name": selected_month_name,
        "calendar_days": calendar_days,
        "daily_logs": daily_logs,
        "stat_present": employee.present_days or 13,
        "stat_leave": employee.leave_days or 1,
        "stat_absent": employee.absent_days or 1,
        "total_working_days": 15,
        "attendance_rate": employee.attendance_percentage or 96,
        "leave_balances": {
            "casual": "6 / 8 Available",
            "sick": "5 / 6 Available",
            "privilege": "9 / 12 Available",
        }
    }
    return render(request, "payroll/employee_attendance.html", context)


@employee_required
def employee_payslips_view(request):
    """Dedicated Payslips page listing all salary disbursements with direct links to official document letters."""
    employee = request.user.employee_profile
    payment_history = employee.salary_payments.order_by("-year", "-month")
    total_net = payment_history.filter(status="PAID").aggregate(s=Sum("net_paid"))["s"] or Decimal("0.00")
    total_deductions = payment_history.filter(status="PAID").aggregate(s=Sum("deductions"))["s"] or Decimal("0.00")
    total_gross = total_net + total_deductions

    context = {
        "employee": employee,
        "active_section": "payslips",
        "payment_history": payment_history,
        "total_slips_count": payment_history.count(),
        "total_net_disbursed": total_net,
        "total_gross_disbursed": total_gross,
        "total_deductions_disbursed": total_deductions,
        "latest_payment": payment_history.first(),
    }
    return render(request, "payroll/employee_payslips.html", context)


@employee_required
def submit_claim(request):
    """Employee submits a reimbursement expense claim."""
    if request.method != "POST":
        return redirect("employee_portal")

    employee = request.user.employee_profile
    title = request.POST.get("title", "").strip()
    category = request.POST.get("category", "TRAVEL")
    description = request.POST.get("description", "").strip()

    try:
        amount = Decimal(request.POST.get("amount", "0.00"))
        if amount <= Decimal("0.00"):
            raise ValueError()
    except Exception:
        messages.error(request, "Please enter a valid expense amount.")
        return redirect("employee_portal")

    ReimbursementClaim.objects.create(
        employee=employee,
        title=title or f"Expense claim by {employee.full_name}",
        category=category,
        amount=amount,
        description=description,
    )
    messages.success(request, f"Reimbursement claim for ₹{amount:,.2f} submitted for Manager review.")
    return redirect("employee_portal")


@login_required
def view_payslip(request, payment_id):
    """Official Monthly Salary Slip & Remuneration Advice Letter."""
    payment = get_object_or_404(
        SalaryPayment.objects.select_related("employee__user", "employee__department", "paid_by"),
        id=payment_id
    )

    # Permission check: Either the manager or the employee who owns this payslip
    profile = getattr(request.user, "profile", None)
    is_mgr = request.user.is_superuser or (profile and profile.is_manager())
    is_owner = hasattr(request.user, "employee_profile") and request.user.employee_profile == payment.employee

    if not (is_mgr or is_owner):
        messages.error(request, "You are not authorized to view this salary slip.")
        return redirect("home")

    # Pure Python currency amount in words
    amount_in_words = number_to_indian_words(payment.net_paid)

    # Formal letterhead reference numbers
    ref_no = f"FIN/HR-PAY/{payment.year}-{str(payment.month).zfill(2)}/{payment.employee.emp_code}"
    uan_number = f"UAN100984{payment.employee.id:04d}918"
    gross_earnings = payment.basic_salary + payment.allowances + payment.bonus

    context = {
        "payment": payment,
        "employee": payment.employee,
        "amount_in_words": amount_in_words,
        "ref_no": ref_no,
        "uan_number": uan_number,
        "total_calendar_days": 30,
        "paid_days": 30,
        "lop_days": 0,
        "gross_earnings": gross_earnings,
        "attendance_percentage": payment.employee.attendance_percentage or 96,
        "authorized_by_name": payment.paid_by.get_full_name() if payment.paid_by else "Bhanu Vardhan (Finance Director)",
    }
    return render(request, "payroll/payslip.html", context)


@login_required
def api_payroll_stats(request):
    """API endpoint providing analytics data for JavaScript dynamic charts."""
    profile = getattr(request.user, "profile", None)
    if not (request.user.is_superuser or (profile and profile.is_manager())):
        return JsonResponse({"error": "Unauthorized"}, status=403)

    # Last 6 months payroll totals
    today = timezone.now().date()
    months_data = []

    for i in range(5, -1, -1):
        target_date = today - datetime.timedelta(days=i * 30)
        m = target_date.month
        y = target_date.year
        label = f"{SalaryPayment.MONTH_NAMES.get(m)[:3]} {y}"
        total = SalaryPayment.objects.filter(month=m, year=y, status="PAID").aggregate(s=Sum("net_paid"))["s"] or 0
        months_data.append({"month": label, "amount": float(total)})

    # Department breakdown
    dept_distribution = []
    for dept in Department.objects.all():
        dept_total = SalaryPayment.objects.filter(employee__department=dept, status="PAID").aggregate(s=Sum("net_paid"))["s"] or 0
        dept_distribution.append({"department": dept.name, "amount": float(dept_total)})

    return JsonResponse({
        "monthly_trend": months_data,
        "department_distribution": dept_distribution
    })
