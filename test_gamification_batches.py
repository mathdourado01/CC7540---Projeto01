from pprint import pprint

from services.gamification_service import simulate_gamification_batches


def main():
    """
    Simulação interna da HU5 sem acessar o Supabase.

    Objetivo:
    - validar processamento em lote;
    - validar que registros duplicados não somam novamente;
    - validar que conquistas não são liberadas duas vezes;
    - apoiar testes internos antes de testar pelo Streamlit.
    """

    test_batches = [
        {
            "name": "Lote 1 - primeira sessão e duplicidade",
            "records": [
                {
                    "processing_key": "REQ-001",
                    "subject_name": "Matemática",
                    "studied_minutes": 60,
                    "studied_at": "2026-05-01",
                    "reference_date": "2026-05-01",
                },
                {
                    "processing_key": "REQ-001",
                    "subject_name": "Matemática",
                    "studied_minutes": 60,
                    "studied_at": "2026-05-01",
                    "reference_date": "2026-05-01",
                },
            ],
            "expected": {
                "processed_count": 1,
                "duplicated_count": 1,
                "total_minutes": 60,
                "unlocked_codes": ["first_session", "one_hour_total"],
                "total_points": 30,
            },
        },
        {
            "name": "Lote 2 - múltiplas sessões e streak de 3 dias",
            "records": [
                {
                    "processing_key": "REQ-101",
                    "subject_name": "Programação",
                    "studied_minutes": 30,
                    "studied_at": "2026-05-01",
                    "reference_date": "2026-05-03",
                },
                {
                    "processing_key": "REQ-102",
                    "subject_name": "Banco de Dados",
                    "studied_minutes": 45,
                    "studied_at": "2026-05-02",
                    "reference_date": "2026-05-03",
                },
                {
                    "processing_key": "REQ-103",
                    "subject_name": "Engenharia de Software",
                    "studied_minutes": 50,
                    "studied_at": "2026-05-03",
                    "reference_date": "2026-05-03",
                },
            ],
            "expected": {
                "processed_count": 3,
                "duplicated_count": 0,
                "total_minutes": 125,
                "unlocked_codes": [
                    "first_session",
                    "three_sessions",
                    "one_hour_total",
                    "streak_3_days",
                ],
                "total_points": 80,
            },
        },
        {
            "name": "Lote 3 - 5 horas, 10 sessões e duplicidades misturadas",
            "records": [
                {
                    "processing_key": "REQ-201",
                    "subject_name": "IA",
                    "studied_minutes": 30,
                    "studied_at": "2026-05-01",
                    "reference_date": "2026-05-10",
                },
                {
                    "processing_key": "REQ-202",
                    "subject_name": "IA",
                    "studied_minutes": 30,
                    "studied_at": "2026-05-02",
                    "reference_date": "2026-05-10",
                },
                {
                    "processing_key": "REQ-203",
                    "subject_name": "IA",
                    "studied_minutes": 30,
                    "studied_at": "2026-05-03",
                    "reference_date": "2026-05-10",
                },
                {
                    "processing_key": "REQ-204",
                    "subject_name": "IA",
                    "studied_minutes": 30,
                    "studied_at": "2026-05-04",
                    "reference_date": "2026-05-10",
                },
                {
                    "processing_key": "REQ-205",
                    "subject_name": "IA",
                    "studied_minutes": 30,
                    "studied_at": "2026-05-05",
                    "reference_date": "2026-05-10",
                },
                {
                    "processing_key": "REQ-206",
                    "subject_name": "IA",
                    "studied_minutes": 30,
                    "studied_at": "2026-05-06",
                    "reference_date": "2026-05-10",
                },
                {
                    "processing_key": "REQ-207",
                    "subject_name": "IA",
                    "studied_minutes": 30,
                    "studied_at": "2026-05-07",
                    "reference_date": "2026-05-10",
                },
                {
                    "processing_key": "REQ-208",
                    "subject_name": "IA",
                    "studied_minutes": 30,
                    "studied_at": "2026-05-08",
                    "reference_date": "2026-05-10",
                },
                {
                    "processing_key": "REQ-209",
                    "subject_name": "IA",
                    "studied_minutes": 30,
                    "studied_at": "2026-05-09",
                    "reference_date": "2026-05-10",
                },
                {
                    "processing_key": "REQ-210",
                    "subject_name": "IA",
                    "studied_minutes": 30,
                    "studied_at": "2026-05-10",
                    "reference_date": "2026-05-10",
                },
                {
                    "processing_key": "REQ-210",
                    "subject_name": "IA",
                    "studied_minutes": 30,
                    "studied_at": "2026-05-10",
                    "reference_date": "2026-05-10",
                },
            ],
            "expected": {
                "processed_count": 10,
                "duplicated_count": 1,
                "total_minutes": 300,
                "unlocked_codes": [
                    "first_session",
                    "three_sessions",
                    "ten_sessions",
                    "one_hour_total",
                    "five_hours_total",
                    "streak_3_days",
                    "streak_7_days",
                ],
                "total_points": 250,
            },
        },
    ]

    results = simulate_gamification_batches(test_batches)

    print("\n=== Resultado da simulação da HU5 ===\n")

    for result in results:
        print(f"--- {result['batch_name']} ---")
        print(f"Registros recebidos: {result['records_received']}")
        print(f"Registros processados: {result['processed_count']}")
        print(f"Registros duplicados ignorados: {result['duplicated_count']}")
        print(f"Minutos finais: {result['final_metrics']['total_minutes']}")
        print(f"Streak atual: {result['final_metrics']['current_streak']}")
        print(f"Maior streak: {result['final_metrics']['highest_streak']}")
        print(f"Pontos totais: {result['total_points']}")
        print(f"Conquistas liberadas: {', '.join(result['unlocked_codes']) or '-'}")
        print(f"Expectativas atendidas: {result['all_expectations_match']}")

        if not result["all_expectations_match"]:
            print("\nDetalhe das expectativas:")
            pprint(result["expectation_checks"])

        print()

    all_passed = all(result["all_expectations_match"] for result in results)

    if all_passed:
        print("✅ Todos os lotes passaram nas expectativas definidas.")
    else:
        print("❌ Pelo menos um lote não bateu com as expectativas definidas.")


if __name__ == "__main__":
    main()