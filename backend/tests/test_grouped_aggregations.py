"""
Tests for Group Aggregations ('In Each', 'Per', 'By', 'For Every') vs Global Extremum.
Ensures universal, non-hardcoded rules for multi-group breakdowns and accurate answer summarization.
"""

import unittest
from unittest.mock import patch, MagicMock
from app.services.llm_service import LLMService


class TestGroupedAggregationsPrinciples(unittest.TestCase):
    def setUp(self):
        self.llm = LLMService()

    def test_schema_prompt_contains_group_aggregation_rules(self):
        """Verify _build_schema_prompt includes explicit multi-group breakdown and global extremum instructions."""
        schema = "Table: employees [(id INT, department VARCHAR, salary NUMERIC, name VARCHAR)]"
        prompt = self.llm._build_schema_prompt(schema, "PostgreSQL")

        # Must instruct GROUP BY for in each / per / by / for every
        self.assertIn("GROUP AGGREGATIONS ('IN EACH', 'PER', 'FOR EVERY', 'BY') VS GLOBAL EXTREMUM", prompt)
        self.assertIn("in each <dimension>", prompt)
        self.assertIn("NEVER apply `LIMIT 1`", prompt)
        self.assertIn("ROW_NUMBER() OVER (PARTITION BY", prompt)
        self.assertIn("NULLIF(denominator, 0)", prompt)
        self.assertIn("COUNT(DISTINCT column)", prompt)

    def test_fix_sql_prompt_contains_group_aggregation_instruction(self):
        """Verify fix_sql prompt preserves group breakdowns."""
        schema = "Table: sales [(id INT, region VARCHAR, amount NUMERIC)]"
        with patch.object(self.llm, "_call_vllm", return_value="```sql\nSELECT region, SUM(amount) FROM sales GROUP BY region;\n```"):
            sql, explanation, tokens = self.llm.fix_sql(
                natural_language="total sales in each region",
                sql="SELECT region, amount FROM sales LIMIT 1;",
                error="Invalid query",
                schema_context=schema,
                connection_type="postgresql",
            )
            self.assertIn("GROUP BY", sql)

    def test_synthesize_data_summary_multi_group_instructions(self):
        """Verify synthesize_data_summary prompt instructs listing all returned groups without single-entity collapsing."""
        columns = ["department", "highest_salary"]
        rows = [["Engineering", 168000], ["Sales", 145000], ["Marketing", 120000]]
        
        captured_messages = []
        def mock_call_llm(messages, temperature=0.1, max_tokens=700):
            captured_messages.extend(messages)
            return "### 🎯 Direct Answer\n- Engineering: $168,000.00\n- Sales: $145,000.00\n- Marketing: $120,000.00"

        with patch.object(self.llm, "_call_llm", side_effect=mock_call_llm):
            summary = self.llm.synthesize_data_summary(
                natural_language="give me the highest salary in each department",
                sql="SELECT department, MAX(salary) AS highest_salary FROM employees GROUP BY department;",
                columns=columns,
                rows=rows,
            )
            self.assertIn("Engineering", summary)
            self.assertIn("Sales", summary)
            self.assertIn("Marketing", summary)

            # Check that system prompt in call has multi-group instructions
            system_prompt = captured_messages[0]["content"]
            self.assertIn("MULTI-GROUP VS SINGLE-ENTITY HANDLING", system_prompt)
            self.assertIn("NEVER collapse a multi-group result set into only the single top row", system_prompt)


if __name__ == "__main__":
    unittest.main()
