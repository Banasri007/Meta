from typing import Annotated, Dict, List, Literal, Union

from pydantic import BaseModel, Field


class CloudResource(BaseModel):
    """Represents a cloud asset and its recent utilization profile."""

    id: str = Field(..., description="Unique identifier for the resource")
    category: Literal["compute", "storage", "database"]
    resource_type: str = Field(..., description="SKU, e.g., m5.xlarge, gp3, db.r6g.large")
    monthly_cost: float = Field(..., ge=0.0, description="USD cost per month")
    cpu_usage_pct_30d: float = Field(0.0, ge=0.0, le=100.0)
    memory_usage_pct_30d: float = Field(0.0, ge=0.0, le=100.0)
    network_io_mbps_30d: float = Field(0.0, ge=0.0)
    is_attached: bool = True
    is_production: bool = False
    is_legacy: bool = False
    tags: Dict[str, str] = Field(default_factory=dict)


class CostData(BaseModel):
    daily_burn_rate: float = Field(..., ge=0.0)
    projected_monthly_bill: float = Field(..., ge=0.0)


class HealthStatus(BaseModel):
    system_latency_ms: float = Field(..., ge=0.0)
    throttling_events: int = Field(0, ge=0)
    downtime_events: int = Field(0, ge=0)


class Observation(BaseModel):
    inventory: List[CloudResource]
    cost_data: CostData
    health_status: HealthStatus
    status_message: str


class Reward(BaseModel):
    total: float
    action_reward: float
    bill_change_reward: float


class ModifyInstanceAction(BaseModel):
    action_type: Literal["modify_instance"] = "modify_instance"
    instance_id: str
    new_type: str


class DeleteResourceAction(BaseModel):
    action_type: Literal["delete_resource"] = "delete_resource"
    resource_id: str


class PurchaseSavingsPlanAction(BaseModel):
    action_type: Literal["purchase_savings_plan"] = "purchase_savings_plan"
    plan_type: Literal["compute", "database"]
    duration: Literal["1y", "3y"]


class TagResourceAction(BaseModel):
    action_type: Literal["tag_resource"] = "tag_resource"
    resource_id: str
    tag_key: str
    tag_value: str


Action = Annotated[
    Union[
        ModifyInstanceAction,
        DeleteResourceAction,
        PurchaseSavingsPlanAction,
        TagResourceAction,
    ],
    Field(discriminator="action_type"),
]