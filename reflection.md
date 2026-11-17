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

**Tradeoff: the scheduler warns about time conflicts and fixes them itself, based only on preferred times.**

- **What it does.** `Scheduler.conflict_warnings` compares the time span of each task that has a `preferred_time` (start to start plus duration), so a 30-minute walk at 08:00 conflicts with a task at 08:15, not just one at exactly 08:00. It returns a warning message and never raises an error. `generate_plan` then keeps both tasks and moves the lower-ranked one to the nearest free slot, so the final plan never has overlapping tasks.
- **What it gives up.**
  - Only tasks with a preferred time can conflict. A task with no time is simply placed in a gap, so it is never reported.
  - The owner isn't asked which task should win. Priority decides, then the shorter task, and the loser can end up away from the time they wanted. It can even be skipped if the day is full.
  - The scheduler is fixed to one owner's single timeline. It doesn't model two things happening at once, such as walking two pets together, and flags them as a conflict.
- **Why it is reasonable.** Pet-care times are mostly preferences, not appointments. A walk at 08:10 instead of 08:00 rarely matters, so a plan that always works and tells the owner what it moved is more useful than one that stops with an error or demands a decision for every clash. The warning keeps the owner informed, and the reason shown beside each moved task explains why it moved. I also kept the check small, a sort plus one pass, so it is easy to read and test.
- **What I'd change with more time.** Add a way to mark a task as fixed (a vet visit or medication at a set time) so it never moves, and let the owner choose which task yields.

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

I used AI at every stage, in roughly this order:

- **Design brainstorming.** I asked for the main objects with their attributes and methods, and it proposed `Owner`, `Pet`, `Task`, `Scheduler` and `DailyPlan`. It also suggested making walking and feeding `Task` objects rather than pet actions.
- **Drafting.** I asked it to turn that into a Mermaid class diagram, then into dataclass stubs, then to fill in the logic, the demo script and the tests.
- **Design review.** I asked it to review my own skeleton for missing relationships and logic bottlenecks. This was the most useful prompt, because it found real flaws before any logic existed.
- **Documentation.** It drafted the docstrings, the README sections and the reflection text. I edit them so they match what I built.

The most helpful prompts were specific and gave it something concrete to check, such as "review my skeleton" or "how should the Scheduler retrieve all tasks from the Owner's pets?". Open requests like "brainstorm the objects" gave a starting point that I still had to question.

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

**What the AI suggested, and what I accepted or rejected.** The review of my skeleton produced a list of problems in three groups: missing relationships, logic gaps, and smaller cleanups plus a bottleneck note. I accepted the first two groups and left the rest out:

- Accepted: tasks linked to their pet, task ids with identity-based equality, removing the circular `Owner.create_plan`, replacing `completed` with `last_completed` and `due_date`, a day window on `Owner`, scheduler results that keep reasons, and one source for the explanation.
- Not taken: the smaller cleanups (renaming `DailyPlan.date`, dropping `priority_score`, changing `get_tasks` to a status enum) and the idea of a `required` flag so medication is never skipped. They didn't block the requirements, so I kept the scope smaller. The `required` flag is the one I'd add first, because right now a medication can be skipped when time runs out.
- Also not taken: its suggestion to redesign the terminal output as a table. I kept the simple format and pasted the real `main.py` output into the README.

I did not take the AI's first design as correct either. Its own initial design had flaws, such as `Owner.create_plan` making `Owner` and `Scheduler` depend on each other, and a `completed` flag that would stay true for a daily task the next day. Asking it to review its own work found them.

**How I verified the result.**
- I ran code instead of trusting the explanations. I created two identical "Walk" tasks to confirm they compare unequal and stay distinct in a set, and I ran a small scenario to see the plan the scheduler produced.
- I wrote pytest tests, including one with two pets to check that the scheduler reads tasks from every pet and that the pets share one time budget. All five tests pass.
- I ran `python main.py` and read the schedule against my expectations, for example that tasks landed at their preferred times and that the totals added up.
- I compared the UML diagram with the code after each design change, so the two stayed in sync.

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
