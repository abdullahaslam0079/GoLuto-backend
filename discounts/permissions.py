from rest_framework import permissions


class IsBusinessAccount(permissions.BasePermission):
    message = "Business account required."

    def has_permission(self, request, view):
        user = request.user
        return (
            user
            and user.is_authenticated
            and user.is_business_account
            and hasattr(user, "business_profile")
        )


class IsConsumerAccount(permissions.BasePermission):
    message = "Consumer account required."

    def has_permission(self, request, view):
        user = request.user
        return (
            user
            and user.is_authenticated
            and user.account_type == user.AccountType.CONSUMER
        )
