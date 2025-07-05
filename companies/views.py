"""
View functions for the companies app.
All helper functions have been moved to helpers.py.
Only endpoint functions remain here for clarity.
"""
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes

from .models import Company, CompanyUser, InviteToken
from .helpers import (
    is_company_member, is_company_admin, get_user_companies,
    company_to_dict, company_user_to_dict, invite_token_to_dict,
    validate_company_data, validate_company_user_data,
    create_company, update_company, invite_company_user
)

# Custom permission classes
class IsCompanyMember(permissions.BasePermission):
    """
    Custom permission to only allow members of a company to access its data.
    """
    def has_permission(self, request, view):
        # Checking if user is authenticated and member of any company
        return is_company_member(request)

    def has_object_permission(self, request, view, obj):
        # For company objects
        if isinstance(obj, Company):
            return is_company_member(request, str(obj.id))
        # For company user objects
        if isinstance(obj, CompanyUser):
            return is_company_member(request, str(obj.company.id))
        return False

class IsCompanyAdmin(permissions.BasePermission):
    """
    Custom permission to only allow company admins to perform certain actions.
    """
    def has_permission(self, request, view):
        # Checking if user is authenticated and admin of any company
        return is_company_admin(request)

    def has_object_permission(self, request, view, obj):
        # For company objects
        if isinstance(obj, Company):
            return is_company_admin(request, str(obj.id))
        # For company user objects
        if isinstance(obj, CompanyUser):
            return is_company_admin(request, str(obj.company.id))
        return False

# Company endpoints
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated, IsCompanyMember])
def list_companies(request):
    """
    Get a list of companies where the user is a member.
    """
    companies = get_user_companies(request)
    companies_data = [company_to_dict(company) for company in companies]
    return Response(companies_data)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_company_view(request):
    """
    Create a new company and make the current user an admin.
    """
    errors, validated_data = validate_company_data(request.data)
    
    if errors:
        return Response(errors, status=status.HTTP_400_BAD_REQUEST)
    
    company, error = create_company(validated_data, request.user)
    
    if error:
        return Response({"detail": error}, status=status.HTTP_400_BAD_REQUEST)
    
    return Response(company_to_dict(company), status=status.HTTP_201_CREATED)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated, IsCompanyMember])
def get_company(request, company_id):
    """
    Get details of a specific company.
    """
    if not is_company_member(request, company_id):
        return Response(
            {"detail": "You do not have access to this company."},
            status=status.HTTP_403_FORBIDDEN
        )
    
    company = get_object_or_404(Company, id=company_id)
    include_members = is_company_admin(request, company_id)
    
    return Response(company_to_dict(company, include_members=include_members))

@api_view(['PUT', 'PATCH'])
@permission_classes([permissions.IsAuthenticated, IsCompanyAdmin])
def update_company_view(request, company_id):
    """
    Update a company's details.
    """
    if not is_company_admin(request, company_id):
        return Response(
            {"detail": "You do not have permission to update this company."},
            status=status.HTTP_403_FORBIDDEN
        )
    
    company = get_object_or_404(Company, id=company_id)
    errors, validated_data = validate_company_data(request.data)
    
    if errors:
        return Response(errors, status=status.HTTP_400_BAD_REQUEST)
    
    updated_company, error = update_company(company, validated_data)
    
    if error:
        return Response({"detail": error}, status=status.HTTP_400_BAD_REQUEST)
    
    return Response(company_to_dict(updated_company))

# Company User endpoints
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated, IsCompanyMember])
def list_company_users(request, company_id):
    """
    Get a list of all users in a company.
    """
    if not is_company_member(request, company_id):
        return Response(
            {"detail": "You do not have access to this company."},
            status=status.HTTP_403_FORBIDDEN
        )
    
    company = get_object_or_404(Company, id=company_id)
    company_users = CompanyUser.objects.filter(company=company)
    users_data = [company_user_to_dict(user) for user in company_users]
    
    return Response(users_data)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated, IsCompanyAdmin])
def invite_company_user_view(request, company_id):
    """
    Invite a user to a company with a specific role.
    Generic endpoint for inviting users with any valid role (interviewer, HR manager, etc.)
    """
    # Get company by primary key
    try:
        company = Company.objects.get(id=company_id)
    except Company.DoesNotExist:
        return Response({"detail": "Company not found."}, status=status.HTTP_404_NOT_FOUND)
    
    # Check if user has admin permissions for this company
    company_user = CompanyUser.objects.filter(
        user=request.user,
        company=company,
        role='company_admin',
        status='active'
    ).first()
    
    if not company_user:
        return Response({"detail": "You don't have admin permissions for this company."}, 
                      status=status.HTTP_403_FORBIDDEN)
    
    # Validate required fields
    email = request.data.get('email')
    role = request.data.get('role')
    
    if not email:
        return Response(
            {"detail": "Email is required."},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if not role:
        return Response(
            {"detail": "Role is required."},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Invite the company user with the specified role
    user, auth_token, error = invite_company_user(company, email, role, request.user)
    
    if error:
        return Response({"detail": error}, status=status.HTTP_400_BAD_REQUEST)
    
    # Generate frontend URL for the dashboard
    from django.conf import settings
    
    # Check if the user needs to set up their password
    has_password_set = user.has_usable_password()
    
    # Determine the dashboard URL based on role
    if role == 'interviewer':
        dashboard_path = 'interviewer-dashboard'
    else:
        dashboard_path = 'dashboard'
        
    dashboard_url = f"{company.subdomain}.{settings.FRONTEND_BASE_URL}/{dashboard_path}?token={auth_token.key}"
    
    # If it's a new user, append setup parameter to indicate password setup is needed
    if not has_password_set:
        dashboard_url += "&setup=1"
    
    # Get role display name
    role_display = {
        'company_admin': 'Company Administrator',
        'hr_manager': 'HR Manager',
        'interviewer': 'Interviewer',
        'recruiter': 'Recruiter'
    }.get(role, role.replace('_', ' ').title())
    
    return Response({
        "message": f"{role_display} added successfully.",
        "user_id": str(user.id),
        "email": user.email,
        "role": role,
        "token": auth_token.key,
        "dashboard_url": dashboard_url,
        "requires_setup": not has_password_set
    }, status=status.HTTP_201_CREATED)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated, IsCompanyMember])
def get_company_user(request, company_id, user_id):
    """
    Get details of a specific user in a company.
    """
    if not is_company_member(request, company_id):
        return Response(
            {"detail": "You do not have access to this company."},
            status=status.HTTP_403_FORBIDDEN
        )
    
    company_user = get_object_or_404(CompanyUser, company_id=company_id, user_id=user_id)
    return Response(company_user_to_dict(company_user))

@api_view(['PUT', 'PATCH'])
@permission_classes([permissions.IsAuthenticated, IsCompanyAdmin])
def update_company_user(request, company_id, user_id):
    """
    Update a user's role or status in a company.
    """
    if not is_company_admin(request, company_id):
        return Response(
            {"detail": "You do not have permission to update users in this company."},
            status=status.HTTP_403_FORBIDDEN
        )
    
    company_user = get_object_or_404(CompanyUser, company_id=company_id, user_id=user_id)
    errors, validated_data = validate_company_user_data(request.data, update=True)
    
    if errors:
        return Response(errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        for key, value in validated_data.items():
            setattr(company_user, key, value)
        company_user.save()
        return Response(company_user_to_dict(company_user))
    except Exception as e:
        return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated, IsCompanyAdmin])
def remove_company_user(request, company_id, user_id):
    """
    Remove a user from a company.
    """
    if not is_company_admin(request, company_id):
        return Response(
            {"detail": "You do not have permission to remove users from this company."},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Can't remove yourself if you're the only admin
    if str(request.user.id) == user_id:
        admin_count = CompanyUser.objects.filter(
            company_id=company_id,
            role='company_admin',
            status='active'
        ).exclude(user_id=user_id).count()
        
        if admin_count == 0:
            return Response(
                {"detail": "You cannot remove yourself as you are the only admin."},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    company_user = get_object_or_404(CompanyUser, company_id=company_id, user_id=user_id)
    company_user.delete()
    
    return Response(status=status.HTTP_204_NO_CONTENT)
