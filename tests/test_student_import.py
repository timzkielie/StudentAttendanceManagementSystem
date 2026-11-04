import csv
import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook

from student_import import (
    assess_rows,
    detect_field,
    read_student_file,
    suggested_mapping,
)


class TestStudentImport(unittest.TestCase):
    def test_header_aliases_are_recognized(self):
        examples = {
            "Student No.": "student_id",
            "Complete Name": "full_name",
            "Gmail Address": "email",
            "Cellphone": "mobile_number",
            "DOB": "birth_date",
            "Program": "course",
            "Block": "section",
            "Guardian Phone Number": "guardian_contact_number",
        }
        for header, expected in examples.items():
            with self.subTest(header=header):
                self.assertEqual(detect_field(header), expected)

    def test_csv_rows_are_mapped_and_validated_flexibly(self):
        headers = ["Student No.", "Surname", "Given Name", "Gmail", "Block", "Extra"]
        rows = [
            {
                "Student No.": "A-1",
                "Surname": "D'Souza",
                "Given Name": "Zoë",
                "Gmail": "zoe@example.com",
                "Block": "A",
                "Extra": "kept in source only",
            },
            {
                "Student No.": "A-1",
                "Surname": "Other",
                "Given Name": "Student",
                "Gmail": "",
                "Block": "B",
                "Extra": "",
            },
            {
                "Student No.": "A-3",
                "Surname": "",
                "Given Name": "No Last Name",
                "Gmail": "not-an-email",
                "Block": "C",
                "Extra": "",
            },
            {header: "" for header in headers},
        ]
        mapping = suggested_mapping(headers)
        results = assess_rows(rows, mapping, existing_ids={"A-9"})
        self.assertEqual([row["status"] for row in results], ["VALID", "DUPLICATE", "INVALID"])
        self.assertEqual(results[0]["values"]["fullname"], "D'Souza, Zoë")
        self.assertEqual(results[0]["values"]["course"], "Unassigned")
        self.assertIn("Last Name", " ".join(results[2]["errors"]))

    def test_full_name_and_existing_id(self):
        rows = [
            {"ID": "existing-1", "Name": "Ána de León", "Email Address": ""},
            {"ID": "new-2", "Name": "A"},
        ]
        mapping = suggested_mapping(list(rows[0]))
        results = assess_rows(rows, mapping, existing_ids={"EXISTING-1"})
        self.assertEqual(results[0]["status"], "DUPLICATE")
        self.assertEqual(results[1]["status"], "INVALID")
        self.assertEqual(results[0]["values"]["fullname"], "Ána de León")

    def test_csv_reader_handles_utf8_and_empty_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "students.csv"
            with path.open("w", newline="", encoding="utf-8-sig") as stream:
                writer = csv.writer(stream)
                writer.writerow(["Student ID", "Full Name"])
                writer.writerow(["ID-1", "Zoë"])
                writer.writerow(["", ""])
            headers, rows = read_student_file(path)
        self.assertEqual(headers, ["Student ID", "Full Name"])
        self.assertEqual(rows[0]["Full Name"], "Zoë")
        self.assertEqual(rows[1]["Student ID"], "")

    def test_excel_reader_and_duplicate_headers(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "students.xlsx"
            workbook = Workbook()
            worksheet = workbook.active
            worksheet.append(["Student No.", "Name", "Name"])
            worksheet.append(["123", "Student Name", "unused"])
            workbook.save(path)
            workbook.close()
            headers, rows = read_student_file(path)
        self.assertEqual(headers, ["Student No.", "Name", "Name (2)"])
        self.assertEqual(rows[0]["Student No."], "123")
        self.assertEqual(rows[0]["Name (2)"], "unused")

    def test_invalid_email_mobile_age_and_date_are_reported(self):
        headers = ["Student ID", "Full Name", "Email", "Mobile Number", "Age", "DOB"]
        row = dict(zip(headers, ["ID-1", "Student Name", "wrong", "123", "999", "not-a-date"]))
        result = assess_rows([row], suggested_mapping(headers))[0]
        self.assertEqual(result["status"], "INVALID")
        self.assertGreaterEqual(len(result["errors"]), 4)


if __name__ == "__main__":
    unittest.main()
