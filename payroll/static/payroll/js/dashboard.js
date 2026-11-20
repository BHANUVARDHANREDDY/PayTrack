/**
 * Finance Department Portal Interactive Script
 * Pure JavaScript for tabs, employee drill-down modals, live calculations, and filtering.
 */

document.addEventListener("DOMContentLoaded", function () {
    // ----------------------------------------------------
    // Tab Navigation
    // ----------------------------------------------------
    const tabButtons = document.querySelectorAll(".tab-btn");
    const tabPanes = document.querySelectorAll(".tab-pane");

    tabButtons.forEach(btn => {
        btn.addEventListener("click", function () {
            const targetId = this.getAttribute("data-tab");

            tabButtons.forEach(b => b.classList.remove("active"));
            tabPanes.forEach(p => p.classList.remove("active"));

            this.classList.add("active");
            const targetPane = document.getElementById(targetId);
            if (targetPane) {
                targetPane.classList.add("active");
            }
        });
    });

    // ----------------------------------------------------
    // NEW FEATURE: Employee Payroll Drill-Down Detail Modal
    // ----------------------------------------------------
    const detailModal = document.getElementById("employeePayrollDetailModal");
    const closeDetailModalBtn = document.getElementById("closeDetailModal");
    const closeDetailBtn = document.getElementById("closeDetailBtn");
    const detailPayNowBtn = document.getElementById("detailPayNowBtn");
    const clickableRows = document.querySelectorAll(".clickable-emp-row, .searchable-row");
    const viewButtons = document.querySelectorAll(".btn-view-payroll");

    let activeDetailEmployee = null;

    clickableRows.forEach(row => {
        row.addEventListener("click", function (e) {
            // If the user clicked an action button or link inside the row that isn't the view button
            if (e.target.closest("button") || e.target.closest("input")) {
                return;
            }

            const empId = this.getAttribute("data-emp-id");
            if (!empId) return;
            openEmployeePayrollDetails(empId);
        });
    });

    viewButtons.forEach(btn => {
        btn.addEventListener("click", function (e) {
            e.preventDefault();
            e.stopPropagation();
            const empId = this.getAttribute("data-emp-id");
            if (empId) openEmployeePayrollDetails(empId);
        });
    });

    function openEmployeePayrollDetails(empId) {
        if (!detailModal) return;

        // Fetch employee payroll record via pure Python API
        fetch(`/manager/employee/${empId}/details/`)
            .then(res => res.json())
            .then(data => {
                if (data.error) {
                    alert("Could not load employee details: " + data.error);
                    return;
                }
                activeDetailEmployee = data;

                // Populate Modal Header
                const nameEl = document.getElementById("detailEmpName");
                const codeEl = document.getElementById("detailEmpCode");
                const desigEl = document.getElementById("detailEmpDesig");
                const deptEl = document.getElementById("detailEmpDept");
                const avatarEl = document.getElementById("detailEmpAvatar");

                if (nameEl) nameEl.textContent = data.full_name;
                if (codeEl) codeEl.textContent = data.emp_code;
                if (desigEl) desigEl.textContent = data.designation;
                if (deptEl) deptEl.textContent = data.department;
                if (avatarEl) avatarEl.textContent = data.full_name.charAt(0).toUpperCase();

                // Populate Mini Stats
                const netEl = document.getElementById("detailEmpNetPay");
                const totalEl = document.getElementById("detailEmpTotalDisbursed");
                const countEl = document.getElementById("detailEmpCount");

                if (netEl) netEl.textContent = formatCurrency(data.salary_structure.net_salary);
                if (totalEl) totalEl.textContent = formatCurrency(data.total_paid_amount);
                if (countEl) countEl.textContent = data.total_paid_count;

                // Populate Salary Breakdown
                const s = data.salary_structure;
                setElementText("detailEmpBasic", formatCurrency(s.basic_salary));
                setElementText("detailEmpHra", formatCurrency(s.hra));
                setElementText("detailEmpMed", formatCurrency(s.medical_allowance));
                setElementText("detailEmpConv", formatCurrency(s.conveyance_allowance));
                setElementText("detailEmpGross", formatCurrency(s.gross_salary));
                setElementText("detailEmpDeductions", "- " + formatCurrency(s.total_deductions));

                // Populate Banking Info
                setElementText("detailEmpBank", data.bank_name);
                setElementText("detailEmpAccount", data.account_number);
                setElementText("detailEmpIfsc", data.ifsc_code);
                setElementText("detailEmpPan", data.pan_number);

                // Populate Historical Payslips
                const slipsCount = document.getElementById("detailEmpSlipsCount");
                if (slipsCount) slipsCount.textContent = `${data.payments.length} Slips on Record`;

                const historyBody = document.getElementById("detailEmpPaymentHistoryBody");
                if (historyBody) {
                    historyBody.innerHTML = "";
                    if (data.payments.length === 0) {
                        historyBody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 1.5rem;">No historical salary payments recorded yet.</td></tr>`;
                    } else {
                        data.payments.forEach(p => {
                            const tr = document.createElement("tr");
                            tr.innerHTML = `
                                <td><strong>${p.month_year_label}</strong></td>
                                <td>${p.payment_date}</td>
                                <td style="font-weight: 700; color: var(--success);">${formatCurrency(p.net_paid)}</td>
                                <td><span class="badge badge-info">${p.payment_method}</span></td>
                                <td><code style="font-size: 0.75rem;">${p.transaction_id}</code></td>
                                <td style="text-align: right;">
                                    <a href="${p.payslip_url}" target="_blank" class="btn btn-outline btn-sm">
                                        📄 View Slip
                                    </a>
                                </td>
                            `;
                            historyBody.appendChild(tr);
                        });
                    }
                }

                detailModal.classList.add("active");
            })
            .catch(err => {
                console.error("Error fetching employee payroll details:", err);
            });
    }

    function setElementText(id, text) {
        const el = document.getElementById(id);
        if (el) el.textContent = text;
    }

    function hideDetailModal() {
        if (detailModal) detailModal.classList.remove("active");
    }

    if (closeDetailModalBtn) closeDetailModalBtn.addEventListener("click", hideDetailModal);
    if (closeDetailBtn) closeDetailBtn.addEventListener("click", hideDetailModal);

    // Quick Trigger "Pay Salary" from within the Detail Modal
    if (detailPayNowBtn) {
        detailPayNowBtn.addEventListener("click", function () {
            hideDetailModal();
            if (activeDetailEmployee) {
                // Find matching pay button or trigger modal directly
                const empId = activeDetailEmployee.id;
                const payBtn = document.querySelector(`.btn-open-pay-modal[data-emp-id="${empId}"]`);
                if (payBtn) {
                    payBtn.click();
                } else {
                    // Open modal directly with active employee info
                    currentBaseNet = activeDetailEmployee.salary_structure.net_salary;
                    if (modalEmpId) modalEmpId.value = empId;
                    if (modalEmpName) modalEmpName.textContent = activeDetailEmployee.full_name;
                    if (modalEmpCode) modalEmpCode.textContent = activeDetailEmployee.emp_code;
                    if (modalBaseSalary) modalBaseSalary.textContent = formatCurrency(currentBaseNet);
                    if (modalBonusInput) modalBonusInput.value = "0";
                    if (modalTotalNetPay) modalTotalNetPay.textContent = formatCurrency(currentBaseNet);
                    if (payModal) payModal.classList.add("active");
                }
            }
        });
    }

    // ----------------------------------------------------
    // Pay Salary Modal Handler (Single Employee)
    // ----------------------------------------------------
    const payModal = document.getElementById("paySalaryModal");
    const payButtons = document.querySelectorAll(".btn-open-pay-modal");
    const closePayModal = document.getElementById("closePayModal");
    const cancelPayBtn = document.getElementById("cancelPayBtn");

    const modalEmpId = document.getElementById("modalEmployeeId");
    const modalEmpName = document.getElementById("modalEmployeeName");
    const modalEmpCode = document.getElementById("modalEmployeeCode");
    const modalBaseSalary = document.getElementById("modalBaseSalary");
    const modalBonusInput = document.getElementById("modalBonusInput");
    const modalTotalNetPay = document.getElementById("modalTotalNetPay");

    let currentBaseNet = 0;

    payButtons.forEach(btn => {
        btn.addEventListener("click", function (e) {
            e.stopPropagation();
            const empId = this.getAttribute("data-emp-id");
            const empName = this.getAttribute("data-emp-name");
            const empCode = this.getAttribute("data-emp-code");
            const baseNet = parseFloat(this.getAttribute("data-net-salary")) || 0;

            currentBaseNet = baseNet;
            if (modalEmpId) modalEmpId.value = empId;
            if (modalEmpName) modalEmpName.textContent = empName;
            if (modalEmpCode) modalEmpCode.textContent = empCode;
            if (modalBaseSalary) modalBaseSalary.textContent = formatCurrency(baseNet);
            if (modalBonusInput) modalBonusInput.value = "0";
            if (modalTotalNetPay) modalTotalNetPay.textContent = formatCurrency(baseNet);

            if (payModal) payModal.classList.add("active");
        });
    });

    function updateModalTotal() {
        if (!modalBonusInput || !modalTotalNetPay) return;
        const bonus = parseFloat(modalBonusInput.value) || 0;
        const finalNet = currentBaseNet + bonus;
        modalTotalNetPay.textContent = formatCurrency(finalNet);
    }

    if (modalBonusInput) {
        modalBonusInput.addEventListener("input", updateModalTotal);
    }

    function hidePayModal() {
        if (payModal) payModal.classList.remove("active");
    }

    if (closePayModal) closePayModal.addEventListener("click", hidePayModal);
    if (cancelPayBtn) cancelPayBtn.addEventListener("click", hidePayModal);

    // ----------------------------------------------------
    // Add Employee Modal
    // ----------------------------------------------------
    const addEmpModal = document.getElementById("addEmployeeModal");
    const openAddEmpBtn = document.getElementById("openAddEmpModal");
    const closeAddEmpBtn = document.getElementById("closeAddEmpModal");
    const cancelAddEmpBtn = document.getElementById("cancelAddEmpBtn");

    if (openAddEmpBtn && addEmpModal) {
        openAddEmpBtn.addEventListener("click", () => addEmpModal.classList.add("active"));
    }
    if (closeAddEmpBtn && addEmpModal) {
        closeAddEmpBtn.addEventListener("click", () => addEmpModal.classList.remove("active"));
    }
    if (cancelAddEmpBtn && addEmpModal) {
        cancelAddEmpBtn.addEventListener("click", () => addEmpModal.classList.remove("active"));
    }

    // ----------------------------------------------------
    // Bulk Payment Confirmation
    // ----------------------------------------------------
    const bulkPayForm = document.getElementById("bulkPayForm");
    if (bulkPayForm) {
        bulkPayForm.addEventListener("submit", function (e) {
            const count = this.getAttribute("data-pending-count") || "all";
            const confirmMsg = `Are you sure you want to process salary disbursement for ${count} pending employees? This will generate official transaction IDs and marks them as PAID.`;
            if (!confirm(confirmMsg)) {
                e.preventDefault();
            }
        });
    }

    // ----------------------------------------------------
    // Live Employee Net Salary Calculator (Employee Portal)
    // ----------------------------------------------------
    const calcBasic = document.getElementById("calcBasic");
    const calcHra = document.getElementById("calcHra");
    const calcMedical = document.getElementById("calcMedical");
    const calcPf = document.getElementById("calcPf");
    const calcGrossDisplay = document.getElementById("calcGrossDisplay");
    const calcDeductionsDisplay = document.getElementById("calcDeductionsDisplay");
    const calcNetDisplay = document.getElementById("calcNetDisplay");

    function runCalculator() {
        if (!calcBasic) return;
        const basic = parseFloat(calcBasic.value) || 0;
        const hra = parseFloat(calcHra?.value) || 0;
        const med = parseFloat(calcMedical?.value) || 0;
        const pf = parseFloat(calcPf?.value) || 0;

        const gross = basic + hra + med;
        const deductions = pf;
        const net = Math.max(0, gross - deductions);

        if (calcGrossDisplay) calcGrossDisplay.textContent = formatCurrency(gross);
        if (calcDeductionsDisplay) calcDeductionsDisplay.textContent = formatCurrency(deductions);
        if (calcNetDisplay) calcNetDisplay.textContent = formatCurrency(net);
    }

    const calcInputs = [calcBasic, calcHra, calcMedical, calcPf];
    calcInputs.forEach(input => {
        if (input) input.addEventListener("input", runCalculator);
    });

    // ----------------------------------------------------
    // Employee Search Filter (Manager Portal)
    // ----------------------------------------------------
    const searchInput = document.getElementById("employeeSearchInput");
    if (searchInput) {
        searchInput.addEventListener("input", function () {
            const query = this.value.toLowerCase().trim();
            const rows = document.querySelectorAll(".searchable-row");

            rows.forEach(row => {
                const text = row.textContent.toLowerCase();
                if (text.includes(query)) {
                    row.style.display = "";
                } else {
                    row.style.display = "none";
                }
            });
        });
    }

    // ----------------------------------------------------
    // Utility Formatter
    // ----------------------------------------------------
    function formatCurrency(amount) {
        return "₹" + Number(amount).toLocaleString("en-IN", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    }

    // Close modal on Escape
    window.addEventListener("keydown", function (e) {
        if (e.key === "Escape") {
            if (payModal) payModal.classList.remove("active");
            if (addEmpModal) addEmpModal.classList.remove("active");
            if (detailModal) detailModal.classList.remove("active");
        }
    });
});
