from django.contrib.auth import get_user_model
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView

from .password_reset import request_password_reset
from .serializers import (
    ForgotPasswordSerializer,
    LoginTokenObtainPairSerializer,
    RegisterSerializer,
    ResetPasswordSerializer,
)

User = get_user_model()


class LoginAPIView(TokenObtainPairView):
    authentication_classes = []
    serializer_class = LoginTokenObtainPairSerializer


class RegisterAPIView(generics.CreateAPIView):
    """Create a user account."""

    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"message": "Account created successfully.", "errors": {}},
            status=status.HTTP_201_CREATED,
        )


class ForgotPasswordAPIView(generics.GenericAPIView):
    serializer_class = ForgotPasswordSerializer
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            message = request_password_reset(serializer.validated_data["email"])
        except Exception:
            return Response(
                {
                    "message": "Unable to send password reset email. Please try again later.",
                    "errors": {},
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response({"message": message, "errors": {}})


class ResetPasswordAPIView(generics.GenericAPIView):
    serializer_class = ResetPasswordSerializer
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"message": "Password reset successfully.", "errors": {}},
            status=status.HTTP_200_OK,
        )
