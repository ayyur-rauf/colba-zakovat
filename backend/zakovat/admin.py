"""Zakovat admin paneli. Holatni o'zgartiruvchi amallar services.py orqali bajariladi,
shuning uchun Nizom qoidalari admin paneldan ham chetlab o'tilmaydi."""
from django import forms
from django.contrib import admin, messages

from core.models import Season

from . import services as svc
from .models import (
    Appeal, AnswerMark, Game, GameRegistration, GameResult, LineupEntry, Question, Team, TeamMember,
)


def _run(modeladmin, request, fn, objs, ok_msg):
    done = 0
    for obj in objs:
        try:
            fn(obj)
            done += 1
        except svc.RuleError as exc:
            modeladmin.message_user(request, f"{obj}: {exc}", messages.ERROR)
    if done:
        modeladmin.message_user(request, f"{ok_msg}: {done} ta", messages.SUCCESS)


class TeamMemberInline(admin.TabularInline):
    model = TeamMember
    extra = 0
    fields = ("user", "status", "joined_at", "left_at")
    readonly_fields = fields
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("name", "season", "captain", "status", "approved_at")
    list_filter = ("season", "status")
    search_fields = ("name",)
    readonly_fields = ("status", "approved_by", "approved_at", "status_reason", "name_key")
    inlines = [TeamMemberInline]
    actions = ["approve"]

    @admin.action(description="Jamoani tasdiqlash")
    def approve(self, request, queryset):
        _run(self, request, lambda t: svc.approve_team(t, request.user), queryset, "Tasdiqlandi")


class RegistrationInline(admin.TabularInline):
    model = GameRegistration
    extra = 0
    fields = ("team", "status", "table_number", "created_at")
    readonly_fields = fields
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class ResultInline(admin.TabularInline):
    model = GameResult
    extra = 0
    fields = ("place", "team", "points", "rating_j", "eligible", "tie_group")
    readonly_fields = fields
    can_delete = False
    ordering = ("place",)

    def has_add_permission(self, request, obj=None):
        return False


class GameForm(forms.ModelForm):
    change_reason = forms.CharField(
        label="O'zgartirish sababi", required=False,
        help_text="O'yinga 1 kundan kam qolganda sana yoki joyni o'zgartirish uchun majburiy [N-1.4]")

    class Meta:
        model = Game
        fields = "__all__"


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    form = GameForm
    list_display = ("title", "season", "kind", "starts_at", "venue", "status")
    list_filter = ("season", "kind", "status")
    readonly_fields = ("status", "current_round", "current_question", "tiebreak_for", "tiebreak_for_season")
    inlines = [RegistrationInline, ResultInline]
    actions = ["open_registration", "start", "publish", "finalize"]

    def save_model(self, request, obj, form, change):
        if change:
            changes = {f: form.cleaned_data[f] for f in form.changed_data if f != "change_reason"}
            if not changes:
                return
            try:
                svc.update_game(Game.objects.get(pk=obj.pk), request.user,
                                reason=form.cleaned_data.get("change_reason", ""), **changes)
            except svc.RuleError as exc:
                self.message_user(request, str(exc), messages.ERROR)
        else:
            super().save_model(request, obj, form, change)

    @admin.action(description="Ro'yxatdan o'tishni ochish")
    def open_registration(self, request, queryset):
        _run(self, request, lambda g: svc.open_registration(g, request.user), queryset, "Ochildi")

    @admin.action(description="O'yinni boshlash")
    def start(self, request, queryset):
        _run(self, request, lambda g: svc.start_game(g, request.user), queryset, "Boshlandi")

    @admin.action(description="Dastlabki natijani e'lon qilish")
    def publish(self, request, queryset):
        _run(self, request, lambda g: svc.publish_preliminary(g, request.user), queryset, "E'lon qilindi")

    @admin.action(description="Yakuniy natijani tasdiqlash")
    def finalize(self, request, queryset):
        _run(self, request, lambda g: svc.finalize_game(g, request.user), queryset, "Yakunlandi")


@admin.register(GameRegistration)
class GameRegistrationAdmin(admin.ModelAdmin):
    list_display = ("game", "team", "status", "table_number", "created_at")
    list_filter = ("game__season", "game", "status")
    readonly_fields = ("game", "team", "status", "table_number")
    actions = ["approve"]

    def has_add_permission(self, request):
        return False

    @admin.action(description="Arizani tasdiqlash")
    def approve(self, request, queryset):
        _run(self, request, lambda r: svc.approve_registration(r, request.user), queryset, "Tasdiqlandi")


@admin.register(Appeal)
class AppealAdmin(admin.ModelAdmin):
    list_display = ("game", "team", "number", "status", "created_at", "decided_by")
    list_filter = ("game", "status")
    readonly_fields = ("game", "team", "number", "content", "evidence", "evidence_file", "submitted_by",
                       "status", "decided_by", "decision_reason", "created_at", "decided_at")

    def has_add_permission(self, request):
        return False


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("__str__", "topic", "difficulty", "status", "author")
    list_filter = ("status", "topic", "difficulty")
    search_fields = ("text", "answer")


@admin.register(AnswerMark)
class AnswerMarkAdmin(admin.ModelAdmin):
    list_display = ("game", "team", "number", "correct", "updated_by", "updated_at")
    list_filter = ("game",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(LineupEntry)
class LineupEntryAdmin(admin.ModelAdmin):
    list_display = ("game", "team", "round_no", "user", "from_question")
    list_filter = ("game",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.action(description="Zakovat: har oyning 3-shanbasiga liga o'yinlarini yaratish")
def generate_schedule(modeladmin, request, queryset):
    for season in queryset:
        try:
            games = svc.generate_league_schedule(season, request.user)
            modeladmin.message_user(request, f"{season}: {len(games)} ta o'yin yaratildi", messages.SUCCESS)
        except svc.RuleError as exc:
            modeladmin.message_user(request, f"{season}: {exc}", messages.ERROR)


admin.site._registry[Season].actions = [*admin.site._registry[Season].actions, generate_schedule]
