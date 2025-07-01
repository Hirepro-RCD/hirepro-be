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
