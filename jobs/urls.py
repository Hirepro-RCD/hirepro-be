from django.urls import path
from . import views

app_name = 'jobs'

# Simple, explicit URL patterns using function-based views
urlpatterns = [
    # List and create
    path('', views.list_jobs, name='job-list'),
    path('create/', views.create_job_view, name='job-create'),
    
    # Detail views (retrieve, update, delete)
    path('<uuid:pk>/', views.get_job, name='job-detail'),
    path('<uuid:pk>/update/', views.update_job_view, name='job-update'),
    path('<uuid:pk>/delete/', views.delete_job, name='job-delete'),
    
    # Dashboard view
    path('dashboard/', views.dashboard_view, name='job-dashboard'),
]
