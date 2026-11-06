"""API-level acceptance case that complements M2's in-memory graph matrix."""

import pytest


@pytest.mark.integration
async def test_nonexistent_course_returns_not_found(
    async_client, test_session, make_student, login_as
):
    student = await make_student(test_session)
    await test_session.commit()

    response = await async_client.get(
        "/api/v1/prerequisites/check?course_id=2147483647",
        headers=login_as(student),
    )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "NOT_FOUND"
