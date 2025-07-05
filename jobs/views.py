"""
View functions for the jobs app.
All helper functions have been moved to helpers.py.
Only endpoint functions remain here for clarity.
"""
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes

from .models import Job
from companies.models import CompanyUser
from companies.views import IsCompanyAdmin
from utils.email import send_email
from django.conf import settings

from .helpers import (
    is_company_member, has_job_permission, job_to_dict,
    create_job as helper_create_job, update_job as helper_update_job,
    get_user_company
)

# Custom permission class (kept for backward compatibility)
class IsCompanyMember(permissions.BasePermission):
    """
    Custom permission to only allow members of the company to access jobs.
    """
    def has_permission(self, request, view):
        return is_company_member(request)

    def has_object_permission(self, request, view, obj):
        return has_job_permission(request, obj)

# API views with decorators - only functions called directly from urls.py
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated, IsCompanyMember])
def list_jobs(request):
    """Get a list of all jobs for the user's company."""
    user = request.user
    # Get all companies where the user is an active member
    company_ids = get_user_company_ids(request)
    
    # Apply filters
    queryset = filter_jobs(Job.objects.filter(company_id__in=company_ids), request)
    
    # Convert to list representation
    jobs_data = [job_to_dict(job, include_all_fields=False) for job in queryset]
    return Response(jobs_data)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated, IsCompanyMember])
def create_job_view(request):
    """Create a new job."""
    job, error = helper_create_job(request)
    
    if error:
        return Response(error, status=status.HTTP_400_BAD_REQUEST)
        
    return Response(job_to_dict(job), status=status.HTTP_201_CREATED)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated, IsCompanyMember])
def get_job(request, pk):
    """Get a specific job by ID."""
    try:
        job = Job.objects.get(pk=pk)
    except Job.DoesNotExist:
        return Response({"detail": "Job not found."}, status=status.HTTP_404_NOT_FOUND)
    
    # Check if user has permission to access this job
    if not has_job_permission(request, job):
        return Response({"detail": "You don't have permission to access this job."}, 
                       status=status.HTTP_403_FORBIDDEN)
    
    return Response(job_to_dict(job))

@api_view(['PUT', 'PATCH'])
@permission_classes([permissions.IsAuthenticated, IsCompanyMember])
def update_job_view(request, pk):
    """Update an existing job."""
    try:
        job = Job.objects.get(pk=pk)
    except Job.DoesNotExist:
        return Response({"detail": "Job not found."}, status=status.HTTP_404_NOT_FOUND)
    
    # Check if user has permission to update this job
    if not has_job_permission(request, job):
        return Response({"detail": "You don't have permission to update this job."}, 
                       status=status.HTTP_403_FORBIDDEN)
    
    updated_job, error = helper_update_job(job, request.data)
    
    if error:
        return Response(error, status=status.HTTP_400_BAD_REQUEST)
        
    return Response(job_to_dict(updated_job))

@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated, IsCompanyMember])
def delete_job(request, pk):
    """Delete a job."""
    try:
        job = Job.objects.get(pk=pk)
    except Job.DoesNotExist:
        return Response({"detail": "Job not found."}, status=status.HTTP_404_NOT_FOUND)
    
    # Check if user has permission to delete this job
    if not has_job_permission(request, job):
        return Response({"detail": "You don't have permission to delete this job."}, 
                       status=status.HTTP_403_FORBIDDEN)
    
    job.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated, IsCompanyMember])
def dashboard_view(request):
    """Return a summary of jobs for the company dashboard."""
    company = get_user_company(request)
    
    if not company:
        return Response(
            {"detail": "You must be a member of a company."},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Get counts by status
    total_jobs = Job.objects.filter(company=company).count()
    draft_jobs = Job.objects.filter(company=company, status='DRAFT').count()
    published_jobs = Job.objects.filter(company=company, status='PUBLISHED').count()
    closed_jobs = Job.objects.filter(company=company, status='CLOSED').count()
    archived_jobs = Job.objects.filter(company=company, status='ARCHIVED').count()
    
    # Get recent jobs
    recent_jobs = Job.objects.filter(company=company).order_by('-created_at')[:5]
    recent_jobs_data = [job_to_dict(job, include_all_fields=False) for job in recent_jobs]
    
    # Get upcoming deadlines
    upcoming_deadlines = Job.objects.filter(
        company=company,
        status='PUBLISHED',
        application_deadline__gte=timezone.now().date()
    ).order_by('application_deadline')[:5]
    upcoming_deadlines_data = [job_to_dict(job, include_all_fields=False) for job in upcoming_deadlines]
    
    return Response({
        'job_counts': {
            'total': total_jobs,
            'draft': draft_jobs,
            'published': published_jobs,
            'closed': closed_jobs,
            'archived': archived_jobs
        },
        'recent_jobs': recent_jobs_data,
        'upcoming_deadlines': upcoming_deadlines_data
    })

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated, IsCompanyMember])
def publish_job(request, pk):
    """
    Publish a job by changing its status from 'DRAFT' to 'PUBLISHED'.
    Only jobs in 'DRAFT' status can be published.
    """
    try:
        job = Job.objects.get(pk=pk)
    except Job.DoesNotExist:
        return Response({"detail": "Job not found."}, status=status.HTTP_404_NOT_FOUND)
    
    # Check if user has permission to update this job
    if not has_job_permission(request, job):
        return Response(
            {"detail": "You don't have permission to publish this job."}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Check if job is in draft status
    if job.status != 'DRAFT':
        return Response(
            {"detail": f"Cannot publish job. Current status is '{job.status}', not 'DRAFT'."},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Update job status to published
    job.status = 'PUBLISHED'
    job.published_at = timezone.now()
    job.save()
    
    # Notify company members about the new job
    company_users = CompanyUser.objects.filter(
        company=job.company,
        status='active'
    ).select_related('user')
    
    # Send email notification to company members
    for company_user in company_users:
        user = company_user.user
        
        email_subject = f"New Job Published: {job.title}"
        email_body = f"""
Hello {user.first_name},

A new job has been published in your company:

Title: {job.title}
Location: {job.location}
Application Deadline: {job.application_deadline.strftime('%B %d, %Y') if job.application_deadline else 'Not specified'}

You can view the full job details on your dashboard.

Thank you,
The HirePro Team
        """
        
        # HTML version for better formatting
        html_content = email_body.replace('\n', '<br>')
        
        # Send email
        send_email(
            subject=email_subject,
            body=email_body,
            to_email=user.email,
            html_content=html_content,
            from_email=f"HirePro <no-reply@{settings.FRONTEND_BASE_URL}>",
            template_context={
                'first_name': user.first_name,
                'job_title': job.title,
                'company_name': job.company.name
            }
        )
    
    return Response({
        "message": "Job published successfully.",
        "job": job_to_dict(job)
    })

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated, IsCompanyAdmin])
def invite_interviewer_view(request, job_id):
    """
    Invite an interviewer for a job.
    """
    try:
        job = Job.objects.get(id=job_id)
    except Job.DoesNotExist:
        return Response({"detail": "Job not found."}, status=status.HTTP_404_NOT_FOUND)
    
    # Check if user has permission to invite interviewers for this job
    company_user = CompanyUser.objects.filter(
        user=request.user,
        company=job.company,
        role__in=['company_admin', 'hr_manager'],
        status='active'
    ).first()
    
    if not company_user:
        return Response({"detail": "You don't have permission to invite interviewers."}, 
                      status=status.HTTP_403_FORBIDDEN)
    
    # Validate email
    email = request.data.get('email')
    if not email:
        return Response(
            {"detail": "Email is required."},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Use the generic invite function with role='interviewer'
    from companies.helpers import invite_company_user
    
    user, auth_token, error = invite_company_user(job.company, email, 'interviewer', request.user)
    
    if error:
        return Response({"detail": error}, status=status.HTTP_400_BAD_REQUEST)
    
    # Associate the interviewer with the job
    job_interviewer, created = job.interviewers.get_or_create(
        interviewer=user,
        defaults={
            'added_by': request.user,
            'status': 'active'
        }
    )
    
    if not created and job_interviewer.status != 'active':
        job_interviewer.status = 'active'
        job_interviewer.save()
    
    # Generate frontend URL for the interviewer dashboard
    from django.conf import settings
    
    # Check if the user needs to set up their password
    has_password_set = user.has_usable_password()
    dashboard_url = f"{job.company.subdomain}.{settings.FRONTEND_BASE_URL}/interviewer-dashboard?token={auth_token.key}&job_id={job_id}"
    
    # If it's a new user, append setup parameter to indicate password setup is needed
    if not has_password_set:
        dashboard_url += "&setup=1"
    
    return Response({
        "message": "Interviewer invited successfully.",
        "user_id": str(user.id),
        "email": user.email,
        "job_id": str(job.id),
        "token": auth_token.key,
        "dashboard_url": dashboard_url,
        "requires_setup": not has_password_set
    }, status=status.HTTP_201_CREATED)

# Local helper functions - kept here as they are only used within views.py
def get_user_company_ids(request):
    """Get all company IDs where the user is an active member."""
    from companies.models import CompanyUser
    return CompanyUser.objects.filter(
        user=request.user, 
        status='active'
    ).values_list('company_id', flat=True)

def filter_jobs(queryset, request):
    """Apply filters, search, and ordering to the job queryset."""
    from django.db.models import Q
    
    # Filter by status if provided
    status_filter = request.query_params.get('status', None)
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    
    # Apply search if provided
    search_term = request.query_params.get('search', None)
    if search_term:
        queryset = queryset.filter(
            Q(title__icontains=search_term) | 
            Q(description__icontains=search_term) | 
            Q(requirements__icontains=search_term) | 
            Q(location__icontains=search_term)
        )
    
    # Apply ordering if provided
    ordering = request.query_params.get('ordering', '-created_at')
    if ordering and ordering.replace('-', '') in ['created_at', 'application_deadline', 'title']:
        queryset = queryset.order_by(ordering)
        
    return queryset