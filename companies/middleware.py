from django.shortcuts import redirect
from django.urls import reverse
from .models import Company

class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Extract subdomain from host
        host = request.get_host()
        host_parts = host.split('.')
        
        # Check if it's a company subdomain
        if len(host_parts) >= 3 and host_parts[-2:] == ['hirepro', 'com']:
            subdomain = host_parts[0]
            
            # Skip for main domain and common subdomains
            if subdomain not in ['www', 'api', 'admin', 'mail']:
                try:
                    company = Company.objects.get(
                        subdomain=subdomain, 
                        status='active'
                    )
                    request.tenant_company = company
                    request.is_company_domain = True
                except Company.DoesNotExist:
                    # Invalid subdomain - redirect to main site
                    return redirect('https://hirepro.com')
            else:
                request.tenant_company = None
                request.is_company_domain = False
        else:
            # Main domain or development
            request.tenant_company = None
            request.is_company_domain = False
        
        response = self.get_response(request)
        return response