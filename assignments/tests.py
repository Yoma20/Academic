from django.test import TestCase
from django.utils import timezone

from users.models import CustomUser
from .models import Assignment


class AssignmentModelTests(TestCase):
    def test_create_assignment_and_str(self):
        student = CustomUser.objects.create_user(
            username="teststudent",
            password="password123",
            user_type="student",
        )

        assignment = Assignment.objects.create(
            student=student,
            title="Test Assignment",
            description="This is a test assignment.",
            deadline=timezone.now() + timezone.timedelta(days=1),
        )

        self.assertEqual(Assignment.objects.count(), 1)
        self.assertEqual(str(assignment), "Test Assignment")
        self.assertEqual(assignment.student.username, "teststudent")

