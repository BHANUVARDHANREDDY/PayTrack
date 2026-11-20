from django.urls import path
from . import views

urlpatterns = [
    # Gateway & General Auth
    path("", views.home_view, name="home"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),

    # ========================================================
    # 1ST URL: MANAGER PORTAL (Dedicated Dashboard & Operations)
    # ========================================================
    path("manager/", views.manager_dashboard, name="manager_portal"),
    path("manager/login/", views.manager_login_view, name="manager_login"),
    path("manager/logout/", views.manager_logout_view, name="manager_logout"),
    path("manager/employees/", views.manager_employees_view, name="manager_employees"),
    path("manager/employee/<int:emp_id>/", views.manager_employee_detail_page, name="manager_employee_detail_page"),
    path("manager/attendance/", views.manager_attendance_view, name="manager_attendance"),
    path("manager/payroll/", views.manager_payroll_view, name="manager_payroll"),
    path("manager/employee/<int:emp_id>/details/", views.employee_payroll_detail_api, name="employee_payroll_detail_api"),
    path("manager/pay-salary/", views.process_single_payment, name="process_single_payment"),
    path("manager/pay-all-salaries/", views.process_bulk_payment, name="process_bulk_payment"),
    path("manager/add-employee/", views.add_employee, name="add_employee"),
    path("manager/edit-employee/<int:emp_id>/", views.edit_employee, name="edit_employee"),
    path("manager/review-claim/<int:claim_id>/", views.review_claim, name="review_claim"),

    # ========================================================
    # 2ND URL: EMPLOYEE PORTAL (Dedicated Dashboard & Sections)
    # ========================================================
    path("employee/", views.employee_dashboard, name="employee_portal"),
    path("employee/login/", views.employee_login_view, name="employee_login"),
    path("employee/logout/", views.employee_logout_view, name="employee_logout"),
    path("employee/profile/", views.employee_profile_view, name="employee_profile"),
    path("employee/attendance/", views.employee_attendance_view, name="employee_attendance"),
    path("employee/payslips/", views.employee_payslips_view, name="employee_payslips"),
    path("employee/submit-claim/", views.submit_claim, name="submit_claim"),

    # Official Document Letter Payslip
    path("payslip/<int:payment_id>/", views.view_payslip, name="view_payslip"),

    # Dynamic JSON API for JavaScript charts
    path("api/payroll-stats/", views.api_payroll_stats, name="api_payroll_stats"),
]
