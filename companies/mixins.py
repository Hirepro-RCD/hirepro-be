from django.db import models

class TenantModelMixin(models.Model):
    """
    Abstract base model that includes company relationship
    for multi-tenant data isolation
    """
    company = models.ForeignKey(
        'companies.Company',
        on_delete=models.CASCADE,
        related_name='%(class)s_set'
    )
    
    class Meta:
        abstract = True

class TenantManager(models.Manager):
    """
    Manager that automatically filters by tenant company
    when company context is available
    """
    def get_queryset(self):
        # This will be enhanced later to use request context
        return super().get_queryset()
    
    def for_company(self, company):
        """Explicitly filter by company"""
        return self.get_queryset().filter(company=company)