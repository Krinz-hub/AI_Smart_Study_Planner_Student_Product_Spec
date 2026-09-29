from fastapi import APIRouter
from app.api.v1.health import router as health_router
from app.auth.routes import router as auth_router
from app.students.routes import router as student_router
from app.academics.routes import router as academics_router
from app.learner.routes import router as learner_router
from app.decisions.routes import router as decisions_router
from app.planner.routes import router as planner_router
from app.documents.routes import router as documents_router
from app.rag.routes import router as retrieval_router
from app.quiz.routes import router as quiz_router
from app.tutor.routes import router as tutor_router

api_router = APIRouter(prefix="/api/v1")

# Mount health routes
api_router.include_router(health_router)

# Mount auth routes under /api/v1/auth
api_router.include_router(auth_router)

# Mount student routes under /api/v1/student
api_router.include_router(student_router)

# Mount academics routes under /api/v1
api_router.include_router(academics_router)

# Mount learner routes under /api/v1/learner
api_router.include_router(learner_router)

# Mount decisions routes under /api/v1/decisions
api_router.include_router(decisions_router)

# Mount planner routes under /api/v1
api_router.include_router(planner_router)

# Mount documents routes under /api/v1
api_router.include_router(documents_router)

# Mount retrieval routes under /api/v1
api_router.include_router(retrieval_router)

# Mount quiz routes under /api/v1
api_router.include_router(quiz_router)

# Mount tutor routes under /api/v1
api_router.include_router(tutor_router)

# Mount exam mode routes under /api/v1
from app.exam_mode.routes import router as exam_mode_router
api_router.include_router(exam_mode_router)

# Mount research routes under /api/v1
from app.research.routes import router as research_router
api_router.include_router(research_router)

# Mount student onboarding routes under /api/v1
from app.onboarding.routes import router as onboarding_router
api_router.include_router(onboarding_router)

# Mount user settings routes under /api/v1/settings
from app.settings.routes import router as settings_router
api_router.include_router(settings_router)

# Mount spec compatibility aliases under /api/v1
from app.api.compat_router import compat_router
api_router.include_router(compat_router)

# Mount /materials alias to documents
api_router.include_router(documents_router, prefix="/materials")

# Mount /practice alias to quiz
api_router.include_router(quiz_router, prefix="/practice")






