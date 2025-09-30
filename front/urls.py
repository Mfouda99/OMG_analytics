from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing, name='home'),
    path('test/', views.test_landing, name='test_landing'),
    path('mc/', views.mc, name='mc'),
    path('lc_athens/', views.lc_athens, name='lc_athens'),
    path('lc_unipi/', views.lc_unipi, name='lc_unipi'),
    path('lc_uom_thessaloniki/', views.lc_uom_thessaloniki, name='lc_uom_thessaloniki'),
    path('lc_auth/', views.lc_auth, name='lc_auth'),
    path('ie_uoi/', views.ie_uoi, name='ie_uoi'),
    path('ie_volos/', views.ie_volos, name='ie_volos'),
    # E2E URLs
    path('e2e_mc/', views.e2e_mc, name='e2e_mc'),
    path('e2e_lc_athens/', views.e2e_lc_athens, name='e2e_lc_athens'),
    path('e2e_lc_unipi/', views.e2e_lc_unipi, name='e2e_lc_unipi'),
    path('e2e_lc_uom_thessaloniki/', views.e2e_lc_uom_thessaloniki, name='e2e_lc_uom_thessaloniki'),
    path('e2e_lc_auth/', views.e2e_lc_auth, name='e2e_lc_auth'),
    path('e2e_ie_uoi/', views.e2e_ie_uoi, name='e2e_ie_uoi'),
    path('e2e_ie_volos/', views.e2e_ie_volos, name='e2e_ie_volos'),

    # MC analytics API endpoints
    path('api/mc-analytics/', views.mc_analytics_api, name='mc_analytics_api'),

    # LCs analytics API endpoints
    path('api/lc-athens-analytics/', views.lc_athens_analytics_api, name='lc_athens_analytics_api'),
    path('api/lc-auth-analytics/', views.lc_auth_analytics_api, name='lc_auth_analytics_api'),
    path('api/lc-unipi-analytics/', views.lc_unipi_analytics_api, name='lc_unipi_analytics_api'),
    path('api/lc-uom-thessaloniki-analytics/', views.LC_UoM_Thessaloniki_analytics_api, name='lc_uom_thessaloniki_analytics_api'),
    path('api/ie-uoi-analytics/', views.IE_UOI_analytics_api, name='ie_uoi_analytics_api'),
    path('api/ie-volos-analytics/', views.IE_Volos_analytics_api, name='ie_volos_analytics_api'),
    # MC E2EAPI endpoints
    
    path('api/e2e-entities/', views.e2e_entities_api, name='e2e_entities_api'),
    path('api/e2e-mc-analytics/', views.e2e_mc_analytics_api, name='e2e_mc_analytics_api'),
    # LCs E2E API endpoints
    path('api/e2e-lc-athens-analytics/', views.e2e_LC_Athens_analytics_api, name='e2e_lc_athens_analytics_api'),
    path('api/e2e-IE-UOI-analytics/', views.e2e_IE_UOI_analytics_api, name='e2e_lc_uoi_analytics_api'),
    path('api/e2e-IE-Volos-analytics/', views.e2e_IE_Volos_analytics_api, name='e2e_lc_volos_analytics_api'),
    path('api/e2e-lc-Auth-analytics/', views.e2e_LC_Auth_analytics_api, name='e2e_lc_auth_analytics_api'),
    path('api/e2e-lc-Unipi-analytics/', views.e2e_LC_Unipi_analytics_api, name='e2e_lc_unipi_analytics_api'),
    path('api/e2e-lc-UoM-Thessaloniki-analytics/', views.e2e_LC_UoM_Thessaloniki_analytics_api, name='e2e_lc_uom_thessaloniki_analytics_api'),
]