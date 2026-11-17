from datetime import date

from pawpal_system import Owner, Pet, Priority, Scheduler, Task

PLAN_DATE = date(2026, 11, 16)


def make_two_pet_owner() -> tuple[Owner, Pet, Pet]:
    owner = Owner("Sam", available_minutes_per_day=120)
    biscuit = Pet("Biscuit", "dog")
    mochi = Pet("Mochi", "cat")
    owner.add_pet(biscuit)
    owner.add_pet(mochi)
    return owner, biscuit, mochi


def test_owner_get_all_tasks_returns_tasks_from_every_pet():
    owner, biscuit, mochi = make_two_pet_owner()
    walk = Task("Walk", "walk", 30)
    feed = Task("Feed", "feeding", 10)
    biscuit.add_task(walk)
    mochi.add_task(feed)

    assert set(owner.get_all_tasks()) == {walk, feed}


def test_scheduler_plans_tasks_for_all_pets():
    owner, biscuit, mochi = make_two_pet_owner()
    walk = Task("Walk", "walk", 30, Priority.HIGH)
    feed = Task("Feed", "feeding", 10, Priority.MEDIUM)
    biscuit.add_task(walk)
    mochi.add_task(feed)

    plan = Scheduler(owner).generate_plan(PLAN_DATE)

    scheduled = {item.task for item in plan.scheduled_items}
    assert scheduled == {walk, feed}
    assert {item.task.pet_id for item in plan.scheduled_items} == {biscuit.id, mochi.id}


def test_pets_share_one_time_budget():
    owner, biscuit, mochi = make_two_pet_owner()
    owner.set_availability(30)
    urgent = Task("Meds", "meds", 30, Priority.HIGH)
    optional = Task("Play", "enrichment", 30, Priority.LOW)
    biscuit.add_task(optional)
    mochi.add_task(urgent)

    plan = Scheduler(owner).generate_plan(PLAN_DATE)

    assert [item.task for item in plan.scheduled_items] == [urgent]
    assert [s.task for s in plan.skipped_tasks] == [optional]
