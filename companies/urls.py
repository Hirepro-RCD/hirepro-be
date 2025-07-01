from django.urls import path
from . import views

app_name = 'companies'

urlpatterns = [
    # Company endpoints
    path('', views.list_companies, name='company-list'),
    path('create/', views.create_company_view, name='company-create'),
    path('<uuid:company_id>/', views.get_company, name='company-detail'),
    path('<uuid:company_id>/update/', views.update_company_view, name='company-update'),
    
    # Company User endpoints
    path('<uuid:company_id>/users/', views.list_company_users, name='company-user-list'),
    path('<uuid:company_id>/users/invite/', views.invite_company_user, name='company-user-invite'),
    path('<uuid:company_id>/users/<uuid:user_id>/', views.get_company_user, name='company-user-detail'),
    path('<uuid:company_id>/users/<uuid:user_id>/update/', views.update_company_user, name='company-user-update'),
    path('<uuid:company_id>/users/<uuid:user_id>/remove/', views.remove_company_user, name='company-user-remove'),
]