"""
Helper functions for the accounts app.
Contains validation, data transformation, and other utility functions.
"""
from .models import User
from companies.models import Company, CompanyUser
from rest_framework.authtoken.models import Token
from django.db import transaction
from django.contrib.auth import authenticate

# Data transformation functions
def user_to_dict(user):
    """
    Convert a User model instance to a dictionary.
    
    Args:
        user (User): The user instance to convert
        
    Returns:
        dict: Dictionary representation of the user
    """
    return {
        'id': str(user.id) if hasattr(user, 'id') else None,
        'username': user.username,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'user_type': user.user_type,
        'phone': user.phone,
        'profile_picture': user.profile_picture.url if user.profile_picture else None,
        'is_profile_complete': user.is_profile_complete
    }

# Validation functions
def validate_user_email(email):
    """
    Validate that email doesn't already exist.
    
    Args:
        email (str): Email to validate
        
    Returns:
        tuple: (is_valid, error_message)
    """
    if User.objects.filter(email=email).exists():
        return False, "Email already exists"
    return True, None

def validate_company_subdomain(subdomain):
    """
    Validate that company subdomain doesn't already exist.
    
    Args:
        subdomain (str): Subdomain to validate
        
    Returns:
        tuple: (is_valid, error_message)
    """
    if Company.objects.filter(subdomain=subdomain).exists():
        return False, "Subdomain already taken"
    return True, None

def validate_company_admin_signup_data(data):
    """
    Validate company admin signup data.
    
    Args:
        data (dict): The data to validate
        
    Returns:
        tuple: (errors, validated_data) where errors is a dict of validation errors
              and validated_data is the validated data
    """
    errors = {}
    validated_data = {}
    
    # Required fields
    required_fields = ['email', 'first_name', 'last_name', 'password', 'company_name', 'subdomain']
    for field in required_fields:
        if field not in data or not data[field]:
            errors[field] = "This field is required"
        else:
            validated_data[field] = data[field]
    
    # Optional fields
    if 'website' in data:
        validated_data['website'] = data['website']
    if 'contact_phone' in data:
        validated_data['contact_phone'] = data['contact_phone']
    
    # Validate email uniqueness
    if 'email' in validated_data:
        is_valid, error = validate_user_email(validated_data['email'])
        if not is_valid:
            errors['email'] = error
            
    # Validate subdomain uniqueness
    if 'subdomain' in validated_data:
        is_valid, error = validate_company_subdomain(validated_data['subdomain'])
        if not is_valid:
            errors['subdomain'] = error
            
    # Validate password length
    if 'password' in validated_data and len(validated_data['password']) < 8:
        errors['password'] = "Password must be at least 8 characters"
    
    return errors, validated_data

def validate_candidate_signup_data(data):
    """
    Validate candidate signup data.
    
    Args:
        data (dict): The data to validate
        
    Returns:
        tuple: (errors, validated_data) where errors is a dict of validation errors
              and validated_data is the validated data
    """
    errors = {}
    validated_data = {}
    
    # Required fields
    required_fields = ['email', 'first_name', 'last_name', 'password']
    for field in required_fields:
        if field not in data or not data[field]:
            errors[field] = "This field is required"
        else:
            validated_data[field] = data[field]
    
    # Optional fields
    if 'phone' in data:
        validated_data['phone'] = data['phone']
    
    # Validate email uniqueness
    if 'email' in validated_data:
        is_valid, error = validate_user_email(validated_data['email'])
        if not is_valid:
            errors['email'] = error
            
    # Validate password length
    if 'password' in validated_data and len(validated_data['password']) < 8:
        errors['password'] = "Password must be at least 8 characters"
    
    return errors, validated_data

def validate_login_data(data):
    """
    Validate login data.
    
    Args:
        data (dict): The data to validate
        
    Returns:
        tuple: (errors, validated_data) where errors is a dict of validation errors
              and validated_data is the validated data
    """
    errors = {}
    validated_data = {}
    
    # Required fields
    required_fields = ['email', 'password']
    for field in required_fields:
        if field not in data or not data[field]:
            errors[field] = "This field is required"
        else:
            validated_data[field] = data[field]
    
    return errors, validated_data

# Auth functions
def create_company_admin(data):
    """
    Create a company admin user and associated company.
    
    Args:
        data (dict): Validated data for creating company admin
        
    Returns:
        tuple: (user, company, token) or (None, None, None) if creation fails
    """
    with transaction.atomic():
        # Create the user
        user = User.objects.create_user(
            username=data['email'],
            email=data['email'],
            password=data['password'],
            first_name=data['first_name'],
            last_name=data['last_name'],
            user_type='company_admin',
            phone=data.get('contact_phone', '')
        )
        
        # Create the company
        company = Company.objects.create(
            name=data['company_name'],
            subdomain=data['subdomain'],
            website=data.get('website', ''),
            contact_email=data['email'],
            contact_phone=data.get('contact_phone', '')
        )
        
        # Link the user to the company
        CompanyUser.objects.create(
            user=user,
            company=company,
            role='company_admin',
            status='active'
        )
        
        # Generate auth token
        token, created = Token.objects.get_or_create(user=user)
        
        return user, company, token

def create_candidate(data):
    """
    Create a candidate user.
    
    Args:
        data (dict): Validated data for creating candidate
        
    Returns:
        tuple: (user, token) or (None, None) if creation fails
    """
    # Create the user
    user = User.objects.create_user(
        username=data['email'],
        email=data['email'],
        password=data['password'],
        first_name=data['first_name'],
        last_name=data['last_name'],
        user_type='candidate',
        phone=data.get('phone', '')
    )
    
    # Generate auth token
    token, created = Token.objects.get_or_create(user=user)
    
    return user, token

def login_user(data):
    """
    Authenticate a user.
    
    Args:
        data (dict): Validated login data
        
    Returns:
        tuple: (user, token, company_domain) or (None, None, None) if auth fails
              company_domain is None for candidates
    """
    user = authenticate(
        username=data['email'],
        password=data['password']
    )
    
    if not user:
        return None, None, None
    
    # Generate auth token
    token, created = Token.objects.get_or_create(user=user)
    
    # Check if the user is associated with a company
    company_domain = None
    company_user = CompanyUser.objects.filter(user=user).first()
    if company_user and user.user_type in ['company_admin', 'hr_manager', 'hr_recruiter', 'interviewer', 'csr']:
        company_domain = company_user.company.domain_url
    
    return user, token, company_domain
