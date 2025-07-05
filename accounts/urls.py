from django.urls import path, include
from . import views

app_name = 'accounts'

urlpatterns = [
    # User endpoints
    path('api/users/', views.user_list, name='user_list'),
    path('api/users/<str:pk>/', views.user_detail, name='user_detail'),
    path('api/users/me/', views.user_detail, name='current_user_detail'),
    
    # Authentication endpoints
    path('login/', views.login_view, name='login'),
    path('signup/company/', views.company_admin_signup, name='company_signup'),
    path('signup/candidate/', views.candidate_signup, name='candidate_signup'),
    path('setup/complete/', views.complete_user_setup, name='complete-user-setup'),
    path('setup/validate-token/', views.validate_setup_token, name='validate-setup-token'),
    
    # # Authentication endpoints - commented out as they're not implemented yet
    # path('logout/', views.logout_view, name='logout'),
    # path('set-password/<uuid:token>/', views.set_password, name='set_password'),
    # path('profile/setup/', views.profile_setup, name='profile_setup'),
    
    # # Main site pages - commented out as they're not implemented yet
    # path('', views.home_view, name='home'),
    # path('candidate/<uuid:user_id>/', views.candidate_profile, name='candidate_profile'),
]