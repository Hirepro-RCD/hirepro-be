from django.db import models
import uuid
from companies.models import Company
from accounts.models import User

class Job(models.Model):
    EMPLOYMENT_TYPE_CHOICES = [
        ('FULL_TIME', 'Full Time'),
        ('PART_TIME', 'Part Time'),
        ('CONTRACT', 'Contract'),
        ('INTERNSHIP', 'Internship'),
        ('FREELANCE', 'Freelance'),
    ]
    
    EXPERIENCE_LEVEL_CHOICES = [
        ('ENTRY_LEVEL', 'Entry Level'),
        ('MID_LEVEL', 'Mid Level'),
        ('SENIOR_LEVEL', 'Senior Level'),
        ('EXECUTIVE', 'Executive'),
    ]
    
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('PUBLISHED', 'Published'),
        ('CLOSED', 'Closed'),
        ('ARCHIVED', 'Archived'),
    ]
    
    VISIBILITY_CHOICES = [
        ('PUBLIC', 'Public'),
        ('PRIVATE', 'Private'),
        ('INTERNAL', 'Internal'),
    ]
    
    INTERVIEW_TYPE_CHOICES = [
        ('NONE', 'No Interview'),
        ('AI_INTERVIEW', 'AI Interview'),
        ('HUMAN_INTERVIEW', 'Human Interview'),
        ('HYBRID', 'Hybrid Interview'),
    ]
    
    CURRENCY_CHOICES = [
        ('USD', 'US Dollar'),
        ('EUR', 'Euro'),
        ('GBP', 'British Pound'),
        ('INR', 'Indian Rupee'),
        ('CAD', 'Canadian Dollar'),
        ('AUD', 'Australian Dollar'),
        ('SGD', 'Singapore Dollar'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='jobs')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_jobs')
    
    title = models.CharField(max_length=255)
    description = models.TextField()
    requirements = models.TextField()
    location = models.CharField(max_length=255)
    
    employment_type = models.CharField(max_length=20, choices=EMPLOYMENT_TYPE_CHOICES)
    experience_level = models.CharField(max_length=20, choices=EXPERIENCE_LEVEL_CHOICES)
    
    salary_min = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    salary_max = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    salary_currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='USD')
    
    application_deadline = models.DateField()
    interview_type = models.CharField(max_length=20, choices=INTERVIEW_TYPE_CHOICES, default='NONE')
    
    # Interview configuration stored as JSON
    ai_interview_config = models.JSONField(null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default='PUBLIC')
    
    # Additional timestamp for tracking when a job is published
    published_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.title} at {self.company.name}"


class JobInterviewer(models.Model):
    """
    Associates users with jobs as interviewers.
    """
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive'),
    ]
    
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='interviewers')
    interviewer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='interviewer_jobs')
    added_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='added_interviewers')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['job', 'interviewer']
        
    def __str__(self):
        return f"{self.interviewer.email} - {self.job.title}"
