from django.contrib import admin
from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)

from hospital.views import UserProfileView
from hospital.views import (
    PatientCreateView,
    DoctorListCreateView,
    AppointmentListCreateView,
    AppointmentDetailView,
    AppointmentStatusUpdateView,
    AppointmentPaymentView,
    AppointmentCancelView,
)

urlpatterns = [
    path('admin/', admin.site.urls),

    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/user/profile/', UserProfileView.as_view(), name='user_profile'),

    path('patients/', PatientCreateView.as_view(), name='patient-create'),
    path('doctors/', DoctorListCreateView.as_view(), name='doctor-list-create'),
    path('appointments/', AppointmentListCreateView.as_view(), name='appointment-list-create'),
    path('appointments/<int:pk>/', AppointmentDetailView.as_view(), name='appointment-detail'),
    path('appointments/<int:pk>/status/', AppointmentStatusUpdateView.as_view(), name='appointment-status'),
    path('appointments/<int:pk>/payment/', AppointmentPaymentView.as_view(), name='appointment-payment'),
    path('appointments/<int:pk>/cancel/', AppointmentCancelView.as_view(), name='appointment-cancel'),

    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]
