
from django.db import transaction, IntegrityError
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

from .models import Patient, Doctor, Appointment, Payment
from .serializers import (
    PatientSerializer,
    DoctorSerializer,
    AppointmentSerializer,
    PaymentSerializer,
)
from .permissions import (
    IsAdminUserRole,
    IsPatientRole,
    IsDoctorRole,
    IsAdminOrPatientRole,
    IsAdminOrDoctorRole,
)


def is_admin(user):
    return (
        user.is_authenticated
        and (
            user.is_staff
            or user.groups.filter(name="Admin").exists()
        )
    )


def appointments_for_user(user, allowed_roles):
    queryset = Appointment.objects.select_related(
        "patient", "doctor"
    )

    if is_admin(user):
        return queryset

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

    return queryset.filter(conditions)


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

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAdminOrPatientRole()]
        return [IsAuthenticated()]

    def get_queryset(self):
        queryset = appointments_for_user(
            self.request.user,
            ["Patient", "Doctor"]
        )

        patient_id = self.request.query_params.get("patient_id")
        doctor_id = self.request.query_params.get("doctor_id")
        appointment_status = self.request.query_params.get("status")

        if patient_id:
            queryset = queryset.filter(patient_id=patient_id)

        if doctor_id:
            queryset = queryset.filter(doctor_id=doctor_id)

        if appointment_status:
            queryset = queryset.filter(status=appointment_status)

        return queryset.order_by(
            "appointment_date", "appointment_time"
        )

    def create(self, request, *args, **kwargs):
        data = request.data.copy()

        if not is_admin(request.user):
            patient = getattr(
                request.user, "patient_profile", None
            )

            if patient is None:
                return Response(
                    {
                        "error": (
                            "Your account is not linked to a patient record."
                        )
                    },
                    status=status.HTTP_403_FORBIDDEN
                )

            data["patient"] = patient.pk

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)

        try:
            with transaction.atomic():
                appointment = serializer.save(status="Scheduled")
        except IntegrityError:
            return Response(
                {
                    "error": (
                        "This doctor already has an appointment "
                        "at this date and time."
                    )
                },
                status=status.HTTP_409_CONFLICT
            )

        return Response(
            self.get_serializer(appointment).data,
            status=status.HTTP_201_CREATED
        )


class AppointmentDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        appointment = get_object_or_404(
            appointments_for_user(
                request.user, ["Patient", "Doctor"]
            ),
            pk=pk
        )

        data = AppointmentSerializer(appointment).data
        data["patient_details"] = PatientSerializer(
            appointment.patient
        ).data
        data["doctor_details"] = DoctorSerializer(
            appointment.doctor
        ).data

        try:
            payment = appointment.payment
            data["payment_details"] = PaymentSerializer(payment).data
        except Payment.DoesNotExist:
            data["payment_details"] = None

        return Response(data)


class AppointmentStatusUpdateView(APIView):
    permission_classes = [IsAdminOrDoctorRole]

    def put(self, request, pk):
        new_status = request.data.get("status")

        if new_status not in ["Confirmed", "Completed", "Cancelled"]:
            return Response(
                {
                    "error": (
                        "Status must be Confirmed, Completed, or Cancelled."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            appointment = get_object_or_404(
                appointments_for_user(request.user, ["Doctor"]),
                pk=pk
            )

            appointment = Appointment.objects.select_for_update().get(
                pk=appointment.pk
            )

            if appointment.status == "Cancelled":
                return Response(
                    {"error": "Cancelled appointments cannot be updated."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if appointment.status == "Completed":
                return Response(
                    {"error": "Completed appointments cannot be updated."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if (
                new_status == "Completed"
                and appointment.status != "Confirmed"
            ):
                return Response(
                    {
                        "error": (
                            "Only confirmed appointments can be completed."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            appointment_datetime = timezone.make_aware(
                timezone.datetime.combine(
                    appointment.appointment_date,
                    appointment.appointment_time
                ),
                timezone.get_current_timezone()
            )

            if (
                new_status == "Completed"
                and timezone.now() < appointment_datetime
            ):
                return Response(
                    {
                        "error": (
                            "An appointment cannot be completed before "
                            "its scheduled date and time."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            appointment.status = new_status
            appointment.save(update_fields=["status"])

        return Response({
            "message": "Appointment status updated successfully.",
            "appointment": AppointmentSerializer(appointment).data
        })


class AppointmentPaymentView(APIView):
    permission_classes = [IsAdminOrPatientRole]

    def post(self, request, pk):
        payment_method = request.data.get("payment_method")

        if payment_method not in ["Cash", "UPI", "Card"]:
            return Response(
                {"error": "Payment method must be Cash, UPI, or Card."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            with transaction.atomic():
                appointment = get_object_or_404(
                    appointments_for_user(request.user, ["Patient"]),
                    pk=pk
                )

                appointment = Appointment.objects.select_related(
                    "doctor"
                ).select_for_update().get(pk=appointment.pk)

                if appointment.status == "Cancelled":
                    return Response(
                        {"error": "Cannot pay for a cancelled appointment."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                if Payment.objects.filter(
                    appointment=appointment
                ).exists():
                    return Response(
                        {
                            "error": (
                                "A payment already exists for this appointment."
                            )
                        },
                        status=status.HTTP_409_CONFLICT
                    )

                payment = Payment.objects.create(
                    appointment=appointment,
                    amount=appointment.doctor.consultation_fee,
                    payment_method=payment_method,
                    payment_status="Paid",
                    payment_date=timezone.now()
                )

        except IntegrityError:
            return Response(
                {"error": "A payment already exists for this appointment."},
                status=status.HTTP_409_CONFLICT
            )

        return Response(
            {
                "message": "Payment recorded successfully.",
                "payment": PaymentSerializer(payment).data
            },
            status=status.HTTP_201_CREATED
        )


class AppointmentCancelView(APIView):
    permission_classes = [IsAdminOrPatientRole]

    def post(self, request, pk):
        with transaction.atomic():
            appointment = get_object_or_404(
                appointments_for_user(request.user, ["Patient"]),
                pk=pk
            )

            appointment = Appointment.objects.select_for_update().get(
                pk=appointment.pk
            )

            if appointment.status == "Completed":
                return Response(
                    {"error": "Completed appointments cannot be cancelled."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if appointment.status == "Cancelled":
                return Response(
                    {"error": "Appointment is already cancelled."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            appointment.status = "Cancelled"
            appointment.save(update_fields=["status"])

            try:
                payment = Payment.objects.select_for_update().get(
                    appointment=appointment
                )

                if payment.payment_status == "Paid":
                    payment.payment_status = "Refunded"
                    payment.save(update_fields=["payment_status"])

            except Payment.DoesNotExist:
                pass

        return Response({
            "message": "Appointment cancelled successfully.",
            "appointment_id": appointment.id,
            "status": appointment.status
        })


class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            "message": "Authentication successful",
            "username": request.user.username,
            "user_id": request.user.id
        })
