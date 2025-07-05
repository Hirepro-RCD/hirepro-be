"""
View functions for the accounts app.
All helper functions have been moved to helpers.py.
Only endpoint functions remain here for clarity.
"""
from django.shortcuts import render
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from django.contrib.auth import authenticate, login
from django.db import transaction
from django.utils import timezone
from datetime import timedelta

from .models import User
from companies.models import Company, CompanyUser, InviteToken
from rest_framework.authtoken.models import Token

from .helpers import (
    user_to_dict,
    validate_company_admin_signup_data,
    validate_candidate_signup_data,
    validate_login_data,
    create_company_admin,
    create_candidate,
    login_user
)

# Custom permission class (kept for backward compatibility)
class IsAuthenticated(permissions.BasePermission):
    """
    Custom permission to only allow authenticated users.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

# API views with decorators - only functions called directly from urls.py
@api_view(['GET', 'PUT', 'PATCH'])
@permission_classes([permissions.IsAuthenticated])
def user_detail(request, pk=None):
    """
    Get or update user details
    """
    if pk and str(request.user.id) != pk:
        return Response(
            {"detail": "You don't have permission to access this user's information."},
            status=status.HTTP_403_FORBIDDEN
        )
    
    user = request.user
        
    if request.method in ['PUT', 'PATCH']:
        # Handle update
        data = request.data
        for field in ['first_name', 'last_name', 'phone']:
            if field in data:
                setattr(user, field, data[field])
        
        # Save the user
        user.save()
    
    # Return user data
    return Response(user_to_dict(user))

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_list(request):
    """
    List all users (admin only)
    """
    if not request.user.is_staff:
        return Response(
            {"detail": "You don't have permission to access this resource."},
            status=status.HTTP_403_FORBIDDEN
        )
    
    users = User.objects.all()
    data = [user_to_dict(user) for user in users]
    return Response(data)

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def company_admin_signup(request):
    """
    Register a new company admin user
    """
    errors, validated_data = validate_company_admin_signup_data(request.data)
    
    if errors:
        return Response(errors, status=status.HTTP_400_BAD_REQUEST)
    
    # Create company admin
    try:
        user, company, token = create_company_admin(validated_data)
    except Exception as e:
        return Response(
            {"detail": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    # Return response
    return Response({
        'token': token.key,
        'user': user_to_dict(user),
        'company_domain': company.domain_url
    }, status=status.HTTP_201_CREATED)

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def candidate_signup(request):
    """
    Register a new candidate user
    """
    errors, validated_data = validate_candidate_signup_data(request.data)
    
    if errors:
        return Response(errors, status=status.HTTP_400_BAD_REQUEST)
    
    # Create candidate
    try:
        user, token = create_candidate(validated_data)
    except Exception as e:
        return Response(
            {"detail": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    # Return response
    return Response({
        'token': token.key,
        'user': user_to_dict(user)
    }, status=status.HTTP_201_CREATED)

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def login_view(request):
    """
    Login a user and return token
    """
    errors, validated_data = validate_login_data(request.data)
    
    if errors:
        return Response(errors, status=status.HTTP_400_BAD_REQUEST)
    
    # Authenticate
    user, token, company_domain = login_user(validated_data)
    
    if not user:
        return Response(
            {'error': 'Invalid credentials'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    # Return response
    response_data = {
        'token': token.key,
        'user': user_to_dict(user)
    }
    
    # Add company domain for company users
    if company_domain:
        response_data['company_domain'] = company_domain
        
    return Response(response_data)

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def validate_setup_token(request):
    """
    Validate a setup token and return information about the associated user.
    This is used by the frontend to confirm if a token is valid before showing
    the setup form, and to determine what type of account is being set up.
    """
    # Get token from request
    token_key = request.data.get('token')
    if not token_key:
        return Response({"detail": "Token is required."}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Find the auth token
        auth_token = Token.objects.get(key=token_key)
        user = auth_token.user
    except Token.DoesNotExist:
        return Response({"detail": "Invalid token."}, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if user has a usable password (i.e., if setup is needed)
    requires_setup = not user.has_usable_password()
    
    # Get user's company information
    from companies.models import CompanyUser
    company_user = CompanyUser.objects.filter(user=user, status='active').order_by('-created_at').first()
    
    company_data = None
    if company_user:
        company_data = {
            "id": str(company_user.company.id),
            "name": company_user.company.name,
            "subdomain": company_user.company.subdomain,
            "role": company_user.role
        }
    
    # Return basic user info
    return Response({
        "token_valid": True,
        "requires_setup": requires_setup,
        "user": {
            "id": str(user.id),
            "email": user.email,
            "first_name": user.first_name or "",
            "last_name": user.last_name or "",
            "user_type": user.user_type
        },
        "company": company_data
    })

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def complete_user_setup(request):
    """
    Complete user setup after receiving an invitation.
    This endpoint is used when a user receives an invite email with a token,
    and needs to set their password and complete their profile.
    """
    # Validate token
    token_key = request.data.get('token')
    if not token_key:
        return Response({"detail": "Token is required."}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Find the auth token
        auth_token = Token.objects.get(key=token_key)
        user = auth_token.user
    except Token.DoesNotExist:
        return Response({"detail": "Invalid token."}, status=status.HTTP_400_BAD_REQUEST)
    
    # Validate required fields
    required_fields = ['password', 'first_name', 'last_name']
    for field in required_fields:
        if not request.data.get(field):
            return Response(
                {"detail": f"{field.replace('_', ' ').title()} is required."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    # Update user information
    user.first_name = request.data.get('first_name')
    user.last_name = request.data.get('last_name')
    user.set_password(request.data.get('password'))
    
    # Optional fields
    if 'phone' in request.data:
        user.phone = request.data.get('phone')
    
    user.save()
    
    # Generate a new auth token (invalidate the old one for security)
    auth_token.delete()
    new_token = Token.objects.create(user=user)
    
    # Get user's company information
    from companies.models import CompanyUser
    company_user = CompanyUser.objects.filter(user=user, status='active').order_by('-created_at').first()
    
    company_data = None
    if company_user:
        company_data = {
            "id": str(company_user.company.id),
            "name": company_user.company.name,
            "subdomain": company_user.company.subdomain,
            "role": company_user.role
        }
    
    # Notify the user that their account has been set up
    from utils.email import send_email
    from django.conf import settings
    
    email_subject = "Your Account Setup is Complete"
    email_body = f"""
Hello {user.first_name},

Your account setup is now complete. You can now log in and access your dashboard.

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
            'first_name': user.first_name
        }
    )
    
    return Response({
        "message": "Account setup completed successfully.",
        "user": {
            "id": str(user.id),
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "user_type": user.user_type
        },
        "token": new_token.key,
        "company": company_data
    })
