# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Implementation summary

The core logic lives in `pawpal_system.py`. `main.py` is a demo script that builds an owner with two pets and prints today's schedule, and `tests/` holds the pytest suite. The class diagram is in `diagrams/uml.mmd`.

**How the classes work together**

- `Owner` has many `Pet`s, and each `Pet` has many `Task`s. Each task stores its pet's `pet_id`, so a plan can still tell which pet a task belongs to.
- `Owner.get_all_tasks()` returns every pet's tasks in one list. The `Scheduler` reads tasks only through this method, so it plans across all pets at once.
- `Scheduler.generate_plan(date)` builds the day in four steps:
  1. Keep the tasks that are due: not yet completed, and on or after their due date. A recurring task is renewed when you complete it, because `Pet.complete_task` adds the next copy.
  2. Sort them by priority, then preferred time, then shortest first.
  3. Apply the owner's daily minutes budget. All pets share one budget, so a high-priority task for one pet can push out a low-priority task for another.
  4. Place each task at its preferred time if that slot is free, or in the earliest free slot inside the owner's day window.
- The result is a `DailyPlan` holding `ScheduledItem`s and `SkippedTask`s. Each one records a reason, which is how the app explains its choices.
- `Priority` and `Recurrence` are enums, so values like HIGH or DAILY can't be mistyped.

**Known tradeoff:** the scheduler is greedy. It fills the budget in priority order, so one long high-priority task can crowd out several short, lower-priority ones.

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

## 🖥️ Sample Output

Output from running `python main.py`:

```
============================================================
Sorting and filtering check
============================================================

As added (out of order):
  18:00  Brush coat           Biscuit  pending
   any   Refill water bowl    Biscuit  pending
  07:30  Morning walk         Biscuit  pending
  12:30  Training session     Biscuit  pending
  18:00  Flea treatment       Biscuit  pending
  07:00  Breakfast            Biscuit  done
  07:00  Breakfast            Biscuit  pending, due 2026-11-17
  12:30  Feather wand play    Mochi    pending
  08:00  Thyroid medication   Mochi    pending

Sorted by time:
  07:00  Breakfast            Biscuit  done
  07:00  Breakfast            Biscuit  pending, due 2026-11-17
  07:30  Morning walk         Biscuit  pending
  08:00  Thyroid medication   Mochi    pending
  12:30  Feather wand play    Mochi    pending
  12:30  Training session     Biscuit  pending
  18:00  Flea treatment       Biscuit  pending
  18:00  Brush coat           Biscuit  pending
   any   Refill water bowl    Biscuit  pending

Filtered: pet = Mochi
  12:30  Feather wand play    Mochi    pending
  08:00  Thyroid medication   Mochi    pending

Filtered: completed only
  07:00  Breakfast            Biscuit  done

Filtered: pending only, sorted by time
  07:00  Breakfast            Biscuit  pending, due 2026-11-17
  07:30  Morning walk         Biscuit  pending
  08:00  Thyroid medication   Mochi    pending
  12:30  Feather wand play    Mochi    pending
  12:30  Training session     Biscuit  pending
  18:00  Flea treatment       Biscuit  pending
  18:00  Brush coat           Biscuit  pending
   any   Refill water bowl    Biscuit  pending

Filtered: pet = Biscuit and pending, sorted by time
  07:00  Breakfast            Biscuit  pending, due 2026-11-17
  07:30  Morning walk         Biscuit  pending
  12:30  Training session     Biscuit  pending
  18:00  Flea treatment       Biscuit  pending
  18:00  Brush coat           Biscuit  pending
   any   Refill water bowl    Biscuit  pending

============================================================
Today's Schedule - Monday, November 16, 2026
Owner: Karen | Pets: Biscuit, Mochi
------------------------------------------------------------
07:00-07:05  Refill water bowl    [Biscuit, low]
             why: low priority, placed in the earliest free slot
07:30-08:00  Morning walk         [Biscuit, high]
             why: high priority, scheduled at its preferred time
08:00-08:05  Thyroid medication   [Mochi, high]
             why: high priority, scheduled at its preferred time
12:30-12:45  Feather wand play    [Mochi, medium]
             why: medium priority, scheduled at its preferred time
12:45-13:05  Training session     [Biscuit, medium]
             why: medium priority, moved to the nearest free slot (preferred time was unavailable)
18:00-18:05  Flea treatment       [Biscuit, medium]
             why: medium priority, scheduled at its preferred time
18:05-18:25  Brush coat           [Biscuit, low]
             why: low priority, moved to the nearest free slot (preferred time was unavailable)

Warning: time conflict - Feather wand play (Mochi) at 12:30 overlaps Training session (Biscuit) at 12:30 (different pets)

Warning: time conflict - Flea treatment (Biscuit) at 18:00 overlaps Brush coat (Biscuit) at 18:00 (same pet)
------------------------------------------------------------
Total: 100 of 120 min
```

## 🧪 Testing PawPal+

```bash
# Run the full test suite:
pytest

# Run with coverage:
pytest --cov
```

Sample test output:

```
# Paste your pytest output here
```

## 📐 Smarter Scheduling

Each feature below names the method that implements it. `python main.py` prints a demo of sorting, filtering, conflicts and recurrence, and `tests/` covers each one.

### Sorting

| Method | Order | Used for |
|--------|-------|----------|
| `Scheduler.sort_by_time(tasks)` | Preferred time, with untimed tasks last, then shortest first | The task table in the app and the sorting demo in `main.py` |
| `Scheduler.sort_tasks(tasks)` | Priority (high first), then preferred time, then shortest first | Deciding which tasks get the time budget and the best slots when the plan is built |

`sort_by_time` uses a tuple key, `(is untimed, time, duration)`, so `None` never has to be compared with a time. The finished plan's items are always returned in chronological order.

### Filtering

`Owner.filter_tasks(pet_name=None, completed=None)` returns tasks across all pets:

- `pet_name` matches one pet, ignoring case. `None` means every pet.
- `completed=True` keeps tasks completed at least once, `False` keeps the rest, and `None` keeps both.
- The two filters combine, for example `owner.filter_tasks(pet_name="Biscuit", completed=False)`.

`Pet.get_tasks(completed)` does the same for a single pet. Separately, `Scheduler.fit_to_time_budget(tasks)` drops tasks that don't fit the owner's daily minutes and records a reason for each.

### Conflict detection

Detection returns warning messages and never raises an error, so a bad schedule can't crash the app.

- `Scheduler.conflict_warnings(tasks)` is the lightweight check. Each task with a preferred time covers its start to start plus duration. Two tasks conflict if their spans overlap, whether they are for the same pet or different pets. Tasks at exactly the same time conflict, and back-to-back tasks do not. Each message names both tasks and says "same pet" or "different pets".
- `Scheduler.detect_conflicts(items)` is the pairing step. It sorts items by start time and scans forward, stopping as soon as a later item starts at or after the current item's end.
- `Scheduler.generate_plan(date)` runs the check and stores the messages in `plan.warnings`. It still builds a full plan: `Scheduler._place` gives the higher-ranked task its preferred time and moves the other to the nearest free slot, so the final plan has no overlaps. Tasks with no preferred time are not checked, because they are placed into free gaps.

```
Warning: time conflict - Flea treatment (Biscuit) at 18:00 overlaps Brush coat (Biscuit) at 18:00 (same pet)
```

### Recurring tasks

- `Task.mark_complete(date)` records the completion. The first time a daily or weekly task is completed, it also adds the next occurrence to the task's pet. Completing it twice does not create a second copy.
- `Task.next_occurrence()` builds that copy: a new task with a new id, due 1 day (daily) or 7 days (weekly) after the completion date. It is not yet completed, so it recurs in turn.
- `Pet.complete_task(task_id, date)` does the same thing for a task looked up by id. The app's "Mark complete" button uses it.
- `Task.is_due(date)` keeps the copy out of today's plan until its due date. A completed task is never due again.

## 📸 Demo Walkthrough

Describe your app in numbered steps so a reader can follow along without watching a video:

1. <!-- Describe this step -->
2. <!-- Describe this step -->
3. <!-- Describe this step -->
4. <!-- Describe this step -->
5. <!-- Add more steps as needed -->

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or link to a demo video here -->
