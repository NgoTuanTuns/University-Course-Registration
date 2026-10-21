"""Import đủ 7 model để Alembic thấy hết metadata (alembic/env.py: `from app.models import Base`)."""
from app.models.base import Base
from app.models.completed_course import CompletedCourse
from app.models.course import Course
from app.models.course_offering import CourseOffering
from app.models.enrollment import Enrollment
from app.models.prerequisite import Prerequisite
from app.models.student import Student
from app.models.waitlist import Waitlist

__all__ = [
    "Base",
    "CompletedCourse",
    "Course",
    "CourseOffering",
    "Enrollment",
    "Prerequisite",
    "Student",
    "Waitlist",
]
