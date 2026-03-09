from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token
from users.models import CustomUser
from expert_profiles.models import ExpertProfile
from .models import Assignment, AssignmentBid


class AssignmentModelTests(TestCase):
    
    ...


class AssignmentAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.student = CustomUser.objects.create_user(
            username='student1', password='pass1234', user_type='student'
        )
        self.expert_user = CustomUser.objects.create_user(
            username='expert1', password='pass1234', user_type='expert'
        )
        self.expert_profile = ExpertProfile.objects.create(
            user=self.expert_user, field_of_study='Computer Science'
        )
        self.student_token = Token.objects.create(user=self.student)
        self.expert_token = Token.objects.create(user=self.expert_user)

    def test_student_can_create_assignment(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.student_token.key)
        res = self.client.post('/api/assignments/', {
            'title': 'Test',
            'description': 'Desc',
            'deadline': (timezone.now() + timezone.timedelta(days=2)).isoformat(),
        })
        self.assertEqual(res.status_code, 201)

    def test_expert_cannot_create_assignment(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.expert_token.key)
        res = self.client.post('/api/assignments/', {
            'title': 'Test',
            'description': 'Desc',
            'deadline': (timezone.now() + timezone.timedelta(days=2)).isoformat(),
        })
        self.assertEqual(res.status_code, 403)

    def test_expert_can_bid(self):
        assignment = Assignment.objects.create(
            student=self.student, title='Help', description='Please',
            deadline=timezone.now() + timezone.timedelta(days=3)
        )
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.expert_token.key)
        res = self.client.post('/api/assignments/bids/', {
            'assignment': assignment.id,
            'price': '50.00',
            'message': 'I can help',
        })
        self.assertEqual(res.status_code, 201)

    def test_unauthenticated_cannot_access(self):
        res = self.client.get('/api/assignments/')
        self.assertEqual(res.status_code, 401)
