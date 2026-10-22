from rest_framework import serializers

from .models import Application, Company


class CompanySerializer(serializers.ModelSerializer):
    application_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Company
        fields = (
            "id",
            "name",
            "website",
            "industry",
            "location",
            "application_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate_name(self, value: str) -> str:
        user = self.context["request"].user
        qs = Company.objects.filter(owner=user, name__iexact=value)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("You already have a company with this name.")
        return value


class CompanySummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ("id", "name", "website")


class ApplicationSerializer(serializers.ModelSerializer):
    company = CompanySummarySerializer(read_only=True)
    company_id = serializers.PrimaryKeyRelatedField(source="company", queryset=Company.objects.none(), write_only=True)

    class Meta:
        model = Application
        fields = (
            "id",
            "company",
            "company_id",
            "role_title",
            "status",
            "job_url",
            "salary_min",
            "salary_max",
            "applied_on",
            "notes",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Users can only attach applications to their own companies.
        request = self.context.get("request")
        if request is not None and request.user.is_authenticated:
            self.fields["company_id"].queryset = Company.objects.filter(owner=request.user)

    def validate(self, attrs):
        # On PATCH, compare against the stored value for whichever side wasn't sent.
        salary_min = attrs.get("salary_min", getattr(self.instance, "salary_min", None))
        salary_max = attrs.get("salary_max", getattr(self.instance, "salary_max", None))
        if salary_min is not None and salary_max is not None and salary_min > salary_max:
            raise serializers.ValidationError({"salary_min": "Must be less than or equal to salary_max."})
        return attrs


class StatusCountSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Application.Status.choices)
    count = serializers.IntegerField()


class ApplicationStatsSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    by_status = StatusCountSerializer(many=True)
    response_rate = serializers.FloatField(help_text="Share of submitted applications that reached interview or offer.")
