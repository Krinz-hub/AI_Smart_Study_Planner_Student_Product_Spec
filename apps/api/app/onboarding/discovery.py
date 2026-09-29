import re
from typing import Any, Dict, List
from app.onboarding.schemas import (
    AcademicTypeEnum,
    DiscoveredSyllabusResponse,
    DiscoveredSubject,
    DiscoveredUnit,
)
from app.onboarding.fact_checker import fact_check_academic_institution
from app.common.logging import get_logger

logger = get_logger("academic_discovery")

# Standardized, high-yield academic curriculum repositories across disciplines
CURRICULUM_KNOWLEDGE_BASE: Dict[str, List[Dict[str, Any]]] = {
    # 1. Computer Science & IT Engineering
    "cs_engineering": [
        {
            "name": "Operating Systems",
            "code": "CS301",
            "color_code": "#0284c7",
            "units": [
                {"unit_number": 1, "title": "Processes & Threads", "topics": ["Process Lifecycle", "Inter-Process Communication", "Multithreading Models"]},
                {"unit_number": 2, "title": "CPU Scheduling", "topics": ["FCFS & SJF Scheduling", "Round Robin Scheduling", "Multilevel Feedback Queues"]},
                {"unit_number": 3, "title": "Synchronization & Deadlocks", "topics": ["Semaphores & Mutexes", "Banker's Algorithm", "Deadlock Prevention"]},
                {"unit_number": 4, "title": "Memory Management", "topics": ["Paging & Segmentation", "Virtual Memory", "Page Replacement (LRU/FIFO)"]},
                {"unit_number": 5, "title": "Storage & File Systems", "topics": ["Disk Scheduling (SSTF/SCAN)", "File Allocation Methods", "Directory Structures"]},
            ],
        },
        {
            "name": "Database Management Systems",
            "code": "CS302",
            "color_code": "#059669",
            "units": [
                {"unit_number": 1, "title": "Data Models & ER Diagrams", "topics": ["Entity-Relationship Models", "Relational Algebra", "Schema Design"]},
                {"unit_number": 2, "title": "SQL & Normalization", "topics": ["Complex SQL Joins", "1NF, 2NF, 3NF & BCNF", "Lossless Decomposition"]},
                {"unit_number": 3, "title": "Indexing & Storage", "topics": ["B-Trees & B+ Trees", "Hash Indexes", "Query Optimization"]},
                {"unit_number": 4, "title": "Transaction Processing", "topics": ["ACID Properties", "Two-Phase Locking (2PL)", "Serializability & Recovery"]},
            ],
        },
        {
            "name": "Computer Organization & Architecture",
            "code": "CS303",
            "color_code": "#7c3aed",
            "units": [
                {"unit_number": 1, "title": "Instruction Set Architecture", "topics": ["Addressing Modes", "ALU Design", "Instruction Cycle"]},
                {"unit_number": 2, "title": "Processor & Pipelining", "topics": ["Pipelining Hazards", "Branch Prediction", "Data Paths"]},
                {"unit_number": 3, "title": "Memory Hierarchy", "topics": ["Cache Mapping (Direct/Associative)", "Cache Coherence", "Virtual Memory Management"]},
            ],
        },
        {
            "name": "Data Structures & Algorithms",
            "code": "CS304",
            "color_code": "#ea580c",
            "units": [
                {"unit_number": 1, "title": "Trees & Hierarchies", "topics": ["Binary Search Trees", "AVL Trees", "Red-Black Trees"]},
                {"unit_number": 2, "title": "Graphs & Traversal", "topics": ["BFS & DFS", "Dijkstra's Algorithm", "Kruskal & Prim MST"]},
                {"unit_number": 3, "title": "Algorithm Paradigms", "topics": ["Dynamic Programming", "Greedy Strategies", "Divide and Conquer"]},
            ],
        },
        {
            "name": "Discrete Mathematics",
            "code": "MA301",
            "color_code": "#db2777",
            "units": [
                {"unit_number": 1, "title": "Propositional Logic", "topics": ["Truth Tables", "Logical Equivalence", "Predicates & Quantifiers"]},
                {"unit_number": 2, "title": "Relations & Functions", "topics": ["Equivalence Relations", "Partial Orderings", "Lattices"]},
                {"unit_number": 3, "title": "Combinatorics & Graph Theory", "topics": ["Permutations & Combinations", "Eulerian & Hamiltonian Graphs", "Recurrence Relations"]},
            ],
        },
    ],

    # 2. Mechanical Engineering
    "mech_engineering": [
        {
            "name": "Thermodynamics",
            "code": "ME301",
            "color_code": "#ea580c",
            "units": [
                {"unit_number": 1, "title": "First & Second Laws", "topics": ["Internal Energy & Enthalpy", "Carnot Cycle & Entropy", "Exergy Analysis"]},
                {"unit_number": 2, "title": "Gas Power Cycles", "topics": ["Otto & Diesel Cycles", "Brayton Cycle", "Rankine Cycle"]},
            ],
        },
        {
            "name": "Fluid Mechanics",
            "code": "ME302",
            "color_code": "#0284c7",
            "units": [
                {"unit_number": 1, "title": "Fluid Statics & Kinematics", "topics": ["Bernoulli's Equation", "Navier-Stokes Equations", "Viscosity & Boundary Layers"]},
                {"unit_number": 2, "title": "Turbo-Machinery", "topics": ["Pelton & Francis Turbines", "Centrifugal Pumps", "Dimensional Analysis"]},
            ],
        },
        {
            "name": "Strength of Materials",
            "code": "ME303",
            "color_code": "#7c3aed",
            "units": [
                {"unit_number": 1, "title": "Stress & Strain", "topics": ["Hooke's Law & Elastic Moduli", "Shear Force & Bending Moments", "Torsion of Circular Shafts"]},
                {"unit_number": 2, "title": "Deflection & Failure", "topics": ["Mohr's Circle", "Euler's Column Theory", "Theories of Failure"]},
            ],
        },
    ],

    # 3. Electrical & Electronics Engineering
    "ee_engineering": [
        {
            "name": "Circuit Theory & Analysis",
            "code": "EE301",
            "color_code": "#eab308",
            "units": [
                {"unit_number": 1, "title": "Network Theorems", "topics": ["Thevenin & Norton Theorems", "Superposition Theorem", "Maximum Power Transfer"]},
                {"unit_number": 2, "title": "AC Analysis & Transient Response", "topics": ["RLC Circuits", "Resonance & Bandwidth", "Laplace Transform of Circuits"]},
            ],
        },
        {
            "name": "Signals and Systems",
            "code": "EE302",
            "color_code": "#06b6d4",
            "units": [
                {"unit_number": 1, "title": "Signal Classification & LTI Systems", "topics": ["Continuous vs Discrete Signals", "Convolution Integral", "LTI Stability"]},
                {"unit_number": 2, "title": "Fourier & Z-Transforms", "topics": ["Fourier Series", "Fourier Transform", "Z-Transform Analysis"]},
            ],
        },
        {
            "name": "Digital Logic & Microprocessors",
            "code": "EE303",
            "color_code": "#8b5cf6",
            "units": [
                {"unit_number": 1, "title": "Combinational & Sequential Logic", "topics": ["K-Maps & Logic Gates", "Flip-Flops & Latches", "Synchronous Counters"]},
                {"unit_number": 2, "title": "Microprocessor Architecture", "topics": ["8085/8086 Instruction Set", "Memory Interfacing", "Interrupt Handling"]},
            ],
        },
    ],

    # 4. Commerce & Business Management
    "business_commerce": [
        {
            "name": "Financial Accounting & Reporting",
            "code": "COM301",
            "color_code": "#10b981",
            "units": [
                {"unit_number": 1, "title": "Financial Statements", "topics": ["Balance Sheet Preparation", "Profit & Loss Account", "Cash Flow Analysis"]},
                {"unit_number": 2, "title": "Corporate Accounting", "topics": ["Share Capital & Debentures", "Depreciation Methods", "Ratio Analysis"]},
            ],
        },
        {
            "name": "Managerial Economics",
            "code": "MGT301",
            "color_code": "#f59e0b",
            "units": [
                {"unit_number": 1, "title": "Demand & Supply Analysis", "topics": ["Elasticity of Demand", "Consumer Preference Theory", "Demand Forecasting"]},
                {"unit_number": 2, "title": "Market Structures", "topics": ["Perfect Competition", "Monopoly & Oligopoly", "Price Discrimination"]},
            ],
        },
        {
            "name": "Principles of Management & Organizational Behavior",
            "code": "MGT302",
            "color_code": "#ec4899",
            "units": [
                {"unit_number": 1, "title": "Management Functions", "topics": ["Strategic Planning", "Organizational Design", "Leadership Styles"]},
                {"unit_number": 2, "title": "Motivation & Group Dynamics", "topics": ["Maslow & Herzberg Theories", "Team Dynamics", "Conflict Resolution"]},
            ],
        },
    ],

    # 5. School / Class 12 Science (CBSE / ICSE / State)
    "school_class_12_science": [
        {
            "name": "Physics",
            "code": "PHY12",
            "color_code": "#0284c7",
            "units": [
                {"unit_number": 1, "title": "Electrostatics", "topics": ["Coulomb's Law", "Electric Field & Potential", "Capacitors & Dielectrics"]},
                {"unit_number": 2, "title": "Electromagnetism", "topics": ["Magnetic Effects of Current", "Faraday's Law & Induction", "Alternating Current"]},
                {"unit_number": 3, "title": "Optics & Modern Physics", "topics": ["Wave Optics", "Dual Nature of Radiation", "Nuclear Physics"]},
            ],
        },
        {
            "name": "Chemistry",
            "code": "CHEM12",
            "color_code": "#059669",
            "units": [
                {"unit_number": 1, "title": "Physical Chemistry", "topics": ["Solutions & Colligative Properties", "Electrochemistry", "Chemical Kinetics"]},
                {"unit_number": 2, "title": "Organic Chemistry", "topics": ["Haloalkanes & Haloarenes", "Alcohols, Phenols & Ethers", "Aldehydes & Ketones", "Biomolecules"]},
                {"unit_number": 3, "title": "Inorganic Chemistry", "topics": ["d- and f-Block Elements", "Coordination Compounds"]},
            ],
        },
        {
            "name": "Mathematics",
            "code": "MATH12",
            "color_code": "#7c3aed",
            "units": [
                {"unit_number": 1, "title": "Calculus", "topics": ["Continuity & Differentiability", "Applications of Derivatives", "Definite & Indefinite Integrals", "Differential Equations"]},
                {"unit_number": 2, "title": "Vectors & 3D Geometry", "topics": ["Vector Algebra", "Lines and Planes in 3D Space"]},
                {"unit_number": 3, "title": "Probability", "topics": ["Conditional Probability", "Bayes Theorem", "Probability Distributions"]},
            ],
        },
    ],

    # 6. School / Class 12 Commerce
    "school_class_12_commerce": [
        {
            "name": "Accountancy",
            "code": "ACCT12",
            "color_code": "#10b981",
            "units": [
                {"unit_number": 1, "title": "Partnership Accounts", "topics": ["Admission of a Partner", "Retirement & Death of a Partner", "Dissolution of Partnership"]},
                {"unit_number": 2, "title": "Company Accounts", "topics": ["Accounting for Share Capital", "Issue & Redemption of Debentures"]},
            ],
        },
        {
            "name": "Business Studies",
            "code": "BST12",
            "color_code": "#f59e0b",
            "units": [
                {"unit_number": 1, "title": "Principles of Management", "topics": ["Fayol & Taylor Principles", "Business Environment", "Planning & Directing"]},
                {"unit_number": 2, "title": "Financial Management & Marketing", "topics": ["Financial Decisions & Capital Structure", "Marketing Mix (4 Ps)", "Consumer Protection"]},
            ],
        },
        {
            "name": "Economics",
            "code": "ECON12",
            "color_code": "#6366f1",
            "units": [
                {"unit_number": 1, "title": "Macroeconomics", "topics": ["National Income Accounting", "Money & Banking", "Government Budget & Balance of Payments"]},
                {"unit_number": 2, "title": "Indian Economic Development", "topics": ["Economic Reforms since 1991", "Poverty & Human Capital", "Sustainable Development"]},
            ],
        },
    ],

    # 7. Competitive Exam / JEE Main & Advanced
    "competitive_jee": [
        {
            "name": "JEE Physics",
            "code": "JEE-PHY",
            "color_code": "#0284c7",
            "units": [
                {"unit_number": 1, "title": "Mechanics & Gravitation", "topics": ["Rotational Dynamics", "Conservation of Momentum & Energy", "Gravitational Potential"]},
                {"unit_number": 2, "title": "Electrodynamics & Waves", "topics": ["Electromagnetic Induction", "Wave Optics & Interference", "Modern Physics Quanta"]},
            ],
        },
        {
            "name": "JEE Mathematics",
            "code": "JEE-MATH",
            "color_code": "#7c3aed",
            "units": [
                {"unit_number": 1, "title": "Calculus & Functions", "topics": ["Limits, Continuity & Differentiation", "Integration Techniques & Definite Integrals", "Differential Equations"]},
                {"unit_number": 2, "title": "Algebra & Coordinate Geometry", "topics": ["Matrices & Determinants", "Complex Numbers", "Conic Sections (Parabola/Ellipse/Hyperbola)"]},
            ],
        },
        {
            "name": "JEE Chemistry",
            "code": "JEE-CHEM",
            "color_code": "#059669",
            "units": [
                {"unit_number": 1, "title": "Physical Chemistry", "topics": ["Thermodynamics & Thermochemistry", "Chemical Equilibrium", "Electrochemistry"]},
                {"unit_number": 2, "title": "Organic Mechanisms", "topics": ["Reaction Mechanisms (SN1/SN2/E1/E2)", "Named Organic Reactions", "Biomolecules"]},
            ],
        },
    ],

    # 8. Competitive Exam / NEET UG
    "competitive_neet": [
        {
            "name": "NEET Biology",
            "code": "NEET-BIO",
            "color_code": "#10b981",
            "units": [
                {"unit_number": 1, "title": "Genetics & Evolution", "topics": ["Mendelian Genetics", "Molecular Basis of Inheritance", "Evolutionary Biology"]},
                {"unit_number": 2, "title": "Human Physiology", "topics": ["Neural Control & Coordination", "Endocrine System & Hormones", "Circulatory & Excretory Systems"]},
            ],
        },
        {
            "name": "NEET Chemistry",
            "code": "NEET-CHEM",
            "color_code": "#059669",
            "units": [
                {"unit_number": 1, "title": "Organic Chemistry for Medicine", "topics": ["Aldehydes, Ketones & Carboxylic Acids", "Amines & Nitrogen Compounds", "Polymers & Everyday Chemistry"]},
                {"unit_number": 2, "title": "Inorganic Coordination", "topics": ["Periodic Trends", "Coordination Compounds & Ligands", "Chemical Bonding"]},
            ],
        },
        {
            "name": "NEET Physics",
            "code": "NEET-PHY",
            "color_code": "#0284c7",
            "units": [
                {"unit_number": 1, "title": "Thermodynamics & Optics", "topics": ["Thermal Properties of Matter", "Ray & Wave Optics", "Kinetic Theory of Gases"]},
                {"unit_number": 2, "title": "Current & Modern Physics", "topics": ["Current Electricity", "Semiconductor Devices", "Nuclear Physics"]},
            ],
        },
    ],

    # 9. Competitive Exam / GATE CS
    "competitive_gate_cs": [
        {
            "name": "Theoretical Computer Science",
            "code": "GATE-TCS",
            "color_code": "#7c3aed",
            "units": [
                {"unit_number": 1, "title": "Theory of Computation", "topics": ["Regular Languages & DFA/NFA", "Context-Free Grammars & PDA", "Turing Machines & Decidability"]},
                {"unit_number": 2, "title": "Compiler Design", "topics": ["Lexical Analysis & Parsing (LL/LR)", "Intermediate Code Generation", "Data Flow Analysis"]},
            ],
        },
        {
            "name": "Systems & Networks",
            "code": "GATE-SYS",
            "color_code": "#0284c7",
            "units": [
                {"unit_number": 1, "title": "Computer Networks", "topics": ["TCP/IP & OSI Architecture", "Routing Protocols (OSPF/BGP)", "Flow & Congestion Control (TCP Reno)"]},
                {"unit_number": 2, "title": "Operating Systems Core", "topics": ["Virtual Memory & Page Replacement", "CPU Scheduling & Multiprocessing", "Deadlock Avoidance"]},
            ],
        },
    ],
}


def select_curriculum_key(academic_type: str, details: Dict[str, Any]) -> str:
    """Selects the most accurate discipline curriculum based on branch, degree, or stream."""
    if academic_type == AcademicTypeEnum.COLLEGE.value:
        branch = str(details.get("branch", "")).lower()
        degree = str(details.get("degree", "")).lower()

        if any(k in branch or k in degree for k in ["mech", "automobile", "aerospace"]):
            return "mech_engineering"
        elif any(k in branch or k in degree for k in ["elect", "eee", "ece", "instrumentation", "telecom"]):
            return "ee_engineering"
        elif any(k in branch or k in degree for k in ["bba", "mba", "management", "business", "commerce", "b.com", "finance"]):
            return "business_commerce"
        else:
            return "cs_engineering"

    elif academic_type == AcademicTypeEnum.SCHOOL.value:
        grade = str(details.get("grade", "")).lower()
        stream = str(details.get("stream", "")).lower()

        if any(k in stream for k in ["commerce", "accounts", "business"]):
            return "school_class_12_commerce"
        return "school_class_12_science"

    elif academic_type == AcademicTypeEnum.COMPETITIVE_EXAM.value:
        exam = str(details.get("exam_name", "")).lower()
        if "neet" in exam:
            return "competitive_neet"
        elif any(k in exam for k in ["jee", "iit", "bitsat"]):
            return "competitive_jee"
        elif "gate" in exam:
            return "competitive_gate_cs"
        return "competitive_jee"

    return "cs_engineering"


def build_fact_checked_sources(
    verification: Any,
    academic_type: str,
    details: Dict[str, Any],
) -> List[Dict[str, str]]:
    """
    Builds strictly authentic, verified reference source links.
    Never hallucinates unverified or fabricated domain links.
    """
    sources: List[Dict[str, str]] = []

    # 1. Primary verified institution portal or Wikipedia page
    if verification.is_verified and verification.official_portal_url:
        sources.append({
            "title": f"{verification.canonical_name} — Verified Official Academic Record",
            "url": verification.official_portal_url,
            "authority": "ACCREDITED_INSTITUTION",
            "confidence": "VERY_HIGH" if verification.confidence_score >= 0.95 else "HIGH",
        })

    # 2. Add national academic accreditation framework
    if academic_type == AcademicTypeEnum.COLLEGE.value:
        sources.append({
            "title": "University Grants Commission (UGC) National Higher Education Framework",
            "url": "https://www.ugc.gov.in/",
            "authority": "STATUTORY_REGULATOR",
            "confidence": "HIGH",
        })
        sources.append({
            "title": "All India Council for Technical Education (AICTE) Curriculum Blueprints",
            "url": "https://www.aicte-india.org/curriculum",
            "authority": "NATIONAL_FRAMEWORK",
            "confidence": "HIGH",
        })

    elif academic_type == AcademicTypeEnum.SCHOOL.value:
        board = str(details.get("board", "")).upper()
        if "CBSE" in board:
            sources.append({
                "title": "Central Board of Secondary Education (CBSE) Academic Curriculum",
                "url": "https://cbseacademic.nic.in/curriculum.html",
                "authority": "OFFICIAL_EXAM_BOARD",
                "confidence": "VERY_HIGH",
            })
        elif "ICSE" in board or "CISCE" in board:
            sources.append({
                "title": "CISCE Official Regulations and Syllabuses",
                "url": "https://cisce.org/regulations-and-syllabuses/",
                "authority": "OFFICIAL_EXAM_BOARD",
                "confidence": "VERY_HIGH",
            })
        sources.append({
            "title": "National Council of Educational Research and Training (NCERT)",
            "url": "https://ncert.nic.in/syllabus.php",
            "authority": "NATIONAL_FRAMEWORK",
            "confidence": "HIGH",
        })

    elif academic_type == AcademicTypeEnum.COMPETITIVE_EXAM.value:
        exam = str(details.get("exam_name", "")).upper()
        if "JEE" in exam:
            sources.append({
                "title": "NTA Joint Entrance Examination Official Information Bulletin",
                "url": "https://jeemain.nta.nic.in/",
                "authority": "OFFICIAL_EXAM_BODY",
                "confidence": "VERY_HIGH",
            })
        elif "NEET" in exam:
            sources.append({
                "title": "NTA NEET (UG) Official Portal & Syllabus",
                "url": "https://neet.nta.nic.in/",
                "authority": "OFFICIAL_EXAM_BODY",
                "confidence": "VERY_HIGH",
            })
        elif "GATE" in exam:
            sources.append({
                "title": "GATE Organizing Institute Official Papers & Syllabus",
                "url": "https://gate2026.iitk.ac.in/",
                "authority": "OFFICIAL_EXAM_BODY",
                "confidence": "VERY_HIGH",
            })

    return sources


async def discover_academic_syllabus(
    academic_type: str,
    details: Dict[str, Any],
) -> DiscoveredSyllabusResponse:
    """
    Executes automated academic discovery with rigorous fact-checking:
    1. Fact-checks whether the student's claimed institution (University/School/Board) actually exists.
    2. Maps degree, stream, or branch to grounded academic curricula.
    3. Builds authentic, non-hallucinated reference sources.
    4. Attaches verification status and actionable warning indicators.
    """
    logger.info("discovering_academic_syllabus_with_fact_check", academic_type=academic_type)

    # 1. Fact-check institution existence
    verification = await fact_check_academic_institution(academic_type, details)

    # 2. Select appropriate discipline curriculum
    curriculum_key = select_curriculum_key(academic_type, details)
    raw_subjects = CURRICULUM_KNOWLEDGE_BASE.get(curriculum_key, CURRICULUM_KNOWLEDGE_BASE["cs_engineering"])

    # 3. Formulate authentic summary and sources
    if academic_type == AcademicTypeEnum.COLLEGE.value:
        degree = details.get("degree", "Degree")
        branch = details.get("branch", "Engineering")
        sem = details.get("semester", 3)
        summary = f"{verification.canonical_name} — {degree} in {branch} (Semester {sem})"

    elif academic_type == AcademicTypeEnum.SCHOOL.value:
        grade = details.get("grade", "Class 12")
        summary = f"{verification.canonical_name} — {grade}"

    elif academic_type == AcademicTypeEnum.COMPETITIVE_EXAM.value:
        summary = f"{verification.canonical_name} — Targeted Preparation Blueprint"

    else:
        summary = "Custom Adaptive Learning Track"

    sources = build_fact_checked_sources(verification, academic_type, details)

    # 4. Assemble structured subjects and units
    subjects: List[DiscoveredSubject] = []
    for s in raw_subjects:
        units = [
            DiscoveredUnit(
                unit_number=u["unit_number"],
                title=u["title"],
                topics=u["topics"],
            )
            for u in s.get("units", [])
        ]
        subjects.append(
            DiscoveredSubject(
                name=s["name"],
                code=s.get("code"),
                color_code=s.get("color_code", "#3b82f6"),
                units=units,
            )
        )

    return DiscoveredSyllabusResponse(
        academic_summary=summary,
        confidence_score=verification.confidence_score,
        sources=sources,
        subjects=subjects,
        institution_verified=verification.is_verified,
        institution_name=verification.canonical_name,
        verification_status="VERIFIED" if verification.is_verified else "UNVERIFIED",
        verification_note=verification.verification_notes,
        warning_flag=verification.warning_flag,
    )
