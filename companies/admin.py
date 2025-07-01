from django.contrib import admin

from django.contrib import admin
from .models import Company, CompanyUser, InviteToken

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['name', 'subdomain', 'status', 'contact_email', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['name', 'subdomain', 'contact_email']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    actions = ['approve_companies', 'suspend_companies']
    
    def approve_companies(self, request, queryset):
        queryset.update(status='active')
        self.message_user(request, f"Approved {queryset.count()} companies")
    approve_companies.short_description = "Approve selected companies"
    
    def suspend_companies(self, request, queryset):
        queryset.update(status='suspended')
        self.message_user(request, f"Suspended {queryset.count()} companies")
    suspend_companies.short_description = "Suspend selected companies"

@admin.register(CompanyUser)
class CompanyUserAdmin(admin.ModelAdmin):
    list_display = ['user', 'company', 'role', 'status', 'invited_at']
    list_filter = ['role', 'status', 'company']
    search_fields = ['user__username', 'user__email', 'company__name']
    readonly_fields = ['invited_at', 'activated_at']

@admin.register(InviteToken)
class InviteTokenAdmin(admin.ModelAdmin):
    list_display = ['email', 'token_type', 'expires_at', 'used_at', 'created_at']
    list_filter = ['token_type', 'expires_at', 'used_at']
    search_fields = ['email', 'token']
    readonly_fields = ['token', 'created_at']