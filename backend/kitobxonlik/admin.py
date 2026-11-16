from django.contrib import admin, messages

from . import services as svc
from .models import Book, Criterion, Extension, Grade, ReadingRound, Review, SeasonConfig, Vote


@admin.register(SeasonConfig)
class SeasonConfigAdmin(admin.ModelAdmin):
    list_display = ("season", "leaderboard_public")


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "rights_confirmed", "added_by", "created_at")
    search_fields = ("title", "author")

    def save_model(self, request, obj, form, change):
        if not obj.rights_confirmed:
            self.message_user(request, "Diqqat: tarqatish huquqi tasdiqlanmagan.", messages.WARNING)
        if not obj.added_by_id:
            obj.added_by = request.user
        super().save_model(request, obj, form, change)


class CriterionInline(admin.TabularInline):
    model = Criterion
    extra = 0


@admin.register(ReadingRound)
class ReadingRoundAdmin(admin.ModelAdmin):
    list_display = ("title", "season", "status", "selected_book", "vote_ends", "reading_ends")
    list_filter = ("season", "status")
    filter_horizontal = ("candidates",)
    readonly_fields = ("status", "selected_book", "reading_starts", "reading_ends", "created_by")
    inlines = [CriterionInline]
    actions = ["start_grading", "approve"]

    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def _run(self, request, queryset, fn, ok):
        for rnd in queryset:
            try:
                fn(rnd)
                self.message_user(request, f"{rnd}: {ok}", messages.SUCCESS)
            except svc.RuleError as exc:
                self.message_user(request, f"{rnd}: {exc}", messages.ERROR)

    @admin.action(description="Baholashni boshlash")
    def start_grading(self, request, queryset):
        self._run(request, queryset, lambda r: svc.start_grading(r, request.user), "baholash boshlandi")

    @admin.action(description="Natijalarni tasdiqlash (ballar reestrga)")
    def approve(self, request, queryset):
        self._run(request, queryset, lambda r: svc.approve_results(r, request.user), "tasdiqlandi")


class GradeInline(admin.TabularInline):
    model = Grade
    extra = 0
    fields = ("reviewer", "total", "comment", "updated_at")
    readonly_fields = fields
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("user", "round", "status", "final_score", "submitted_at")
    list_filter = ("round", "status")
    readonly_fields = ("round", "user", "text", "file", "status", "final_score", "submitted_at")
    inlines = [GradeInline]

    def has_add_permission(self, request):
        return False


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ("round", "user", "book", "updated_at")
    list_filter = ("round",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Extension)
class ExtensionAdmin(admin.ModelAdmin):
    list_display = ("round", "user", "until", "reason", "granted_by")
    readonly_fields = ("round", "user", "until", "reason", "granted_by")

    def has_add_permission(self, request):
        return False
