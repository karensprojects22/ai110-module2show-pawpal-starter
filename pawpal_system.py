from dataclasses import dataclass, field, replace
from datetime import date, datetime, time, timedelta
from enum import Enum
from typing import Optional
from uuid import uuid4


def _new_id() -> str:
    return uuid4().hex


def _to_minutes(t: time) -> int:
    return t.hour * 60 + t.minute


def _to_time(minutes: int) -> time:
    return time(minutes // 60, minutes % 60)


class Priority(Enum):
    HIGH = 3
    MEDIUM = 2
    LOW = 1


class Recurrence(Enum):
    NONE = "none"
    DAILY = "daily"
    WEEKLY = "weekly"


_RECURRENCE_DAYS = {Recurrence.DAILY: 1, Recurrence.WEEKLY: 7}


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
        self.last_completed = on_date

    def is_due(self, on_date: date) -> bool:
        if self.due_date and on_date < self.due_date:
            return False
        if self.last_completed is None:
            return True
        if self.recurrence is Recurrence.NONE:
            return False
        interval = _RECURRENCE_DAYS[self.recurrence]
        return (on_date - self.last_completed).days >= interval

    def next_occurrence(self) -> Optional["Task"]:
        if self.recurrence is Recurrence.NONE:
            return None
        base = self.last_completed or self.due_date or date.today()
        next_due = base + timedelta(days=_RECURRENCE_DAYS[self.recurrence])
        return replace(self, id=_new_id(), due_date=next_due, last_completed=None)

    def priority_score(self) -> int:
        return self.priority.value


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
        task.pet_id = self.id
        if task not in self.tasks:
            self.tasks.append(task)

    def remove_task(self, task_id: str) -> None:
        for i, task in enumerate(self.tasks):
            if task.id == task_id:
                del self.tasks[i]
                return
        raise KeyError(f"No task with id {task_id!r} for {self.name}")

    def edit_task(self, task_id: str, **changes) -> None:
        task = next((t for t in self.tasks if t.id == task_id), None)
        if task is None:
            raise KeyError(f"No task with id {task_id!r} for {self.name}")
        for key, value in changes.items():
            if key in ("id", "pet_id") or not hasattr(task, key):
                raise AttributeError(f"Cannot edit task field {key!r}")
            setattr(task, key, value)

    def get_tasks(self, completed: Optional[bool] = None) -> list[Task]:
        # "completed" means the task has been completed at least once.
        if completed is None:
            return list(self.tasks)
        return [t for t in self.tasks if (t.last_completed is not None) == completed]

    def describe(self) -> str:
        text = f"{self.name} ({self.breed or self.species}, age {self.age})"
        if self.special_needs:
            text += f" - needs: {self.special_needs}"
        return text


@dataclass
class Owner:
    name: str
    available_minutes_per_day: int = 0
    day_start: time = time(8, 0)
    day_end: time = time(20, 0)
    preferences: dict = field(default_factory=dict)
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        if pet not in self.pets:
            self.pets.append(pet)

    def remove_pet(self, pet_id: str) -> None:
        pet = self.find_pet(pet_id)
        if pet is None:
            raise KeyError(f"No pet with id {pet_id!r}")
        self.pets.remove(pet)

    def find_pet(self, pet_id: str) -> Optional[Pet]:
        return next((p for p in self.pets if p.id == pet_id), None)

    def set_availability(self, minutes: int) -> None:
        if minutes < 0:
            raise ValueError("Availability cannot be negative")
        self.available_minutes_per_day = minutes

    def get_all_tasks(self) -> list[Task]:
        return [task for pet in self.pets for task in pet.tasks]


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
        start_dt = datetime.combine(self.date, start)
        end_dt = start_dt + timedelta(minutes=task.duration_minutes)
        if end_dt.date() != self.date:
            raise ValueError(f"{task.title!r} would run past midnight")
        self.scheduled_items.append(ScheduledItem(task, start, end_dt.time(), reason))

    def total_duration(self) -> int:
        return sum(item.task.duration_minutes for item in self.scheduled_items)

    def get_explanation(self) -> str:
        lines = [f"Plan for {self.date.isoformat()} ({self.total_duration()} min total)"]
        for item in self.scheduled_items:
            lines.append(
                f"{item.start:%H:%M}-{item.end:%H:%M} {item.task.title}: {item.reason}"
            )
        for skipped in self.skipped_tasks:
            lines.append(f"Skipped {skipped.task.title}: {skipped.reason}")
        return "\n".join(lines)

    def to_rows(self) -> list[dict]:
        return [
            {
                "Start": f"{item.start:%H:%M}",
                "End": f"{item.end:%H:%M}",
                "Task": item.task.title,
                "Category": item.task.category,
                "Duration (min)": item.task.duration_minutes,
                "Priority": item.task.priority.name.title(),
                "Why": item.reason,
            }
            for item in self.scheduled_items
        ]


class Scheduler:
    def __init__(self, owner: Owner, constraints: Optional[dict] = None):
        self.owner = owner
        self.constraints = constraints or {}

    def generate_plan(self, on_date: date) -> DailyPlan:
        plan = DailyPlan(on_date)
        due = [t for t in self.owner.get_all_tasks() if t.is_due(on_date)]
        fitting, skipped = self.fit_to_time_budget(self.sort_tasks(due))
        plan.skipped_tasks.extend(skipped)

        window_start = _to_minutes(self.owner.day_start)
        window_end = _to_minutes(self.owner.day_end)
        busy: list[tuple[int, int]] = []  # (start, end) in minutes, kept sorted

        for task in fitting:
            start, reason = self._place(task, busy, window_start, window_end)
            if start is None:
                plan.skipped_tasks.append(
                    SkippedTask(task, "No free slot left between "
                                f"{self.owner.day_start:%H:%M} and {self.owner.day_end:%H:%M}")
                )
                continue
            busy.append((start, start + task.duration_minutes))
            busy.sort()
            plan.add_item(task, _to_time(start), reason)

        plan.scheduled_items.sort(key=lambda item: item.start)
        return plan

    def sort_tasks(self, tasks: list[Task]) -> list[Task]:
        # Highest priority first, then earliest preferred time, then shortest.
        return sorted(
            tasks,
            key=lambda t: (-t.priority_score(), t.preferred_time or time.max,
                           t.duration_minutes),
        )

    def fit_to_time_budget(
        self, tasks: list[Task]
    ) -> tuple[list[Task], list[SkippedTask]]:
        remaining = self.owner.available_minutes_per_day
        fitting: list[Task] = []
        skipped: list[SkippedTask] = []
        for task in tasks:
            if task.duration_minutes <= remaining:
                fitting.append(task)
                remaining -= task.duration_minutes
            else:
                skipped.append(SkippedTask(
                    task,
                    f"Needs {task.duration_minutes} min but only {remaining} min "
                    "of the daily budget was left",
                ))
        return fitting, skipped

    def detect_conflicts(self, items: list[ScheduledItem]) -> list[tuple[Task, Task]]:
        ordered = sorted(items, key=lambda item: item.start)
        conflicts = []
        for i, first in enumerate(ordered):
            for second in ordered[i + 1:]:
                if second.start >= first.end:
                    break
                conflicts.append((first.task, second.task))
        return conflicts

    @staticmethod
    def _place(
        task: Task, busy: list[tuple[int, int]], window_start: int, window_end: int
    ) -> tuple[Optional[int], str]:
        """Pick a start time (in minutes) for the task, or None if nothing fits."""
        length = task.duration_minutes

        def is_free(start: int) -> bool:
            end = start + length
            return (window_start <= start and end <= window_end
                    and all(end <= b_start or start >= b_end for b_start, b_end in busy))

        label = task.priority.name.lower()
        if task.preferred_time is not None:
            wanted = _to_minutes(task.preferred_time)
            if is_free(wanted):
                return wanted, f"{label} priority, scheduled at its preferred time"

        # Earliest gap: try the window start and the end of every busy block.
        for start in sorted([window_start] + [b_end for _, b_end in busy]):
            if is_free(start):
                note = " (preferred time was unavailable)" if task.preferred_time else ""
                return start, f"{label} priority, placed in the earliest free slot{note}"
        return None, ""
