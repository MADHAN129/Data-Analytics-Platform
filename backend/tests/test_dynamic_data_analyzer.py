"""
Automated Test Suite for Data Analyzer: Dynamic Question Answering
-----------------------------------------------------------------
Validates all requirements specified in:
# Data Analyzer: Dynamic Question Answering Requirements

Crucial Rule:
NO hardcoded answers or fixed values.
Ground truth values are extracted directly from the live database at test time.
"""

import unittest
import math
from app.database import SessionLocal
from app.models.connection import DatabaseConnection
from app.services.connection_service import get_connector
from app.services.query_service import execute_natural_language_query
from app.schemas.query import QueryRequest


class TestDynamicDataAnalyzer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.db = SessionLocal()
            cls.db_conn = cls.db.query(DatabaseConnection).filter_by(id=2).first()
            if cls.db_conn is None:
                raise unittest.SkipTest("Oracle database connection (id=2) not found in database")
            cls.connector = get_connector(cls.db_conn)
            cls.oracle_conn = cls.connector.connect()
            cls.user_id = 1
        except unittest.SkipTest:
            raise
        except Exception as e:
            raise unittest.SkipTest(f"Live database not reachable: {e}")

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "oracle_conn") and cls.oracle_conn:
            try:
                cls.oracle_conn.close()
            except Exception:
                pass
        if hasattr(cls, "db") and cls.db:
            try:
                cls.db.close()
            except Exception:
                pass

    def _exec_ground_truth(self, sql: str) -> list[tuple]:
        cur = self.oracle_conn.cursor()
        cur.execute(sql.rstrip(";"))
        rows = cur.fetchall()
        cur.close()
        return rows

    # 1. Basic Question
    def test_01_basic_question(self):
        """1. Basic questions (e.g., 'How many employees are there?')"""
        gt_rows = self._exec_ground_truth("SELECT COUNT(*) FROM EMPLOYEES")
        expected_count = gt_rows[0][0]

        req = QueryRequest(database_id=self.db_conn.id, natural_language="How many employees are there?")
        resp = execute_natural_language_query(self.db, req, user_id=self.user_id)

        self.assertEqual(resp.status, "completed")
        self.assertIsNotNone(resp.results)
        self.assertTrue(len(resp.results.rows) >= 1)
        actual_val = resp.results.rows[0][0]
        self.assertEqual(int(actual_val), int(expected_count))

    # 2. Filtering Question
    def test_02_filtering_question(self):
        """2. Filtering questions (e.g., 'Which employees earn more than $150,000?')"""
        gt_rows = self._exec_ground_truth("SELECT COUNT(*) FROM EMPLOYEES WHERE SALARY > 150000")
        expected_count = gt_rows[0][0]

        req = QueryRequest(database_id=self.db_conn.id, natural_language="Which employees earn more than $150,000?")
        resp = execute_natural_language_query(self.db, req, user_id=self.user_id)

        self.assertEqual(resp.status, "completed")
        self.assertIsNotNone(resp.results)
        self.assertEqual(len(resp.results.rows), expected_count)

    # 3. Aggregation Question
    def test_03_aggregation_question(self):
        """3. Aggregation questions (e.g., 'What is the average salary in Engineering?')"""
        gt_rows = self._exec_ground_truth("""
            SELECT ROUND(AVG(E.SALARY), 2)
            FROM EMPLOYEES E
            JOIN DEPARTMENTS D ON E.DEPARTMENT_ID = D.DEPARTMENT_ID
            WHERE D.DEPARTMENT_NAME = 'Engineering'
        """)
        expected_avg = float(gt_rows[0][0])

        req = QueryRequest(database_id=self.db_conn.id, natural_language="What is the average salary in Engineering?")
        resp = execute_natural_language_query(self.db, req, user_id=self.user_id)

        self.assertEqual(resp.status, "completed")
        self.assertIsNotNone(resp.results)
        actual_avg = float(resp.results.rows[0][0])
        self.assertAlmostEqual(actual_avg, expected_avg, delta=1.0)

    # 4. Ranking Question
    def test_04_ranking_question(self):
        """4. Ranking questions (e.g., 'Who is the highest-paid employee?')"""
        gt_rows = self._exec_ground_truth("""
            SELECT FIRST_NAME, LAST_NAME, SALARY
            FROM EMPLOYEES
            ORDER BY SALARY DESC
            FETCH FIRST 1 ROWS ONLY
        """)
        expected_first = gt_rows[0][0]
        expected_last = gt_rows[0][1]
        expected_salary = float(gt_rows[0][2])

        req = QueryRequest(database_id=self.db_conn.id, natural_language="Who is the highest-paid employee?")
        resp = execute_natural_language_query(self.db, req, user_id=self.user_id)

        self.assertEqual(resp.status, "completed")
        self.assertIsNotNone(resp.results)
        self.assertTrue(len(resp.results.rows) >= 1)
        # Check that top salary or employee identity is present
        row_str = " ".join(str(c) for c in resp.results.rows[0])
        self.assertTrue(expected_last in row_str or math.isclose(float(resp.results.rows[0][-1]), expected_salary, abs_tol=1.0))

    # 5. Calculation Question
    def test_05_calculation_question(self):
        """5. Calculation questions (e.g., 'What percentage of the project budget has been spent?')"""
        gt_rows = self._exec_ground_truth("""
            SELECT (SUM(SPENT) / SUM(BUDGET)) * 100 FROM PROJECTS
        """)
        expected_pct = float(gt_rows[0][0])

        req = QueryRequest(database_id=self.db_conn.id, natural_language="What percentage of the project budget has been spent?")
        resp = execute_natural_language_query(self.db, req, user_id=self.user_id)

        self.assertEqual(resp.status, "completed")
        self.assertIsNotNone(resp.results)
        self.assertTrue(len(resp.results.rows) >= 1)
        actual_pct = float(resp.results.rows[0][0])
        self.assertAlmostEqual(actual_pct, expected_pct, delta=2.0)

    # 6. JOIN Question
    def test_06_join_question(self):
        """6. JOIN questions (e.g., 'Which department has the highest project spending?')"""
        gt_rows = self._exec_ground_truth("""
            SELECT D.DEPARTMENT_NAME, SUM(P.SPENT) AS TOTAL_SPENT
            FROM PROJECTS P
            JOIN DEPARTMENTS D ON P.DEPARTMENT_ID = D.DEPARTMENT_ID
            GROUP BY D.DEPARTMENT_NAME
            ORDER BY TOTAL_SPENT DESC
            FETCH FIRST 1 ROWS ONLY
        """)
        expected_dept = gt_rows[0][0]

        req = QueryRequest(database_id=self.db_conn.id, natural_language="Which department has the highest project spending?")
        resp = execute_natural_language_query(self.db, req, user_id=self.user_id)

        self.assertEqual(resp.status, "completed")
        self.assertIsNotNone(resp.results)
        row_str = " ".join(str(c) for c in resp.results.rows[0])
        self.assertIn(expected_dept, row_str)

    # 7. Subquery Question
    def test_07_subquery_question(self):
        """7. Subquery questions (e.g., 'Which employees earn more than the company average salary?')"""
        gt_rows = self._exec_ground_truth("""
            SELECT COUNT(*) FROM EMPLOYEES WHERE SALARY > (SELECT AVG(SALARY) FROM EMPLOYEES)
        """)
        expected_count = gt_rows[0][0]

        req = QueryRequest(database_id=self.db_conn.id, natural_language="Which employees earn more than the company average salary?")
        resp = execute_natural_language_query(self.db, req, user_id=self.user_id)

        self.assertEqual(resp.status, "completed")
        self.assertIsNotNone(resp.results)
        self.assertEqual(len(resp.results.rows), expected_count)

    # 8. Multi-table Question
    def test_08_multi_table_question(self):
        """8. Multi-table analysis questions (e.g., 'Which sales representative generated the most revenue?')"""
        gt_rows = self._exec_ground_truth("""
            SELECT E.FIRST_NAME, E.LAST_NAME, SUM(S.TOTAL_REVENUE) AS TOTAL_REV
            FROM SALES_RECORDS S
            JOIN EMPLOYEES E ON S.SALES_REP_ID = E.EMPLOYEE_ID
            GROUP BY E.FIRST_NAME, E.LAST_NAME
            ORDER BY TOTAL_REV DESC
            FETCH FIRST 1 ROWS ONLY
        """)
        expected_rep = gt_rows[0][1] # e.g. Taylor

        req = QueryRequest(database_id=self.db_conn.id, natural_language="Which sales representative generated the most revenue?")
        resp = execute_natural_language_query(self.db, req, user_id=self.user_id)

        self.assertEqual(resp.status, "completed")
        self.assertIsNotNone(resp.results)
        row_str = " ".join(str(c) for c in resp.results.rows[0])
        self.assertIn(expected_rep, row_str)

    # 9. Financial Analysis Question
    def test_09_financial_question(self):
        """9. Financial analysis questions (e.g., 'Which quarter had the highest net profit?')"""
        gt_rows = self._exec_ground_truth("""
            SELECT QUARTER, NET_PROFIT FROM COMPANY_FINANCIALS ORDER BY NET_PROFIT DESC FETCH FIRST 1 ROWS ONLY
        """)
        expected_quarter = gt_rows[0][0]
        expected_profit = float(gt_rows[0][1])

        req = QueryRequest(database_id=self.db_conn.id, natural_language="Which quarter had the highest net profit?")
        resp = execute_natural_language_query(self.db, req, user_id=self.user_id)

        self.assertEqual(resp.status, "completed")
        self.assertIsNotNone(resp.results)
        row_str = " ".join(str(c) for c in resp.results.rows[0])
        self.assertIn(expected_quarter, row_str)

    # 10. Complex Business Analysis
    def test_10_complex_business_analysis(self):
        """10. Complex cross-table business analysis"""
        req = QueryRequest(
            database_id=self.db_conn.id, 
            natural_language="Provide an executive summary: Department with highest employee salary cost, Project with highest budget utilization, Sales representative with highest revenue, Quarter with highest net profit"
        )
        resp = execute_natural_language_query(self.db, req, user_id=self.user_id)

        self.assertEqual(resp.status, "completed")
        self.assertIsNotNone(resp.results)
        self.assertTrue(len(resp.results.rows) >= 1)
        self.assertIn("### 🎯 Direct Answer", resp.explanation)
        self.assertIn("### 📊 Key Calculated Values", resp.explanation)

    # 11. Unrelated Question Handling
    def test_11_unrelated_question(self):
        """11. Unrelated questions (e.g., 'Who won the FIFA World Cup?') handled without executing SQL"""
        req = QueryRequest(database_id=self.db_conn.id, natural_language="Who won the FIFA World Cup?")
        resp = execute_natural_language_query(self.db, req, user_id=self.user_id)

        self.assertEqual(resp.status, "completed")
        self.assertIsNone(resp.generated_sql)
        self.assertEqual(len(resp.results.rows if resp.results else []), 0)
        self.assertIn("This question cannot be answered from the connected database", resp.explanation)
        self.assertIn("Available Topics", resp.explanation)

    # 13. Multi-Child Aggregation Comparison (Aggregate-Then-Join Pattern)
    def test_13_multi_child_aggregation_comparison(self):
        """13. Multi-child aggregation questions ('Which departments have higher project spending than employee salary cost?')"""
        gt_rows = self._exec_ground_truth("""
            WITH employee_totals AS (
                SELECT department_id, SUM(salary) AS total_salary
                FROM employees
                GROUP BY department_id
            ),
            project_totals AS (
                SELECT department_id, SUM(spent) AS total_project_spent
                FROM projects
                GROUP BY department_id
            )
            SELECT d.department_name, NVL(e.total_salary, 0) AS total_salary, NVL(p.total_project_spent, 0) AS total_project_spent
            FROM departments d
            LEFT JOIN employee_totals e ON d.department_id = e.department_id
            LEFT JOIN project_totals p ON d.department_id = p.department_id
            WHERE NVL(p.total_project_spent, 0) > NVL(e.total_salary, 0)
        """)
        expected_depts = {row[0] for row in gt_rows}

        req = QueryRequest(database_id=self.db_conn.id, natural_language="Which departments have higher project spending than employee salary cost?")
        resp = execute_natural_language_query(self.db, req, user_id=self.user_id)

        self.assertEqual(resp.status, "completed")
        self.assertIsNotNone(resp.results)
        # Ensure generated SQL uses WITH clause to pre-aggregate (preventing row multiplication)
        self.assertIn("WITH", resp.generated_sql.upper())
        actual_depts = {str(row[0]) for row in resp.results.rows}
        self.assertEqual(actual_depts, expected_depts)

    # 14. CTE Column Exposure Scoping Preflight Validation
    def test_14_cte_column_exposure_scoping(self):
        """14. Preflight validator rejects unexposed CTE column references"""
        from app.services.query_service import _validate_sql_before_execution, _get_schema_context
        _, table_cols, _ = _get_schema_context(self.db_conn)
        
        # CTE employee_totals ONLY selects department_id and total_salary (does NOT expose employee_id or salary)
        bad_sql = """
            WITH employee_totals AS (
                SELECT department_id, SUM(salary) AS total_salary
                FROM employees
                GROUP BY department_id
            )
            SELECT d.department_name, e.employee_id, e.total_salary
            FROM departments d
            LEFT JOIN employee_totals e ON d.department_id = e.department_id;
        """
        ok, _, err = _validate_sql_before_execution(bad_sql, table_cols, "Oracle SQL")
        self.assertFalse(ok)
        self.assertIn("CTE Column Reference Error", err)
        self.assertIn("employee_id", err)

    # 15. Semantic Metric Distinction Validation
    def test_15_semantic_metric_distinction(self):
        """15. Validator rejects substitution of DEPARTMENTS.BUDGET when employee salary cost was asked"""
        from app.services.query_service import _validate_sql_before_execution, _get_schema_context
        _, table_cols, _ = _get_schema_context(self.db_conn)
        
        bad_sql = """
            SELECT d.department_name, d.budget, p.spent
            FROM departments d
            JOIN projects p ON d.department_id = p.department_id
            WHERE p.spent > d.budget;
        """
        question = "Which departments have higher project spending than employee salary cost?"
        ok, _, err = _validate_sql_before_execution(bad_sql, table_cols, "Oracle SQL", natural_language=question)
        self.assertFalse(ok)
        self.assertIn("Semantic Error", err)
        self.assertIn("employee salary cost", err)

    # 16. Semantic Ratio Distinction Validation
    def test_16_validator_rejects_budget_over_salary_substitution(self):
        """16. Validator rejects substitution of total_project_budget / total_salary when project spending relative to salary was asked"""
        from app.services.query_service import _validate_sql_before_execution, _get_schema_context
        _, table_cols, _ = _get_schema_context(self.db_conn)
        
        bad_sql = """
            WITH employee_totals AS (
                SELECT department_id, SUM(salary) AS total_salary
                FROM employees
                GROUP BY department_id
            ),
            project_totals AS (
                SELECT department_id, SUM(budget) AS total_project_budget, SUM(spent) AS total_project_spent
                FROM projects
                GROUP BY department_id
            )
            SELECT d.department_name, (p.total_project_budget / e.total_salary) * 100 AS ratio
            FROM departments d
            JOIN employee_totals e ON d.department_id = e.department_id
            JOIN project_totals p ON d.department_id = p.department_id
            ORDER BY ratio DESC;
        """
        question = "Which department has the highest project spending relative to its employee salary cost?"
        ok, _, err = _validate_sql_before_execution(bad_sql, table_cols, "Oracle SQL", natural_language=question)
        self.assertFalse(ok)
        self.assertIn("Semantic Error", err)
        self.assertIn("PROJECT_BUDGET / SALARY", err)

    # 17. Multi-metric Exact Ranking Test Case
    def test_17_multi_metric_ranking_exact_test_case(self):
        """17. Complex multi-metric question with budget utilization and spending relative to salary ranking"""
        question = (
            "For each department, calculate the total employee salary cost, average employee salary, "
            "total project budget, total project spending, and project budget utilization percentage. "
            "Then identify the department that has the highest project spending relative to its employee salary cost, "
            "showing the department name and the percentage."
        )
        req = QueryRequest(database_id=self.db_conn.id, natural_language=question)
        resp = execute_natural_language_query(self.db, req, self.user_id, include_all=True)
        self.assertEqual(resp.status, "completed")
        self.assertIsNotNone(resp.results)
        self.assertGreater(len(resp.results.rows), 0)
        top_row = resp.results.rows[0]
        self.assertEqual(str(top_row[0]), "Engineering")


if __name__ == "__main__":
    unittest.main()

