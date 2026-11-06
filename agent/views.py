"""Resume agent endpoints. Every one is locked to the owner (see access.py)."""

import io
import re

from django.conf import settings
from django.http import HttpResponse
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .access import IsAgentOwner
from .engine.profile import parse_profile
from .engine.render import to_docx, to_markdown
from .models import AgentRun, CareerEntry, CareerProfile
from .serializers import (
    AgentRunListSerializer,
    AgentRunSerializer,
    CareerEntrySerializer,
    ImportEntriesSerializer,
    JobRequestSerializer,
    LogEntrySerializer,
    ProfileSerializer,
    StatusSerializer,
)
from .services import (
    AgentUnavailable,
    import_entries,
    import_profile_bullets,
    is_configured,
    log_entry,
    run_job,
    usage_today,
)

TEMPLATE = (settings.BASE_DIR / "agent" / "engine" / "profile_template.yaml").read_text(encoding="utf-8")


def problem(exc: AgentUnavailable) -> Response:
    return Response({"detail": str(exc)}, status=exc.status)


class AgentView:
    """Shared by every agent view: owner only, and its own stricter rate limit."""

    permission_classes = [IsAgentOwner]
    throttle_scope = "agent"


class StatusView(AgentView, APIView):
    """Whether the agent is ready, and how much of today's cap is used."""

    @extend_schema(responses=StatusSerializer)
    def get(self, request):
        record = CareerProfile.objects.filter(owner=request.user).first()
        data = {
            "configured": is_configured(),
            "model": settings.AGENT_MODEL,
            "has_profile": bool(record and record.yaml.strip()),
            "entry_count": CareerEntry.objects.filter(owner=request.user).count(),
            **usage_today(request.user),
        }
        return Response(StatusSerializer(data).data)


class ProfileView(AgentView, APIView):
    """Your profile as YAML. Until you save one, a starter template is returned."""

    @staticmethod
    def payload(record):
        text = record.yaml if record and record.yaml.strip() else TEMPLATE
        try:
            roles = [
                {"key": r["key"], "company": r["company"], "title": r["title"]}
                for r in parse_profile(text).get("roles", [])
            ]
        except ValueError:
            roles = []
        return {"yaml": text, "updated_at": record.updated_at if record else None, "roles": roles}

    @extend_schema(responses=ProfileSerializer)
    def get(self, request):
        return Response(self.payload(CareerProfile.objects.filter(owner=request.user).first()))

    @extend_schema(request=ProfileSerializer, responses=ProfileSerializer)
    def put(self, request):
        serializer = ProfileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        text = serializer.validated_data["yaml"]
        try:
            parse_profile(text)
        except ValueError as exc:
            return Response({"yaml": [str(exc)]}, status=status.HTTP_400_BAD_REQUEST)
        record, _ = CareerProfile.objects.update_or_create(owner=request.user, defaults={"yaml": text})
        return Response(self.payload(record))


class CareerEntryViewSet(AgentView, viewsets.ModelViewSet):
    """Your career log. Each resume bullet must cite at least one of these entries."""

    serializer_class = CareerEntrySerializer
    pagination_class = None
    http_method_names = ["get", "post", "patch", "delete"]

    queryset = CareerEntry.objects.none()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return CareerEntry.objects.none()
        return CareerEntry.objects.filter(owner=self.request.user).order_by("-entry_date", "-id")

    @extend_schema(request=LogEntrySerializer, responses={201: CareerEntrySerializer})
    def create(self, request):
        serializer = LogEntrySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            entry, questions = log_entry(request.user, **serializer.validated_data)
        except AgentUnavailable as exc:
            return problem(exc)
        data = CareerEntrySerializer(entry).data | {"open_questions": questions}
        return Response(data, status=status.HTTP_201_CREATED)

    @extend_schema(request=None, responses={200: OpenApiResponse(description="How many bullets were imported")})
    @action(detail=False, methods=["post"])
    def import_profile(self, request):
        """Copy the bullets under each role in your profile into the log as starting evidence."""
        try:
            count = import_profile_bullets(request.user)
        except AgentUnavailable as exc:
            return problem(exc)
        return Response({"imported": count})

    @extend_schema(
        request=ImportEntriesSerializer, responses={200: OpenApiResponse(description="How many were imported")}
    )
    @action(detail=False, methods=["post"])
    def import_json(self, request):
        """Load entries exported from another copy of the agent. With replace, your current log is cleared first."""
        serializer = ImportEntriesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            count = import_entries(
                request.user, serializer.validated_data["entries"], serializer.validated_data["replace"]
            )
        except AgentUnavailable as exc:
            return problem(exc)
        return Response({"imported": count})


class RunViewSet(AgentView, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Fit checks and tailored resumes you've run, newest first."""

    queryset = AgentRun.objects.none()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return AgentRun.objects.none()
        runs = AgentRun.objects.filter(owner=self.request.user).exclude(kind=AgentRun.Kind.EXTRACT)
        if application := self.request.query_params.get("application"):
            runs = runs.filter(application_id=application) if application.isdigit() else runs.none()
        return runs

    def get_serializer_class(self):
        return AgentRunListSerializer if self.action == "list" else AgentRunSerializer

    def _start(self, request, kind):
        serializer = JobRequestSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        app = data["application_id"]
        title = data["job_title"] or (f"{app.role_title} at {app.company.name}" if app else "")
        try:
            run = run_job(request.user, kind, data["job_text"], job_title=title, application=app)
        except AgentUnavailable as exc:
            return problem(exc)
        return Response(AgentRunSerializer(run).data, status=status.HTTP_201_CREATED)

    @extend_schema(request=JobRequestSerializer, responses={201: AgentRunSerializer})
    @action(detail=False, methods=["post"])
    def evaluate(self, request):
        """Score how well a job posting fits your record, without writing a resume."""
        return self._start(request, AgentRun.Kind.EVALUATE)

    @extend_schema(request=JobRequestSerializer, responses={201: AgentRunSerializer})
    @action(detail=False, methods=["post"])
    def tailor(self, request):
        """Write a resume for a job posting. Every claim is checked against your record before it's returned."""
        return self._start(request, AgentRun.Kind.TAILOR)

    def _tailored(self):
        run = self.get_object()
        if run.kind != AgentRun.Kind.TAILOR or not run.ok:
            raise AgentUnavailable("Only a finished tailored resume can be downloaded.", 404)
        return run

    @extend_schema(responses={200: OpenApiResponse(description="Word file")})
    @action(detail=True, methods=["get"])
    def docx(self, request, pk=None):
        """The tailored resume as a Word file that applicant tracking systems can read."""
        try:
            run = self._tailored()
        except AgentUnavailable as exc:
            return problem(exc)
        buffer = io.BytesIO()
        to_docx(run.result, run.profile_snapshot, buffer)
        name = (run.profile_snapshot.get("contact") or {}).get("name") or "Resume"
        filename = re.sub(r"[^A-Za-z0-9 ._-]+", "", f"{name} - {run.job_title or 'Resume'}")[:120].strip() or "Resume"
        response = HttpResponse(
            buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}.docx"'
        return response

    @extend_schema(responses={200: OpenApiResponse(description="Plain text for pasting into forms")})
    @action(detail=True, methods=["get"])
    def text(self, request, pk=None):
        """The tailored resume as Markdown text."""
        try:
            run = self._tailored()
        except AgentUnavailable as exc:
            return problem(exc)
        return Response({"text": to_markdown(run.result, run.profile_snapshot)})
