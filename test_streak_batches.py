from services.dashboard_service import simulate_streak_batches


test_cases = [
    {
        "name": "Sem registros",
        "study_dates": [],
        "reference_date": "2026-04-23",
        "expected_current_streak": 0,
        "expected_highest_streak": 0,
        "expected_streak_broken": False,
    },
    {
        "name": "Primeiro dia de estudo",
        "study_dates": ["2026-04-23"],
        "reference_date": "2026-04-23",
        "expected_current_streak": 1,
        "expected_highest_streak": 1,
        "expected_streak_broken": False,
    },
    {
        "name": "Dias consecutivos",
        "study_dates": ["2026-04-23", "2026-04-22", "2026-04-21"],
        "reference_date": "2026-04-23",
        "expected_current_streak": 3,
        "expected_highest_streak": 3,
        "expected_streak_broken": False,
    },
    {
        "name": "Mesmo dia repetido não duplica streak",
        "study_dates": ["2026-04-23", "2026-04-23", "2026-04-22"],
        "reference_date": "2026-04-23",
        "expected_current_streak": 2,
        "expected_highest_streak": 2,
        "expected_streak_broken": False,
    },
    {
        "name": "Buraco no histórico",
        "study_dates": ["2026-04-23", "2026-04-21", "2026-04-20"],
        "reference_date": "2026-04-23",
        "expected_current_streak": 1,
        "expected_highest_streak": 2,
        "expected_streak_broken": False,
    },
    {
        "name": "Streak quebrada",
        "study_dates": ["2026-04-20", "2026-04-19"],
        "reference_date": "2026-04-23",
        "expected_current_streak": 0,
        "expected_highest_streak": 2,
        "expected_streak_broken": True,
    },
]


results = simulate_streak_batches(test_cases)

print("\nRESULTADOS DOS TESTES DE STREAK\n")

all_ok = True

for result in results:
    print(f"Cenário: {result['case_name']}")
    print(f"  Datas informadas: {result['input_study_dates']}")
    print(f"  Datas únicas: {result['unique_study_dates']}")
    print(f"  Current streak: {result['current_streak']}")
    print(f"  Highest streak: {result['highest_streak']}")
    print(f"  Streak broken: {result['streak_broken']}")
    print(f"  Tudo ok? {result['all_expectations_match']}")
    print("-" * 60)

    if not result["all_expectations_match"]:
        all_ok = False

if not all_ok:
    raise AssertionError("Um ou mais cenários falharam.")

print("Todos os cenários passaram com sucesso.")