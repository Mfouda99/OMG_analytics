from django.urls import path
from . import views

urlpatterns = [
    path('api/sync-expa-data/', views.sync_expa_data, name='sync_expa_data'),
    path('api/sync_signup_people/', views.sync_signup_people, name='sync_signup_people'),
    
    # Auto Sync Scheduler Control Endpoints
    path('api/start-scheduler/', views.start_scheduler_view, name='start_scheduler'),
    path('api/stop-scheduler/', views.stop_scheduler_view, name='stop_scheduler'),
    path('api/scheduler-status/', views.scheduler_status_view, name='scheduler_status'),
    path('api/manual-sync/', views.manual_sync_view, name='manual_sync'),
    
    # Podio API Endpoints
    path('api/sync-podio-ogv/', views.sync_podio_ogv, name='sync_podio_ogv'),
    path('api/sync-podio-ogta/', views.sync_podio_ogta, name='sync_podio_ogta'),
    path('api/sync-podio-ogte/', views.sync_podio_ogte, name='sync_podio_ogte'),
    path('api/sync-all-podio/', views.sync_all_podio_data, name='sync_all_podio'),
    path('api/podio-signup-counts/', views.get_podio_signup_counts, name='podio_signup_counts'),
    
    
    
    # MC Timeline Endpoints
    path('api/ogv-timeline/', views.get_ogv_timeline, name='ogv_timeline'),
    path('api/ogta-timeline/', views.get_ogta_timeline, name='ogta_timeline'),
    path('api/ogte-timeline/', views.get_ogte_timeline, name='ogte_timeline'),
    path('api/igv-timeline/', views.get_igv_timeline, name='igv_timeline'),
    path('api/igta-timeline/', views.get_igta_timeline, name='igta_timeline'),
    
    # LC Athens Timeline Endpoints
    path('api/lc-athens-ogv-timeline/', views.get_lc_athens_ogv_timeline, name='lc_athens_ogv_timeline'),
    path('api/lc-athens-ogta-timeline/', views.get_lc_athens_ogta_timeline, name='lc_athens_ogta_timeline'),
    path('api/lc-athens-ogte-timeline/', views.get_lc_athens_ogte_timeline, name='lc_athens_ogte_timeline'),
    path('api/lc-athens-igv-timeline/', views.get_lc_athens_igv_timeline, name='lc_athens_igv_timeline'),
    path('api/lc-athens-igta-timeline/', views.get_lc_athens_igta_timeline, name='lc_athens_igta_timeline'),
    
    #LC AUTH Timeline Endpoints
    path('api/lc-auth-ogv-timeline/', views.get_lc_auth_ogv_timeline, name='lc_auth_ogv_timeline'),
    path('api/lc-auth-ogta-timeline/', views.get_lc_auth_ogta_timeline, name='lc_auth_ogta_timeline'),
    path('api/lc-auth-ogte-timeline/', views.get_lc_auth_ogte_timeline, name='lc_auth_ogte_timeline'),    
    path('api/lc-auth-igv-timeline/', views.get_lc_auth_igv_timeline, name='lc_auth_igv_timeline'),
    path('api/lc-auth-igta-timeline/', views.get_lc_auth_igta_timeline, name='lc_auth_igta_timeline'),  
    # LC UniPi Timeline Endpoints
    path('api/lc-unipi-ogv-timeline/', views.get_lc_unipi_ogv_timeline, name='lc_unipi_ogv_timeline'),
    path('api/lc-unipi-ogta-timeline/', views.get_lc_unipi_ogta_timeline, name='lc_unipi_ogta_timeline'),
    path('api/lc-unipi-ogte-timeline/', views.get_lc_unipi_ogte_timeline, name='lc_unipi_ogte_timeline'),
    path('api/lc-unipi-igv-timeline/', views.get_lc_unipi_igv_timeline, name='lc_unipi_igv_timeline'),
    path('api/lc-unipi-igta-timeline/', views.get_lc_unipi_igta_timeline, name='lc_unipi_igta_timeline'),

    # LC UoM Thessaloniki Timeline Endpoints
    path('api/lc-uom-thessaloniki-ogv-timeline/', views.get_LC_UoM_Thessaloniki_ogv_timeline, name='lc_uom_thessaloniki_ogv_timeline'),
    path('api/lc-uom-thessaloniki-ogta-timeline/', views.get_LC_UoM_Thessaloniki_ogta_timeline, name='lc_uom_thessaloniki_ogta_timeline'),
    path('api/lc-uom-thessaloniki-ogte-timeline/', views.get_LC_UoM_Thessaloniki_ogte_timeline, name='lc_uom_thessaloniki_ogte_timeline'),
    path('api/lc-uom-thessaloniki-igv-timeline/', views.get_lc_UoM_Thessaloniki_igv_timeline, name='lc_uom_thessaloniki_igv_timeline'),
    path('api/lc-uom-thessaloniki-igta-timeline/', views.get_lc_UoM_Thessaloniki_igta_timeline, name='lc_uom_thessaloniki_igta_timeline'),

    # IE UoI Timeline Endpoints 
    path('api/ie-uoi-ogv-timeline/', views.get_IE_UOI_ogv_timeline, name='ie_uoi_ogv_timeline'),
    path('api/ie-uoi-ogta-timeline/', views.get_IE_UOI_ogta_timeline, name='ie_uoi_ogta_timeline'),
    path('api/ie-uoi-ogte-timeline/', views.get_IE_UOI_ogte_timeline, name='ie_uoi_ogte_timeline'),
    path('api/ie-uoi-igv-timeline/', views.get_IE_UOI_igv_timeline, name='ie_uoi_igv_timeline'),
    path('api/ie-uoi-igta-timeline/', views.get_IE_UOI_igta_timeline, name='ie_uoi_igta_timeline'),

    # IE Volos Timeline Endpoints
    path('api/ie-volos-ogv-timeline/', views.get_IE_Volos_ogv_timeline, name='ie_volos_ogv_timeline'),
    path('api/ie-volos-ogta-timeline/', views.get_IE_Volos_ogta_timeline, name='ie_volos_ogta_timeline'),
    path('api/ie-volos-ogte-timeline/', views.get_IE_Volos_ogte_timeline, name='ie_volos_ogte_timeline'),
    path('api/ie-volos-igv-timeline/', views.get_IE_Volos_igv_timeline, name='ie_volos_igv_timeline'),
    path('api/ie-volos-igta-timeline/', views.get_IE_Volos_igta_timeline, name='ie_volos_igta_timeline'),
]