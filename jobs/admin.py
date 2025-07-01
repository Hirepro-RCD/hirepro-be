from django.contrib import admin
from .models import Job

@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ['title', 'company', 'status', 'employment_type', 'experience_level', 'application_deadline', 'created_at']
    list_filter = ['status', 'employment_type', 'experience_level', 'interview_type', 'visibility']
    search_fields = ['title', 'description', 'requirements', 'company__name']
    date_hierarchy = 'created_at'
    fieldsets = (
        ('Basic Info', {
            'fields': ('title', 'description', 'requirements', 'location')
        }),
        ('Job Details', {
            'fields': ('employment_type', 'experience_level', 'application_deadline')
        }),
        ('Compensation', {
            'fields': ('salary_min', 'salary_max', 'salary_currency')
        }),
        ('Interview', {
            'fields': ('interview_type', 'ai_interview_config')
        }),
        ('Status', {
            'fields': ('status', 'visibility')
        }),
        ('Relationships', {
            'fields': ('company', 'created_by')
        }),
    )
