from django.contrib.auth import get_user_model
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.views import TokenObtainPairView

from .auth_utils import blacklist_user_tokens, logout_response_message
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


class LogoutAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if request.user.account_type != User.AccountType.CONSUMER:
            return Response(
                {
                    "message": "Consumer account required.",
                    "errors": {"detail": ["Consumer account required."]},
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        refresh = request.data.get("refresh")
        try:
            blacklist_user_tokens(request.user, refresh=refresh or None)
        except TokenError:
            return Response(
                {
                    "message": "Invalid or expired token.",
                    "errors": {"refresh": ["Invalid or expired token."]},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "message": logout_response_message(refresh),
                "errors": {},
            },
            status=status.HTTP_200_OK,
        )


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
