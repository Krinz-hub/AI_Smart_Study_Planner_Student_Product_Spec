import pytest
from httpx import AsyncClient
from app.onboarding.fact_checker import fact_check_academic_institution
from app.onboarding.discovery import discover_academic_syllabus
from tests.test_student_state import create_authenticated_user


@pytest.mark.asyncio
async def test_fact_check_canonical_university():
    """Verifies that recognized universities pass fact check with authentic portals."""
    res = await fact_check_academic_institution(
        academic_type="COLLEGE",
        details={"university": "Anna University", "degree": "B.Tech", "branch": "Computer Science"},
    )
    assert res.is_verified is True
    assert res.institution_type == "UNIVERSITY"
    assert "Anna University" in res.canonical_name
    assert res.official_portal_url == "https://www.annauniv.edu"
    assert res.confidence_score >= 0.95
    assert res.warning_flag is None


@pytest.mark.asyncio
async def test_fact_check_fictional_or_invalid_university():
    """Verifies that fictional or non-existent institutions are flagged and not given fabricated URLs."""
    res = await fact_check_academic_institution(
        academic_type="COLLEGE",
        details={"university": "Hogwarts School of Witchcraft", "degree": "B.Tech", "branch": "Magic"},
    )
    assert res.is_verified is False
    assert res.confidence_score <= 0.40
    assert res.warning_flag is not None
    assert "Unverified" in res.warning_flag or "fictional" in res.warning_flag.lower()


@pytest.mark.asyncio
async def test_fact_check_school_board():
    """Verifies that recognized boards (e.g. CBSE) pass verification with official links."""
    res = await fact_check_academic_institution(
        academic_type="SCHOOL",
        details={"board": "CBSE", "grade": "Class 12"},
    )
    assert res.is_verified is True
    assert res.institution_type == "SCHOOL"
    assert "CBSE" in res.canonical_name
    assert "cbseacademic.nic.in" in res.official_portal_url
    assert res.confidence_score >= 0.90


@pytest.mark.asyncio
async def test_discipline_specific_syllabus_generation():
    """Verifies that mechanical engineering gets mechanical curriculum, not CS."""
    mech_res = await discover_academic_syllabus(
        academic_type="COLLEGE",
        details={"university": "Anna University", "degree": "B.Tech", "branch": "Mechanical Engineering"},
    )
    subject_names = [s.name for s in mech_res.subjects]
    assert "Thermodynamics" in subject_names
    assert "Fluid Mechanics" in subject_names
    assert "Operating Systems" not in subject_names


@pytest.mark.asyncio
async def test_onboarding_discovery_endpoint_contract(async_client: AsyncClient):
    """Verifies full onboarding discovery endpoint returns fact-checking contract."""
    user = await create_authenticated_user(async_client, "fact_check_student")

    # 1. Set academic type
    await async_client.post(
        "/api/v1/onboarding/academic-type",
        headers=user["headers"],
        json={"academic_type": "COLLEGE"},
    )

    # 2. Set academic profile
    await async_client.post(
        "/api/v1/onboarding/academic-profile",
        headers=user["headers"],
        json={
            "details": {
                "country": "India",
                "university": "Visvesvaraya Technological University",
                "degree": "B.E.",
                "branch": "Computer Science & Engineering",
                "year": 2,
                "semester": 3,
            }
        },
    )

    # 3. Discover syllabus
    disc_res = await async_client.post(
        "/api/v1/onboarding/discover-syllabus",
        headers=user["headers"],
    )
    assert disc_res.status_code == 200
    data = disc_res.json()
    assert data["institution_verified"] is True
    assert data["verification_status"] == "VERIFIED"
    assert "VTU" in data["institution_name"] or "Visvesvaraya" in data["institution_name"]
    assert len(data["subjects"]) >= 3
    # Check that sources don't contain fake domains
    for source in data["sources"]:
        assert not source["url"].endswith(".ac.in/academic-curriculum/syllabus")
