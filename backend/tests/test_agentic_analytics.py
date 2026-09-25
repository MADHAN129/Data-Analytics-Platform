"""
Test suite for Agentic Analytics Workflow:
- Intent analysis and clarification for broad questions
- Executable SQL generation and execution
- Structured clarification options and quick follow-up suggestions
- Dynamic schema exploration and system catalog query support
- Multi-tenant conversation message scoping
"""

import pytest
from unittest.mock import MagicMock, patch
from app.services.llm_service import llm_service
from app.schemas.conversation import (
    ClarificationOption,
    ConversationMessageResponse,
    SendMessageRequest,
)
from app.services.conversation_service import (
    send_message,
    get_messages,
    create_conversation,
)
from app.services.query_service import (
    _validate_sql_before_execution,
    _analyze_intent_and_resolve,
)
from app.models.conversation import Conversation, ConversationMessage
from app.models.connection import DatabaseConnection


def test_table_listing_intent_exploration():
    """Test that asking 'what are the tables available in the DB' returns a structured tables overview with exploration cards."""
    schema_context = (
        "Table: dishes [id (INTEGER), name (VARCHAR), price (NUMERIC), category_id (INTEGER)]\n"
        "Table: orders [id (INTEGER), order_date (TIMESTAMP), total (NUMERIC)]\n"
        "Table: menu_categories [id (INTEGER), category_name (VARCHAR)]"
    )
    res = llm_service.analyze_intent_and_clarify("what are the tables available in the DB", schema_context)
    assert res["status"] == "clarify"
    assert "dishes" in res["message"]
    assert "orders" in res["message"]
    assert len(res["options"]) == 3
    assert any("Explore Dishes" in opt["label"] for opt in res["options"])
    assert any("Explore Orders" in opt["label"] for opt in res["options"])


def test_sql_validation_system_catalogs():
    """Test that standard system catalog queries pass preflight validation across dialects."""
    table_cols = {
        "DISHES": {"ID", "NAME", "PRICE"},
        "ORDERS": {"ID", "ORDER_DATE", "TOTAL"}
    }

    # 1. MySQL information_schema table listing
    mysql_sql = "SELECT table_name FROM information_schema.tables WHERE table_schema = DATABASE();"
    is_valid, sanitized, err = _validate_sql_before_execution(mysql_sql, table_cols, "MySQL")
    assert is_valid is True
    assert err is None

    # 2. MySQL SHOW TABLES
    show_sql = "SHOW TABLES;"
    is_valid, sanitized, err = _validate_sql_before_execution(show_sql, table_cols, "MySQL")
    assert is_valid is True
    assert err is None

    # 3. PostgreSQL information_schema table listing
    pg_sql = "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE';"
    is_valid, sanitized, err = _validate_sql_before_execution(pg_sql, table_cols, "PostgreSQL")
    assert is_valid is True
    assert err is None

    # 4. Oracle user_tables query
    ora_sql = "SELECT table_name FROM user_tables;"
    is_valid, sanitized, err = _validate_sql_before_execution(ora_sql, table_cols, "Oracle SQL")
    assert is_valid is True
    assert err is None

    # 5. SQLite sqlite_master query
    sqlite_sql = "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%';"
    is_valid, sanitized, err = _validate_sql_before_execution(sqlite_sql, table_cols, "SQLite")
    assert is_valid is True
    assert err is None


def test_sql_validation_custom_database_tables():
    """Test that custom database table names are dynamically displayed in validation error messages without being blank."""
    table_cols = {
        "RESTAURANTS": {"ID", "NAME", "CITY"},
        "MENU_ITEMS": {"ITEM_ID", "ITEM_NAME", "PRICE"}
    }
    # Query referencing a non-existent table
    invalid_sql = "SELECT * FROM NON_EXISTENT_TABLE;"
    is_valid, sanitized, err = _validate_sql_before_execution(invalid_sql, table_cols, "MySQL")
    assert is_valid is False
    assert "Available tables are: MENU_ITEMS, RESTAURANTS" in err


def test_intent_analysis_broad_sales_query():
    """Test that a broad sales query returns clarify status with rich option cards."""
    schema_context = "Table: sales [id (INTEGER), order_date (TIMESTAMP), total_amount (NUMERIC), category (VARCHAR)]"
    res = llm_service.analyze_intent_and_clarify("what is the sales", schema_context)
    assert res["status"] == "clarify"
    assert "sales" in res["message"].lower()
    assert len(res["options"]) >= 3
    assert any("Today" in opt["label"] for opt in res["options"])
    assert any("Monthly" in opt["label"] for opt in res["options"])


def test_intent_analysis_specific_query():
    """Test that a specific and targeted query proceeds directly to execution without unnecessary clarification."""
    schema_context = "Table: sales [id (INTEGER), order_date (TIMESTAMP), total_amount (NUMERIC)]"
    res = llm_service.analyze_intent_and_clarify("show total sales revenue for today", schema_context)
    assert res["status"] == "direct"


def test_intent_analysis_unrelated_query():
    """Test that an unrelated query provides helpful guidance with available tables."""
    schema_context = "Table: employees [id (INTEGER), first_name (VARCHAR), salary (NUMERIC)]"
    res = llm_service.analyze_intent_and_clarify("what is the weather", schema_context)
    assert res["status"] == "unrelated"
    assert "employees" in res["message"].lower()
    assert len(res["options"]) >= 1


def test_follow_up_suggestions_generation():
    """Test generating insightful follow-up suggestion pills based on executed query."""
    suggestions = llm_service.generate_follow_up_suggestions(
        natural_language="Show total sales today",
        sql="SELECT SUM(total_amount) FROM sales WHERE order_date = CURRENT_DATE",
        columns=["total_amount", "order_date"],
        rows=[[15420.50, "2026-09-25"]]
    )
    assert len(suggestions) > 0
    assert len(suggestions) <= 4
    assert any("week" in s.lower() or "month" in s.lower() or "category" in s.lower() for s in suggestions)


def test_conversation_clarification_message_schema():
    """Verify ConversationMessageResponse serializes clarification_options and quick_options correctly."""
    options = [
        ClarificationOption(
            id="opt_1",
            label="📅 Today's Sales",
            prompt="Show total sales for today",
            description="Today's revenue summary",
            icon="📅"
        )
    ]
    msg = ConversationMessageResponse(
        id=101,
        conversation_id=1,
        role="assistant",
        content="Please choose an option to view sales data:",
        clarification_options=options,
        quick_options=["Show monthly summary", "Top selling items"],
        created_at="2026-09-25T12:00:00Z"
    )
    data = msg.model_dump()
    assert data["role"] == "assistant"
    assert len(data["clarification_options"]) == 1
    assert data["clarification_options"][0]["label"] == "📅 Today's Sales"
    assert data["clarification_options"][0]["icon"] == "📅"
    assert len(data["quick_options"]) == 2


def test_send_message_broad_intent_clarification():
    """Test that send_message produces clarification message with options when user asks broad question."""
    mock_db = MagicMock()
    mock_conv = MagicMock()
    mock_conv.id = 1
    mock_conv.user_id = 10
    mock_conv.company_id = 1
    mock_conv.database_id = 2
    mock_conv.context = {}
    mock_conv.messages = []
    mock_conv.message_count = 0

    mock_db.query.return_value.filter.return_value.first.return_value = mock_conv

    def mock_refresh(obj):
        if not getattr(obj, "id", None):
            obj.id = 102
        if not getattr(obj, "created_at", None):
            from datetime import datetime, timezone
            obj.created_at = datetime.now(timezone.utc)

    mock_db.refresh.side_effect = mock_refresh
    
    # Mock connector and schema
    mock_table = MagicMock()
    mock_table.name = "sales"
    col1 = MagicMock()
    col1.name = "id"
    col1.data_type = "INTEGER"
    col2 = MagicMock()
    col2.name = "created_at"
    col2.data_type = "TIMESTAMP"
    col3 = MagicMock()
    col3.name = "amount"
    col3.data_type = "NUMERIC"
    mock_table.columns = [col1, col2, col3]

    mock_schema = MagicMock()
    mock_schema.tables = [mock_table]

    mock_connector = MagicMock()
    mock_connector.get_schema.return_value = mock_schema
    
    mock_clarification = {
        "status": "clarify",
        "message": "I found the sales table. How would you like to view it?",
        "options": [
            {
                "id": "1",
                "label": "📅 Today's Sales",
                "prompt": "Show today's sales",
                "description": "Daily breakdown",
                "icon": "📅"
            }
        ],
    }

    with patch("app.services.conversation_service.get_connector", return_value=mock_connector), \
         patch.object(llm_service, "analyze_intent_and_clarify", return_value=mock_clarification), \
         patch("app.services.conversation_service.user_has_permission_by_id", return_value=True):
        
        req = SendMessageRequest(content="what is the sales")
        resp = send_message(
            db=mock_db,
            conversation_id=1,
            data=req,
            user_id=10,
        )
        
        assert resp.role == "assistant"
        assert "sales" in resp.content.lower()
        assert resp.clarification_options is not None
        assert len(resp.clarification_options) == 1
        assert "Today" in resp.clarification_options[0].label


def test_time_period_validation_quarter_without_year_fails():
    """Test that grouping by quarter alone on tables with separate year and quarter columns fails with Time Period Validation Error."""
    table_cols = {
        "COMPANY_FINANCIALS": {
            "FINANCIAL_ID", "FISCAL_YEAR", "QUARTER", "REVENUE",
            "OPERATING_EXPENSES", "NET_PROFIT", "PROFIT_MARGIN_PCT"
        }
    }
    
    # Grouping by quarter alone combines 2024 Q2 and 2025 Q2 -> Must fail
    invalid_sql = "SELECT quarter, SUM(revenue) FROM company_financials GROUP BY quarter;"
    is_valid, sanitized, err = _validate_sql_before_execution(invalid_sql, table_cols, "PostgreSQL")
    assert is_valid is False
    assert "Time Period Validation Error" in err
    assert "FISCAL_YEAR" in err
    assert "QUARTER" in err
    assert "2024 Q2 and 2025 Q2" in err


def test_time_period_validation_quarter_with_year_passes():
    """Test that grouping by both fiscal_year and quarter passes validation."""
    table_cols = {
        "COMPANY_FINANCIALS": {
            "FINANCIAL_ID", "FISCAL_YEAR", "QUARTER", "REVENUE",
            "OPERATING_EXPENSES", "NET_PROFIT", "PROFIT_MARGIN_PCT"
        }
    }
    
    valid_sql = "SELECT fiscal_year, quarter, SUM(revenue) AS total_rev FROM company_financials GROUP BY fiscal_year, quarter ORDER BY fiscal_year, quarter;"
    is_valid, sanitized, err = _validate_sql_before_execution(valid_sql, table_cols, "PostgreSQL")
    assert is_valid is True
    assert err is None


def test_time_period_validation_ranking_single_period_passes():
    """Test that ranking complete period records with year and quarter passes validation."""
    table_cols = {
        "COMPANY_FINANCIALS": {
            "FINANCIAL_ID", "FISCAL_YEAR", "QUARTER", "REVENUE",
            "OPERATING_EXPENSES", "NET_PROFIT", "PROFIT_MARGIN_PCT"
        }
    }
    
    # Highest revenue single period query
    valid_sql = (
        "SELECT fiscal_year, quarter, revenue, operating_expenses, net_profit, profit_margin_pct "
        "FROM company_financials "
        "ORDER BY revenue DESC "
        "FETCH FIRST 1 ROWS ONLY;"
    )
    is_valid, sanitized, err = _validate_sql_before_execution(valid_sql, table_cols, "Oracle SQL")
    assert is_valid is True
    assert err is None


def test_time_period_validation_aggregate_quarter_without_year_fails():
    """Test that aggregating metrics over quarter without including year fails validation."""
    table_cols = {
        "COMPANY_FINANCIALS": {
            "FINANCIAL_ID", "FISCAL_YEAR", "QUARTER", "REVENUE",
            "OPERATING_EXPENSES", "NET_PROFIT", "PROFIT_MARGIN_PCT"
        }
    }
    
    # Query referencing quarter with SUM() without fiscal_year
    invalid_sql = "SELECT quarter, SUM(revenue) FROM company_financials WHERE quarter = 'Q2';"
    is_valid, sanitized, err = _validate_sql_before_execution(invalid_sql, table_cols, "PostgreSQL")
    assert is_valid is False
    assert "Time Period Validation Error" in err


def test_window_and_analytic_functions_not_treated_as_columns():
    """Test that DENSE_RANK(), ROW_NUMBER(), RANK(), OVER(), and query aliases like RN are never treated as columns."""
    table_cols = {
        "COMPANY_FINANCIALS": {
            "FINANCIAL_ID", "FISCAL_YEAR", "QUARTER", "REVENUE",
            "OPERATING_EXPENSES", "NET_PROFIT", "PROFIT_MARGIN_PCT"
        }
    }
    
    # Complex Oracle subquery with DENSE_RANK() OVER (ORDER BY REVENUE DESC) AS RN
    oracle_sql = """
    SELECT
        FISCAL_YEAR,
        QUARTER,
        REVENUE,
        OPERATING_EXPENSES,
        NET_PROFIT,
        PROFIT_MARGIN_PCT
    FROM (
        SELECT
            FISCAL_YEAR,
            QUARTER,
            REVENUE,
            OPERATING_EXPENSES,
            NET_PROFIT,
            PROFIT_MARGIN_PCT,
            DENSE_RANK() OVER (ORDER BY REVENUE DESC) AS RN
        FROM COMPANY_FINANCIALS
    )
    WHERE RN = 1;
    """
    is_valid, sanitized, err = _validate_sql_before_execution(oracle_sql, table_cols, "Oracle SQL")
    assert is_valid is True
    assert err is None


def test_functions_and_constructs_whitelist():
    """Test that SQL functions (NVL, COALESCE, NULLIF, ROUND, TO_CHAR, CAST) pass validation."""
    table_cols = {
        "COMPANY_FINANCIALS": {
            "FINANCIAL_ID", "FISCAL_YEAR", "QUARTER", "REVENUE",
            "OPERATING_EXPENSES", "NET_PROFIT", "PROFIT_MARGIN_PCT"
        }
    }
    
    sql = """
    SELECT
        FISCAL_YEAR,
        QUARTER,
        ROUND(NVL(REVENUE, 0), 2) AS FORMATTED_REV,
        COALESCE(NET_PROFIT, 0) AS SAFE_PROFIT,
        TO_CHAR(FISCAL_YEAR) AS FY_STR
    FROM COMPANY_FINANCIALS;
    """
    is_valid, sanitized, err = _validate_sql_before_execution(sql, table_cols, "Oracle SQL")
    assert is_valid is True
    assert err is None


def test_genuinely_nonexistent_column_still_rejected():
    """Test that actual non-existent columns (e.g. COMPANY_NAME, UNKNOWN_COL) are properly caught and rejected."""
    table_cols = {
        "COMPANY_FINANCIALS": {
            "FINANCIAL_ID", "FISCAL_YEAR", "QUARTER", "REVENUE",
            "OPERATING_EXPENSES", "NET_PROFIT", "PROFIT_MARGIN_PCT"
        }
    }
    
    # COMPANY_NAME does not exist in COMPANY_FINANCIALS
    bad_sql = "SELECT COMPANY_NAME, REVENUE FROM COMPANY_FINANCIALS;"
    is_valid, sanitized, err = _validate_sql_before_execution(bad_sql, table_cols, "Oracle SQL")
    assert is_valid is False
    assert "Invalid column 'COMPANY_NAME'" in err


