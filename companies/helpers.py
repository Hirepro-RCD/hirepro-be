"""
Helper functions for the companies app.
Contains validation, data transformation, and other utility functions.
"""
from django.utils import timezone
from django.db.models import Q
from .models import Company, CompanyUser, InviteToken
from django.contrib.auth import get_user_model

User = get_user_model()

# Permission functions
def is_company_member(request, company_id=None):
    """
    Check if a user is a member of any company or a specific company.
    
    Args:
        request: The request object containing the user
        company_id (str, optional): The ID of a specific company to check
        
    Returns:
        bool: True if the user is a member of the company
    """
    if not request.user or not request.user.is_authenticated:
        return False
        
    if company_id:
        return CompanyUser.objects.filter(
            user=request.user,
            company_id=company_id,
            status='active'
        ).exists()
    else:
        return CompanyUser.objects.filter(
            user=request.user,
            status='active'
        ).exists()

def is_company_admin(request, company_id=None):
    """
    Check if a user is an admin of any company or a specific company.
    
    Args:
        request: The request object containing the user
        company_id (str, optional): The ID of a specific company to check
        
    Returns:
        bool: True if the user is an admin of the company
    """
    if not request.user or not request.user.is_authenticated:
        return False
        
    if company_id:
        return CompanyUser.objects.filter(
            user=request.user,
            company_id=company_id,
            role='company_admin',
            status='active'
        ).exists()
    else:
        return CompanyUser.objects.filter(
            user=request.user,
            role='company_admin',
            status='active'
        ).exists()

def get_user_companies(request):
    """
    Get all companies where the user is an active member.
    
    Args:
        request: The request object containing the user
        
    Returns:
        QuerySet: Companies where the user is an active member
    """
    if not request.user or not request.user.is_authenticated:
        return Company.objects.none()
        
    company_ids = CompanyUser.objects.filter(
        user=request.user,
        status='active'
    ).values_list('company_id', flat=True)
    
    return Company.objects.filter(id__in=company_ids)

# Data transformation functions
def company_to_dict(company, include_members=False):
    """
    Convert a Company model instance to a dictionary.
    
    Args:
        company (Company): The company to convert
        include_members (bool): Whether to include company members
        
    Returns:
        dict: Dictionary representation of the company
    """
    result = {
        'id': str(company.id),
        'name': company.name,
        'subdomain': company.subdomain,
        'description': company.description,
        'website': company.website,
        'logo': company.logo.url if company.logo else None,
        'status': company.status,
        'contact_email': company.contact_email,
        'contact_phone': company.contact_phone,
        'address': company.address,
        'created_at': company.created_at,
        'updated_at': company.updated_at,
        'domain_url': company.domain_url
    }
    
    if include_members:
        members = CompanyUser.objects.filter(company=company)
        result['members'] = [company_user_to_dict(member) for member in members]
        
    return result

def company_user_to_dict(company_user):
    """
    Convert a CompanyUser model instance to a dictionary.
    
    Args:
        company_user (CompanyUser): The company user to convert
        
    Returns:
        dict: Dictionary representation of the company user
    """
    return {
        'id': str(company_user.id),
        'user_id': str(company_user.user.id) if company_user.user else None,
        'company_id': str(company_user.company.id) if company_user.company else None,
        'role': company_user.role,
        'permissions': company_user.permissions,
        'status': company_user.status,
        'user_email': company_user.user.email if company_user.user else None,
        'user_name': f"{company_user.user.first_name} {company_user.user.last_name}" if company_user.user else None,
        'invited_by': str(company_user.invited_by.id) if company_user.invited_by else None,
        'invited_at': company_user.invited_at,
        'activated_at': company_user.activated_at
    }

def invite_token_to_dict(invite_token):
    """
    Convert an InviteToken model instance to a dictionary.
    
    Args:
        invite_token (InviteToken): The invite token to convert
        
    Returns:
        dict: Dictionary representation of the invite token
    """
    return {
        'token': str(invite_token.token),
        'token_type': invite_token.token_type,
        'user_id': str(invite_token.user.id) if invite_token.user else None,
        'company_id': str(invite_token.company.id) if invite_token.company else None,
        'email': invite_token.email,
        'data': invite_token.data,
        'expires_at': invite_token.expires_at,
        'used_at': invite_token.used_at,
        'created_at': invite_token.created_at,
        'is_expired': invite_token.is_expired,
        'is_used': invite_token.is_used
    }

# Validation functions
def validate_company_data(data):
    """
    Validate company data.
    
    Args:
        data (dict): The company data to validate
        
    Returns:
        tuple: (errors, validated_data) where errors is a dict of validation errors
    """
    errors = {}
    validated_data = {}
    
    # Required fields
    required_fields = ['name', 'subdomain', 'contact_email']
    for field in required_fields:
        if field not in data or not data[field]:
            errors[field] = "This field is required"
        else:
            validated_data[field] = data[field]
            
    # Validate subdomain uniqueness
    if 'subdomain' in validated_data:
        if Company.objects.filter(subdomain=validated_data['subdomain']).exists():
            errors['subdomain'] = "This subdomain is already in use"
            
    # Optional fields
    optional_fields = ['description', 'website', 'contact_phone', 'address', 'status']
    for field in optional_fields:
        if field in data:
            validated_data[field] = data[field]
    
    # Validate status choices
    if 'status' in validated_data:
        valid_statuses = [choice[0] for choice in Company.STATUS_CHOICES]
        if validated_data['status'] not in valid_statuses:
            errors['status'] = f"Status must be one of: {', '.join(valid_statuses)}"
            
    return errors, validated_data

def validate_company_user_data(data, update=False):
    """
    Validate company user data.
    
    Args:
        data (dict): The company user data to validate
        update (bool): Whether this is an update operation
        
    Returns:
        tuple: (errors, validated_data) where errors is a dict of validation errors
    """
    errors = {}
    validated_data = {}
    
    # Required fields for creation
    if not update:
        required_fields = ['email', 'role']
        for field in required_fields:
            if field not in data or not data[field]:
                errors[field] = "This field is required"
            else:
                validated_data[field] = data[field]
    else:
        # For update, copy provided fields
        for field in ['role', 'status', 'permissions']:
            if field in data:
                validated_data[field] = data[field]
    
    # Validate role choices
    if 'role' in validated_data:
        valid_roles = [choice[0] for choice in CompanyUser.ROLE_CHOICES]
        if validated_data['role'] not in valid_roles:
            errors['role'] = f"Role must be one of: {', '.join(valid_roles)}"
    
    # Validate status choices
    if 'status' in validated_data:
        valid_statuses = [choice[0] for choice in CompanyUser.STATUS_CHOICES]
        if validated_data['status'] not in valid_statuses:
            errors['status'] = f"Status must be one of: {', '.join(valid_statuses)}"
            
    return errors, validated_data

# Company operations
def create_company(data, user):
    """
    Create a new company and make the user an admin.
    
    Args:
        data (dict): Validated company data
        user (User): The user creating the company
        
    Returns:
        tuple: (company, error) where error is None if creation successful
    """
    try:
        company = Company.objects.create(**data)
        
        # Make the user an admin of the company
        CompanyUser.objects.create(
            user=user,
            company=company,
            role='company_admin',
            status='active',
            activated_at=timezone.now()
        )
        
        return company, None
    except Exception as e:
        return None, str(e)

def update_company(company, data):
    """
    Update an existing company.
    
    Args:
        company (Company): The company to update
        data (dict): Validated company data
        
    Returns:
        tuple: (company, error) where error is None if update successful
    """
    try:
        for key, value in data.items():
            setattr(company, key, value)
        company.save()
        return company, None
    except Exception as e:
        return None, str(e)

def invite_user_to_company(company, data, invited_by):
    """
    Create an invite for a user to join a company.
    
    Args:
        company (Company): The company to invite to
        data (dict): Validated invitation data
        invited_by (User): The user creating the invitation
        
    Returns:
        tuple: (invite_token, error) where error is None if creation successful
    """
    from datetime import timedelta
    
    try:
        # Create an invite token
        token = InviteToken.objects.create(
            token_type='user_invite',
            company=company,
            email=data['email'],
            data={
                'role': data['role'],
                'permissions': data.get('permissions', {})
            },
            expires_at=timezone.now() + timedelta(days=7)
        )
        
        # Check if user already exists
        user = None
        try:
            user = User.objects.get(email=data['email'])
        except User.DoesNotExist:
            pass
            
        # Create pending company user association
        company_user = CompanyUser.objects.create(
            user=user,  # May be None
            company=company,
            role=data['role'],
            permissions=data.get('permissions', {}),
            status='pending_setup',
            invited_by=invited_by,
            invited_at=timezone.now()
        )
        
        if user:
            token.user = user
            token.save()
            
        return token, None
    except Exception as e:
        return None, str(e)
