"""Edge-case tests for sorting, recurring tasks and scheduler limits.

Grouped by risk area: sorting, recurring tasks, scheduler limits, and budget
accounting plus input validation.
"""
from datetime import date, time, timedelta

import pytest

from pawpal_system import Owner, Pet, Priority, Recurrence, Scheduler, Task

TODAY = date(2026, 11, 16)


def make_owner(budget: int = 240, start=time(8, 0), end=time(20, 0)):
    owner = Owner("Sam", available_minutes_per_day=budget, day_start=start, day_end=end)
    pet = Pet("Biscuit", "dog")
    owner.add_pet(pet)
    return owner, pet


def titles(plan) -> list[str]:
    return [item.task.title for item in plan.scheduled_items]


# --- Sorting -----------------------------------------------------------------


def test_sort_by_time_handles_empty_and_single_lists():
    scheduler = Scheduler(make_owner()[0])
    only = Task("Walk", "walk", 30)

    assert scheduler.sort_by_time([]) == []
    assert scheduler.sort_by_time([only]) == [only]


def test_sort_by_time_orders_untimed_tasks_by_duration():
    scheduler = Scheduler(make_owner()[0])
    long, short, mid = Task("L", "x", 40), Task("S", "x", 5), Task("M", "x", 20)

    assert scheduler.sort_by_time([long, short, mid]) == [short, mid, long]


def test_sort_by_time_breaks_equal_times_with_shorter_task_first():
    scheduler = Scheduler(make_owner()[0])
    long = Task("Long", "x", 30, preferred_time=time(9, 0))
    short = Task("Short", "x", 10, preferred_time=time(9, 0))

    assert scheduler.sort_by_time([long, short]) == [short, long]


def test_sort_by_time_is_stable_for_identical_keys():
    scheduler = Scheduler(make_owner()[0])
    first = Task("A", "x", 10, preferred_time=time(9, 0))
    second = Task("B", "x", 10, preferred_time=time(9, 0))

    assert scheduler.sort_by_time([first, second]) == [first, second]
    assert scheduler.sort_by_time([second, first]) == [second, first]


def test_midnight_is_a_real_time_not_treated_as_untimed():
    scheduler = Scheduler(make_owner()[0])
    midnight = Task("Midnight", "x", 10, preferred_time=time(0, 0))
    morning = Task("Morning", "x", 10, preferred_time=time(7, 0))
    untimed = Task("Untimed", "x", 10)

    assert scheduler.sort_by_time([untimed, morning, midnight]) == [
        midnight, morning, untimed,
    ]


def test_sorting_does_not_mutate_the_input_list():
    scheduler = Scheduler(make_owner()[0])
    tasks = [Task("B", "x", 10, preferred_time=time(9, 0)),
             Task("A", "x", 10, preferred_time=time(7, 0))]
    snapshot = list(tasks)

    scheduler.sort_by_time(tasks)
    scheduler.sort_tasks(tasks)

    assert tasks == snapshot


def test_sort_tasks_ranks_priority_above_time_of_day():
    scheduler = Scheduler(make_owner()[0])
    late_high = Task("Late", "x", 10, Priority.HIGH, preferred_time=time(18, 0))
    early_low = Task("Early", "x", 10, Priority.LOW, preferred_time=time(7, 0))

    assert scheduler.sort_tasks([early_low, late_high]) == [late_high, early_low]


# --- Recurring tasks -----------------------------------------------------------


@pytest.mark.parametrize(
    "completed_on, recurrence, expected",
    [
        (date(2026, 12, 31), Recurrence.DAILY, date(2027, 1, 1)),   # year boundary
        (date(2026, 1, 31), Recurrence.DAILY, date(2026, 2, 1)),    # month boundary
        (date(2028, 2, 28), Recurrence.DAILY, date(2028, 2, 29)),   # leap day exists
        (date(2027, 2, 28), Recurrence.DAILY, date(2027, 3, 1)),    # no leap day
        (date(2026, 12, 28), Recurrence.WEEKLY, date(2027, 1, 4)),  # weekly year wrap
        (date(2028, 2, 26), Recurrence.WEEKLY, date(2028, 3, 4)),   # weekly past leap day
    ],
)
def test_next_due_date_across_calendar_boundaries(completed_on, recurrence, expected):
    owner, pet = make_owner()
    task = Task("Walk", "walk", 30, recurrence=recurrence)
    pet.add_task(task)

    successor = task.mark_complete(completed_on)

    assert successor.due_date == expected


def test_late_completion_counts_from_the_completion_date():
    owner, pet = make_owner()
    task = Task("Walk", "walk", 30, recurrence=Recurrence.DAILY,
                due_date=TODAY - timedelta(days=6))
    pet.add_task(task)

    successor = task.mark_complete(TODAY - timedelta(days=3))

    assert successor.due_date == TODAY - timedelta(days=2)


def test_successor_copies_fields_but_is_an_independent_task():
    owner, pet = make_owner()
    task = Task("Walk", "walk", 30, Priority.HIGH, preferred_time=time(7, 30),
                recurrence=Recurrence.DAILY)
    pet.add_task(task)

    successor = task.mark_complete(TODAY)

    assert successor is not task and successor.id != task.id
    assert (successor.title, successor.category, successor.duration_minutes,
            successor.priority, successor.preferred_time, successor.recurrence) == (
        "Walk", "walk", 30, Priority.HIGH, time(7, 30), Recurrence.DAILY)
    assert successor.last_completed is None
    successor.title = "Changed"
    assert task.title == "Walk"


def test_is_due_boundaries_on_the_due_date():
    task = Task("Vet", "meds", 60, due_date=TODAY)

    assert not task.is_due(TODAY - timedelta(days=1))
    assert task.is_due(TODAY)
    assert task.is_due(TODAY + timedelta(days=1))

    task.mark_complete(TODAY)
    assert not task.is_due(TODAY)
    assert not task.is_due(TODAY + timedelta(days=1))


def test_completed_recurring_task_waits_for_its_successor_due_date():
    owner, pet = make_owner()
    task = Task("Walk", "walk", 30, recurrence=Recurrence.DAILY)
    pet.add_task(task)
    pet.complete_task(task.id, TODAY)

    today_plan = Scheduler(owner).generate_plan(TODAY)
    tomorrow_plan = Scheduler(owner).generate_plan(TODAY + timedelta(days=1))

    assert today_plan.scheduled_items == [] and today_plan.skipped_tasks == []
    assert titles(tomorrow_plan) == ["Walk"]


def test_filters_see_the_completed_original_and_the_pending_successor():
    owner, pet = make_owner()
    task = Task("Walk", "walk", 30, recurrence=Recurrence.DAILY)
    pet.add_task(task)

    successor = task.mark_complete(TODAY)

    assert owner.filter_tasks(completed=True) == [task]
    assert owner.filter_tasks(completed=False) == [successor]


def test_completing_an_unknown_task_id_raises_key_error():
    owner, pet = make_owner()

    with pytest.raises(KeyError):
        pet.complete_task("does-not-exist", TODAY)


# --- Scheduler limits ------------------------------------------------------------


def test_owner_with_no_pets_or_tasks_gets_an_empty_plan():
    plan = Scheduler(Owner("Sam", available_minutes_per_day=60)).generate_plan(TODAY)

    assert plan.scheduled_items == [] and plan.skipped_tasks == []
    assert plan.warnings == [] and plan.to_rows() == []
    assert plan.total_duration() == 0
    assert "0 min total" in plan.get_explanation()


def test_zero_budget_skips_every_task_with_a_reason():
    owner, pet = make_owner(budget=0)
    pet.add_task(Task("Walk", "walk", 30))

    plan = Scheduler(owner).generate_plan(TODAY)

    assert plan.scheduled_items == []
    assert "budget" in plan.skipped_tasks[0].reason


def test_task_that_exactly_fills_the_budget_is_scheduled():
    owner, pet = make_owner(budget=30)
    pet.add_task(Task("Walk", "walk", 30))

    assert titles(Scheduler(owner).generate_plan(TODAY)) == ["Walk"]


def test_task_ending_exactly_at_day_end_fits_but_one_minute_more_does_not():
    owner, pet = make_owner(budget=240, start=time(8, 0), end=time(9, 0))
    pet.add_task(Task("Fits", "x", 60))
    pet.add_task(Task("TooLong", "x", 61, Priority.HIGH))

    plan = Scheduler(owner).generate_plan(TODAY)

    assert titles(plan) == ["Fits"]
    assert plan.scheduled_items[0].end == time(9, 0)
    assert [s.task.title for s in plan.skipped_tasks] == ["TooLong"]
    assert "No free slot" in plan.skipped_tasks[0].reason


def test_preferred_time_before_the_day_window_is_moved_inside_it():
    owner, pet = make_owner(start=time(8, 0), end=time(20, 0))
    pet.add_task(Task("Early", "x", 30, preferred_time=time(6, 0)))

    item = Scheduler(owner).generate_plan(TODAY).scheduled_items[0]

    assert item.start == time(8, 0)


def test_many_tasks_wanting_the_same_time_never_overlap_or_leave_the_window():
    owner, pet = make_owner(budget=600, start=time(8, 0), end=time(20, 0))
    for n in range(8):
        pet.add_task(Task(f"T{n}", "x", 20, preferred_time=time(10, 0)))
    scheduler = Scheduler(owner)

    plan = scheduler.generate_plan(TODAY)

    assert len(plan.scheduled_items) == 8
    assert scheduler.detect_conflicts(plan.scheduled_items) == []
    assert all(time(8, 0) <= i.start and i.end <= time(20, 0)
               for i in plan.scheduled_items)
    assert len(plan.warnings) == 28  # every one of the 28 pairs shares 10:00


# --- Budget accounting and input validation --------------------------------------


def test_unplaceable_task_does_not_consume_budget():
    owner, pet = make_owner(budget=100, start=time(8, 0), end=time(9, 0))
    pet.add_task(Task("A", "x", 50, Priority.HIGH))
    pet.add_task(Task("B", "x", 50, Priority.MEDIUM))  # fits budget, no slot left
    pet.add_task(Task("C", "x", 10, Priority.LOW))     # fits the last 10 minutes

    plan = Scheduler(owner).generate_plan(TODAY)

    assert set(titles(plan)) == {"A", "C"}
    assert [s.task.title for s in plan.skipped_tasks] == ["B"]
    assert "No free slot" in plan.skipped_tasks[0].reason


def test_scheduled_minutes_never_exceed_the_budget():
    owner, pet = make_owner(budget=70)
    for n, minutes in enumerate((30, 25, 20, 15, 10)):
        pet.add_task(Task(f"T{n}", "x", minutes, Priority.MEDIUM))

    plan = Scheduler(owner).generate_plan(TODAY)

    assert plan.total_duration() <= 70
    assert plan.total_duration() == 70  # 30 + 25 + 15 fills it exactly


def test_over_budget_task_is_skipped_but_a_smaller_one_still_fits():
    owner, pet = make_owner(budget=40)
    pet.add_task(Task("Big", "x", 35, Priority.HIGH))
    pet.add_task(Task("Huge", "x", 30, Priority.MEDIUM))  # only 5 min left: skipped
    pet.add_task(Task("Tiny", "x", 5, Priority.LOW))

    plan = Scheduler(owner).generate_plan(TODAY)

    assert set(titles(plan)) == {"Big", "Tiny"}
    assert "budget" in plan.skipped_tasks[0].reason


@pytest.mark.parametrize("minutes", [0, -1, -20])
def test_non_positive_duration_is_rejected(minutes):
    with pytest.raises(ValueError):
        Task("Backwards", "x", minutes)


def test_one_minute_duration_is_allowed():
    assert Task("Quick", "x", 1).duration_minutes == 1


@pytest.mark.parametrize("minutes", [0, -5])
def test_editing_a_task_to_a_non_positive_duration_is_rejected(minutes):
    owner, pet = make_owner()
    task = Task("Walk", "walk", 30)
    pet.add_task(task)

    with pytest.raises(ValueError):
        pet.edit_task(task.id, duration_minutes=minutes)

    assert task.duration_minutes == 30


def test_recurring_copy_keeps_a_valid_duration():
    owner, pet = make_owner()
    task = Task("Walk", "walk", 30, recurrence=Recurrence.DAILY)
    pet.add_task(task)

    assert task.mark_complete(TODAY).duration_minutes == 30


def test_negative_budget_is_rejected_at_construction_and_by_setter():
    with pytest.raises(ValueError):
        Owner("Sam", available_minutes_per_day=-1)
    owner = Owner("Sam", available_minutes_per_day=10)
    with pytest.raises(ValueError):
        owner.set_availability(-1)
    assert owner.available_minutes_per_day == 10
