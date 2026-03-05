# ======================================================
# File: users/urls.py
# ======================================================
from django.urls import path, include
from rest_framework.routers import SimpleRouter
from .views import CustomUserViewSet, RegisterView, LoginView, LogoutView

# SimpleRouter avoids the API root page that DefaultRouter adds,
# which was conflicting with the auth routes at the same prefix.
router = SimpleRouter()
# Register at 'manage/' so ViewSet URLs never overlap with auth URLs.
# Results in: /api/users/manage/        (list)
#             /api/users/manage/{id}/   (detail)
router.register(r'manage', CustomUserViewSet, basename='user')

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('', include(router.urls)),
]
