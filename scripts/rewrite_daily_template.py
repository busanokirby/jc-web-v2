from pathlib import Path

content = '''{% extends 'layouts/base.html' %}

{% block title %}Daily Sales Report - JC Icons{% endblock %}

{% block content %}
<div class="d-flex justify-content-between align-items-center mb-4">
    <h1><i class="bi bi-cash-stack"></i> Daily Sales Report</h1>
    <div>
        <a href="{{ url_for('sales.reports') }}" class="btn btn-outline-secondary">
            <i class="bi bi-graph-up"></i> Back to Reports
        </a>
    </div>
</div>

<div class="card mb-4">
    <div class="card-body">
        <form method="GET" id="daily-sales-filter" class="mb-3">
            <div class="row g-2 align-items-end">
                <div class="col-auto">
                    <label class="form-label" for="sales-date">Select Date</label>
                    <input type="date" id="sales-date" name="date" class="form-control"
                        value="{{ selected_date }}" max="{{ today }}" onchange="this.form.submit()">
                </div>
            </div>
        </form>

        {% if sales_records and sales_records|length > 0 %}
        <div class="table-responsive">
            <table class="table table-hover mb-0">
                <thead class="table-light">
                    <tr>
                        <th>Customer Name</th>
                        <th>Transaction Type</th>
                        <th>Description</th>
                        <th class="text-end">Amount Paid</th>
                        <th>Date &amp; Time</th>
                    </tr>
                </thead>
                <tbody>
                    {% for rec in sales_records %}
                    <tr>
                        <td>{{ rec.customer }}</td>
                        <td>{{ rec.type }}</td>
                        <td>{{ rec.description }}</td>
                        <td class="text-end">₱{{ "%.2f"|format(rec.amount) }}</td>
                        <td>{{ rec.datetime.strftime('%Y-%m-%d %I:%M %p') if rec.datetime }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        <div class="text-end mt-2">
            <strong>Total Sales: ₱{{ "%.2f"|format(total_sales) }}</strong>
        </div>
        {% else %}
        <p class="text-muted">No sales recorded for the selected date.</p>
        {% endif %}
    </div>
</div>
{% endblock %}
'''

out = Path(r'c:\jc-web-v2\templates\sales\daily_sales.html')
out.write_text(content, encoding='utf-8')
print('rewrote daily_sales.html')
