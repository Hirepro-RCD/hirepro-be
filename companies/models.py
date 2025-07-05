from django.db import models
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()

class Company(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('rejected', 'Rejected'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    subdomain = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    website = models.URLField(blank=True)
    logo = models.ImageField(upload_to='company_logos/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Companies"
    
    def __str__(self):
        return self.name
    
    @property
    def domain_url(self):
        return f"{self.subdomain}"

class CompanyUser(models.Model):
    ROLE_CHOICES = [
        ('company_admin', 'Company Admin'),
        ('hr_manager', 'HR Manager'), 
        ('hr_recruiter', 'HR Recruiter'),
        ('interviewer', 'Interviewer'),
        ('csr', 'Customer Success Representative'),
    ]
    
    STATUS_CHOICES = [
        ('pending_setup', 'Pending Setup'),
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    permissions = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending_setup')
    invited_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='invited_users'
    )
    invited_at = models.DateTimeField(auto_now_add=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ['user', 'company']
    
    def __str__(self):
        return f"{self.user.username} - {self.company.name} ({self.role})"

class InviteToken(models.Model):
    TOKEN_TYPE_CHOICES = [
        ('user_invite', 'User Invite'),
        ('password_reset', 'Password Reset'),
        ('company_setup', 'Company Setup'),
    ('interviewer_invite', 'Interviewer Invite'), 
    ]
    
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    token_type = models.CharField(max_length=20, choices=TOKEN_TYPE_CHOICES)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True)
    email = models.EmailField()
    data = models.JSONField(default=dict, blank=True)  # Store additional data
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.token_type} - {self.email}"
    
    @property
    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.expires_at
    
    @property
    def is_used(self):
        return self.used_at is not None