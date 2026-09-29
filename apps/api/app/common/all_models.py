"""
Centralized registry that imports all SQLAlchemy declarative models.
Ensures that Base.metadata knows about all tables and foreign key relationships
across all modules upon application startup or script execution.
"""

import app.auth.models  # noqa: F401
import app.academics.models  # noqa: F401
import app.students.models  # noqa: F401
import app.learner.models  # noqa: F401
import app.tasks.models  # noqa: F401
import app.documents.models  # noqa: F401
import app.quiz.models  # noqa: F401
import app.exam_mode.models  # noqa: F401
