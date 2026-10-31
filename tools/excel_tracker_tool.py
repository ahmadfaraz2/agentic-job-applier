"""
Excel Application Tracking & Anti-Duplicate Tool for Ahmad Faraz.
Maintains a professional, formatted Excel workbook (data/applied_jobs_tracker.xlsx)
and ensures emails are NEVER sent more than once to the same recipient or opening.
"""

from __future__ import annotations

import csv
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from config import Config

logger = logging.getLogger(__name__)

EXCEL_FILE = Config.DATA_DIR / "applied_jobs_tracker.xlsx"
CSV_FILE = Config.DATA_DIR / "applied_jobs_tracker.csv"

COLUMNS = [
    "ID",
    "Timestamp",
    "Company",
    "Job Title",
    "Recipient Email",
    "Platform / Source",
    "Status",
    "CV Attached",
    "Subject Line",
    "Pitch / Notes"
]

def _init_excel_file() -> openpyxl.Workbook:
    """Initializes a new styled Excel tracking workbook if one does not exist."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Applications Record"

    # Header styling
    header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    thin_border = Border(
        left=Side(style="thin", color="CBD5E1"),
        right=Side(style="thin", color="CBD5E1"),
        top=Side(style="thin", color="CBD5E1"),
        bottom=Side(style="thin", color="CBD5E1")
    )

    ws.append(COLUMNS)
    for col_num in range(1, len(COLUMNS) + 1):
        cell = ws.cell(row=1, column=col_num)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = thin_border

    ws.row_dimensions[1].height = 28
    ws.freeze_panes = "A2"
    return wb

def _auto_fit_columns(ws: openpyxl.worksheet.worksheet.Worksheet):
    """Automatically adjusts column widths for clean viewing in Excel."""
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            val_str = str(cell.value or "")
            if len(val_str) > max_len:
                max_len = len(val_str)
        ws.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 50)

def is_already_applied(recipient_email: str, company: str = "", job_title: str = "") -> bool:
    """Checks whether an application was already recorded for this email or (company + role).

    Args:
        recipient_email: Target email address.
        company: Optional company name.
        job_title: Optional job title.

    Returns:
        True if already applied, preventing duplicate outreach.
    """
    clean_email = recipient_email.strip().lower()
    clean_comp = company.strip().lower()
    clean_title = job_title.strip().lower()

    if not EXCEL_FILE.exists():
        return False

    try:
        wb = openpyxl.load_workbook(EXCEL_FILE, data_only=True)
        ws = wb.active
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not row or len(row) < 5:
                continue
            r_email = str(row[4] or "").strip().lower()
            r_comp = str(row[2] or "").strip().lower()
            r_title = str(row[3] or "").strip().lower()
            r_status = str(row[6] or "").strip().upper()

            if r_status == "APPLIED":
                # Check email match
                if clean_email and r_email == clean_email:
                    return True
                # Check company + title match
                if clean_comp and clean_title and r_comp == clean_comp and r_title == clean_title:
                    return True
    except Exception as e:
        logger.warning(f"Could not read excel for deduplication ({e}), checking CSV fallback...")

    # Fallback to CSV check
    if CSV_FILE.exists():
        try:
            with open(CSV_FILE, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("Status", "").upper() == "APPLIED":
                        if clean_email and row.get("Recipient Email", "").lower() == clean_email:
                            return True
                        if clean_comp and clean_title:
                            if row.get("Company", "").lower() == clean_comp and row.get("Job Title", "").lower() == clean_title:
                                return True
        except Exception:
            pass

    return False

def record_excel_application(
    company: str,
    job_title: str,
    recipient_email: str,
    source: str = "LinkedIn / Direct",
    status: str = "APPLIED",
    cv_attached: str = "Ahmad_Faraz_CV.pdf",
    subject: str = "",
    pitch_snippet: str = ""
) -> str:
    """Appends an application record to the Excel tracker and syncs the CSV companion."""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Load or create Excel
    if EXCEL_FILE.exists():
        try:
            wb = openpyxl.load_workbook(EXCEL_FILE)
            ws = wb.active
        except Exception:
            wb = _init_excel_file()
            ws = wb.active
    else:
        wb = _init_excel_file()
        ws = wb.active

    row_idx = ws.max_row + 1
    record_id = f"APP-{row_idx - 1:04d}"

    row_data = [
        record_id,
        now_str,
        company.strip(),
        job_title.strip(),
        recipient_email.strip(),
        source.strip(),
        status.strip(),
        cv_attached.strip(),
        subject.strip() or f"Application for {job_title.strip()} - Ahmad Faraz",
        pitch_snippet.strip()[:200]
    ]

    ws.append(row_data)

    # Style the newly added row
    thin_border = Border(
        left=Side(style="thin", color="E2E8F0"),
        right=Side(style="thin", color="E2E8F0"),
        top=Side(style="thin", color="E2E8F0"),
        bottom=Side(style="thin", color="E2E8F0")
    )
    applied_fill = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid")
    applied_font = Font(name="Calibri", size=10, bold=True, color="166534")

    for col_idx in range(1, len(row_data) + 1):
        cell = ws.cell(row=row_idx, column=col_idx)
        cell.border = thin_border
        cell.alignment = Alignment(vertical="center")
        if col_idx == 7 and status.upper() == "APPLIED":
            cell.fill = applied_fill
            cell.font = applied_font
            cell.alignment = Alignment(horizontal="center", vertical="center")
        elif col_idx in (1, 2):
            cell.alignment = Alignment(horizontal="center", vertical="center")

    _auto_fit_columns(ws)
    wb.save(EXCEL_FILE)

    # Also sync CSV
    write_header = not CSV_FILE.exists()
    try:
        with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if write_header:
                writer.writerow(COLUMNS)
            writer.writerow(row_data)
    except Exception as e:
        logger.warning(f"Could not append to CSV: {e}")

    logger.info(f"Recorded application to {company} ({recipient_email}) in Excel tracker.")
    return f"Recorded in Excel Tracker: {record_id} -> {company} ({recipient_email})"

def update_excel_recruiter_status(
    company_or_email: str,
    status: str,
    reply_snippet: str = ""
) -> bool:
    """Updates the status and notes of a company application when a reply/interview is detected."""
    if not EXCEL_FILE.exists():
        return False

    clean_target = company_or_email.strip().lower()
    updated = False

    try:
        wb = openpyxl.load_workbook(EXCEL_FILE)
        ws = wb.active

        # Style mapping
        color_map = {
            "INTERVIEW_INVITE": ("DCFCE7", "166534"), # Green
            "ASSESSMENT": ("FEF3C7", "B45309"),       # Amber
            "INQUIRY": ("E0F2FE", "0369A1"),          # Cyan
            "REJECTION": ("F1F5F9", "64748B"),        # Slate
        }
        fill_hex, font_hex = color_map.get(status.upper(), ("DCFCE7", "166534"))
        status_fill = PatternFill(start_color=fill_hex, end_color=fill_hex, fill_type="solid")
        status_font = Font(name="Calibri", size=10, bold=True, color=font_hex)

        for row_idx in range(2, ws.max_row + 1):
            cell_comp = str(ws.cell(row=row_idx, column=3).value or "").strip().lower()
            cell_email = str(ws.cell(row=row_idx, column=5).value or "").strip().lower()

            if clean_target in cell_comp or clean_target in cell_email or cell_email in clean_target:
                # Update status cell (column 7)
                cell_s = ws.cell(row=row_idx, column=7)
                cell_s.value = status.upper().replace("_", " ")
                cell_s.fill = status_fill
                cell_s.font = status_font

                # Update notes cell (column 10)
                if reply_snippet:
                    cell_n = ws.cell(row=row_idx, column=10)
                    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                    cell_n.value = f"[{now_str} Reply]: {reply_snippet[:150]}"

                updated = True

        if updated:
            wb.save(EXCEL_FILE)
            logger.info(f"Updated Excel tracker status for '{company_or_email}' -> {status}")
    except Exception as e:
        logger.error(f"Failed to update Excel status: {e}")

    return updated

def get_excel_stats() -> Dict[str, Any]:
    """Returns statistics from the Excel tracker."""
    if not EXCEL_FILE.exists():
        return {"total_applications": 0, "companies": []}

    try:
        wb = openpyxl.load_workbook(EXCEL_FILE, data_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(min_row=2, values_only=True))
        companies = set()
        applied_count = 0
        interview_count = 0
        for r in rows:
            if r and len(r) > 6 and r[0]:
                status_str = str(r[6] or "").upper()
                applied_count += 1
                companies.add(str(r[2] or "").strip())
                if "INTERVIEW" in status_str:
                    interview_count += 1
        return {
            "total_applications": applied_count,
            "interview_invites": interview_count,
            "unique_companies": len(companies),
            "companies": sorted(list(companies)),
            "excel_path": str(EXCEL_FILE)
        }
    except Exception as e:
        logger.error(f"Error reading Excel stats: {e}")
        return {"total_applications": 0, "error": str(e)}

def get_recent_applications(limit: int = 5) -> List[Dict[str, Any]]:
    """Returns the last N application records from the Excel tracker (or CSV fallback)."""
    records: List[Dict[str, Any]] = []

    if EXCEL_FILE.exists():
        try:
            wb = openpyxl.load_workbook(EXCEL_FILE, data_only=True)
            ws = wb.active
            rows = list(ws.iter_rows(min_row=2, values_only=True))
            for r in reversed(rows):
                if r and len(r) > 6 and r[0]:
                    records.append({
                        "id": str(r[0] or ""),
                        "timestamp": str(r[1] or ""),
                        "company": str(r[2] or ""),
                        "job_title": str(r[3] or ""),
                        "recipient_email": str(r[4] or ""),
                        "source": str(r[5] or ""),
                        "status": str(r[6] or ""),
                        "subject": str(r[8] or "") if len(r) > 8 else "",
                    })
                    if len(records) >= limit:
                        break
            return records
        except Exception as e:
            logger.warning(f"Error reading recent applications from Excel ({e}), falling back to CSV...")

    if CSV_FILE.exists():
        try:
            with open(CSV_FILE, "r", encoding="utf-8") as f:
                reader = list(csv.DictReader(f))
                for row in reversed(reader):
                    records.append({
                        "id": row.get("ID", ""),
                        "timestamp": row.get("Timestamp", ""),
                        "company": row.get("Company", ""),
                        "job_title": row.get("Job Title", ""),
                        "recipient_email": row.get("Recipient Email", ""),
                        "source": row.get("Platform / Source", ""),
                        "status": row.get("Status", ""),
                        "subject": row.get("Subject Line", ""),
                    })
                    if len(records) >= limit:
                        break
        except Exception as e:
            logger.warning(f"Error reading recent applications from CSV: {e}")

    return records
