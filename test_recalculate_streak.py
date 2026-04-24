from datetime import date
from services.dashboard_service import recalculate_streaks_from_history


history = [
    {"studied_at": "2026-04-23"},
    {"studied_at": "2026-04-23"},
    {"studied_at": "2026-04-22"},
    {"studied_at": "2026-04-20"},
]

result = recalculate_streaks_from_history(
    history,
    reference_date=date(2026, 4, 23),
)

print(result)

assert result["current_streak"] == 2
assert result["highest_streak"] == 2
assert result["streak_broken"] is False
assert result["total_unique_study_days"] == 3

print("Recalculo do histórico validado com sucesso.")