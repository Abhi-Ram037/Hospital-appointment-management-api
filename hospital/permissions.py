
from rest_framework.permissions import BasePermission


class IsAdminUserRole(BasePermission):
    def has_permission(self, request, view):
        user = request.user

        return (
            user
            and user.is_authenticated
            and (
                user.is_staff
                or user.groups.filter(name="Admin").exists()
            )
        )


class IsPatientRole(BasePermission):
    def has_permission(self, request, view):
        user = request.user

        return (
            user
            and user.is_authenticated
            and user.groups.filter(name="Patient").exists()
        )


class IsDoctorRole(BasePermission):
    def has_permission(self, request, view):
        user = request.user

        return (
            user
            and user.is_authenticated
            and user.groups.filter(name="Doctor").exists()
        )


class IsAdminOrPatientRole(BasePermission):
    def has_permission(self, request, view):
        user = request.user

        return (
            user
            and user.is_authenticated
            and (
                user.is_staff
                or user.groups.filter(
                    name__in=["Admin", "Patient"]
                ).exists()
            )
        )


class IsAdminOrDoctorRole(BasePermission):
    def has_permission(self, request, view):
        user = request.user

        return (
            user
            and user.is_authenticated
            and (
                user.is_staff
                or user.groups.filter(
                    name__in=["Admin", "Doctor"]
                ).exists()
            )
        )
