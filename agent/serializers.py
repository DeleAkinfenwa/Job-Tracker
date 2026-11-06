from rest_framework import serializers

from tracker.models import Application

from .models import AgentRun, CareerEntry

MAX_JOB_TEXT = 20000
MAX_LOG_TEXT = 4000


class ProfileSerializer(serializers.Serializer):
    yaml = serializers.CharField(allow_blank=True, max_length=60000, trim_whitespace=False)
    updated_at = serializers.DateTimeField(read_only=True, allow_null=True)
    roles = serializers.ListField(child=serializers.DictField(), read_only=True)


class CareerEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = CareerEntry
        fields = (
            "id", "entry_date", "role", "source", "raw_text", "summary",
            "tools", "skills", "accomplishments", "metrics", "created_at",
        )  # fmt: skip
        read_only_fields = ("id", "source", "created_at")


# Input for logging new work. use_ai asks the model to pull out the facts (counts toward the daily cap).
class LogEntrySerializer(serializers.Serializer):
    role = serializers.CharField(max_length=80)
    entry_date = serializers.DateField()
    raw_text = serializers.CharField(max_length=MAX_LOG_TEXT)
    use_ai = serializers.BooleanField(default=False)


# A list of entries exported from another copy of the agent.
class ImportEntriesSerializer(serializers.Serializer):
    entries = serializers.ListField(child=serializers.DictField(), max_length=2000)
    replace = serializers.BooleanField(default=False)


# Input for a fit check or a tailored resume.
class JobRequestSerializer(serializers.Serializer):
    job_text = serializers.CharField(max_length=MAX_JOB_TEXT)
    job_title = serializers.CharField(max_length=200, required=False, allow_blank=True, default="")
    application_id = serializers.IntegerField(required=False, allow_null=True, default=None)

    # Only your own applications can be linked.
    def validate_application_id(self, value):
        if value is None:
            return None
        app = Application.objects.filter(pk=value, owner=self.context["request"].user).first()
        if not app:
            raise serializers.ValidationError("Choose one of your applications.")
        return app


class AgentRunSerializer(serializers.ModelSerializer):
    application_id = serializers.IntegerField(source="application.id", read_only=True, allow_null=True)

    class Meta:
        model = AgentRun
        fields = (
            "id", "kind", "job_title", "job_text", "application_id", "result", "ok", "error",
            "input_tokens", "output_tokens", "created_at",
        )  # fmt: skip
        read_only_fields = fields


class AgentRunListSerializer(AgentRunSerializer):
    fit_score = serializers.SerializerMethodField()

    class Meta(AgentRunSerializer.Meta):
        fields = ("id", "kind", "job_title", "application_id", "fit_score", "ok", "error", "created_at")
        read_only_fields = fields

    def get_fit_score(self, run) -> int | None:
        score = (run.result or {}).get("fit_score")
        return score if isinstance(score, int) else None


class StatusSerializer(serializers.Serializer):
    configured = serializers.BooleanField()
    model = serializers.CharField()
    has_profile = serializers.BooleanField()
    entry_count = serializers.IntegerField()
    runs_today = serializers.IntegerField()
    daily_run_limit = serializers.IntegerField()
    tokens_today = serializers.IntegerField()
    daily_token_limit = serializers.IntegerField()
