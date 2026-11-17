from datetime import date, time

from pawpal_system import Owner, Pet, Priority, Recurrence, Scheduler, Task


def build_demo_owner() -> Owner:
    owner = Owner(
        "Karen",
        available_minutes_per_day=120,
        day_start=time(7, 0),
        day_end=time(21, 0),
    )

    biscuit = Pet("Biscuit", "dog", breed="Golden Retriever", age=3)
    mochi = Pet("Mochi", "cat", breed="Siamese", age=5, special_needs="thyroid meds")
    owner.add_pet(biscuit)
    owner.add_pet(mochi)

    biscuit.add_task(Task("Morning walk", "walk", 30, Priority.HIGH,
                          preferred_time=time(7, 30), recurrence=Recurrence.DAILY))
    biscuit.add_task(Task("Brush coat", "grooming", 20, Priority.LOW,
                          preferred_time=time(18, 0), recurrence=Recurrence.WEEKLY))
    mochi.add_task(Task("Thyroid medication", "meds", 5, Priority.HIGH,
                        preferred_time=time(8, 0), recurrence=Recurrence.DAILY))
    mochi.add_task(Task("Feather wand play", "enrichment", 15, Priority.MEDIUM,
                        preferred_time=time(12, 30)))
    return owner


def print_schedule(owner: Owner, today: date) -> None:
    plan = Scheduler(owner).generate_plan(today)

    print(f"Today's Schedule - {today:%A, %B %d, %Y}")
    print(f"Owner: {owner.name} | Pets: {', '.join(p.name for p in owner.pets)}")
    print("-" * 60)
    for item in plan.scheduled_items:
        pet = owner.find_pet(item.task.pet_id)
        print(f"{item.start:%H:%M}-{item.end:%H:%M}  {item.task.title:<20} "
              f"[{pet.name}, {item.task.priority.name.lower()}]")
        print(f"             why: {item.reason}")
    if plan.skipped_tasks:
        print("\nSkipped:")
        for skipped in plan.skipped_tasks:
            print(f"  {skipped.task.title}: {skipped.reason}")
    print("-" * 60)
    print(f"Total: {plan.total_duration()} of {owner.available_minutes_per_day} min")


if __name__ == "__main__":
    print_schedule(build_demo_owner(), date.today())
