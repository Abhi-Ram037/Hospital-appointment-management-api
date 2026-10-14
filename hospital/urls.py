
from django.urls import path
from .views import (
    PatientCreateView,
    DoctorListCreateView,
    AppointmentListCreateView,
    AppointmentDetailView,
    AppointmentStatusUpdateView,
    AppointmentPaymentView,
    AppointmentCancelView,
)

urlpatterns = [
    path('patients/', PatientCreateView.as_view(), name='patient-create'),

    path('doctors/', DoctorListCreateView.as_view(), name='doctor-list-create'),

    path('appointments/', AppointmentListCreateView.as_view(), name='appointment-list-create'),

    path('appointments/<int:pk>/', AppointmentDetailView.as_view(), name='appointment-detail'),

    path('appointments/<int:pk>/status/', AppointmentStatusUpdateView.as_view(), name='appointment-status'),

    path('appointments/<int:pk>/payment/', AppointmentPaymentView.as_view(), name='appointment-payment'),

    path('appointments/<int:pk>/cancel/', AppointmentCancelView.as_view(), name='appointment-cancel'),
]
