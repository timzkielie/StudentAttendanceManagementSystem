"""Read, map, and validate flexible student-list files before database import."""
import csv
import re
from datetime import date, datetime
from pathlib import Path

from openpyxl import load_workbook


FIELD_LABELS = {
    "student_id": "Student ID",
    "full_name": "Full Name",
    "last_name": "Last Name",
    "first_name": "First Name",
    "middle_name": "Middle Name",
    "email": "Gmail Address",
    "mobile_number": "Mobile Number",
    "age": "Age",
    "birth_date": "Date of Birth",
    "gender": "Gender",
    "course": "Course",
    "year_level": "Year Level",
    "section": "Section",
    "modality": "Modality",
    "address": "Address",
    "guardian_name": "Guardian Name",
    "guardian_contact_number": "Guardian Contact Number",
}
IGNORE_FIELD = "Ignore"


def _normalized_heading(value):
    return re.sub(r"[^a-z0-9]", "", str(value).strip().lower())


_ALIASES = {
    "student_id": (
        "studentid", "studentno", "studentnumber", "idnumber", "idno", "student#", "id",
    ),
    "full_name": (
        "fullname", "completename", "studentname", "name", "completefullname",
    ),
    "last_name": ("lastname", "surname", "familyname"),
    "first_name": ("firstname", "givenname", "forename"),
    "middle_name": ("middlename", "middleinitial", "mi"),
    "email": ("email", "emailaddress", "gmail", "gmailaddress", "emailid"),
    "mobile_number": (
        "mobile", "mobilenumber", "mobileno", "contact", "contactnumber", "phone",
        "phonenumber", "cellphone", "cellnumber", "telephone",
    ),
    "age": ("age", "studentage"),
    "birth_date": ("birthdate", "dateofbirth", "dob", "birthday"),
    "gender": ("gender", "sex"),
    "course": ("course", "coursename", "program", "programname", "degree"),
    "year_level": ("yearlevel", "year", "gradelevel", "level"),
    "section": ("section", "block", "class", "classsection"),
    "modality": ("modality", "learningmodality", "learningmode"),
    "address": ("address", "homeaddress", "permanentaddress"),
    "guardian_name": ("guardian", "guardianname", "parentname", "parentguardian"),
    "guardian_contact_number": (
        "guardiancontact", "guardiancontactnumber", "guardianphone",
        "guardianphonenumber", "parentcontact", "parentcontactnumber",
    ),
}
_FIELD_BY_ALIAS = {
    _normalized_heading(alias): field
    for field, aliases in _ALIASES.items()
    for alias in aliases
}
_STUDENT_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]*\Z")
_EMAIL_PATTERN = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+\Z")
_MOBILE_PATTERN = re.compile(r"[+0-9().\-\s]+\Z")


class StudentFileError(ValueError):
    """A readable error caused by a student file or its column mapping."""


def detect_field(header):
    """Return a known student field for a column heading, or None."""
    return _FIELD_BY_ALIAS.get(_normalized_heading(header))


def _cell_text(value):
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _unique_headers(values):
    headers = []
    counts = {}
    for index, value in enumerate(values, 1):
        header = _cell_text(value) or f"Column {index}"
        counts[header] = counts.get(header, 0) + 1
        if counts[header] > 1:
            header = f"{header} ({counts[header]})"
        headers.append(header)
    if not headers:
        raise StudentFileError("The file does not contain a header row.")
    return headers


def read_student_file(filename):
    """Return (unique headers, rows as header/value dictionaries) from CSV or XLSX."""
    path = Path(filename)
    suffix = path.suffix.lower()
    if suffix == ".xlsx":
        workbook = load_workbook(path, read_only=True, data_only=True)
        try:
            worksheet = workbook.active
            values = worksheet.iter_rows(values_only=True)
            header_row = next(values, None)
            if header_row is None:
                raise StudentFileError("The Excel file is empty.")
            headers = _unique_headers(header_row)
            rows = [
                [_cell_text(value) for value in row[:len(headers)]]
                + [""] * max(0, len(headers) - len(row))
                for row in values
            ]
        finally:
            workbook.close()
    elif suffix == ".csv":
        rows = None
        last_error = None
        for encoding in ("utf-8-sig", "cp1252"):
            try:
                with path.open("r", encoding=encoding, newline="") as stream:
                    sample = stream.read(4096)
                    stream.seek(0)
                    try:
                        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
                    except csv.Error:
                        dialect = csv.excel
                    reader = csv.reader(stream, dialect)
                    header_row = next(reader, None)
                    if header_row is None:
                        raise StudentFileError("The CSV file is empty.")
                    headers = _unique_headers(header_row)
                    rows = [
                        [_cell_text(value) for value in row[:len(headers)]]
                        + [""] * max(0, len(headers) - len(row))
                        for row in reader
                    ]
                break
            except UnicodeDecodeError as error:
                last_error = error
        if rows is None:
            raise StudentFileError("The CSV file encoding could not be read.") from last_error
    else:
        raise StudentFileError("Choose an Excel (.xlsx) or CSV (.csv) file.")

    return headers, [dict(zip(headers, row)) for row in rows]


def suggested_mapping(headers):
    """Automatically map recognizable headers, leaving unfamiliar ones ignored."""
    return {header: detect_field(header) or IGNORE_FIELD for header in headers}


def _parse_age(value):
    text = _cell_text(value)
    if not re.fullmatch(r"\d{1,3}", text):
        raise ValueError("Age must be a whole number.")
    age = int(text)
    if age < 0 or age > 130:
        raise ValueError("Age must be between 0 and 130.")
    return age


def _parse_birth_date(value):
    if isinstance(value, datetime):
        parsed = value.date()
    elif isinstance(value, date):
        parsed = value
    else:
        text = _cell_text(value)
        formats = (
            "%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%m-%d-%Y", "%d-%m-%Y",
            "%Y/%m/%d", "%b %d %Y", "%B %d %Y",
        )
        parsed = None
        for date_format in formats:
            try:
                parsed = datetime.strptime(text, date_format).date()
                break
            except ValueError:
                continue
        if parsed is None:
            raise ValueError("Date of birth must use a supported date format.")
    if parsed > date.today():
        raise ValueError("Date of birth cannot be in the future.")
    return parsed


def _age_on(birth_date, today=None):
    today = today or date.today()
    return today.year - birth_date.year - (
        (today.month, today.day) < (birth_date.month, birth_date.day)
    )


def _field_values(row, mapping):
    values = {}
    errors = []
    by_field = {}
    for header, field in mapping.items():
        if field == IGNORE_FIELD:
            continue
        by_field.setdefault(field, []).append(header)
    duplicated = [FIELD_LABELS[field] for field, headers in by_field.items() if len(headers) > 1]
    if duplicated:
        errors.append("Multiple columns are mapped to: " + ", ".join(duplicated) + ".")

    def get(field):
        headers = by_field.get(field, ())
        return _cell_text(row.get(headers[0])) if len(headers) == 1 else ""

    student_id = get("student_id")
    if not student_id:
        errors.append("Student ID is required.")
    elif not _STUDENT_ID_PATTERN.fullmatch(student_id):
        errors.append("Student ID contains unsupported characters.")

    full_name = get("full_name")
    first_name = get("first_name")
    last_name = get("last_name")
    middle_name = get("middle_name")
    if full_name:
        fullname = full_name
    elif first_name and last_name:
        fullname = f"{last_name}, {first_name}" + (f" {middle_name}" if middle_name else "")
    else:
        fullname = ""
        errors.append("Full Name or both First Name and Last Name are required.")
    if fullname and len(fullname) < 3:
        errors.append("Student name must contain at least 3 characters.")

    email = get("email")
    if email and not _EMAIL_PATTERN.fullmatch(email):
        errors.append("Email address is invalid.")

    mobile = get("mobile_number")
    if mobile:
        digits = sum(character.isdigit() for character in mobile)
        if not _MOBILE_PATTERN.fullmatch(mobile) or not 7 <= digits <= 15:
            errors.append("Mobile number must contain 7 to 15 digits.")

    age_value = get("age")
    age = None
    if age_value:
        try:
            age = _parse_age(age_value)
        except ValueError as error:
            errors.append(str(error))

    birth_date_value = get("birth_date")
    birth_date = None
    if birth_date_value:
        try:
            birth_date = _parse_birth_date(birth_date_value)
        except ValueError as error:
            errors.append(str(error))
    if birth_date and age is not None and age != _age_on(birth_date):
        errors.append("Age does not match the date of birth.")
    elif birth_date and age is None:
        age = _age_on(birth_date)

    return {
        "student_id": student_id,
        "fullname": fullname,
        "course": get("course") or "Unassigned",
        "section": get("section"),
        "email": email or None,
        "mobile_number": mobile or None,
        "age": age,
        "birth_date": birth_date,
        "gender": get("gender") or None,
        "year_level": get("year_level") or None,
        "modality": get("modality") or None,
        "address": get("address") or None,
        "guardian_name": get("guardian_name") or None,
        "guardian_contact_number": get("guardian_contact_number") or None,
    }, errors


def assess_rows(rows, mapping, existing_ids=()):
    """Validate rows and classify them as VALID, DUPLICATE, or INVALID."""
    mapped_fields = [field for field in mapping.values() if field != IGNORE_FIELD]
    if "student_id" not in mapped_fields:
        mapping_error = "Map an uploaded column to Student ID."
    elif "full_name" not in mapped_fields and not (
        "first_name" in mapped_fields and "last_name" in mapped_fields
    ):
        mapping_error = "Map Full Name, or map both First Name and Last Name."
    else:
        mapping_error = None

    existing = {str(student_id).casefold() for student_id in existing_ids}
    seen = set()
    results = []
    for line_number, row in enumerate(rows, 2):
        if not any(_cell_text(value) for value in row.values()):
            continue
        values, errors = _field_values(row, mapping)
        if mapping_error and mapping_error not in errors:
            errors.append(mapping_error)

        key = values["student_id"].casefold() if values["student_id"] else None
        duplicate = bool(key) and (key in existing or key in seen)
        if duplicate:
            status = "DUPLICATE"
            errors.append("Student ID already exists.")
        elif errors:
            status = "INVALID"
        else:
            status = "VALID"
        if key:
            seen.add(key)
        results.append({
            "line": line_number,
            "raw": row,
            "values": values,
            "status": status,
            "errors": errors,
        })
    return results


def import_template_rows():
    """Return reusable template column headings and one example record."""
    headers = [
        "Student ID", "Last Name", "First Name", "Middle Name", "Gmail Address",
        "Mobile Number", "Age", "Birth Date", "Gender", "Course", "Year Level",
        "Section", "Modality", "Address", "Guardian Name", "Guardian Contact Number",
    ]
    sample = [
        "2026-0001", "Santos", "Jamie", "Lee", "jamie.santos@example.com",
        "+639171234567", "18", "2008-03-15", "Female", "BSIT", "1st Year",
        "A", "On-site", "Sample City", "Alex Santos", "+639181234567",
    ]
    return headers, sample
