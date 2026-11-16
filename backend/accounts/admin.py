from django import forms
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.shortcuts import redirect, render
from django.urls import path, reverse

from core.services import log_action

from .importer import ImportFormatError, import_employees
from .models import AuthIdentity, Branch, Employee, User, mask_phone


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


class EmployeeImportForm(forms.Form):
    file = forms.FileField(label="Excel fayl (.xlsx)")
    dry_run = forms.BooleanField(label="Faqat tekshirish (saqlamaslik)", required=False, initial=True)
    deactivate_missing = forms.BooleanField(
        label="Faylda yo'q xodimlarni 'ishlamaydi' deb belgilash", required=False)


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("full_name", "branch", "position", "masked_phone", "email", "is_active", "has_account")
    list_filter = ("is_active", "branch")
    search_fields = ("full_name", "email", "telegram_username", "phone")
    change_list_template = "admin/accounts/employee/change_list.html"

    @admin.display(description="telefon")
    def masked_phone(self, obj):
        return mask_phone(obj.phone)

    @admin.display(description="akkaunt", boolean=True)
    def has_account(self, obj):
        return hasattr(obj, "user")

    def get_urls(self):
        return [
            path("import/", self.admin_site.admin_view(self.import_view), name="accounts_employee_import"),
        ] + super().get_urls()

    def import_view(self, request):
        if not request.user.is_superuser:
            messages.error(request, "Faqat bosh admin xodimlar ro'yxatini yuklay oladi.")
            return redirect(reverse("admin:accounts_employee_changelist"))
        report = None
        form = EmployeeImportForm(request.POST or None, request.FILES or None)
        if request.method == "POST" and form.is_valid():
            try:
                report = import_employees(
                    form.cleaned_data["file"],
                    dry_run=form.cleaned_data["dry_run"],
                    deactivate_missing=form.cleaned_data["deactivate_missing"],
                )
            except ImportFormatError as exc:
                messages.error(request, str(exc))
            except Exception:  # noqa: BLE001 — buzilgan fayl
                messages.error(request, "Faylni o'qib bo'lmadi. U .xlsx formatida ekanini tekshiring.")
            else:
                if not report.ok:
                    messages.error(request, "Xatolar bor — hech narsa saqlanmadi.")
                elif form.cleaned_data["dry_run"]:
                    messages.info(request, "Tekshiruv tugadi, bazaga yozilmadi. " + report.summary())
                else:
                    log_action(request.user, "employees.imported", note=report.summary())
                    messages.success(request, "Saqlandi. " + report.summary())
        context = {**self.admin_site.each_context(request), "form": form, "report": report,
                   "title": "Xodimlar ro'yxatini yuklash", "opts": self.model._meta}
        return render(request, "admin/accounts/employee/import.html", context)


class AuthIdentityInline(admin.TabularInline):
    model = AuthIdentity
    extra = 0
    fields = ("provider", "uid", "created_at", "last_used_at")
    readonly_fields = fields
    can_delete = True

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("__str__", "status", "employee", "is_superuser", "last_login")
    list_filter = ("status", "is_superuser", "employee__branch")
    search_fields = ("username", "display_name", "employee__full_name", "email")
    autocomplete_fields = ("employee",)
    inlines = [AuthIdentityInline]
    actions = ["approve", "block"]
    fieldsets = (
        (None, {"fields": ("username", "status", "employee", "display_name", "email", "avatar")}),
        ("Huquqlar", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Sanalar", {"fields": ("last_login", "date_joined")}),
        ("Parol (faqat admin panel uchun)", {"classes": ("collapse",), "fields": ("password",)}),
    )

    def save_model(self, request, obj, form, change):
        before = None
        if change:
            old = User.objects.get(pk=obj.pk)
            before = {"status": old.status, "employee": old.employee_id}
        super().save_model(request, obj, form, change)
        log_action(request.user, "user.saved", obj, before=before,
                   after={"status": obj.status, "employee": obj.employee_id})

    @admin.action(description="Tasdiqlash (faollashtirish)")
    def approve(self, request, queryset):
        no_emp = queryset.filter(employee__isnull=True, is_superuser=False)
        if no_emp.exists():
            self.message_user(request, "Avval akkauntni xodimga bog'lang: "
                              + ", ".join(str(u) for u in no_emp[:10]), messages.ERROR)
            return
        for user in queryset:
            log_action(request.user, "user.approved", user, before={"status": user.status},
                       after={"status": User.Status.ACTIVE})
        queryset.update(status=User.Status.ACTIVE)

    @admin.action(description="Bloklash")
    def block(self, request, queryset):
        for user in queryset:
            log_action(request.user, "user.blocked", user, before={"status": user.status},
                       after={"status": User.Status.BLOCKED})
        queryset.update(status=User.Status.BLOCKED)
