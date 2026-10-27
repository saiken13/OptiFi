from datetime import date
from decimal import Decimal

from sqlalchemy import select, func

from models.goal import Goal
from models.message import Message


async def record_goal_contribution(db, user_id, plan, available_goals):
    """Update saved progress; moving money into savings is not new income."""
    def clarify(question):
        return {
            "response": question + " No savings progress has been changed yet.",
            "structured_data": {"goal_action": "needs_contribution_details", "pending_goal": plan.model_dump(mode="json")},
        }

    if not plan.name or plan.name.casefold() not in {g.name.casefold() for g in available_goals}:
        names = ", ".join(g.name for g in available_goals)
        return clarify(f"Which existing goal should receive this savings contribution? Your goals are: {names}." if names
                       else "You don't have an existing savings goal to update. Please create a goal with a target amount first.")
    if plan.contribution_amount is None:
        return clarify(f"How much did you add to {plan.name}?")
    contribution_date = plan.contribution_date or date.today()
    if contribution_date > date.today():
        return clarify("That date is in the future. When did you actually add the savings?")
    goal = (await db.execute(select(Goal).where(
        Goal.user_id == user_id, func.lower(Goal.name) == plan.name.casefold(),
    ).with_for_update())).scalar_one_or_none()
    if goal is None:
        return clarify("I couldn't find that goal. Please give its exact name from the Goals page.")
    if goal.status != "active":
        return clarify(f"{goal.name} is {goal.status}. Please choose an active goal.")

    amount = plan.contribution_amount
    # The assistant message is the contribution receipt, saved in the same transaction.
    duplicate = (await db.execute(select(Message).where(
        Message.user_id == user_id, Message.role == "assistant",
        Message.structured_data["goal_action"].astext == "contribution_recorded",
        Message.structured_data["goal_id"].astext == str(goal.id),
        Message.structured_data["contribution_amount"].astext == format(amount, ".2f"),
        Message.structured_data["contribution_date"].astext == contribution_date.isoformat(),
    ).limit(1))).scalar_one_or_none()
    if duplicate:
        return {
            "response": f"A ${amount:,.2f} contribution to {goal.name} on {contribution_date} is already recorded. I haven't added it again. Check your chat history before recording another contribution.",
            "structured_data": {"goal_action": "already_recorded", "goal_id": str(goal.id)},
        }
    before = Decimal(str(goal.current_amount)).quantize(Decimal("0.01"))
    after = before + amount
    if after > Decimal("9999999999.99"):
        return clarify("That would exceed the supported goal balance. Please check the contribution amount.")
    goal.current_amount = after
    # Keep the goal active so it remains visible to existing analysis paths.
    await db.flush()
    target = Decimal(str(goal.target_amount))
    percent = after / target * 100 if target > 0 else Decimal("0")
    return {
        "response": (
            f"Added ${amount:,.2f} to {goal.name}. Your saved amount increased from ${before:,.2f} "
            f"to ${after:,.2f} toward your ${target:,.2f} target ({percent:.1f}%). "
            "The target and monthly contribution setting are unchanged."
        ),
        "structured_data": {
            "goal_action": "contribution_recorded", "goal_id": str(goal.id),
            "contribution_amount": format(amount, ".2f"), "contribution_date": contribution_date.isoformat(),
            "previous_amount": float(before), "current_amount": float(after),
            "target_amount": float(target), "percent_complete": float(percent),
        },
    }
