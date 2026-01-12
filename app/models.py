from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class MethodType(str, Enum):
    workflow = "workflow"
    task = "task"
    experiment = "experiment"


class ImpactType(str, Enum):
    cost_savings = "cost_savings"
    time_savings = "time_savings"
    quality = "quality"
    new_capability = "new_capability"


class Frequency(str, Enum):
    one_time = "one_time"
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"
    quarterly = "quarterly"


# Config Models
class FunctionBase(BaseModel):
    name: str


class FunctionCreate(FunctionBase):
    pass


class Function(FunctionBase):
    id: int
    active: bool = True
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TeamBase(BaseModel):
    function_id: int
    name: str


class TeamCreate(TeamBase):
    pass


class Team(TeamBase):
    id: int
    active: bool = True
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TeamWithFunction(Team):
    function_name: Optional[str] = None


class ToolBase(BaseModel):
    name: str


class ToolCreate(ToolBase):
    pass


class Tool(ToolBase):
    id: int
    active: bool = True
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CapabilityBase(BaseModel):
    name: str


class CapabilityCreate(CapabilityBase):
    pass


class Capability(CapabilityBase):
    id: int
    active: bool = True
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Impact Models
class Impact(BaseModel):
    type: Optional[ImpactType] = None
    value: Optional[float] = None
    frequency: Optional[Frequency] = None
    time_unit: Optional[str] = None
    annual_value: Optional[float] = None
    description: Optional[str] = None


# Response Models
class ResponseBase(BaseModel):
    function_id: int
    team_id: Optional[int] = None
    method_type: MethodType
    capability_id: int
    capability_other: Optional[str] = None
    description: str
    tools_used: str  # JSON array of tool IDs
    other_tools: Optional[str] = None  # JSON for custom tool names

    # Impact 1 (Primary)
    impact1_type: Optional[ImpactType] = None
    impact1_value: Optional[float] = None
    impact1_frequency: Optional[Frequency] = None
    impact1_time_unit: Optional[str] = None
    impact1_annual_value: Optional[float] = None
    impact1_description: Optional[str] = None

    # Impact 2
    impact2_type: Optional[ImpactType] = None
    impact2_value: Optional[float] = None
    impact2_frequency: Optional[Frequency] = None
    impact2_time_unit: Optional[str] = None
    impact2_annual_value: Optional[float] = None
    impact2_description: Optional[str] = None

    # Impact 3
    impact3_type: Optional[ImpactType] = None
    impact3_value: Optional[float] = None
    impact3_frequency: Optional[Frequency] = None
    impact3_time_unit: Optional[str] = None
    impact3_annual_value: Optional[float] = None
    impact3_description: Optional[str] = None

    # Impact 4
    impact4_type: Optional[ImpactType] = None
    impact4_value: Optional[float] = None
    impact4_frequency: Optional[Frequency] = None
    impact4_time_unit: Optional[str] = None
    impact4_annual_value: Optional[float] = None
    impact4_description: Optional[str] = None


class ResponseCreate(ResponseBase):
    submitted_by: Optional[str] = None


class ResponseUpdate(BaseModel):
    function_id: Optional[int] = None
    team_id: Optional[int] = None  # Can be null for functions without teams
    method_type: Optional[MethodType] = None
    capability_id: Optional[int] = None
    capability_other: Optional[str] = None
    description: Optional[str] = None
    tools_used: Optional[str] = None
    other_tools: Optional[str] = None

    impact1_type: Optional[ImpactType] = None
    impact1_value: Optional[float] = None
    impact1_frequency: Optional[Frequency] = None
    impact1_time_unit: Optional[str] = None
    impact1_annual_value: Optional[float] = None
    impact1_description: Optional[str] = None

    impact2_type: Optional[ImpactType] = None
    impact2_value: Optional[float] = None
    impact2_frequency: Optional[Frequency] = None
    impact2_time_unit: Optional[str] = None
    impact2_annual_value: Optional[float] = None
    impact2_description: Optional[str] = None

    impact3_type: Optional[ImpactType] = None
    impact3_value: Optional[float] = None
    impact3_frequency: Optional[Frequency] = None
    impact3_time_unit: Optional[str] = None
    impact3_annual_value: Optional[float] = None
    impact3_description: Optional[str] = None

    impact4_type: Optional[ImpactType] = None
    impact4_value: Optional[float] = None
    impact4_frequency: Optional[Frequency] = None
    impact4_time_unit: Optional[str] = None
    impact4_annual_value: Optional[float] = None
    impact4_description: Optional[str] = None


class Response(ResponseBase):
    id: int
    submitted_by: Optional[str] = None
    submitted_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ResponseWithDetails(Response):
    function_name: Optional[str] = None
    team_name: Optional[str] = None
    capability_name: Optional[str] = None


# Dashboard Models
class DashboardSummary(BaseModel):
    total_methods: int = 0
    total_workflows: int = 0
    total_tasks: int = 0
    total_experiments: int = 0
    total_cost_savings: float = 0.0
    total_time_savings: float = 0.0
    quality_count: int = 0
    new_capability_count: int = 0


class FunctionBreakdown(BaseModel):
    function_id: int
    function_name: str
    method_count: int = 0
    workflow_count: int = 0
    task_count: int = 0
    experiment_count: int = 0
    cost_savings: float = 0.0
    time_savings: float = 0.0
    quality_count: int = 0
    new_capability_count: int = 0


class TeamBreakdown(BaseModel):
    team_id: int
    team_name: str
    function_id: int
    function_name: str
    method_count: int = 0
    cost_savings: float = 0.0
    time_savings: float = 0.0


# Config Response (all config data)
class ConfigData(BaseModel):
    functions: List[Function] = []
    teams: List[TeamWithFunction] = []
    tools: List[Tool] = []
    capabilities: List[Capability] = []
