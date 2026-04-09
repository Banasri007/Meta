"""
FinOps Environment - Basic Classes for Cloud Optimization Program
"""

from typing import Dict, List, Literal, Optional, Union, Annotated
from pydantic import BaseModel, Field
from dataclasses import dataclass
import random
import os


# ────────────────────────────────────────────────────────────────────────────
# DATA MODELS
# ────────────────────────────────────────────────────────────────────────────

class CloudResource(BaseModel):
    """Represents a cloud asset and its utilization profile."""
    
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
    """Financial metrics for the environment."""
    
    daily_burn_rate: float = Field(..., ge=0.0)
    projected_monthly_bill: float = Field(..., ge=0.0)


class HealthStatus(BaseModel):
    """System health and performance metrics."""
    
    system_latency_ms: float = Field(..., ge=0.0)
    throttling_events: int = Field(0, ge=0)
    downtime_events: int = Field(0, ge=0)


class Observation(BaseModel):
    """Complete snapshot of the environment state."""
    
    inventory: List[CloudResource]
    cost_data: CostData
    health_status: HealthStatus
    status_message: str


class Reward(BaseModel):
    """Reward breakdown for an action."""
    
    total: float
    action_reward: float
    bill_change_reward: float


# ────────────────────────────────────────────────────────────────────────────
# ACTION MODELS
# ────────────────────────────────────────────────────────────────────────────

class ModifyInstanceAction(BaseModel):
    """Modify a compute instance to a different type."""
    
    action_type: Literal["modify_instance"] = "modify_instance"
    instance_id: str
    new_type: str


class DeleteResourceAction(BaseModel):
    """Delete a cloud resource."""
    
    action_type: Literal["delete_resource"] = "delete_resource"
    resource_id: str


class PurchaseSavingsPlanAction(BaseModel):
    """Purchase a savings plan for committed capacity."""
    
    action_type: Literal["purchase_savings_plan"] = "purchase_savings_plan"
    plan_type: Literal["compute", "database"]
    duration: Literal["1y", "3y"]


class TagResourceAction(BaseModel):
    """Add or update a tag on a resource."""
    
    action_type: Literal["tag_resource"] = "tag_resource"
    resource_id: str
    tag_key: str
    tag_value: str


# Union type for all possible actions
Action = Annotated[
    Union[
        ModifyInstanceAction,
        DeleteResourceAction,
        PurchaseSavingsPlanAction,
        TagResourceAction,
    ],
    Field(discriminator="action_type"),
]


# ────────────────────────────────────────────────────────────────────────────
# UTILITY CLASSES
# ────────────────────────────────────────────────────────────────────────────

@dataclass
class SavingsPlan:
    """Represents a purchased savings plan."""
    
    plan_type: str
    duration: str
    discount_rate: float
    coverage_ratio: float


class Config(BaseModel):
    """Configuration for FinOps environment."""
    
    max_steps: int = 35
    base_latency_ms: float = 80.0
    initial_inventory_size: int = 15
    seed: Optional[int] = None


# ────────────────────────────────────────────────────────────────────────────
# ENGINE CLASS
# ────────────────────────────────────────────────────────────────────────────

class FinOpsEngine:
    """Cloud resource optimization engine."""
    
    INSTANCE_CATALOG: Dict[str, Dict[str, float]] = {
        "m5.xlarge": {"monthly_cost": 150.0, "capacity": 1.0},
        "m5.large": {"monthly_cost": 90.0, "capacity": 0.65},
        "t3.medium": {"monthly_cost": 45.0, "capacity": 0.4},
        "t3.small": {"monthly_cost": 25.0, "capacity": 0.25},
        "t3.micro": {"monthly_cost": 10.0, "capacity": 0.1},
    }
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize the FinOps engine."""
        self.config = config or Config()
        seed_text = os.getenv("FINOPS_SEED")
        self.seed: Optional[int] = int(seed_text) if seed_text and seed_text.strip() else self.config.seed
        self.rng = random.Random(self.seed) if self.seed is not None else random.Random()
        
        self.resources: List[CloudResource] = []
        self.system_latency_ms: float = self.config.base_latency_ms
        self.initial_bill: float = 0.0
        self.base_latency_ms: float = self.config.base_latency_ms
        self.step_count: int = 0
        self.max_steps: int = self.config.max_steps
        self.throttling_events: int = 0
        self.downtime_events: int = 0
        self.critical_failures: int = 0
    
    def reset(self) -> Observation:
        """Reset the environment to initial state."""
        self.resources = self._generate_resources()
        self.system_latency_ms = self.base_latency_ms
        self.step_count = 0
        self.throttling_events = 0
        self.downtime_events = 0
        self.critical_failures = 0
        self.initial_bill = sum(r.monthly_cost for r in self.resources)
        return self.get_observation("Environment reset.")
    
    def _generate_resources(self) -> List[CloudResource]:
        """Generate initial inventory of cloud resources."""
        resources = []
        resource_types = [
            ("compute", ["m5.xlarge", "t3.medium", "t3.small"]),
            ("storage", ["gp3", "io2", "s3-standard"]),
            ("database", ["db.r6g.large", "db.m6i.xlarge"]),
        ]
        
        for _ in range(self.config.initial_inventory_size):
            category, types = resource_types[self.rng.randint(0, 2)]
            resource_type = types[self.rng.randint(0, len(types) - 1)]
            
            monthly_cost = self.INSTANCE_CATALOG.get(resource_type, {}).get("monthly_cost", 50.0)
            
            resource = CloudResource(
                id=f"res-{self.rng.randint(10000, 99999)}",
                category=category,
                resource_type=resource_type,
                monthly_cost=monthly_cost,
                cpu_usage_pct_30d=self.rng.uniform(5.0, 95.0),
                memory_usage_pct_30d=self.rng.uniform(5.0, 95.0),
                network_io_mbps_30d=self.rng.uniform(1.0, 100.0),
                is_attached=self.rng.choice([True, False]),
                is_production=self.rng.choice([True, False, False]),
                is_legacy=self.rng.choice([True, False, False, False]),
                tags={"env": self.rng.choice(["prod", "staging", "test", "dev"])},
            )
            resources.append(resource)
        
        return resources
    
    def get_observation(self, status_msg: str = "Ready") -> Observation:
        """Get current environment observation."""
        total_bill = sum(r.monthly_cost for r in self.resources)
        
        return Observation(
            inventory=self.resources,
            cost_data=CostData(
                daily_burn_rate=total_bill / 30.0,
                projected_monthly_bill=total_bill,
            ),
            health_status=HealthStatus(
                system_latency_ms=self.system_latency_ms,
                throttling_events=self.throttling_events,
                downtime_events=self.downtime_events,
            ),
            status_message=status_msg,
        )
    
    def step(self, action: Action) -> tuple[Observation, Reward, bool, Dict]:
        """Execute an action and return observation, reward, done flag, and info."""
        self.step_count += 1
        done = self.step_count >= self.max_steps
        
        action_reward = 0.0
        bill_change_reward = 0.0
        info = {"action": action.action_type}
        
        old_bill = sum(r.monthly_cost for r in self.resources)
        
        # Handle different action types
        if isinstance(action, DeleteResourceAction):
            self.resources = [r for r in self.resources if r.id != action.resource_id]
            action_reward = 10.0
        
        elif isinstance(action, ModifyInstanceAction):
            for r in self.resources:
                if r.id == action.instance_id and r.category == "compute":
                    new_cost = self.INSTANCE_CATALOG.get(action.new_type, {}).get("monthly_cost", r.monthly_cost)
                    r.resource_type = action.new_type
                    r.monthly_cost = new_cost
                    if new_cost < r.monthly_cost:
                        action_reward = 5.0
                    break
        
        elif isinstance(action, PurchaseSavingsPlanAction):
            action_reward = 3.0
        
        elif isinstance(action, TagResourceAction):
            for r in self.resources:
                if r.id == action.resource_id:
                    r.tags[action.tag_key] = action.tag_value
                    action_reward = 1.0
                    break
        
        new_bill = sum(r.monthly_cost for r in self.resources)
        bill_change_reward = max(0, old_bill - new_bill) / 10.0
        
        total_reward = float(action_reward + bill_change_reward)
        reward = Reward(
            total=total_reward,
            action_reward=action_reward,
            bill_change_reward=bill_change_reward,
        )
        
        obs = self.get_observation(f"Step {self.step_count} completed")
        
        return obs, reward, done, info


# ────────────────────────────────────────────────────────────────────────────
# UTILITY FUNCTIONS
# ────────────────────────────────────────────────────────────────────────────

def list_tasks() -> List[Dict[str, str]]:
    """List all available tasks."""
    return [
        {"id": "cleanup_unattached", "name": "Clean Up Unattached Resources", "difficulty": "easy"},
        {"id": "rightsize_compute", "name": "Right-Size Compute Instances", "difficulty": "medium"},
        {"id": "fleet_strategy", "name": "Fleet Optimization Strategy", "difficulty": "hard"},
    ]


def get_task_score(engine: FinOpsEngine, task_id: str) -> float:
    """Calculate score for a task."""
    if task_id not in ["cleanup_unattached", "rightsize_compute", "fleet_strategy"]:
        raise KeyError(f"Unknown task: {task_id}")
    
    obs = engine.get_observation()
    total_resources = len(obs.inventory)
    
    if task_id == "cleanup_unattached":
        unattached = sum(1 for r in obs.inventory if not r.is_attached)
        return min(1.0, unattached / max(1, total_resources))
    
    elif task_id == "rightsize_compute":
        compute = [r for r in obs.inventory if r.category == "compute"]
        rightsized = sum(1 for r in compute if r.resource_type in ["t3.small", "t3.micro"])
        return min(1.0, rightsized / max(1, len(compute)))
    
    else:  # fleet_strategy
        cost_before = engine.initial_bill
        cost_after = obs.cost_data.projected_monthly_bill
        cost_reduction = (cost_before - cost_after) / cost_before if cost_before > 0 else 0
        return min(1.0, cost_reduction)
