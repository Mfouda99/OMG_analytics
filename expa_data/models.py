from django.db import models

class ExpaApplication(models.Model):
    ep_id = models.CharField(max_length=100, unique=True)  # EXPA ID
    status = models.CharField(max_length=100)
    current_status = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(null=True, blank=True)
    signuped_at = models.CharField(max_length=100, blank=True, null=True)  # Keep as string as in old_views
    experience_end_date = models.DateTimeField(null=True, blank=True)
    date_matched = models.DateTimeField(null=True, blank=True)
    date_approved = models.DateTimeField(null=True, blank=True)
    date_realized = models.DateTimeField(null=True, blank=True)
    
    # Person fields
    full_name = models.CharField(max_length=255)
    email = models.EmailField()
    profile_photo = models.URLField(blank=True, null=True)
    home_lc_name = models.CharField(max_length=255)
    home_mc_name = models.CharField(max_length=255)
    
    # Opportunity fields
    opportunity_title = models.CharField(max_length=500)
    opportunity_duration = models.CharField(max_length=100, blank=True, null=True)
    opportunity_earliest_start_date = models.CharField(max_length=100, blank=True, null=True)
    opportunity_latest_end_date = models.CharField(max_length=100, blank=True, null=True)
    programme_short_name = models.CharField(max_length=100)
    programme_id = models.IntegerField()
    home_lc_name_opportunity = models.CharField(max_length=255)
    home_mc_name_opportunity = models.CharField(max_length=255)
    host_lc_name = models.CharField(max_length=255, blank=True, null=True)
    
    def __str__(self):
        return f"{self.full_name} - {self.status}"

class SignupPerson(models.Model):
    ep_id = models.CharField(max_length=100, unique=True)  # EXPA ID
    full_name = models.CharField(max_length=255)
    email = models.EmailField()
    created_at = models.DateTimeField(null=True, blank=True)
    profile_photo = models.URLField(blank=True, null=True)
    home_lc_name = models.CharField(max_length=255, blank=True, null=True)
    home_mc_name = models.CharField(max_length=255, blank=True, null=True)
    selected_programmes = models.TextField(blank=True, null=True)  # Comma-separated string
    
    def __str__(self):
        return f"{self.full_name} - {self.email}"

class Opportunity(models.Model):
    expa_id = models.CharField(max_length=100, unique=True)  # EXPA ID
    title = models.CharField(max_length=500)
    status = models.CharField(max_length=100)
    created_at = models.DateTimeField(null=True, blank=True)
    date_opened = models.DateTimeField(null=True, blank=True)
    applicants_count = models.IntegerField(default=0)
    accepted_count = models.IntegerField(default=0)
    programme_short_name = models.CharField(max_length=100)
    sub_product_name = models.CharField(max_length=255, blank=True, null=True)
    sdg_target_id = models.CharField(max_length=100, blank=True, null=True)
    slots = models.IntegerField(default=0)
    available_slots_count = models.IntegerField(default=0)
    
    def __str__(self):
        return f"{self.title} - {self.status}"

# Podio Signup Models
class PodioSignupOGV(models.Model):
    """Podio signups for OGV programme"""
    podio_item_id = models.CharField(max_length=100, unique=True)  # Podio item ID
    first_name = models.CharField(max_length=255, blank=True, null=True)
    last_name = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(null=True, blank=True)
    home_lc = models.CharField(max_length=255, blank=True, null=True)
    ep_id = models.CharField(max_length=100, blank=True, null=True)  # EXPA EP ID
    sync_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Podio Signup OGV"
        verbose_name_plural = "Podio Signups OGV"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} - OGV"

class PodioSignupOGTa(models.Model):
    """Podio signups for OGTa programme"""
    podio_item_id = models.CharField(max_length=100, unique=True)  # Podio item ID
    first_name = models.CharField(max_length=255, blank=True, null=True)
    last_name = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(null=True, blank=True)
    home_lc = models.CharField(max_length=255, blank=True, null=True)
    ep_id = models.CharField(max_length=100, blank=True, null=True)  # EXPA EP ID
    sync_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Podio Signup OGTa"
        verbose_name_plural = "Podio Signups OGTa"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} - OGTa"

class PodioSignupOGTe(models.Model):
    """Podio signups for OGTe programme"""
    podio_item_id = models.CharField(max_length=100, unique=True)  # Podio item ID
    first_name = models.CharField(max_length=255, blank=True, null=True)
    last_name = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(null=True, blank=True)
    home_lc = models.CharField(max_length=255, blank=True, null=True)
    ep_id = models.CharField(max_length=100, blank=True, null=True)  # EXPA EP ID
    sync_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Podio Signup OGTe"
        verbose_name_plural = "Podio Signups OGTe"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} - OGTe"
