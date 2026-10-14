from datetime import datetime

from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone
from django.shortcuts import get_object_or_404

from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import extend_schema, OpenApiResponse

from .models import Patient, Doctor, Appointment, Payment
from .serializers import (
    PatientSerializer,
    DoctorSerializer,
    AppointmentSerializer,
    PaymentSerializer,
)
from .permissions import (
    IsAdminUserRole,
    IsAdminOrPatientRole,
    IsAdminOrDoctorRole,
)


def is_admin(user):
    return user.is_authenticated and (
        user.is_staff or user.groups.filter(name="Admin").exists()
    )


def appointments_for_user(user, allowed_roles=None):
    appointments = Appointment.objects.select_related(
        "patient",
        "doctor",
    )

    if is_admin(user):
        return appointments

    allowed_roles = allowed_roles or []

    conditions = Q(pk__in=[])

    if (
        "Patient" in allowed_roles
        and user.groups.filter(name="Patient").exists()
    ):
        patient = getattr(user, "patient_profile", None)

        if patient is not None:
            conditions |= Q(patient=patient)

    if (
        "Doctor" in allowed_roles
        and user.groups.filter(name="Doctor").exists()
    ):
        doctor = getattr(user, "doctor_profile", None)

        if doctor is not None:
            conditions |= Q(doctor=doctor)

    return appointments.filter(conditions).distinct()


class PatientCreateView(generics.CreateAPIView):
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer
    permission_classes = [IsAdminUserRole]


class DoctorListCreateView(generics.ListCreateAPIView):
    queryset = Doctor.objects.all()
    serializer_class = DoctorSerializer

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]

        return [IsAdminUserRole()]


class AppointmentListCreateView(generics.ListCreateAPIView):
    serializer_class = AppointmentSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAdminOrPatientRole()]

        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user

        if is_admin(user):
            queryset = Appointment.objects.select_related(
                "patient",
                "doctor",
            )
        else:
            queryset = appointments_for_user(
                user,
                ["Patient", "Doctor"],
            )

        patient_id = self.request.query_params.get("patient_id")
        doctor_id = self.request.query_params.get("doctor_id")
        appointment_status = self.request.query_params.get("status")

        if patient_id and is_admin(user):
            queryset = queryset.filter(patient_id=patient_id)

        if doctor_id and is_admin(user):
            queryset = queryset.filter(doctor_id=doctor_id)

        if appointment_status:
            queryset = queryset.filter(status=appointment_status)

        return queryset

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if is_admin(request.user):
            patient = serializer.validated_data.get("patient")

            if patient is None:
                return Response(
                    {"error": "A patient must be selected."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            patient = getattr(
                request.user,
                "patient_profile",
                None,
            )

            if patient is None:
                return Response(
                    {"error": "Patient profile not found."},
                    status=status.HTTP_403_FORBIDDEN,
                )

        doctor = serializer.validated_data.get("doctor")

        if doctor is None:
            return Response(
                {"error": "A doctor must be selected."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not doctor.is_available:
            return Response(
                {"error": "Doctor is not available."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        appointment_date = serializer.validated_data.get(
            "appointment_date"
        )
        appointment_time = serializer.validated_data.get(
            "appointment_time"
        )

        appointment_datetime = timezone.make_aware(
            datetime.combine(
                appointment_date,
                appointment_time,
            )
        )

        if appointment_datetime <= timezone.now():
            return Response(
                {
                    "error": (
                        "Appointment date and time must be in the future."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            appointment = serializer.save(patient=patient)
        except IntegrityError:
            return Response(
                {
                    "error": (
                        "This doctor already has an appointment "
                        "at that date and time."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        return Response(
            self.get_serializer(appointment).data,
            status=status.HTTP_201_CREATED,
        )


class AppointmentDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        appointments = appointments_for_user(
            request.user,
            ["Patient", "Doctor"],
        )

        appointment = get_object_or_404(
            appointments,
            pk=pk,
        )

        payment = Payment.objects.filter(
            appointment=appointment
        ).first()

        data = {
            "id": appointment.id,
            "patient": PatientSerializer(
                appointment.patient
            ).data,
            "doctor": DoctorSerializer(
                appointment.doctor
            ).data,
            "appointment_date": appointment.appointment_date,
            "appointment_time": appointment.appointment_time,
            "reason": appointment.reason,
            "status": appointment.status,
            "payment": (
                PaymentSerializer(payment).data
                if payment
                else None
            ),
        }

        return Response(data, status=status.HTTP_200_OK)


class AppointmentStatusUpdateView(APIView):
    permission_classes = [IsAdminOrDoctorRole]

    @extend_schema(
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": [
                            "Confirmed",
                            "Completed",
                            "Cancelled",
                        ],
                    }
                },
                "required": ["status"],
            }
        },
        responses={
            200: OpenApiResponse(
                description="Appointment status updated successfully."
            ),
            400: OpenApiResponse(
                description="Invalid status or status transition."
            ),
            403: OpenApiResponse(
                description="Permission denied."
            ),
            404: OpenApiResponse(
                description="Appointment not found."
            ),
        },
        description="Update an appointment status.",
    )
    def put(self, request, pk):
        new_status = request.data.get("status")

        allowed_statuses = [
            "Confirmed",
            "Completed",
            "Cancelled",
        ]

        if new_status not in allowed_statuses:
            return Response(
                {
                    "error": (
                        "Status must be Confirmed, Completed, "
                        "or Cancelled."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if is_admin(request.user):
            appointments = Appointment.objects.all()
        else:
            doctor = getattr(
                request.user,
                "doctor_profile",
                None,
            )

            if doctor is None:
                return Response(
                    {"error": "Doctor profile not found."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            appointments = Appointment.objects.filter(
                doctor=doctor
            )

        appointment = get_object_or_404(
            appointments,
            pk=pk,
        )

        if appointment.status in ["Completed", "Cancelled"]:
            return Response(
                {
                    "error": (
                        "Completed or cancelled appointments "
                        "cannot be updated."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if new_status == "Completed":
            if appointment.status != "Confirmed":
                return Response(
                    {
                        "error": (
                            "Only confirmed appointments "
                            "can be completed."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            appointment_datetime = timezone.make_aware(
                datetime.combine(
                    appointment.appointment_date,
                    appointment.appointment_time,
                )
            )

            if appointment_datetime > timezone.now():
                return Response(
                    {
                        "error": (
                            "Future appointments cannot be completed."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        appointment.status = new_status
        appointment.save(update_fields=["status"])

        return Response(
            {
                "message": "Appointment status updated successfully.",
                "appointment_id": appointment.id,
                "status": appointment.status,
            },
            status=status.HTTP_200_OK,
        )


class AppointmentPaymentView(APIView):
    permission_classes = [IsAdminOrPatientRole]

    @extend_schema(
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "payment_method": {
                        "type": "string",
                        "enum": ["Cash", "UPI", "Card"],
                    }
                },
                "required": ["payment_method"],
            }
        },
        responses={
            201: PaymentSerializer,
            400: OpenApiResponse(
                description="Invalid payment method or appointment state."
            ),
            404: OpenApiResponse(
                description="Appointment not found."
            ),
            409: OpenApiResponse(
                description="Payment already exists."
            ),
        },
    )
    @transaction.atomic
    def post(self, request, pk):
        if is_admin(request.user):
            appointments = Appointment.objects.all()
        else:
            patient = getattr(
                request.user,
                "patient_profile",
                None,
            )

            if patient is None:
                return Response(
                    {"error": "Patient profile not found."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            appointments = Appointment.objects.filter(
                patient=patient
            )

        appointment = get_object_or_404(
            appointments,
            pk=pk,
        )

        if appointment.status == "Cancelled":
            return Response(
                {
                    "error": (
                        "Payment cannot be made for a cancelled appointment."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if Payment.objects.filter(
            appointment=appointment
        ).exists():
            return Response(
                {"error": "Payment already exists."},
                status=status.HTTP_409_CONFLICT,
            )

        payment_method = request.data.get("payment_method")

        if payment_method not in ["Cash", "UPI", "Card"]:
            return Response(
                {
                    "error": (
                        "Payment method must be Cash, UPI, or Card."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            payment = Payment.objects.create(
                appointment=appointment,
                amount=appointment.doctor.consultation_fee,
                payment_method=payment_method,
                payment_status="Paid",
                payment_date=timezone.now(),
            )
        except IntegrityError:
            return Response(
                {"error": "Payment already exists."},
                status=status.HTTP_409_CONFLICT,
            )

        return Response(
            PaymentSerializer(payment).data,
            status=status.HTTP_201_CREATED,
        )


class AppointmentCancelView(APIView):
    permission_classes = [IsAdminOrPatientRole]

    @extend_schema(
        request={
            "application/json": {
                "type": "object",
                "properties": {},
            }
        },
        responses={
            200: OpenApiResponse(
                description="Appointment cancelled successfully."
            ),
            400: OpenApiResponse(
                description="Appointment cannot be cancelled."
            ),
            404: OpenApiResponse(
                description="Appointment not found."
            ),
        },
    )
    @transaction.atomic
    def post(self, request, pk):
        if is_admin(request.user):
            appointments = Appointment.objects.all()
        else:
            patient = getattr(
                request.user,
                "patient_profile",
                None,
            )

            if patient is None:
                return Response(
                    {"error": "Patient profile not found."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            appointments = Appointment.objects.filter(
                patient=patient
            )

        appointment = get_object_or_404(
            appointments,
            pk=pk,
        )

        if appointment.status == "Completed":
            return Response(
                {
                    "error": (
                        "Completed appointments cannot be cancelled."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if appointment.status == "Cancelled":
            return Response(
                {
                    "error": (
                        "Appointment is already cancelled."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        appointment.status = "Cancelled"
        appointment.save(update_fields=["status"])

        payment = Payment.objects.filter(
            appointment=appointment
        ).first()

        if payment and payment.payment_status == "Paid":
            payment.payment_status = "Refunded"
            payment.save(update_fields=["payment_status"])

        return Response(
            {
                "message": "Appointment cancelled successfully.",
                "appointment_id": appointment.id,
                "status": appointment.status,
                "payment_status": (
                    payment.payment_status if payment else None
                ),
            },
            status=status.HTTP_200_OK,
        )


class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(
            {
                "id": request.user.id,
                "username": request.user.username,
            },
            status=status.HTTP_200_OK,
        )
