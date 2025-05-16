from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import get_user_model
from .models import Role, UserRole, SurveyTemplate, Question, Survey, RaterGroup, Respondent, Rater, \
    Response, Report, User
from django.contrib import admin
from .models import SurveyTemplate


# Inline-админки
class UserRoleInline(admin.TabularInline):
    model = UserRole
    extra = 1
    verbose_name = 'Роль пользователя'
    verbose_name_plural = 'Роли пользователей'


# Кастомная админка для User
class CustomUserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name',
                    'position', 'department', 'is_active')
    list_filter = ('is_active', 'department', 'userrole__role__name')
    search_fields = ('username', 'email', 'first_name', 'last_name')

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Персональная информация', {'fields': ('first_name', 'last_name', 'email')}),
        ('Права доступа', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Важные даты', {'fields': ('last_login', 'date_joined')}),
        ('Дополнительная информация', {'fields': ('position', 'department')}),
    )

    inlines = [UserRoleInline]


# Админки для остальных моделей
@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)
    list_editable = ('description',)


@admin.register(SurveyTemplate)
class SurveyTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_by', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_by')
    actions = ['activate_templates', 'deactivate_templates']

    def activate_templates(self, request, queryset):
        queryset.update(is_active=True)

    activate_templates.short_description = "Активировать выбранные шаблоны"

    def deactivate_templates(self, request, queryset):
        queryset.update(is_active=False)

    deactivate_templates.short_description = "Деактивировать выбранные шаблоны"

    def has_change_permission(self, request, obj=None):
        return request.user.has_perm('feedback360.can_manage_templates')

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('text', 'template', 'answer_type')
    list_filter = ('template', 'answer_type')
    search_fields = ('text',)


@admin.register(Survey)
class SurveyAdmin(admin.ModelAdmin):
    list_display = ('name', 'template', 'status', 'start_date', 'end_date', 'created_by')
    list_filter = ('status', 'template', 'created_by')
    search_fields = ('name', 'description')
    date_hierarchy = 'created_at'


@admin.register(RaterGroup)
class RaterGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)


@admin.register(Respondent)
class RespondentAdmin(admin.ModelAdmin):
    list_display = ('user', 'survey', 'status')
    list_filter = ('survey', 'status')
    search_fields = ('user__username',)


@admin.register(Rater)
class RaterAdmin(admin.ModelAdmin):
    list_display = ('user', 'respondent', 'relationship_type', 'status')
    list_filter = ('status', 'relationship_type')
    search_fields = ('user__username', 'respondent__user__username')


@admin.register(Response)
class ResponseAdmin(admin.ModelAdmin):
    list_display = ('rater', 'question', 'answer_value')
    list_filter = ('question__answer_type',)
    search_fields = ('rater__user__username',)


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('survey', 'respondent', 'generated_at', 'status')
    readonly_fields = ('generated_at',)

    def status(self, obj):
        if not obj.report_data:
            return 'Не сформирован'
        return f"Сформирован ({obj.generated_at.strftime('%d.%m.%Y')})"


# Регистрируем кастомную модель User последней
admin.site.register(User, CustomUserAdmin)
