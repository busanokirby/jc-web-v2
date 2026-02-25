from datetime import date

import pytest

from app.services.email_service import EmailService
from app.services.report_service import ReportService


def test_generate_html_body_daily_includes_transactions(app):
    # build a simple report_data dict for a single day
    start = date.today()
    with app.app_context():
        # use the helper to get combined daily context
        daily_ctx = ReportService.build_daily_sales_context(start)
        # merge into a typical report_data structure that EmailService expects
        report_data = ReportService.generate_report_data(start, start, 'daily')
        report_data.update(daily_ctx)

    html = EmailService.generate_html_body(report_data, config=None)
    # body should mention "Transactions" section
    assert "Transactions" in html
    # customer column should appear if there were records
    if daily_ctx.get('sales_records'):
        assert "Customer" in html
    # make sure the note does not mention the Excel attachment
    assert "Excel attachment" not in html


@pytest.mark.parametrize("freq", ["weekly", "every_3_days"])
def test_generate_html_body_non_daily_has_attachment_note(freq, app):
    with app.app_context():
        report_data = ReportService.generate_report_data(date.today(), date.today(), freq)
    html = EmailService.generate_html_body(report_data, config=None)
    assert "Excel attachment" in html
