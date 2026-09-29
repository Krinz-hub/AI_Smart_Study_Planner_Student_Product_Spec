import re
import urllib.parse
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import httpx
from app.common.logging import get_logger

logger = get_logger("academic_fact_checker")


@dataclass
class InstitutionVerificationResult:
    is_verified: bool
    canonical_name: str
    institution_type: str  # UNIVERSITY, SCHOOL_BOARD, SCHOOL, COMPETITIVE_EXAM, UNKNOWN
    accreditation_body: str
    official_portal_url: Optional[str]
    confidence_score: float
    verification_notes: str
    warning_flag: Optional[str] = None


# Canonical Curated Directory of Recognized Institutions
CANONICAL_UNIVERSITIES: Dict[str, Dict[str, str]] = {
    "anna university": {
        "canonical_name": "Anna University, Chennai",
        "official_url": "https://www.annauniv.edu",
        "accreditation": "State Public University / UGC Recognized / NAAC A++",
    },
    "delhi university": {
        "canonical_name": "University of Delhi (DU)",
        "official_url": "https://www.du.ac.in",
        "accreditation": "Central University / UGC Recognized / Institution of Eminence",
    },
    "mumbai university": {
        "canonical_name": "University of Mumbai",
        "official_url": "https://mu.ac.in",
        "accreditation": "State University / UGC Recognized / NAAC A++",
    },
    "vtu": {
        "canonical_name": "Visvesvaraya Technological University (VTU)",
        "official_url": "https://vtu.ac.in",
        "accreditation": "State Technological University / AICTE & UGC Recognized",
    },
    "visvesvaraya technological university": {
        "canonical_name": "Visvesvaraya Technological University (VTU)",
        "official_url": "https://vtu.ac.in",
        "accreditation": "State Technological University / AICTE & UGC Recognized",
    },
    "jntu": {
        "canonical_name": "Jawaharlal Nehru Technological University (JNTU)",
        "official_url": "https://jntuh.ac.in",
        "accreditation": "State Technological University / UGC & AICTE Approved",
    },
    "iit madras": {
        "canonical_name": "Indian Institute of Technology Madras (IITM)",
        "official_url": "https://www.iitm.ac.in",
        "accreditation": "Institute of National Importance (INI) / NIRF Rank 1",
    },
    "iit bombay": {
        "canonical_name": "Indian Institute of Technology Bombay (IITB)",
        "official_url": "https://www.iitb.ac.in",
        "accreditation": "Institute of National Importance (INI) / NIRF Top 3",
    },
    "iit delhi": {
        "canonical_name": "Indian Institute of Technology Delhi (IITD)",
        "official_url": "https://home.iitd.ac.in",
        "accreditation": "Institute of National Importance (INI) / NIRF Top 3",
    },
    "bits pilani": {
        "canonical_name": "Birla Institute of Technology and Science, Pilani (BITS)",
        "official_url": "https://www.bits-pilani.ac.in",
        "accreditation": "Institution of Eminence Deemed University / UGC Approved",
    },
    "vit": {
        "canonical_name": "Vellore Institute of Technology (VIT)",
        "official_url": "https://vit.ac.in",
        "accreditation": "Institution of Eminence Deemed University / NAAC A++",
    },
    "vellore institute of technology": {
        "canonical_name": "Vellore Institute of Technology (VIT)",
        "official_url": "https://vit.ac.in",
        "accreditation": "Institution of Eminence Deemed University / NAAC A++",
    },
    "mit": {
        "canonical_name": "Massachusetts Institute of Technology (MIT)",
        "official_url": "https://www.mit.edu",
        "accreditation": "NECHE Accredited Private Research University (USA)",
    },
    "harvard": {
        "canonical_name": "Harvard University",
        "official_url": "https://www.harvard.edu",
        "accreditation": "NECHE Accredited Ivy League Research University (USA)",
    },
    "stanford": {
        "canonical_name": "Stanford University",
        "official_url": "https://www.stanford.edu",
        "accreditation": "WSCUC Accredited Private Research University (USA)",
    },
    "oxford": {
        "canonical_name": "University of Oxford",
        "official_url": "https://www.ox.ac.uk",
        "accreditation": "Royal Charter / Russell Group (United Kingdom)",
    },
    "cambridge": {
        "canonical_name": "University of Cambridge",
        "official_url": "https://www.cam.ac.uk",
        "accreditation": "Royal Charter / Russell Group (United Kingdom)",
    },
    "tribhuvan university": {
        "canonical_name": "Tribhuvan University (TU)",
        "official_url": "https://tu.edu.np",
        "accreditation": "National Autonomous University of Nepal / UGC Nepal",
    },
    "kathmandu university": {
        "canonical_name": "Kathmandu University (KU)",
        "official_url": "https://ku.edu.np",
        "accreditation": "Autonomous Public Institution of Nepal / UGC Nepal",
    },
}

CANONICAL_BOARDS: Dict[str, Dict[str, str]] = {
    "cbse": {
        "canonical_name": "Central Board of Secondary Education (CBSE)",
        "official_url": "https://cbseacademic.nic.in",
        "accreditation": "National Board of Education (Ministry of Education, Govt. of India)",
    },
    "icse": {
        "canonical_name": "Council for the Indian School Certificate Examinations (CISCE / ICSE)",
        "official_url": "https://cisce.org",
        "accreditation": "National Examination Board (India)",
    },
    "cisce": {
        "canonical_name": "Council for the Indian School Certificate Examinations (CISCE)",
        "official_url": "https://cisce.org",
        "accreditation": "National Examination Board (India)",
    },
    "ib": {
        "canonical_name": "International Baccalaureate (IB Diploma Programme)",
        "official_url": "https://www.ibo.org",
        "accreditation": "International Educational Foundation (Geneva, Switzerland)",
    },
    "cambridge": {
        "canonical_name": "Cambridge Assessment International Education (CAIE / IGCSE)",
        "official_url": "https://www.cambridgeinternational.org",
        "accreditation": "University of Cambridge Local Examinations Syndicate",
    },
    "state board": {
        "canonical_name": "State Secondary & Higher Secondary Education Board",
        "official_url": "https://education.gov.in/school-education",
        "accreditation": "Recognized Department of School Education",
    },
    "maharashtra state board": {
        "canonical_name": "Maharashtra State Board of Secondary and Higher Secondary Education (MSBSHSE)",
        "official_url": "https://mahahsscboard.in",
        "accreditation": "State Board of Education (Maharashtra, India)",
    },
    "karnataka state board": {
        "canonical_name": "Karnataka School Examination and Assessment Board (KSEAB)",
        "official_url": "https://kseab.karnataka.gov.in",
        "accreditation": "State Board of Education (Karnataka, India)",
    },
}

CANONICAL_EXAMS: Dict[str, Dict[str, str]] = {
    "jee main": {
        "canonical_name": "Joint Entrance Examination (Main) - JEE Main",
        "official_url": "https://jeemain.nta.nic.in",
        "accreditation": "National Testing Agency (NTA), Ministry of Education",
    },
    "jee advanced": {
        "canonical_name": "Joint Entrance Examination (Advanced) - JEE Advanced",
        "official_url": "https://jeeadv.ac.in",
        "accreditation": "IIT Joint Admission Board (JAB)",
    },
    "neet": {
        "canonical_name": "National Eligibility cum Entrance Test (UG) - NEET",
        "official_url": "https://neet.nta.nic.in",
        "accreditation": "National Testing Agency (NTA) & National Medical Commission",
    },
    "gate": {
        "canonical_name": "Graduate Aptitude Test in Engineering (GATE)",
        "official_url": "https://gate2026.iitk.ac.in",
        "accreditation": "National Coordination Board (NCB)-GATE, Department of Higher Education",
    },
    "upsc": {
        "canonical_name": "Union Public Service Commission Civil Services Examination (UPSC CSE)",
        "official_url": "https://upsc.gov.in",
        "accreditation": "Constitutional Body established under Article 315, Govt. of India",
    },
    "cat": {
        "canonical_name": "Common Admission Test (CAT)",
        "official_url": "https://iimcat.ac.in",
        "accreditation": "Indian Institutes of Management (IIMs)",
    },
    "gre": {
        "canonical_name": "GRE General Test",
        "official_url": "https://www.ets.org/gre",
        "accreditation": "Educational Testing Service (ETS)",
    },
}

KNOWN_FICTIONAL_OR_INVALID: List[str] = [
    "hogwarts",
    "springfield",
    "bikinibottom",
    "monsters university",
    "starfleet academy",
    "fake",
    "test school",
    "dummy school",
    "sample university",
    "xyz university",
    "abc school",
    "asdf",
    "qwerty",
]


async def query_wikipedia_institution(name: str) -> Optional[Dict[str, Any]]:
    """
    Performs an online factual check against Wikipedia API to verify whether an educational
    institution exists and returns its canonical title and official Wikipedia URL.
    """
    clean_name = name.strip()
    if len(clean_name) < 3:
        return None

    # Do not call online API for obvious gibberish or test keywords
    lower_name = clean_name.lower()
    if any(fict in lower_name for fict in KNOWN_FICTIONAL_OR_INVALID):
        return None

    params = {
        "action": "query",
        "list": "search",
        "srsearch": f"{clean_name} university OR college OR school OR institute",
        "utf8": "1",
        "format": "json",
        "srlimit": "3",
    }
    url = f"https://en.wikipedia.org/w/api.php?{urllib.parse.urlencode(params)}"

    try:
        async with httpx.AsyncClient(timeout=2.5) as client:
            resp = await client.get(url, headers={"User-Agent": "SmartStudyPlanner/2.0 AcademicDiscovery"})
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("query", {}).get("search", [])
                for item in results:
                    title = item.get("title", "")
                    snippet = item.get("snippet", "").lower()
                    title_lower = title.lower()

                    # Look for education-related indicators in title or snippet
                    edu_terms = [
                        "university",
                        "college",
                        "school",
                        "institute",
                        "campus",
                        "academy",
                        "education",
                        "curriculum",
                        "board",
                        "engineering",
                        "polytechnic",
                    ]
                    has_edu_term = any(t in title_lower or t in snippet for t in edu_terms)

                    # Check for fictional markers
                    fictional_terms = ["fictional", "novel", "film", "comic", "character", "satirical"]
                    is_fictional = any(f in snippet or f in title_lower for f in fictional_terms)

                    if has_edu_term and not is_fictional:
                        page_title = urllib.parse.quote(title.replace(" ", "_"))
                        return {
                            "title": title,
                            "url": f"https://en.wikipedia.org/wiki/{page_title}",
                            "snippet": re.sub(r"<[^>]+>", "", item.get("snippet", ""))[:160] + "...",
                        }
    except Exception as e:
        logger.debug("wikipedia_fact_check_failed", error=str(e), name=name)

    return None


async def fact_check_academic_institution(
    academic_type: str,
    details: Dict[str, Any],
) -> InstitutionVerificationResult:
    """
    Fact-checks whether the student's claimed university, school, or exam actually exists.
    Prevents false data and hallucinated syllabus sources from being produced.
    """
    if academic_type == "COLLEGE":
        target = details.get("university") or details.get("college") or ""
        norm_key = target.lower().strip()

        # Check fictional blacklist
        if any(fict in norm_key for fict in KNOWN_FICTIONAL_OR_INVALID) or len(norm_key) < 3:
            return InstitutionVerificationResult(
                is_verified=False,
                canonical_name=target or "Unspecified Institution",
                institution_type="UNKNOWN",
                accreditation_body="Unaccredited / Fictional",
                official_portal_url=None,
                confidence_score=0.20,
                verification_notes="Institution could not be confirmed in accredited registries or Wikipedia.",
                warning_flag="Unverified institution detected. Custom study syllabus recommended.",
            )

        # 1. Match local canonical registry
        for key, entry in CANONICAL_UNIVERSITIES.items():
            if key in norm_key or norm_key in key:
                return InstitutionVerificationResult(
                    is_verified=True,
                    canonical_name=entry["canonical_name"],
                    institution_type="UNIVERSITY",
                    accreditation_body=entry["accreditation"],
                    official_portal_url=entry["official_url"],
                    confidence_score=0.98,
                    verification_notes=f"Fact-checked and confirmed in official university directory ({entry['accreditation']}).",
                )

        # 2. Live Wikipedia academic fact-check
        wiki_match = await query_wikipedia_institution(target)
        if wiki_match:
            return InstitutionVerificationResult(
                is_verified=True,
                canonical_name=wiki_match["title"],
                institution_type="UNIVERSITY",
                accreditation_body="Wikipedia Verified Academic Institution",
                official_portal_url=wiki_match["url"],
                confidence_score=0.92,
                verification_notes=f"Fact-checked via educational encyclopedia: {wiki_match['snippet']}",
            )

        # If not found
        return InstitutionVerificationResult(
            is_verified=False,
            canonical_name=target,
            institution_type="UNIVERSITY",
            accreditation_body="Unregistered Institution",
            official_portal_url="https://www.ugc.gov.in/",
            confidence_score=0.45,
            verification_notes=f"We could not independently verify '{target}' in recognized national databases. A standardized academic curriculum has been prepared.",
            warning_flag=f"Institution '{target}' could not be validated against official university directories.",
        )

    elif academic_type == "SCHOOL":
        board = details.get("board") or ""
        school_name = details.get("school_name") or ""
        norm_board = board.lower().strip()
        norm_school = school_name.lower().strip()

        # Check fictional blacklist
        if any(fict in norm_school for fict in KNOWN_FICTIONAL_OR_INVALID) or (school_name and len(norm_school) < 3):
            return InstitutionVerificationResult(
                is_verified=False,
                canonical_name=school_name or board,
                institution_type="UNKNOWN",
                accreditation_body="Unaccredited School",
                official_portal_url=None,
                confidence_score=0.25,
                verification_notes="School could not be validated in school board registries.",
                warning_flag="Unverified school detected. Standardized curriculum will be assigned.",
            )

        # 1. Match recognized school board
        board_entry = None
        for key, entry in CANONICAL_BOARDS.items():
            if key in norm_board or norm_board in key:
                board_entry = entry
                break

        if board_entry:
            # If school name provided, optionally verify school via Wikipedia
            school_wiki = await query_wikipedia_institution(school_name) if school_name else None
            disp_name = school_wiki["title"] if school_wiki else (f"{school_name} ({board_entry['canonical_name']})" if school_name else board_entry["canonical_name"])
            return InstitutionVerificationResult(
                is_verified=True,
                canonical_name=disp_name,
                institution_type="SCHOOL",
                accreditation_body=board_entry["accreditation"],
                official_portal_url=school_wiki["url"] if school_wiki else board_entry["official_url"],
                confidence_score=0.96 if school_wiki else 0.90,
                verification_notes=f"Fact-checked against curriculum framework of {board_entry['canonical_name']}.",
            )

        # 2. Check school on Wikipedia
        if school_name:
            wiki_school = await query_wikipedia_institution(school_name)
            if wiki_school:
                return InstitutionVerificationResult(
                    is_verified=True,
                    canonical_name=wiki_school["title"],
                    institution_type="SCHOOL",
                    accreditation_body="Recognized Educational Institution",
                    official_portal_url=wiki_school["url"],
                    confidence_score=0.90,
                    verification_notes=f"Fact-checked via educational registry: {wiki_school['snippet']}",
                )

        return InstitutionVerificationResult(
            is_verified=False,
            canonical_name=school_name or board,
            institution_type="SCHOOL",
            accreditation_body="Unverified Board / School",
            official_portal_url="https://ncert.nic.in/",
            confidence_score=0.45,
            verification_notes=f"Neither board '{board}' nor school '{school_name}' could be confirmed. Standardized curriculum assigned.",
            warning_flag="School or board could not be validated. Standardized curriculum applied.",
        )

    elif academic_type == "COMPETITIVE_EXAM":
        exam = details.get("exam_name") or ""
        norm_exam = exam.lower().strip()

        for key, entry in CANONICAL_EXAMS.items():
            if key in norm_exam or norm_exam in key:
                return InstitutionVerificationResult(
                    is_verified=True,
                    canonical_name=entry["canonical_name"],
                    institution_type="COMPETITIVE_EXAM",
                    accreditation_body=entry["accreditation"],
                    official_portal_url=entry["official_url"],
                    confidence_score=0.99,
                    verification_notes=f"Fact-checked official exam authority: {entry['accreditation']}.",
                )

        wiki_exam = await query_wikipedia_institution(exam)
        if wiki_exam:
            return InstitutionVerificationResult(
                is_verified=True,
                canonical_name=wiki_exam["title"],
                institution_type="COMPETITIVE_EXAM",
                accreditation_body="Recognized Examination Authority",
                official_portal_url=wiki_exam["url"],
                confidence_score=0.93,
                verification_notes=f"Fact-checked competitive exam: {wiki_exam['snippet']}",
            )

        return InstitutionVerificationResult(
            is_verified=False,
            canonical_name=exam,
            institution_type="COMPETITIVE_EXAM",
            accreditation_body="Custom Examination Track",
            official_portal_url="https://education.gov.in/",
            confidence_score=0.50,
            verification_notes=f"Custom exam track for '{exam}'. Syllabus based on foundational syllabus blueprints.",
            warning_flag=f"Target examination '{exam}' is not in recognized national testing registries.",
        )

    return InstitutionVerificationResult(
        is_verified=True,
        canonical_name="General Curriculum",
        institution_type="CUSTOM",
        accreditation_body="Self-Paced Track",
        official_portal_url=None,
        confidence_score=0.85,
        verification_notes="Tailored learning path.",
    )
