from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    database_id: int
    natural_language: str = Field(..., min_length=1, max_length=5000)
    conversation_id: Optional[int] = None
    options: Optional[dict] = None


class SQLExecutionRequest(BaseModel):
    database_id: int
    sql: str = Field(..., min_length=1, max_length=50000)
    timeout_seconds: int = Field(30, ge=5, le=300)


class FollowUpRequest(BaseModel):
    natural_language: str = Field(..., min_length=1, max_length=5000)


class VisualizationSuggestion(BaseModel):
    type: str = Field(..., pattern=r"^(bar_chart|line_chart|pie_chart|table|kpi|scatter_plot|area_chart|heatmap|histogram)$")
    title: Optional[str] = None
    config: Optional[dict] = None


class QueryResult(BaseModel):
    columns: list[str] = []
    rows: list[list] = []
    row_count: int = 0
    execution_time_ms: Optional[int] = None


class QueryResponse(BaseModel):
    id: int
    status: str
    natural_language: str
    generated_sql: Optional[str] = None
    explanation: Optional[str] = None
    results: Optional[QueryResult] = None
    suggested_visualizations: list[VisualizationSuggestion] = []
    tokens_used: Optional[int] = None
    conversation_id: Optional[int] = None
    parent_query_id: Optional[int] = None
    error_message: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class QueryListResponse(BaseModel):
    queries: list[QueryResponse]
    total: int
    page: int = 1
    per_page: int = 20
    pages: int = 1


class ExplainResponse(BaseModel):
    explanation: str
    generated_sql: str


class OptimizeSuggestion(BaseModel):
    type: str
    description: str
    impact: str = Field(..., pattern=r"^(low|medium|high)$")


class OptimizeResponse(BaseModel):
    suggestions: list[OptimizeSuggestion]


class VisualizeResponse(BaseModel):
    visualizations: list[VisualizationSuggestion]
