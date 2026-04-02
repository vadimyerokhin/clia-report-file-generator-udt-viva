"""Database search module for querying the lab results SQLite database.

Provides search, detail retrieval, and file reconstruction functions
for the Search tab in the GUI.
"""
import csv
import os
import sqlite3
import subprocess
import platform
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from src.utils import sanitize_filename
except ImportError:
    from utils import sanitize_filename


DB_PATH = Path.home() / "Downloads" / "Results" / "lab_results.db"


def get_db_path() -> Path:
    """Return the path to the lab results database."""
    return DB_PATH


def db_exists() -> bool:
    """Check whether the lab results database file exists."""
    return DB_PATH.is_file()


def _connect(timeout: float = 5.0) -> sqlite3.Connection:
    """Open a read-only connection to the database.

    Args:
        timeout: Seconds to wait if the database is locked.

    Returns:
        A sqlite3 Connection with row_factory set to sqlite3.Row.

    Raises:
        FileNotFoundError: If the database file does not exist.
        sqlite3.OperationalError: If the database is locked or corrupt.
    """
    if not db_exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    conn = sqlite3.connect(
        f"file:{DB_PATH}?mode=ro",
        uri=True,
        timeout=timeout,
    )
    conn.row_factory = sqlite3.Row
    return conn


def search_patients(
    query: str = "",
    date_from: str = "",
    date_to: str = "",
    test_name: str = "",
    test_result: str = "",
    dob: str = "",
    collected_by: str = "",
    limit: int = 100,
    offset: int = 0,
) -> Tuple[List[Dict[str, Any]], int]:
    """Search specimens with patient info, optional filters.

    All string filters use parameterised queries to prevent SQL injection.

    Args:
        query: Free-text search against patient name or MRN.
        date_from: ISO date string for collection date lower bound (inclusive).
        date_to: ISO date string for collection date upper bound (inclusive).
        test_name: Filter to specimens containing this test name.
        test_result: Filter by result value (e.g. "Positive", "Negative", "Pending").
        dob: ISO date string for date of birth exact match.
        collected_by: Filter by collector name (partial match).
        limit: Maximum rows to return.
        offset: Row offset for pagination.

    Returns:
        Tuple of (list of result dicts, total_count).
        Each dict has keys: patient_name, mrn, dob, collection_date,
        num_tests, num_positive, specimen_id, first_name, last_name.
    """
    conn = _connect()
    try:
        conditions = []
        params: List[Any] = []

        if query:
            conditions.append(
                "(p.first_name || ' ' || p.last_name LIKE ? OR p.mrn LIKE ?)"
            )
            like = f"%{query}%"
            params.extend([like, like])

        if date_from:
            conditions.append("s.collection_date >= ?")
            params.append(date_from)

        if date_to:
            conditions.append("s.collection_date <= ?")
            params.append(date_to)

        if dob:
            conditions.append("p.date_of_birth = ?")
            params.append(dob)

        if collected_by:
            conditions.append("s.collected_by LIKE ?")
            params.append(f"%{collected_by}%")

        # Subquery filters for test-level attributes
        test_conditions = []
        test_params: List[Any] = []
        if test_name:
            test_conditions.append("tr.test_name LIKE ?")
            test_params.append(f"%{test_name}%")
        if test_result:
            if test_result.lower() == "positive":
                test_conditions.append("tr.is_positive = 1")
            elif test_result.lower() == "negative":
                test_conditions.append("tr.is_positive = 0 AND tr.is_pending = 0")
            elif test_result.lower() == "pending":
                test_conditions.append("tr.is_pending = 1")

        if test_conditions:
            sub_where = " AND ".join(test_conditions)
            conditions.append(
                f"s.id IN (SELECT tr.specimen_id FROM test_results tr WHERE {sub_where})"
            )
            params.extend(test_params)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # Count query
        count_sql = f"""
            SELECT COUNT(*) FROM (
                SELECT s.id
                FROM specimens s
                JOIN patients p ON s.patient_id = p.id
                WHERE {where_clause}
            )
        """
        total = conn.execute(count_sql, params).fetchone()[0]

        # Data query
        data_sql = f"""
            SELECT
                p.first_name,
                p.last_name,
                p.mrn,
                p.date_of_birth AS dob,
                s.collection_date,
                s.id AS specimen_id,
                (SELECT COUNT(*) FROM test_results tr WHERE tr.specimen_id = s.id) AS num_tests,
                (SELECT COUNT(*) FROM test_results tr WHERE tr.specimen_id = s.id AND tr.is_positive = 1) AS num_positive
            FROM specimens s
            JOIN patients p ON s.patient_id = p.id
            WHERE {where_clause}
            ORDER BY s.collection_date DESC, p.last_name ASC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])

        rows = conn.execute(data_sql, params).fetchall()
        results = []
        for row in rows:
            results.append({
                "first_name": row["first_name"],
                "last_name": row["last_name"],
                "patient_name": f"{row['first_name']} {row['last_name']}",
                "mrn": row["mrn"],
                "dob": row["dob"] or "",
                "collection_date": row["collection_date"] or "",
                "specimen_id": row["specimen_id"],
                "num_tests": row["num_tests"],
                "num_positive": row["num_positive"],
            })

        return results, total
    finally:
        conn.close()


def get_specimen_details(specimen_id: int) -> List[Dict[str, Any]]:
    """Get all test results for a given specimen.

    Args:
        specimen_id: The specimen's database ID.

    Returns:
        List of dicts with keys: test_name, result, units, flags,
        test_completed_at, is_positive, is_pending.
    """
    conn = _connect()
    try:
        sql = """
            SELECT test_name, result, units, flags,
                   test_completed_at, is_positive, is_pending
            FROM test_results
            WHERE specimen_id = ?
            ORDER BY test_name
        """
        rows = conn.execute(sql, [specimen_id]).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_distinct_test_names() -> List[str]:
    """Return sorted list of unique test names in the database."""
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT DISTINCT test_name FROM test_results ORDER BY test_name"
        ).fetchall()
        return [row["test_name"] for row in rows]
    finally:
        conn.close()


def find_report_pdf(
    reports_dir: str,
    first_name: str,
    last_name: str,
    mrn: str,
    collection_date: str,
) -> List[str]:
    """Reconstruct the expected PDF filename and search for it on disk.

    The convention is: {sanitized_name}_{mrn}_{collection_date}.pdf
    where the name part is the full patient name sanitised by utils.sanitize_filename.

    Args:
        reports_dir: Root directory to search recursively.
        first_name: Patient first name.
        last_name: Patient last name.
        mrn: Medical record number.
        collection_date: ISO YYYY-MM-DD collection date.

    Returns:
        List of absolute paths to matching PDF files (may be empty).
    """
    if not reports_dir or not os.path.isdir(reports_dir):
        return []

    full_name = f"{first_name} {last_name}".strip()
    sanitized = sanitize_filename(full_name)
    expected_filename = f"{sanitized}_{mrn}_{collection_date}.pdf"

    matches = []
    for root, _dirs, files in os.walk(reports_dir):
        for f in files:
            if f == expected_filename:
                matches.append(os.path.join(root, f))

    # Also try last-first ordering in case name was stored differently
    if not matches:
        alt_name = f"{last_name} {first_name}".strip()
        alt_sanitized = sanitize_filename(alt_name)
        alt_filename = f"{alt_sanitized}_{mrn}_{collection_date}.pdf"
        if alt_filename != expected_filename:
            for root, _dirs, files in os.walk(reports_dir):
                for f in files:
                    if f == alt_filename:
                        matches.append(os.path.join(root, f))

    # Fallback: partial match on MRN + date in filename
    if not matches:
        suffix = f"_{mrn}_{collection_date}.pdf"
        for root, _dirs, files in os.walk(reports_dir):
            for f in files:
                if f.endswith(suffix):
                    matches.append(os.path.join(root, f))

    return matches


def find_billing_files(
    reports_dir: str,
    mrn: str,
    date_of_service: str = "",
) -> List[str]:
    """Find billing CSV files that contain entries for a given MRN.

    Searches for billing_80307_*.csv files and checks their content
    for matching MRN rows.

    Args:
        reports_dir: Root directory to search recursively.
        mrn: Medical record number to search for.
        date_of_service: Optional ISO date to narrow matches.

    Returns:
        List of absolute paths to matching billing files.
    """
    if not reports_dir or not os.path.isdir(reports_dir):
        return []

    matches = []
    for root, _dirs, files in os.walk(reports_dir):
        for f in files:
            if f.startswith("billing_80307_") and f.endswith(".csv"):
                filepath = os.path.join(root, f)
                try:
                    with open(filepath, 'r', encoding='utf-8') as csvfile:
                        reader = csv.DictReader(csvfile)
                        for row in reader:
                            row_mrn = row.get("Patient_MRN", "").strip()
                            if row_mrn == mrn:
                                if date_of_service:
                                    row_dos = row.get("Date_of_Service", "").strip()
                                    # Handle MM/DD/YYYY vs YYYY-MM-DD
                                    if date_of_service in row_dos or row_dos in date_of_service:
                                        matches.append(filepath)
                                        break
                                    # Try converting MM/DD/YYYY to YYYY-MM-DD
                                    try:
                                        parts = row_dos.split("/")
                                        if len(parts) == 3:
                                            converted = f"{parts[2]}-{parts[0].zfill(2)}-{parts[1].zfill(2)}"
                                            if converted == date_of_service:
                                                matches.append(filepath)
                                                break
                                    except (IndexError, ValueError):
                                        pass
                                else:
                                    matches.append(filepath)
                                    break
                except (OSError, csv.Error, UnicodeDecodeError):
                    continue

    return matches


def open_file(filepath: str) -> Optional[str]:
    """Open a file with the OS default application.

    Args:
        filepath: Absolute path to the file.

    Returns:
        None on success, error message string on failure.
    """
    try:
        if platform.system() == "Darwin":
            subprocess.run(["open", filepath], check=True)
        elif platform.system() == "Windows":
            os.startfile(filepath)  # type: ignore[attr-defined]
        else:
            subprocess.run(["xdg-open", filepath], check=True)
        return None
    except Exception as e:
        return f"Could not open file: {e}"
