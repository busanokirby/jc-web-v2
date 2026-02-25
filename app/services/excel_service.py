"""
Excel Report Generation Service
Creates .xlsx files with sales and repair data
"""
from __future__ import annotations
from datetime import date
from decimal import Decimal
from typing import Dict
import os
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter


class ExcelReportService:
    """Service for generating Excel reports"""
    
    # Color scheme
    HEADER_FILL = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    HEADER_FONT = Font(bold=True, color="FFFFFF", size=12)
    SUMMARY_FILL = PatternFill(start_color="D9E8F5", end_color="D9E8F5", fill_type="solid")
    SUMMARY_FONT = Font(bold=True, size=11)
    
    BORDER = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    @staticmethod
    def generate_filename(start_date: date, end_date: date) -> str:
        """Generate filename based on date range"""
        if start_date == end_date:
            return f"Sales_Report_{start_date.strftime('%Y_%m_%d')}.xlsx"
        else:
            return f"Sales_Report_{start_date.strftime('%Y_%m_%d')}_to_{end_date.strftime('%Y_%m_%d')}.xlsx"
    
    @staticmethod
    def create_report(report_data: Dict) -> bytes:
        """
        Create Excel workbook from report data.
        
        Args:
            report_data: Report dict from ReportService.generate_report_data()
        
        Returns:
            Excel file as bytes
        """
        wb = Workbook()
        
        # Remove default sheet
        if 'Sheet' in wb.sheetnames:
            wb.remove(wb['Sheet'])
        
        # Create sheets
        ExcelReportService._create_summary_sheet(wb, report_data)
        ExcelReportService._create_sales_sheet(wb, report_data)
        ExcelReportService._create_repairs_sheet(wb, report_data)
        
        # Save to bytes
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        return output.getvalue()
    
    @staticmethod
    def _create_summary_sheet(wb: Workbook, report_data: Dict):
        """Create summary sheet with KPIs"""
        ws = wb.create_sheet("Summary", 0)
        
        # Title
        ws['A1'] = "SALES & REPAIR REPORT"
        ws['A1'].font = Font(bold=True, size=14, color="FFFFFF")
        ws['A1'].fill = PatternFill(start_color="203864", end_color="203864", fill_type="solid")
        ws.merge_cells('A1:B1')
        ws['A1'].alignment = Alignment(horizontal='center', vertical='center')
        ws.row_dimensions[1].height = 25
        
        # Date range
        ws['A3'] = "Report Period:"
        ws['B3'] = report_data['date_range']
        ws['A3'].font = Font(bold=True)
        
        ws['A4'] = "Frequency:"
        ws['B4'] = report_data['frequency'].replace('_', ' ').title()
        ws['A4'].font = Font(bold=True)
        
        # KPIs
        row = 6
        metrics = [
            ("Total Revenue", report_data['total_revenue'], "₱{:,.2f}"),
            ("Total Transactions", report_data['total_transactions'], "{}"),
            ("Sales Payments", report_data['total_sales_payments'], "₱{:,.2f}"),
            ("Repair Payments", report_data['total_repair_payments'], "₱{:,.2f}"),
        ]
        
        for label, value, fmt in metrics:
            ws[f'A{row}'] = label
            ws[f'B{row}'] = fmt.format(value)
            ws[f'A{row}'].font = Font(bold=True)
            ws[f'A{row}'].fill = ExcelReportService.SUMMARY_FILL
            ws[f'B{row}'].fill = ExcelReportService.SUMMARY_FILL
            row += 1
        
        # Payment breakdown
        ws[f'A{row}'] = "Payment Method Breakdown"
        ws[f'A{row}'].font = Font(bold=True, size=11)
        row += 1
        
        ws[f'A{row}'] = "Method"
        ws[f'B{row}'] = "Count"
        ws[f'C{row}'] = "Total"
        for col in ['A', 'B', 'C']:
            ws[f'{col}{row}'].font = ExcelReportService.HEADER_FONT
            ws[f'{col}{row}'].fill = ExcelReportService.HEADER_FILL
            ws[f'{col}{row}'].border = ExcelReportService.BORDER
        row += 1
        
        for method, data in sorted(report_data.get('payment_breakdown', {}).items()):
            ws[f'A{row}'] = method
            ws[f'B{row}'] = data.get('count', 0)
            ws[f'C{row}'] = data.get('total', 0)
            ws[f'C{row}'].number_format = '₱#,##0.00'
            row += 1
        
        # Column widths
        ws.column_dimensions['A'].width = 25
        ws.column_dimensions['B'].width = 20
        ws.column_dimensions['C'].width = 20
    
    @staticmethod
    def _create_sales_sheet(wb: Workbook, report_data: Dict):
        """Create sales transactions sheet"""
        ws = wb.create_sheet("Sales", 1)
        
        # Header
        headers = ["Invoice #", "Customer", "Payment Method", "Amount Paid", "Payment Date"]
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = ExcelReportService.HEADER_FONT
            cell.fill = ExcelReportService.HEADER_FILL
            cell.border = ExcelReportService.BORDER
            cell.alignment = Alignment(horizontal='center', vertical='center')
        
        ws.row_dimensions[1].height = 20
        
        # Data
        row = 2
        for sale in report_data.get('sales_records', []):
            ws.cell(row=row, column=1, value=sale['invoice_number'])
            ws.cell(row=row, column=2, value=sale['customer_name'])
            ws.cell(row=row, column=3, value=sale['payment_method'])
            
            amount_cell = ws.cell(row=row, column=4, value=sale['amount_paid'])
            amount_cell.number_format = '₱#,##0.00'
            
            date_cell = ws.cell(row=row, column=5, value=sale['payment_date'])
            date_cell.number_format = 'yyyy-mm-dd'
            
            for col in range(1, 6):
                ws.cell(row=row, column=col).border = ExcelReportService.BORDER
            
            row += 1
        
        # Totals row
        if row > 2:
            ws.cell(row=row, column=1, value="TOTAL")
            ws.cell(row=row, column=1).font = Font(bold=True)
            
            total_cell = ws.cell(row=row, column=4, value=report_data['total_sales_payments'])
            total_cell.number_format = '₱#,##0.00'
            total_cell.font = Font(bold=True)
            total_cell.fill = ExcelReportService.SUMMARY_FILL
        
        # Column widths
        ws.column_dimensions['A'].width = 15
        ws.column_dimensions['B'].width = 20
        ws.column_dimensions['C'].width = 18
        ws.column_dimensions['D'].width = 15
        ws.column_dimensions['E'].width = 15
    
    @staticmethod
    def _create_repairs_sheet(wb: Workbook, report_data: Dict):
        """Create repairs transactions sheet"""
        ws = wb.create_sheet("Repairs", 2)
        
        # Header
        headers = ["Ticket #", "Customer", "Device", "Payment Method", "Amount Paid", "Payment Date"]
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = ExcelReportService.HEADER_FONT
            cell.fill = ExcelReportService.HEADER_FILL
            cell.border = ExcelReportService.BORDER
            cell.alignment = Alignment(horizontal='center', vertical='center')
        
        ws.row_dimensions[1].height = 20
        
        # Data
        row = 2
        for repair in report_data.get('repair_records', []):
            ws.cell(row=row, column=1, value=repair['ticket_number'])
            ws.cell(row=row, column=2, value=repair['customer_name'])
            ws.cell(row=row, column=3, value=repair['device_type'])
            ws.cell(row=row, column=4, value=repair['payment_method'])
            
            amount_cell = ws.cell(row=row, column=5, value=repair['amount_paid'])
            amount_cell.number_format = '₱#,##0.00'
            
            date_cell = ws.cell(row=row, column=6, value=repair['payment_date'])
            date_cell.number_format = 'yyyy-mm-dd'
            
            for col in range(1, 7):
                ws.cell(row=row, column=col).border = ExcelReportService.BORDER
            
            row += 1
        
        # Totals row
        if row > 2:
            ws.cell(row=row, column=1, value="TOTAL")
            ws.cell(row=row, column=1).font = Font(bold=True)
            
            total_cell = ws.cell(row=row, column=5, value=report_data['total_repair_payments'])
            total_cell.number_format = '₱#,##0.00'
            total_cell.font = Font(bold=True)
            total_cell.fill = ExcelReportService.SUMMARY_FILL
        
        # Column widths
        ws.column_dimensions['A'].width = 15
        ws.column_dimensions['B'].width = 20
        ws.column_dimensions['C'].width = 20
        ws.column_dimensions['D'].width = 18
        ws.column_dimensions['E'].width = 15
        ws.column_dimensions['F'].width = 15
