from django.contrib import admin
from django.urls import path, include

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from hospital.views import UserProfileView

urlpatterns = [
    path("admin/", admin.site.urls),

    path(
        "api/token/",
        TokenObtainPairView.as_view(),
        name="token_obtain_pair",
    ),

    path(
        "api/token/refresh/",
        TokenRefreshView.as_view(),
        name="token_refresh",
    ),

    path(
        "api/user/profile/",
        UserProfileView.as_view(),
        name="user_profile",
    ),

    path("", include("hospital.urls")),
]
