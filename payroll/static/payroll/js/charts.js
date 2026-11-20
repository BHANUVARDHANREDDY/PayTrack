/**
 * Finance Department Canvas Chart Renderer
 * Pure HTML5 Canvas + JS - No external dependencies or CDNs required!
 */

document.addEventListener("DOMContentLoaded", function () {
    const trendCanvas = document.getElementById("monthlyTrendChart");
    const deptCanvas = document.getElementById("deptDistributionChart");

    if (!trendCanvas && !deptCanvas) return;

    // Fetch live statistics from Django pure Python API
    fetch("/api/payroll-stats/")
        .then(res => res.json())
        .then(data => {
            if (trendCanvas && data.monthly_trend) {
                renderBarChart(trendCanvas, data.monthly_trend);
            }
            if (deptCanvas && data.department_distribution) {
                renderDepartmentChart(deptCanvas, data.department_distribution);
            }
        })
        .catch(err => {
            console.error("Could not load payroll charts:", err);
        });

    function renderBarChart(canvas, items) {
        const ctx = canvas.getContext("2d");
        const w = canvas.width;
        const h = canvas.height;
        ctx.clearRect(0, 0, w, h);

        const padding = { top: 30, right: 20, bottom: 40, left: 60 };
        const chartW = w - padding.left - padding.right;
        const chartH = h - padding.top - padding.bottom;

        const maxVal = Math.max(...items.map(i => i.amount), 100000);

        // Draw grid lines
        ctx.strokeStyle = "#e2e8f0";
        ctx.lineWidth = 1;
        const gridSteps = 4;
        for (let i = 0; i <= gridSteps; i++) {
            const y = padding.top + (chartH / gridSteps) * i;
            ctx.beginPath();
            ctx.moveTo(padding.left, y);
            ctx.lineTo(w - padding.right, y);
            ctx.stroke();

            // Label
            const val = maxVal - (maxVal / gridSteps) * i;
            ctx.fillStyle = "#94a3b8";
            ctx.font = "10px sans-serif";
            ctx.textAlign = "right";
            ctx.fillText("₹" + (val / 1000).toFixed(0) + "k", padding.left - 8, y + 3);
        }

        // Draw bars
        const barSpacing = chartW / items.length;
        const barWidth = Math.min(barSpacing * 0.55, 45);

        items.forEach((item, index) => {
            const barH = (item.amount / maxVal) * chartH;
            const x = padding.left + index * barSpacing + (barSpacing - barWidth) / 2;
            const y = padding.top + chartH - barH;

            // Gradient fill
            const grad = ctx.createLinearGradient(0, y, 0, padding.top + chartH);
            grad.addColorStop(0, "#2563eb");
            grad.addColorStop(1, "#60a5fa");

            ctx.fillStyle = grad;
            ctx.beginPath();
            if (ctx.roundRect) {
                ctx.roundRect(x, y, barWidth, barH, [4, 4, 0, 0]);
            } else {
                ctx.rect(x, y, barWidth, barH);
            }
            ctx.fill();

            // Month Label
            ctx.fillStyle = "#475569";
            ctx.font = "11px sans-serif";
            ctx.textAlign = "center";
            ctx.fillText(item.month, x + barWidth / 2, h - 15);

            // Amount label on top
            if (item.amount > 0) {
                ctx.fillStyle = "#0f172a";
                ctx.font = "bold 10px sans-serif";
                ctx.fillText("₹" + (item.amount / 1000).toFixed(1) + "k", x + barWidth / 2, y - 6);
            }
        });
    }

    function renderDepartmentChart(canvas, items) {
        const ctx = canvas.getContext("2d");
        const w = canvas.width;
        const h = canvas.height;
        ctx.clearRect(0, 0, w, h);

        const colors = ["#2563eb", "#10b981", "#f59e0b", "#8b5cf6", "#ec4899", "#14b8a6"];
        const total = items.reduce((acc, curr) => acc + curr.amount, 0);

        if (total === 0) {
            ctx.fillStyle = "#94a3b8";
            ctx.font = "13px sans-serif";
            ctx.textAlign = "center";
            ctx.fillText("No department salary records yet", w / 2, h / 2);
            return;
        }

        const centerX = w * 0.35;
        const centerY = h / 2;
        const radius = Math.min(centerX, centerY) - 20;

        let startAngle = -Math.PI / 2;

        items.forEach((item, index) => {
            const sliceAngle = (item.amount / total) * 2 * Math.PI;
            ctx.beginPath();
            ctx.moveTo(centerX, centerY);
            ctx.arc(centerX, centerY, radius, startAngle, startAngle + sliceAngle);
            ctx.closePath();
            ctx.fillStyle = colors[index % colors.length];
            ctx.fill();
            startAngle += sliceAngle;
        });

        // Donut inner hole
        ctx.beginPath();
        ctx.arc(centerX, centerY, radius * 0.58, 0, 2 * Math.PI);
        ctx.fillStyle = "#ffffff";
        ctx.fill();

        // Legend on right side
        const legendX = w * 0.65;
        let legendY = 35;

        items.forEach((item, index) => {
            ctx.fillStyle = colors[index % colors.length];
            ctx.fillRect(legendX, legendY - 8, 12, 12);

            ctx.fillStyle = "#1e293b";
            ctx.font = "12px sans-serif";
            ctx.textAlign = "left";
            const percent = ((item.amount / total) * 100).toFixed(0);
            ctx.fillText(`${item.department}: ${percent}%`, legendX + 18, legendY + 2);

            legendY += 24;
        });
    }
});
