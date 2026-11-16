from django import forms
from django.contrib import admin

from .models import Announcement, AuditLog, PointsEntry, RoleAssignment, Season
from .services import log_action


@admin.register(Season)
class SeasonAdmin(admin.ModelAdmin):
    list_display = ("name", "start_date", "end_date", "is_active")
    list_filter = ("is_active",)


@admin.register(RoleAssignment)
class RoleAssignmentAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "module", "season", "granted_by", "created_at")
    list_filter = ("role", "module", "season")
    search_fields = ("user__employee__full_name", "user__username")
    autocomplete_fields = ("user",)
    readonly_fields = ("granted_by", "created_at")

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)

        class Form(form):
            def clean(self):
                data = super().clean()
                dup = RoleAssignment.objects.filter(user=data.get("user"), role=data.get("role"),
                                                    module=data.get("module"), season=data.get("season"))
                if self.instance.pk:
                    dup = dup.exclude(pk=self.instance.pk)
                if dup.exists():
                    raise forms.ValidationError("Bu rol allaqachon berilgan.")
                return data

        return Form

    def save_model(self, request, obj, form, change):
        if not obj.granted_by_id:
            obj.granted_by = request.user
        super().save_model(request, obj, form, change)
        log_action(request.user, "role.saved", obj,
                   after={"user": obj.user_id, "role": obj.role, "module": obj.module,
                          "season": obj.season_id})

    def delete_model(self, request, obj):
        log_action(request.user, "role.deleted", obj,
                   before={"user": obj.user_id, "role": obj.role, "module": obj.module,
                           "season": obj.season_id})
        super().delete_model(request, obj)


@admin.register(PointsEntry)
class PointsEntryAdmin(admin.ModelAdmin):
    list_display = ("created_at", "season", "module", "subject_type", "subject_id", "amount",
                    "reason_type", "reason_id", "created_by", "note")
    list_filter = ("season", "module", "subject_type", "reason_type")
    search_fields = ("subject_id", "reason_id", "note")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "actor", "action", "object_type", "object_id")
    list_filter = ("action", "object_type")
    search_fields = ("object_id", "note")

    # Jurnal faqat o'qiladi
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ("title", "module", "pinned", "is_active", "author", "created_at")
    list_filter = ("module", "pinned", "is_active")
