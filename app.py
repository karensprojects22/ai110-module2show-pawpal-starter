from datetime import date, time

import streamlit as st

from pawpal_system import Owner, Pet, Priority, Recurrence, Scheduler, Task

PRIORITY_ICON = {Priority.HIGH: "🔴", Priority.MEDIUM: "🟡", Priority.LOW: "🟢"}
SPECIES_ICON = {"dog": "🐶", "cat": "🐱"}


def priority_label(priority: Priority) -> str:
    return f"{PRIORITY_ICON[priority]} {priority.name.title()}"

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")

st.markdown(
    """
Welcome to the PawPal+ starter app.

This file is intentionally thin. It gives you a working Streamlit app so you can start quickly,
but **it does not implement the project logic**. Your job is to design the system and build it.

Use this app as your interactive demo once your backend classes/functions exist.
"""
)

with st.expander("Scenario", expanded=True):
    st.markdown(
        """
**PawPal+** is a pet care planning assistant. It helps a pet owner plan care tasks
for their pet(s) based on constraints like time, priority, and preferences.

You will design and implement the scheduling logic and connect it to this Streamlit UI.
"""
    )

with st.expander("What you need to build", expanded=True):
    st.markdown(
        """
At minimum, your system should:
- Represent pet care tasks (what needs to happen, how long it takes, priority)
- Represent the pet and the owner (basic info and preferences)
- Build a plan/schedule for a day that chooses and orders tasks based on constraints
- Explain the plan (why each task was chosen and when it happens)
"""
    )

st.divider()

# Streamlit reruns this script on every interaction, so the Owner lives in
# session_state and is only created the first time.
if "owner" not in st.session_state:
    st.session_state.owner = Owner("Jordan", available_minutes_per_day=120)
owner: Owner = st.session_state.owner
scheduler = Scheduler(owner)  # cheap to build; reads the owner's pets and tasks each run

st.subheader("Owner")
owner.name = st.text_input("Owner name", value=owner.name)
owner.set_availability(
    int(
        st.number_input(
            "Time available today (minutes)",
            min_value=0,
            max_value=1440,
            step=15,
            value=owner.available_minutes_per_day,
        )
    )
)

st.subheader("Add a Pet")
col1, col2 = st.columns(2)
with col1:
    pet_name = st.text_input("Pet name", value="Mochi")
with col2:
    species = st.selectbox("Species", ["dog", "cat", "other"])

if st.button("Add pet"):
    if pet_name.strip():
        owner.add_pet(Pet(pet_name.strip(), species))
    else:
        st.error("Give your pet a name first.")

if owner.pets:
    for existing in owner.pets:
        st.caption(f"{SPECIES_ICON.get(existing.species, '🐾')} {existing.describe()}")
else:
    st.info("No pets yet. Add one above.")

st.markdown("### Tasks")
st.caption("Tasks belong to a pet. The scheduler plans all pets' tasks together.")

if owner.pets:
    # Select by id: the selectbox may hand back a copy of an object, so look the
    # real Pet up on the owner instead of using the returned value directly.
    pet_id = st.selectbox(
        "Pet",
        [p.id for p in owner.pets],
        format_func=lambda pid: owner.find_pet(pid).name,
    )
    pet = owner.find_pet(pet_id)

    col1, col2 = st.columns(2)
    with col1:
        task_title = st.text_input("Task title", value="Morning walk")
    with col2:
        category = st.selectbox(
            "Category", ["walk", "feeding", "meds", "enrichment", "grooming", "other"]
        )

    col1, col2, col3 = st.columns(3)
    with col1:
        duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
    with col2:
        priority = st.selectbox("Priority", ["low", "medium", "high"], index=2)
    with col3:
        repeats = st.selectbox("Repeats", ["none", "daily", "weekly"])

    use_time = st.checkbox("Set a preferred time")
    preferred_time = st.time_input("Preferred time", value=time(8, 0)) if use_time else None

    if st.button("Add task"):
        if task_title.strip():
            pet.add_task(
                Task(
                    task_title.strip(),
                    category,
                    int(duration),
                    Priority[priority.upper()],
                    preferred_time=preferred_time,
                    recurrence=Recurrence(repeats),
                )
            )
        else:
            st.error("Give the task a title first.")
else:
    st.info("Add a pet before adding tasks.")

pending = scheduler.sort_by_time(owner.filter_tasks(completed=False))
if pending:
    task_id = st.selectbox(
        "Mark a task complete",
        [t.id for t in pending],
        format_func=lambda tid: next(
            f"{t.title} ({owner.find_pet(t.pet_id).name})" for t in pending if t.id == tid
        ),
    )
    if st.button("Mark complete"):
        task = next(t for t in pending if t.id == task_id)
        following = owner.find_pet(task.pet_id).complete_task(task.id, date.today())
        if following is not None:
            st.success(f"Done. Next {following.title} is due {following.due_date}.")
        else:
            st.success("Done.")
        pending = scheduler.sort_by_time(owner.filter_tasks(completed=False))  # refresh

due_today = [t for t in pending if t.is_due(date.today())]

if owner.get_all_tasks():
    needed = sum(t.duration_minutes for t in due_today)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Pets", len(owner.pets))
    m2.metric("Pending tasks", len(pending))
    m3.metric("Minutes needed today", needed)
    m4.metric("Minutes available", owner.available_minutes_per_day)
    if needed > owner.available_minutes_per_day:
        st.warning(
            f"Today's tasks need {needed} min but you have "
            f"{owner.available_minutes_per_day} min, so lower-priority tasks will be skipped."
        )

    col1, col2 = st.columns(2)
    with col1:
        pet_filter = st.selectbox("Show pet", ["All"] + [p.name for p in owner.pets])
    with col2:
        status_filter = st.selectbox("Show status", ["All", "Pending", "Completed"])

    shown = owner.filter_tasks(
        pet_name=None if pet_filter == "All" else pet_filter,
        completed={"All": None, "Pending": False, "Completed": True}[status_filter],
    )
    st.markdown(f"**Tasks** ({len(shown)} shown, sorted by preferred time)")
    if shown:
        st.dataframe(
            [
                {
                    "Time": f"{task.preferred_time:%H:%M}" if task.preferred_time else "any",
                    "Pet": owner.find_pet(task.pet_id).name,
                    "Task": task.title,
                    "Category": task.category.title(),
                    "Min": task.duration_minutes,
                    "Priority": priority_label(task.priority),
                    "Repeats": task.recurrence.value.title(),
                    "Due": task.due_date.isoformat() if task.due_date else "-",
                    "Status": "✅ Done" if task.last_completed else "⏳ Pending",
                }
                for task in scheduler.sort_by_time(shown)
            ],
            hide_index=True,
        )
    else:
        st.info("No tasks match these filters.")
elif owner.pets:
    st.info("No tasks yet. Add one above.")

# Warn about clashing preferred times as soon as they exist, before a plan is built.
conflicts = scheduler.conflict_warnings(due_today)
if conflicts:
    st.warning(
        f"**{len(conflicts)} time conflict(s)**\n\n"
        + "\n".join(f"- {message}" for message in conflicts)
        + "\n\nGenerate a schedule and the lower-ranked task moves to the nearest free slot."
    )

st.divider()

st.subheader("Build Schedule")
st.caption("Plans every pet's due tasks for today within your available time.")

if st.button("Generate schedule"):
    st.session_state.show_plan = True

# Rebuilt on every run once requested, so the plan stays visible and never goes stale
# when other widgets change.
if st.session_state.get("show_plan"):
    plan = scheduler.generate_plan(date.today())
    total = len(plan.scheduled_items) + len(plan.skipped_tasks)

    if plan.scheduled_items:
        st.success(
            f"Scheduled {len(plan.scheduled_items)} of {total} task(s) "
            f"for {date.today():%A, %B %d}."
        )
        planned = plan.total_duration()
        m1, m2, m3 = st.columns(3)
        m1.metric("Tasks scheduled", len(plan.scheduled_items))
        m2.metric("Minutes planned", planned)
        m3.metric("Minutes free", owner.available_minutes_per_day - planned)
        st.dataframe(
            [
                {
                    "Time": f"{row['Start']}-{row['End']}",
                    "Pet": owner.find_pet(item.task.pet_id).name,
                    "Task": row["Task"],
                    "Category": row["Category"].title(),
                    "Min": row["Duration (min)"],
                    "Priority": priority_label(item.task.priority),
                    "Why": row["Why"],
                }
                for item, row in zip(plan.scheduled_items, plan.to_rows())
            ],
            hide_index=True,
        )
    else:
        st.warning("Nothing could be scheduled today. Add tasks or increase your available time.")

    if plan.warnings:
        st.info(
            f"{len(plan.warnings)} time conflict(s) were resolved by moving the "
            "lower-ranked task to the nearest free slot."
        )

    if plan.skipped_tasks:
        st.warning(
            f"**{len(plan.skipped_tasks)} task(s) could not be scheduled**\n\n"
            + "\n".join(
                f"- {s.task.title} ({owner.find_pet(s.task.pet_id).name}): {s.reason}"
                for s in plan.skipped_tasks
            )
        )

    with st.expander("Why this plan?"):
        st.text(plan.get_explanation())
