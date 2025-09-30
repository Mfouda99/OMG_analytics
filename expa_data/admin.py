from django.contrib import admin
from .models import ExpaApplication, SignupPerson, Opportunity

@admin.register(ExpaApplication)
class ExpaApplicationAdmin(admin.ModelAdmin):
    list_display = ('ep_id', 'full_name', 'status', 'programme_short_name', 'created_at', 'home_lc_name', 'home_mc_name', 'home_mc_name_opportunity')
    list_filter = ('status', 'programme_short_name', 'home_lc_name', 'home_mc_name', 'home_mc_name_opportunity', 'created_at')
    search_fields = ('full_name', 'email', 'ep_id', 'opportunity_title')
    readonly_fields = ('ep_id', 'created_at', 'signuped_at')
    list_per_page = 50
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('ep_id', 'status', 'current_status', 'created_at')
        }),
        ('Person Details', {
            'fields': ('full_name', 'email', 'profile_photo', 'signuped_at')
        }),
        ('Location Info', {
            'fields': ('home_lc_name', 'home_mc_name')
        }),
        ('Opportunity Details', {
            'fields': ('opportunity_title', 'programme_short_name', 'programme_id', 'opportunity_duration')
        }),
        ('Dates', {
            'fields': ('date_matched', 'date_approved', 'date_realized', 'experience_end_date')
        }),
        ('Opportunity Location', {
            'fields': ('home_lc_name_opportunity', 'home_mc_name_opportunity', 'host_lc_name'),
            'classes': ('collapse',)
        }),
        ('Opportunity Details Extended', {
            'fields': ('opportunity_earliest_start_date', 'opportunity_latest_end_date'),
            'classes': ('collapse',)
        })
    )

@admin.register(SignupPerson)
class SignupPersonAdmin(admin.ModelAdmin):
    list_display = ('ep_id', 'full_name', 'email', 'home_lc_name', 'created_at', 'selected_programmes')
    list_filter = ('home_lc_name', 'home_mc_name', 'created_at')
    search_fields = ('full_name', 'email', 'ep_id')
    readonly_fields = ('ep_id', 'created_at')
    list_per_page = 50
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('ep_id', 'full_name', 'email', 'created_at')
        }),
        ('Profile', {
            'fields': ('profile_photo', 'selected_programmes')
        }),
        ('Location', {
            'fields': ('home_lc_name', 'home_mc_name')
        })
    )

@admin.register(Opportunity)
class OpportunityAdmin(admin.ModelAdmin):
    list_display = ('expa_id', 'title', 'status', 'programme_short_name', 'applicants_count', 'accepted_count', 'created_at')
    list_filter = ('status', 'programme_short_name', 'sub_product_name', 'created_at')
    search_fields = ('title', 'expa_id', 'programme_short_name')
    readonly_fields = ('expa_id', 'created_at')
    list_per_page = 50
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('expa_id', 'title', 'status', 'created_at', 'date_opened')
        }),
        ('Programme Details', {
            'fields': ('programme_short_name', 'sub_product_name', 'sdg_target_id')
        }),
        ('Statistics', {
            'fields': ('applicants_count', 'accepted_count', 'slots', 'available_slots_count')
        })
    )
