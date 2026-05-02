from django.urls import path, include
from rest_framework.routers import SimpleRouter
from .views import CustomUserViewSet, RegisterView, LoginView, LogoutView, GoogleAuthView
 
router = SimpleRouter()
router.register(r'manage', CustomUserViewSet, basename='user')
 
urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('google-auth/', GoogleAuthView.as_view(), name='google-auth'),  # NEW
    path('', include(router.urls)),
]
 