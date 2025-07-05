"""
Helper functions for the jobs app.
Contains validation, data transformation, and other utility functions.
"""
from companies.models import CompanyUser
from .models import Job

# Permission helper functions
def is_company_member(request):
    """Check if user is authenticated and is a member of any company."""
    return bool(
        request.user and 
        request.user.is_authenticated and
        CompanyUser.objects.filter(user=request.user, status='active').exists()
    )

def has_job_permission(request, job):
    """Check if user is a member of the company that owns the job."""
    return CompanyUser.objects.filter(
        user=request.user, 
        company=job.company,
        status='active'
    ).exists()

def get_user_company(request):
    """Get the user's active company or None if not found."""
    company_user = CompanyUser.objects.filter(
        user=request.user, 
        status='active'
    ).first()
    return company_user.company if company_user else None

# Validation functions
def validate_ai_interview_config(config):
    """
    Validate AI interview configuration data.
    
    Args:
        config (dict): The AI interview config to validate
        
    Returns:
        tuple: (errors, validated_config) where errors is a dict of validation errors
              and validated_config is the validated config with defaults applied
    """
    errors = {}
    
    # Check required fields
    if not config.get('question_source'):
        errors['question_source'] = "This field is required"
    
    if 'time_limit_per_question' not in config:
        errors['time_limit_per_question'] = "This field is required"
    else:
        # Validate time limit
        time_limit = config.get('time_limit_per_question')
        if time_limit < 30 or time_limit > 300:  # Between 30 seconds and 5 minutes
            errors['time_limit_per_question'] = "Time limit must be between 30 and 300 seconds"
            
    if 'max_retries' not in config:
        errors['max_retries'] = "This field is required"
    else:
        # Validate max retries
        max_retries = config.get('max_retries')
        if max_retries < 0 or max_retries > 3:  # Max 3 retries allowed
            errors['max_retries'] = "Max retries must be between 0 and 3"
            
    # Video required defaults to True if not provided
    if 'video_required' not in config:
        config['video_required'] = True
        
    return errors, config

def validate_job_data(data):
    """
    Validate job data and return errors if any.
    
    Args:
        data (dict): The job data to validate
        
    Returns:
        tuple: (errors, validated_data) where errors is a dict of validation errors
              and validated_data is the validated data
    """
    errors = {}
    
    # Validate that AI interview config is present when interview_type is AI_INTERVIEW
    if data.get('interview_type') == 'AI_INTERVIEW' and not data.get('ai_interview_config'):
        errors['ai_interview_config'] = "AI interview configuration is required when interview type is AI_INTERVIEW"
    
    # Remove AI interview config if interview type is not AI_INTERVIEW
    if data.get('interview_type') != 'AI_INTERVIEW':
        data['ai_interview_config'] = None
    
    # Validate salary range if provided
    salary_min = data.get('salary_min')
    salary_max = data.get('salary_max')
    if salary_min is not None and salary_max is not None and salary_min > salary_max:
        errors['salary_min'] = "Minimum salary cannot be greater than maximum salary"
        
    # If AI interview config is provided, validate it
    ai_interview_config = data.get('ai_interview_config')
    if ai_interview_config:
        config_errors, validated_config = validate_ai_interview_config(ai_interview_config)
        if config_errors:
            errors['ai_interview_config'] = config_errors
        else:
            data['ai_interview_config'] = validated_config
            
    return errors, data

# Data transformation functions
def job_to_dict(job, include_all_fields=True):
    """
    Convert a Job model instance to a dictionary.
    
    Args:
        job (Job): The job instance to convert
        include_all_fields (bool): Whether to include all fields (True) or just list fields (False)
        
    Returns:
        dict: Dictionary representation of the job
    """
    company_name = job.company.name
    
    if include_all_fields:
        # Full representation
        return {
            'id': str(job.id),
            'title': job.title,
            'description': job.description,
            'requirements': job.requirements,
            'location': job.location,
            'employment_type': job.employment_type,
            'experience_level': job.experience_level,
            'salary_min': job.salary_min,
            'salary_max': job.salary_max,
            'salary_currency': job.salary_currency,
            'application_deadline': job.application_deadline,
            'interview_type': job.interview_type,
            'ai_interview_config': job.ai_interview_config,
            'status': job.status,
            'visibility': job.visibility,
            'created_at': job.created_at,
            'updated_at': job.updated_at,
            'company_name': company_name,
            # Read-only fields
            'company': str(job.company.id) if job.company else None,
            'created_by': str(job.created_by.id) if job.created_by else None,
        }
    else:
        # List representation
        return {
            'id': str(job.id),
            'title': job.title,
            'location': job.location,
            'employment_type': job.employment_type, 
            'experience_level': job.experience_level,
            'status': job.status,
            'visibility': job.visibility,
            'application_deadline': job.application_deadline,
            'created_at': job.created_at,
            'company_name': company_name,
            'salary_min': job.salary_min,
            'salary_max': job.salary_max,
            'salary_currency': job.salary_currency,
            'interview_type': job.interview_type
        }

# Job CRUD operations
def create_job(request):
    """
    Create a new job.
    
    Args:
        request: The HTTP request
        
    Returns:
        tuple: (job, errors) where job is the created Job instance or None if errors,
              and errors is a dict of validation errors or None if successful
    """
    # Get the user's active company
    company_user = CompanyUser.objects.filter(
        user=request.user, 
        status='active'
    ).first()
    
    if not company_user:
        return None, {"detail": "You must be a member of a company to create jobs."}
    
    data = request.data
    errors, validated_data = validate_job_data(data)
    
    if errors:
        return None, errors
        
    # Extract AI interview config data
    ai_interview_config = validated_data.pop('ai_interview_config', None)
    
    # Create job with all required fields
    job = Job.objects.create(
        company=company_user.company,
        created_by=request.user,
        **validated_data
    )
    
    # Set AI interview config if provided
    if ai_interview_config:
        job.ai_interview_config = ai_interview_config
        job.save()
        
    return job, None

def update_job(job, data):
    """
    Update an existing job.
    
    Args:
        job (Job): The job instance to update
        data (dict): The data to update the job with
        
    Returns:
        tuple: (job, errors) where job is the updated Job instance or None if errors,
              and errors is a dict of validation errors or None if successful
    """
    errors, validated_data = validate_job_data(data)
    
    if errors:
        return None, errors
        
    # Handle AI interview config separately
    ai_interview_config = validated_data.pop('ai_interview_config', None)
    
    # Update all other fields
    for attr, value in validated_data.items():
        setattr(job, attr, value)
    
    # Update AI interview config if provided
    if ai_interview_config is not None:
        job.ai_interview_config = ai_interview_config
        
    job.save()
    return job, None