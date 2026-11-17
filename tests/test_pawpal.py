from datetime import date, time, timedelta

import pytest

from pawpal_system import Owner, Pet, Priority, Recurrence, Scheduler, Task

TODAY = date(2026, 11, 16)


def test_mark_complete_changes_task_status():
    task = Task("Morning walk", "walk", 30)
    assert task.last_completed is None
    assert task.is_due(date(2026, 11, 16))

    task.mark_complete(date(2026, 11, 16))

    assert task.last_completed == date(2026, 11, 16)
    assert not task.is_due(date(2026, 11, 16))


def test_adding_task_increases_pet_task_count():
    pet = Pet("Biscuit", "dog")
    assert len(pet.tasks) == 0

    pet.add_task(Task("Morning walk", "walk", 30))
    assert len(pet.tasks) == 1

    pet.add_task(Task("Feeding", "feeding", 10))
    assert len(pet.tasks) == 2


def make_owner() -> tuple[Owner, Pet, Pet]:
    owner = Owner("Sam", available_minutes_per_day=240)
    biscuit, mochi = Pet("Biscuit", "dog"), Pet("Mochi", "cat")
    owner.add_pet(biscuit)
    owner.add_pet(mochi)
    return owner, biscuit, mochi


def test_sort_by_time_orders_by_preferred_time_with_untimed_last():
    owner, _, _ = make_owner()
    evening = Task("Evening walk", "walk", 30, preferred_time=time(18, 0))
    untimed = Task("Brush", "grooming", 10)
    morning = Task("Breakfast", "feeding", 10, preferred_time=time(7, 30))

    ordered = Scheduler(owner).sort_by_time([evening, untimed, morning])

    assert ordered == [morning, evening, untimed]


def test_plan_items_come_out_in_chronological_order():
    owner, biscuit, mochi = make_owner()
    biscuit.add_task(Task("Late", "walk", 20, Priority.HIGH, preferred_time=time(17, 0)))
    mochi.add_task(Task("Early", "feeding", 10, Priority.LOW, preferred_time=time(8, 0)))

    plan = Scheduler(owner).generate_plan(TODAY)

    starts = [item.start for item in plan.scheduled_items]
    assert starts == sorted(starts)


def test_filter_tasks_by_pet_and_status():
    owner, biscuit, mochi = make_owner()
    walk = Task("Walk", "walk", 30)
    feed = Task("Feed", "feeding", 10)
    meds = Task("Meds", "meds", 5)
    biscuit.add_task(walk)
    biscuit.add_task(feed)
    mochi.add_task(meds)
    feed.mark_complete(TODAY)

    assert set(owner.filter_tasks(pet_name="biscuit")) == {walk, feed}
    assert owner.filter_tasks(pet_name="Mochi") == [meds]
    assert owner.filter_tasks(completed=True) == [feed]
    assert set(owner.filter_tasks(completed=False)) == {walk, meds}
    assert owner.filter_tasks(pet_name="Biscuit", completed=False) == [walk]


@pytest.mark.parametrize(
    "recurrence, days", [(Recurrence.DAILY, 1), (Recurrence.WEEKLY, 7)]
)
def test_completing_recurring_task_creates_next_occurrence(recurrence, days):
    pet = Pet("Biscuit", "dog")
    task = Task("Walk", "walk", 30, recurrence=recurrence)
    pet.add_task(task)

    following = pet.complete_task(task.id, TODAY)

    assert following is not None and following is not task
    assert following.due_date == TODAY + timedelta(days=days)
    assert following.last_completed is None
    assert following.pet_id == pet.id
    assert len(pet.tasks) == 2
    assert not following.is_due(TODAY)
    assert following.is_due(TODAY + timedelta(days=days))


def test_completing_one_off_task_creates_no_follow_up():
    pet = Pet("Biscuit", "dog")
    task = Task("Vet visit", "meds", 60)
    pet.add_task(task)

    assert pet.complete_task(task.id, TODAY) is None
    assert len(pet.tasks) == 1
    assert not task.is_due(TODAY)


def test_completing_same_task_twice_does_not_duplicate_recurrence():
    pet = Pet("Biscuit", "dog")
    task = Task("Walk", "walk", 30, recurrence=Recurrence.DAILY)
    pet.add_task(task)

    pet.complete_task(task.id, TODAY)
    assert pet.complete_task(task.id, TODAY) is None
    assert len(pet.tasks) == 2


def test_conflict_warnings_flag_overlapping_preferred_times_across_pets():
    owner, biscuit, mochi = make_owner()
    walk = Task("Walk", "walk", 30, preferred_time=time(8, 0))
    meds = Task("Meds", "meds", 5, preferred_time=time(8, 15))
    biscuit.add_task(walk)
    mochi.add_task(meds)

    warnings = Scheduler(owner).conflict_warnings([walk, meds])

    assert len(warnings) == 1
    assert "Walk (Biscuit)" in warnings[0] and "Meds (Mochi)" in warnings[0]


def test_back_to_back_tasks_are_not_conflicts():
    owner, biscuit, _ = make_owner()
    first = Task("Walk", "walk", 30, preferred_time=time(8, 0))
    second = Task("Feed", "feeding", 10, preferred_time=time(8, 30))
    biscuit.add_task(first)
    biscuit.add_task(second)

    assert Scheduler(owner).conflict_warnings([first, second]) == []


def test_plan_reports_conflict_but_still_schedules_both_without_overlap():
    owner, biscuit, mochi = make_owner()
    biscuit.add_task(Task("Walk", "walk", 30, Priority.HIGH, preferred_time=time(8, 0)))
    mochi.add_task(Task("Meds", "meds", 5, Priority.HIGH, preferred_time=time(8, 10)))
    scheduler = Scheduler(owner)

    plan = scheduler.generate_plan(TODAY)

    assert len(plan.warnings) == 1
    assert len(plan.scheduled_items) == 2
    assert scheduler.detect_conflicts(plan.scheduled_items) == []


@pytest.mark.parametrize(
    "recurrence, days", [(Recurrence.DAILY, 1), (Recurrence.WEEKLY, 7)]
)
def test_mark_complete_alone_queues_next_occurrence_on_the_pet(recurrence, days):
    pet = Pet("Biscuit", "dog")
    task = Task("Walk", "walk", 30, recurrence=recurrence)
    pet.add_task(task)

    task.mark_complete(TODAY)

    assert len(pet.tasks) == 2
    following = pet.tasks[1]
    assert following.due_date == TODAY + timedelta(days=days)
    assert following.pet_id == pet.id and not following.is_due(TODAY)


def test_marking_a_one_off_task_complete_adds_nothing():
    pet = Pet("Biscuit", "dog")
    task = Task("Vet visit", "meds", 60)
    pet.add_task(task)

    assert task.mark_complete(TODAY) is None
    assert len(pet.tasks) == 1


def test_marking_complete_twice_queues_only_one_occurrence():
    pet = Pet("Biscuit", "dog")
    task = Task("Walk", "walk", 30, recurrence=Recurrence.DAILY)
    pet.add_task(task)

    task.mark_complete(TODAY)
    task.mark_complete(TODAY)

    assert len(pet.tasks) == 2


def test_next_occurrence_chains_so_the_task_keeps_recurring():
    pet = Pet("Biscuit", "dog")
    task = Task("Walk", "walk", 30, recurrence=Recurrence.DAILY)
    pet.add_task(task)

    task.mark_complete(TODAY)
    pet.tasks[1].mark_complete(TODAY + timedelta(days=1))

    assert len(pet.tasks) == 3
    assert pet.tasks[2].due_date == TODAY + timedelta(days=2)


def test_detached_recurring_task_returns_next_occurrence_without_a_pet():
    task = Task("Walk", "walk", 30, recurrence=Recurrence.DAILY)

    following = task.mark_complete(TODAY)

    assert following is not None
    assert following.due_date == TODAY + timedelta(days=1)


def test_removed_task_no_longer_adds_to_its_old_pet():
    pet = Pet("Biscuit", "dog")
    task = Task("Walk", "walk", 30, recurrence=Recurrence.DAILY)
    pet.add_task(task)
    pet.remove_task(task.id)

    task.mark_complete(TODAY)

    assert pet.tasks == []


def test_identical_start_times_warn_with_pet_scope():
    owner, biscuit, mochi = make_owner()
    walk = Task("Walk", "walk", 30, preferred_time=time(9, 0))
    brush = Task("Brush", "grooming", 15, preferred_time=time(9, 0))
    play = Task("Play", "enrichment", 15, preferred_time=time(9, 0))
    biscuit.add_task(walk)
    biscuit.add_task(brush)
    mochi.add_task(play)

    warnings = Scheduler(owner).conflict_warnings([walk, brush, play])

    assert len(warnings) == 3  # every pair shares 09:00
    assert sum("same pet" in w for w in warnings) == 1
    assert sum("different pets" in w for w in warnings) == 2


def test_conflict_check_never_raises_for_odd_input():
    owner, biscuit, _ = make_owner()
    late = Task("Late", "walk", 90, preferred_time=time(23, 30))  # runs past midnight
    detached = Task("Loose", "walk", 10, preferred_time=time(23, 45))  # no pet

    assert isinstance(Scheduler(owner).conflict_warnings([late, detached]), list)
    assert Scheduler(owner).conflict_warnings([]) == []


def test_clashing_task_moves_to_nearest_free_slot_not_start_of_day():
    owner, biscuit, mochi = make_owner()
    biscuit.add_task(Task("Play", "enrichment", 30, Priority.HIGH, preferred_time=time(12, 0)))
    mochi.add_task(Task("Train", "enrichment", 20, Priority.MEDIUM, preferred_time=time(12, 0)))

    plan = Scheduler(owner).generate_plan(TODAY)

    starts = {i.task.title: i.start for i in plan.scheduled_items}
    assert starts["Play"] == time(12, 0)
    # 11:40 is 20 min from the wanted 12:00; 12:30 would be 30 min away; 08:00 is far.
    assert starts["Train"] == time(11, 40)
