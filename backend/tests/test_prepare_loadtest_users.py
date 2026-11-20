from app.tools.prepare_loadtest_users import _student_account_order


def test_generated_students_are_preferred_over_seeded_kit_accounts():
    generated = {"role": "student", "mssv": "SV0055"}
    kit = {"role": "student", "mssv": "SV0001"}

    assert _student_account_order(generated) < _student_account_order(kit)
