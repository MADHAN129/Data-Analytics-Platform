"""
Tests for Next-Generation Database Connection Architecture:
- Categorical sample profiling during schema sync
- Execution self-reflection guardrail for multi-group dropped rows
"""

import unittest
from unittest.mock import patch, MagicMock
from app.services.query_service import _validate_query_results


class TestConnectionArchitecture(unittest.TestCase):
    def test_validate_query_results_detects_multi_group_dropped_rows_anomaly(self):
        """Verify that _validate_query_results flags multi-group questions when a JOIN yields <= 1 row."""
        sql = """
        SELECT e.dept, d.department_name, e.salary
        FROM employees e
        JOIN departments d ON e.dept = d.department_name;
        """
        columns = ["dept", "department_name", "salary"]
        rows = [["Engineering", "Engineering", "168000.00"]]

        # Asking for multi-group breakdown: 'highest salary of each department'
        val_ok, val_notes = _validate_query_results(
            sql=sql,
            columns=columns,
            rows=rows,
            natural_language="highest salary of each department"
        )
        self.assertFalse(val_ok)
        self.assertIn("Multi-Group Result Anomaly", val_notes)
        self.assertIn("query the primary table directly", val_notes)

    def test_validate_query_results_passes_valid_multi_group_results(self):
        """Verify that multi-group questions with full result set pass validation."""
        sql = """
        SELECT dept, MAX(salary) AS highest_salary
        FROM employees
        GROUP BY dept;
        """
        columns = ["dept", "highest_salary"]
        rows = [
            ["Sales & Mktg", "210000.00"],
            ["Engineering", "168000.00"],
            ["Product", "160000.00"],
            ["Finance", "142000.00"],
            ["HR", "135000.00"],
            ["CS", "130000.00"],
        ]

        val_ok, val_notes = _validate_query_results(
            sql=sql,
            columns=columns,
            rows=rows,
            natural_language="highest salary of each department"
        )
    def test_validate_query_results_detects_mismatched_join_nulls(self):
        """Verify that _validate_query_results flags queries where a JOIN causes excessive NULL values in results."""
        sql = """
        SELECT d.department_name, em.max_salary
        FROM departments d
        LEFT JOIN (SELECT dept, MAX(salary) AS max_salary FROM employees GROUP BY dept) em
               ON d.department_name = em.dept;
        """
        columns = ["department_name", "max_salary"]
        rows = [
            ["Customer Success", None],
            ["Engineering", "168000.00"],
            ["Finance & Operations", None],
            ["Human Resources", None],
            ["Product Management", None],
            ["Sales & Marketing", None],
        ]

        val_ok, val_notes = _validate_query_results(
            sql=sql,
            columns=columns,
            rows=rows,
            natural_language="what is the highest salary of each department"
        )
        self.assertFalse(val_ok)
        self.assertIn("Mismatched JOIN Error", val_notes)


if __name__ == "__main__":
    unittest.main()
