from dataclasses import dataclass, field
from datetime import date, time
from enum import Enum
from typing import Optional
from uuid import uuid4


def _new_id() -> str:
    return uuid4().hex


class Priority(Enum):
    HIGH = 3
    MEDIUM = 2
    LOW = 1


class Recurrence(Enum):
    NONE = "none"
    DAILY = "daily"
    WEEKLY = "weekly"


# eq=False keeps identity-based equality, so two identical "Walk" tasks stay
# distinct and the objects remain hashable.
@dataclass(eq=False)
class Task:
    title: str
    category: str
    duration_minutes: int
    priority: Priority = Priority.MEDIUM
    preferred_time: Optional[time] = None
    recurrence: Recurrence = Recurrence.NONE
    due_date: Optional[date] = None
    last_completed: Optional[date] = None
    pet_id: Optional[str] = None  # set by Pet.add_task
    id: str = field(default_factory=_new_id)

    def mark_complete(self, on_date: date) -> None:
        pass

    def is_due(self, on_date: date) -> bool:
        pass

    def next_occurrence(self) -> Optional["Task"]:
        pass

    def priority_score(self) -> int:
        pass


@dataclass(eq=False)
class Pet:
    name: str
    species: str
    breed: str = ""
    age: int = 0
    special_needs: str = ""
    tasks: list[Task] = field(default_factory=list)
    id: str = field(default_factory=_new_id)

    def add_task(self, task: Task) -> None:
        pass

    def remove_task(self, task_id: str) -> None:
        pass

    def edit_task(self, task_id: str, **changes) -> None:
        pass

    def get_tasks(self, completed: Optional[bool] = None) -> list[Task]:
        pass

    def describe(self) -> str:
        pass


@dataclass
class Owner:
    name: str
    available_minutes_per_day: int = 0
    day_start: time = time(8, 0)
    day_end: time = time(20, 0)
    preferences: dict = field(default_factory=dict)
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        pass

    def remove_pet(self, pet_id: str) -> None:
        pass

    def find_pet(self, pet_id: str) -> Optional[Pet]:
        pass

    def set_availability(self, minutes: int) -> None:
        pass

    def get_all_tasks(self) -> list[Task]:
        pass


@dataclass
class ScheduledItem:
    task: Task
    start: time
    end: time
    reason: str = ""


@dataclass
class SkippedTask:
    task: Task
    reason: str


@dataclass
class DailyPlan:
    date: date
    scheduled_items: list[ScheduledItem] = field(default_factory=list)
    skipped_tasks: list[SkippedTask] = field(default_factory=list)

    def add_item(self, task: Task, start: time, reason: str = "") -> None:
        pass

    def total_duration(self) -> int:
        pass

    def get_explanation(self) -> str:
        pass

    def to_rows(self) -> list[dict]:
        pass


class Scheduler:
    def __init__(self, owner: Owner, constraints: Optional[dict] = None):
        self.owner = owner
        self.constraints = constraints or {}

    def generate_plan(self, on_date: date) -> DailyPlan:
        pass

    def sort_tasks(self, tasks: list[Task]) -> list[Task]:
        pass

    def fit_to_time_budget(
        self, tasks: list[Task]
    ) -> tuple[list[Task], list[SkippedTask]]:
        pass

    def detect_conflicts(self, items: list[ScheduledItem]) -> list[tuple[Task, Task]]:
        pass
