from dataclasses import dataclass, field
from datetime import date, time
from enum import Enum
from typing import Optional


class Priority(Enum):
    HIGH = 3
    MEDIUM = 2
    LOW = 1


class Recurrence(Enum):
    NONE = "none"
    DAILY = "daily"
    WEEKLY = "weekly"


@dataclass
class Task:
    title: str
    category: str
    duration_minutes: int
    priority: Priority = Priority.MEDIUM
    preferred_time: Optional[time] = None
    recurrence: Recurrence = Recurrence.NONE
    completed: bool = False

    def mark_complete(self) -> None:
        pass

    def is_due(self, on_date: date) -> bool:
        pass

    def next_occurrence(self) -> Optional["Task"]:
        pass

    def priority_score(self) -> int:
        pass


@dataclass
class Pet:
    name: str
    species: str
    breed: str = ""
    age: int = 0
    special_needs: str = ""
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        pass

    def remove_task(self, task: Task) -> None:
        pass

    def edit_task(self, task: Task, **changes) -> None:
        pass

    def get_tasks(self, status: Optional[str] = None) -> list[Task]:
        pass

    def describe(self) -> str:
        pass


@dataclass
class Owner:
    name: str
    available_minutes_per_day: int = 0
    preferences: dict = field(default_factory=dict)
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        pass

    def remove_pet(self, pet: Pet) -> None:
        pass

    def set_availability(self, minutes: int) -> None:
        pass

    def get_all_tasks(self) -> list[Task]:
        pass

    def create_plan(self, on_date: date) -> "DailyPlan":
        pass


@dataclass
class DailyPlan:
    date: date
    scheduled_items: list = field(default_factory=list)  # (task, start, end)
    skipped_tasks: list = field(default_factory=list)  # (task, reason)
    total_minutes: int = 0

    def add_item(self, task: Task, start: time) -> None:
        pass

    def total_duration(self) -> int:
        pass

    def get_explanation(self) -> str:
        pass

    def to_rows(self) -> list:
        pass


class Scheduler:
    def __init__(self, owner: Owner, constraints: Optional[dict] = None):
        self.owner = owner
        self.constraints = constraints or {}

    def generate_plan(self, on_date: date) -> DailyPlan:
        pass

    def sort_tasks(self, tasks: list[Task]) -> list[Task]:
        pass

    def fit_to_time_budget(self, tasks: list[Task]) -> list[Task]:
        pass

    def detect_conflicts(self, tasks: list[Task]) -> list[Task]:
        pass

    def explain(self, plan: DailyPlan) -> str:
        pass
