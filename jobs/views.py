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
