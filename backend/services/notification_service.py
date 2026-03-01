import httpx
from typing import Optional
from database import settings


class NotificationService:
    async def send_push(self, player_id: str, title: str, message: str, data: Optional[dict] = None) -> bool:
        if not settings.ONESIGNAL_APP_ID or not settings.ONESIGNAL_REST_API_KEY:
            return False

        payload = {
            "app_id": settings.ONESIGNAL_APP_ID,
            "include_player_ids": [player_id],
            "headings": {"en": title},
            "contents": {"en": message},
        }
        if data:
            payload["data"] = data

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    "https://onesignal.com/api/v1/notifications",
                    headers={
                        "Authorization": f"Basic {settings.ONESIGNAL_REST_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                return response.status_code == 200
        except Exception:
            return False

    async def send_budget_alert(self, player_id: str, category: str, percent_used: float) -> bool:
        title = "Budget Alert"
        message = f"You've used {percent_used:.0f}% of your {category} budget this month."
        return await self.send_push(player_id, title, message, {"type": "budget_alert", "category": category})

    async def send_goal_milestone(self, player_id: str, goal_name: str, milestone: int) -> bool:
        title = "Goal Milestone!"
        message = f"You've reached {milestone}% of your '{goal_name}' goal. Keep it up!"
        return await self.send_push(player_id, title, message, {"type": "goal_milestone"})
