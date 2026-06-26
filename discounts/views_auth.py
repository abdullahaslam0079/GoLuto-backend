from django.contrib.auth import get_user_model
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import LoginTokenObtainPairSerializer, RegisterSerializer

User = get_user_model()


class LoginAPIView(TokenObtainPairView):
    serializer_class = LoginTokenObtainPairSerializer


class RegisterAPIView(generics.CreateAPIView):
    """Create a user and return JWT access + refresh tokens (mobile-friendly)."""

    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "name": user.get_full_name().strip(),
                },
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            },
            status=status.HTTP_201_CREATED,
        )
