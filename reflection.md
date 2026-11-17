# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

- Briefly describe your initial UML design.
- What classes did you include, and what responsibilities did you assign to each?

My UML models a pet owner who builds a daily care plan for their pets. It has five classes, plus two small enums (`Priority` and `Recurrence`) so values like HIGH or DAILY can't be mistyped. `Owner`, `Pet`, `Task` and `DailyPlan` are dataclasses because they mostly hold data. `Scheduler` is a regular class because it holds the logic.

- **Owner**: holds the owner's name, their daily time budget, their preferences, and their list of pets. It adds and removes pets, updates availability, gathers every task across all pets, and starts plan creation by handing off to the `Scheduler`.
- **Pet**: holds the pet's profile (name, species, breed, age, special needs) and that pet's list of tasks. It adds, removes, edits and filters its tasks, and can describe itself for the UI. I made walking, feeding and grooming `Task` objects rather than pet actions, so the scheduler can sort and filter them.
- **Task**: represents one care activity, with a title, category, duration, priority, optional preferred time, recurrence and completed flag. It can mark itself complete, check whether it is due on a date, create its next occurrence if it recurs, and turn its priority into a number for sorting.
- **Scheduler**: holds the scheduling logic, kept separate from the data classes so it is easy to test. It sorts tasks by priority, fits them into the owner's time budget, detects time conflicts, builds the `DailyPlan`, and explains why it chose that plan.
- **DailyPlan**: the result of scheduling for one date. It holds the scheduled items, the skipped tasks and the total minutes. It can add items, report total duration, give the explanation, and format itself as rows for the Streamlit display.

Relationships: an `Owner` has many `Pet`s, a `Pet` has many `Task`s, and the `Scheduler` reads an owner's tasks to produce a `DailyPlan`.
Y
**b. Design changes**

- Did your design change during implementation?
- If yes, describe at least one change and why you made it.

Yes. After reviewing my skeleton I found several gaps and changed the design before writing any logic:

- **Tasks know their pet.** `Owner.get_all_tasks()` flattens every pet's tasks into one list, so a plan couldn't say which pet a task was for. I gave `Pet` and `Task` a unique `id` and added `Task.pet_id`, which `Pet.add_task` sets. `Owner.find_pet()` looks a pet up by id.
- **Tasks have identity.** Dataclasses compare by value, so two identical "Walk" tasks were equal, which made `remove_task` and `edit_task` ambiguous and left tasks unhashable. I set `eq=False` on `Task` and `Pet` and changed those methods to take a `task_id`.
- **Removed `Owner.create_plan`.** `Owner` and `Scheduler` depended on each other. The UI now calls `Scheduler(owner).generate_plan(date)`, so the dependency runs one way.
- **Recurring tasks can be completed per day.** A `completed` flag would stay true tomorrow for a daily task, and `is_due` had nothing to compare against. I replaced it with `last_completed` and added `due_date`, and `mark_complete` now takes a date.
- **The owner has a time window.** A minutes budget alone can't produce clock times, so I added `day_start` and `day_end` to `Owner`.
- **Scheduler results keep their reasons.** `fit_to_time_budget` now returns the scheduled and skipped tasks, with a reason for each skip. `detect_conflicts` returns pairs of tasks. I added `ScheduledItem` and `SkippedTask` dataclasses to replace untyped tuples.
- **One source for the explanation.** I removed `Scheduler.explain` and `DailyPlan.total_minutes`. The scheduler records a reason on each item, and `DailyPlan.get_explanation()` and `total_duration()` derive their output from those items, so nothing goes stale or is stored twice.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
- Why is that tradeoff reasonable for this scenario?

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
