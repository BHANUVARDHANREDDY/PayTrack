from django.contrib import admin
from .models import Department, UserProfile, Employee, SalaryPayment, ReimbursementClaim


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "budget")
    search_fields = ("name", "code")


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "phone")
    list_filter = ("role",)
    search_fields = ("user__username", "user__email", "phone")


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("emp_code", "full_name", "department", "designation", "basic_salary", "net_salary", "status")
    list_filter = ("department", "status")
    search_fields = ("emp_code", "user__first_name", "user__last_name", "user__username")


@admin.register(SalaryPayment)
class SalaryPaymentAdmin(admin.ModelAdmin):
    list_display = ("transaction_id", "employee", "month", "year", "net_paid", "status", "payment_date")
    list_filter = ("year", "month", "status", "payment_method")
    search_fields = ("transaction_id", "employee__emp_code", "employee__user__first_name")


@admin.register(ReimbursementClaim)
class ReimbursementClaimAdmin(admin.ModelAdmin):
    list_display = ("title", "employee", "amount", "category", "status", "claim_date")
    list_filter = ("status", "category")
    search_fields = ("title", "employee__emp_code")
