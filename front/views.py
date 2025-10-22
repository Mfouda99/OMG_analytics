from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from datetime import datetime
import json
from expa_data.models import ExpaApplication, SignupPerson
from django.db.models import Count, Q, Avg
from django.utils import timezone
import pytz

# Create your views here.
def landing(request):
    return render(request, 'landing.html')

def test_landing(request):
    return render(request, 'test_landing.html')

def mc(request):
    return render(request, 'mc.html')



def e2e(request):
    return render(request, 'e2e_mc.html')

def lc_athens(request):
    return render(request, 'lc_athens.html')

def lc_unipi(request):
    return render(request, 'lc_unipi.html')

def lc_uom_thessaloniki(request):
    return render(request, 'lc_uom_thessaloniki.html')

def lc_auth(request):
    return render(request, 'lc_auth.html')

def ie_uoi(request):
    return render(request, 'ie_uoi.html')

def ie_volos(request):
    return render(request, 'ie_volos.html')

# E2E Views
def e2e_mc(request):
    return render(request, 'e2e_mc.html')

def e2e_lc_athens(request):
    return render(request, 'e2e_lc_athens.html')

def e2e_lc_unipi(request):
    return render(request, 'e2e_lc_unipi.html')

def e2e_lc_uom_thessaloniki(request):
    return render(request, 'e2e_lc_uom_thessaloniki.html')

def e2e_lc_auth(request):
    return render(request, 'e2e_lc_auth.html')

def e2e_ie_uoi(request):
    return render(request, 'e2e_ie_uoi.html')

def e2e_ie_volos(request):
    return render(request, 'e2e_ie_volos.html')





# Analytics Section



# MC analytics

@csrf_exempt
@require_http_methods(["POST"])
def mc_analytics_api(request):
    """
    API endpoint to fetch MC analytics data based on date range
    """
    try:
        # Parse request body
        data = json.loads(request.body)
        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')
        
        if not start_date_str or not end_date_str:
            return JsonResponse({
                'success': False,
                'error': 'Both start_date and end_date are required'
            }, status=400)
        
        # Parse dates (DD/MM/YYYY format)
        try:
            start_date = datetime.strptime(start_date_str, '%d/%m/%Y')
            end_date = datetime.strptime(end_date_str, '%d/%m/%Y')
            
            # Set time to cover the entire day
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            # Make timezone aware
            start_date = timezone.make_aware(start_date, pytz.UTC)
            end_date = timezone.make_aware(end_date, pytz.UTC)
            
        except ValueError as e:
            return JsonResponse({
                'success': False,
                'error': f'Invalid date format. Use DD/MM/YYYY: {str(e)}'
            }, status=400)
        
        # Get analytics data
        analytics_data = get_mc_analytics_data(start_date, end_date)
        
        return JsonResponse({
            'success': True,
            'data': analytics_data
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }, status=500)

def get_mc_analytics_data(start_date, end_date):
    """
    Calculate MC analytics data for the given date range
    """
    # Programme mappings
    ogx_programmes = {
        'OGV': [7],      # Global Volunteer
        'OGTa': [8],     # Global Talent
        'OGTe': [9]      # Global Teacher
    }
    
    icx_programmes = {
        'IGV': [7],      # Incoming Global Volunteer  
        'IGTa': [8],     # Incoming Global Talent
    }
    
    # Initialize result structure
    result = {
        'ogx': {},
        'icx': {},
        'process_times': {'ogx': {}, 'icx': {}},
        'lc_data': []  # Add lc_data to result structure
    }
    
    # Calculate OGX analytics (Outgoing - applications and signups from Greece)
    for programme_name, programme_ids in ogx_programmes.items():
        programme_id = programme_ids[0]
        
        # Get signups for this programme in date range
        if programme_name == 'OGV':
            # For OGV: count signups with programme 7 OR empty/null selected_programmes
            signups = SignupPerson.objects.filter(
                created_at__gte=start_date,
                created_at__lte=end_date,
                home_mc_name='Greece'
            ).filter(
                Q(selected_programmes__icontains=f'[{programme_id}]') |
                Q(selected_programmes__icontains=f'{programme_id}') |
                Q(selected_programmes__isnull=True) |
                Q(selected_programmes='') |
                Q(selected_programmes='[]')
            ).count()
        else:
            # For other programmes: only count explicit selections
            signups = SignupPerson.objects.filter(
                created_at__gte=start_date,
                created_at__lte=end_date,
                home_mc_name='Greece'
            ).filter(
                Q(selected_programmes__icontains=f'[{programme_id}]') |
                Q(selected_programmes__icontains=f'{programme_id}')
            ).count()
        
        # Get all applications for this programme (not filtered by created_at)
        all_applications = ExpaApplication.objects.filter(
            programme_id=programme_id,
            home_mc_name='Greece'  # Outgoing from Greece
        )
        
        # Count by date ranges - each status counts applications that reached that stage in the date range
        
        # Applied: applications created in the date range
        applied = all_applications.filter(
            created_at__gte=start_date,
            created_at__lte=end_date
        ).count()
        
        # Accepted: applications that were matched/accepted in the date range
        accepted = all_applications.filter(
            date_matched__gte=start_date,
            date_matched__lte=end_date
        ).count()
        
        # Approved: applications that were approved in the date range
        approved = all_applications.filter(
            date_approved__gte=start_date,
            date_approved__lte=end_date
        ).count()
        
        # Realized: applications that were realized in the date range
        realized = all_applications.filter(
            date_realized__gte=start_date,
            date_realized__lte=end_date
        ).count()
        
        # Finished: applications that ended their experience in the date range with 'finished' status
        finished = all_applications.filter(
            experience_end_date__gte=start_date,
            experience_end_date__lte=end_date,
            status='finished'
        ).count()
        
        # Complete: applications that ended their experience in the date range with 'completed' status
        complete = all_applications.filter(
            experience_end_date__gte=start_date,
            experience_end_date__lte=end_date,
            status='completed'
        ).count()
        
        result['ogx'][programme_name] = {
            'signups': signups,
            'applied': applied,
            'accepted': accepted,
            'approved': approved,
            'realized': realized,
            'finished': finished,
            'complete': complete
        }
        
        # Calculate process times for OGX
        # Calculate process times for applications in the date range
        applications_in_range = all_applications.filter(
            created_at__gte=start_date,
            created_at__lte=end_date
        )
        process_times = calculate_ogx_process_times(applications_in_range)
        result['process_times']['ogx'][programme_name] = process_times
    
    # Calculate ICX analytics (Incoming - applications TO Greece)
    for programme_name, programme_ids in icx_programmes.items():
        programme_id = programme_ids[0]
        
        # Get all applications for this programme (not filtered by created_at)
        all_applications = ExpaApplication.objects.filter(
            programme_id=programme_id,
            home_mc_name_opportunity__icontains='Greece'  # Incoming to Greece
        )
        
        # Count by date ranges - each status counts applications that reached that stage in the date range
        
        # Applied: applications created in the date range
        applied = all_applications.filter(
            created_at__gte=start_date,
            created_at__lte=end_date
        ).count()
        
        # Accepted: applications that were matched/accepted in the date range
        accepted = all_applications.filter(
            date_matched__gte=start_date,
            date_matched__lte=end_date
        ).count()
        
        # Approved: applications that were approved in the date range
        approved = all_applications.filter(
            date_approved__gte=start_date,
            date_approved__lte=end_date
        ).count()
        
        # Realized: applications that were realized in the date range
        # For ICX, we use date_realized field since experience_end_date is not populated
        realized = all_applications.filter(
            date_realized__gte=start_date,
            date_realized__lte=end_date
        ).count()
        
        # Finished: applications that finished their experience in the date range
        # For ICX, we use date_realized as proxy since experience_end_date is not populated
        finished = all_applications.filter(
            date_realized__gte=start_date,
            date_realized__lte=end_date,
            status='finished'
        ).count()
        
        # Complete: applications that completed their experience in the date range
        # For ICX, we use date_realized as proxy since experience_end_date is not populated
        complete = all_applications.filter(
            date_realized__gte=start_date,
            date_realized__lte=end_date,
            status='completed'
        ).count()
        
        result['icx'][programme_name] = {
            'applied': applied,
            'accepted': accepted,
            'approved': approved,
            'realized': realized,
            'finished': finished,
            'complete': complete
        }
        
        # Calculate process times for ICX
        # For process times, we need applications created in the date range
        applications_created_in_range = all_applications.filter(
            created_at__gte=start_date,
            created_at__lte=end_date
        )
        process_times = calculate_icx_process_times(applications_created_in_range)
        result['process_times']['icx'][programme_name] = process_times
    
    # Add LC-specific data for ranking tables
    result['lc_data'] = get_lc_ranking_data(start_date, end_date)
    
    return result

def get_lc_ranking_data(start_date, end_date):
    """
    Calculate LC-specific data for ranking tables
    Returns an array of LC objects with their ICX and OGX product data
    """
    # Define all Greek LCs
    lcs = [
        {'name': 'LC ATHENS', 'filter': 'ATHENS'},
        {'name': 'LC AUTH', 'filter': 'AUTH'},
        {'name': 'LC PIRAEUS', 'filter': 'Piraeus (UniPi)'},
        {'name': 'LC UoM', 'filter': 'UoM THESSALONIKI'},
        {'name': 'IE VOLOS', 'filter': 'Volos (EXP)'},
    ]
    
    # Programme mappings
    ogx_programmes = {
        'IGV': 7,
        'IGTa': 8,
        'OGV': 7,
        'OGTa': 8,
        'OGTe': 9
    }
    
    lc_data = []
    
    for lc in lcs:
        lc_obj = {
            'name': lc['name'],
            'icx': {},  # Incoming (opportunities hosted by this LC)
            'ogx': {}   # Outgoing (people from this LC going abroad)
        }
        
        # Calculate ICX (Incoming) data - opportunities hosted by this LC
        for product in ['IGV', 'IGTa']:
            programme_id = ogx_programmes[product]
            
            # Use icontains for filters that should be flexible, exact match for specific LC names
            if lc['filter'] in ['Piraeus (UniPi)', 'UoM THESSALONIKI', 'Volos (EXP)']:
                applications = ExpaApplication.objects.filter(
                    programme_id=programme_id,
                    home_lc_name_opportunity=lc['filter']
                )
            else:
                applications = ExpaApplication.objects.filter(
                    programme_id=programme_id,
                    home_lc_name_opportunity__icontains=lc['filter']
                )
            
            # Approved: applications that were approved in the date range
            approved = applications.filter(
                date_approved__gte=start_date,
                date_approved__lte=end_date
            ).count()
            
            # Realized: applications that were realized in the date range
            realized = applications.filter(
                date_realized__gte=start_date,
                date_realized__lte=end_date
            ).count()
            
            # Completed: applications that completed in the date range
            completed = applications.filter(
                date_realized__gte=start_date,
                date_realized__lte=end_date,
                status='completed'
            ).count()
            
            lc_obj['icx'][product] = {
                'approved': approved,
                'realized': realized,
                'completed': completed
            }
        
        # Calculate OGX (Outgoing) data - people from this LC going abroad
        for product in ['OGV', 'OGTa', 'OGTe']:
            programme_id = ogx_programmes[product]
            
            # Use icontains for filters that should be flexible, exact match for specific LC names
            if lc['filter'] in ['Piraeus (UniPi)', 'UoM THESSALONIKI', 'Volos (EXP)']:
                applications = ExpaApplication.objects.filter(
                    programme_id=programme_id,
                    home_lc_name=lc['filter']
                )
            else:
                applications = ExpaApplication.objects.filter(
                    programme_id=programme_id,
                    home_lc_name__icontains=lc['filter']
                )
            
            # Approved: applications that were approved in the date range
            approved = applications.filter(
                date_approved__gte=start_date,
                date_approved__lte=end_date
            ).count()
            
            # Realized: applications that were realized in the date range
            realized = applications.filter(
                date_realized__gte=start_date,
                date_realized__lte=end_date
            ).count()
            
            # Completed: applications that completed in the date range
            completed = applications.filter(
                date_realized__gte=start_date,
                date_realized__lte=end_date,
                status='completed'
            ).count()
            
            lc_obj['ogx'][product] = {
                'approved': approved,
                'realized': realized,
                'completed': completed
            }
        
        lc_data.append(lc_obj)
    
    return lc_data

def calculate_ogx_process_times(applications):
    """
    Calculate average process times for OGX applications
    """
    from django.db.models import Avg
    from django.db.models import F, ExpressionWrapper, DurationField
    
    times = {
        'signup_to_app': 0,
        'app_to_acc': 0,
        'acc_to_apd': 0,
        'total': 0
    }
    
    # Calculate app to accepted time (created_at to date_matched)
    app_to_acc = applications.filter(
        created_at__isnull=False,
        date_matched__isnull=False
    ).aggregate(
        avg_days=Avg(
            ExpressionWrapper(
                F('date_matched') - F('created_at'),
                output_field=DurationField()
            )
        )
    )['avg_days']
    
    if app_to_acc:
        times['app_to_acc'] = app_to_acc.total_seconds() / (24 * 3600)  # Convert to days
    
    # Calculate accepted to approved time (date_matched to date_approved)
    acc_to_apd = applications.filter(
        date_matched__isnull=False,
        date_approved__isnull=False
    ).aggregate(
        avg_days=Avg(
            ExpressionWrapper(
                F('date_approved') - F('date_matched'),
                output_field=DurationField()
            )
        )
    )['avg_days']
    
    if acc_to_apd:
        times['acc_to_apd'] = acc_to_apd.total_seconds() / (24 * 3600)  # Convert to days
    
    # Calculate total process time (created_at to date_approved)
    total_time = applications.filter(
        created_at__isnull=False,
        date_approved__isnull=False
    ).aggregate(
        avg_days=Avg(
            ExpressionWrapper(
                F('date_approved') - F('created_at'),
                output_field=DurationField()
            )
        )
    )['avg_days']
    
    if total_time:
        times['total'] = total_time.total_seconds() / (24 * 3600)  # Convert to days
    
    return times

def calculate_icx_process_times(applications):
    """
    Calculate average process times for ICX applications
    """
    from django.db.models import Avg
    from django.db.models import F, ExpressionWrapper, DurationField
    
    times = {
        'app_to_acc': 0,
        'acc_to_apd': 0,
        'total': 0
    }
    
    # Calculate app to accepted time (created_at to date_matched)
    app_to_acc = applications.filter(
        created_at__isnull=False,
        date_matched__isnull=False
    ).aggregate(
        avg_days=Avg(
            ExpressionWrapper(
                F('date_matched') - F('created_at'),
                output_field=DurationField()
            )
        )
    )['avg_days']
    
    if app_to_acc:
        times['app_to_acc'] = app_to_acc.total_seconds() / (24 * 3600)  # Convert to days
    
    # Calculate accepted to approved time (date_matched to date_approved)
    acc_to_apd = applications.filter(
        date_matched__isnull=False,
        date_approved__isnull=False
    ).aggregate(
        avg_days=Avg(
            ExpressionWrapper(
                F('date_approved') - F('date_matched'),
                output_field=DurationField()
            )
        )
    )['avg_days']
    
    if acc_to_apd:
        times['acc_to_apd'] = acc_to_apd.total_seconds() / (24 * 3600)  # Convert to days
    
    # Calculate total process time (created_at to date_approved)
    total_time = applications.filter(
        created_at__isnull=False,
        date_approved__isnull=False
    ).aggregate(
        avg_days=Avg(
            ExpressionWrapper(
                F('date_approved') - F('created_at'),
                output_field=DurationField()
            )
        )
    )['avg_days']
    
    if total_time:
        times['total'] = total_time.total_seconds() / (24 * 3600)  # Convert to days
    
    return times



# LC Athens analytics
@csrf_exempt
@require_http_methods(["POST"])
def lc_athens_analytics_api(request):
    """
    API endpoint to fetch MC analytics data based on date range
    """
    try:
        # Parse request body
        data = json.loads(request.body)
        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')
        
        if not start_date_str or not end_date_str:
            return JsonResponse({
                'success': False,
                'error': 'Both start_date and end_date are required'
            }, status=400)
        
        # Parse dates (DD/MM/YYYY format)
        try:
            start_date = datetime.strptime(start_date_str, '%d/%m/%Y')
            end_date = datetime.strptime(end_date_str, '%d/%m/%Y')
            
            # Set time to cover the entire day
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            # Make timezone aware
            start_date = timezone.make_aware(start_date, pytz.UTC)
            end_date = timezone.make_aware(end_date, pytz.UTC)
            
        except ValueError as e:
            return JsonResponse({
                'success': False,
                'error': f'Invalid date format. Use DD/MM/YYYY: {str(e)}'
            }, status=400)
        
        # Get analytics data
        analytics_data = get_lc_athens_analytics_data(start_date, end_date)
        
        return JsonResponse({
            'success': True,
            'data': analytics_data
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }, status=500)

def get_lc_athens_analytics_data(start_date, end_date):
    """
    Calculate LC Athens analytics data for the given date range
    """
    # Programme mappings
    ogx_programmes = {
        'OGV': [7],      # Global Volunteer
        'OGTa': [8],     # Global Talent
        'OGTe': [9]      # Global Teacher
    }
    
    icx_programmes = {
        'IGV': [7],      # Incoming Global Volunteer  
        'IGTa': [8],     # Incoming Global Talent
    }
    
    # Initialize result structure
    result = {
        'ogx': {},
        'icx': {},
        'process_times': {'ogx': {}, 'icx': {}}
    }
    
    # Calculate OGX analytics (Outgoing - applications and signups from Greece)
    for programme_name, programme_ids in ogx_programmes.items():
        programme_id = programme_ids[0]
        
        # Get signups for this programme in date range
        if programme_name == 'OGV':
            # For OGV: count signups with programme 7 OR empty/null selected_programmes
            signups = SignupPerson.objects.filter(
                created_at__gte=start_date,
                created_at__lte=end_date,
                home_lc_name__icontains='Athens'
            ).filter(
                Q(selected_programmes__icontains=f'[{programme_id}]') |
                Q(selected_programmes__icontains=f'{programme_id}') |
                Q(selected_programmes__isnull=True) |
                Q(selected_programmes='') |
                Q(selected_programmes='[]')
            ).count()
        else:
            # For other programmes: only count explicit selections
            signups = SignupPerson.objects.filter(
                created_at__gte=start_date,
                created_at__lte=end_date,
                home_lc_name__icontains='Athens'
            ).filter(
                Q(selected_programmes__icontains=f'[{programme_id}]') |
                Q(selected_programmes__icontains=f'{programme_id}')
            ).count()
        
        # Get all applications for this programme (not filtered by created_at)
        all_applications = ExpaApplication.objects.filter(
            programme_id=programme_id,
            home_lc_name__icontains='Athens'  # Case-insensitive
    )
        # Count by date ranges - each status counts applications that reached that stage in the date range
        
        # Applied: applications created in the date range
        applied = all_applications.filter(
            created_at__gte=start_date,
            created_at__lte=end_date
        ).count()
        
        # Accepted: applications that were matched/accepted in the date range
        accepted = all_applications.filter(
            date_matched__gte=start_date,
            date_matched__lte=end_date
        ).count()
        
        # Approved: applications that were approved in the date range
        approved = all_applications.filter(
            date_approved__gte=start_date,
            date_approved__lte=end_date
        ).count()
        
        # Realized: applications that were realized in the date range
        realized = all_applications.filter(
            date_realized__gte=start_date,
            date_realized__lte=end_date
        ).count()
        
        # Finished: applications that ended their experience in the date range with 'finished' status
        finished = all_applications.filter(
            experience_end_date__gte=start_date,
            experience_end_date__lte=end_date,
            status='finished'
        ).count()
        
        # Complete: applications that ended their experience in the date range with 'completed' status
        complete = all_applications.filter(
            experience_end_date__gte=start_date,
            experience_end_date__lte=end_date,
            status='completed'
        ).count()
        
        result['ogx'][programme_name] = {
            'signups': signups,
            'applied': applied,
            'accepted': accepted,
            'approved': approved,
            'realized': realized,
            'finished': finished,
            'complete': complete
        }
        
        # Calculate process times for OGX
        # Calculate process times for applications in the date range
        applications_in_range = all_applications.filter(
            created_at__gte=start_date,
            created_at__lte=end_date
        )
        process_times = calculate_ogx_process_times(applications_in_range)
        result['process_times']['ogx'][programme_name] = process_times
    
    # Calculate ICX analytics (Incoming - applications TO Greece)
    for programme_name, programme_ids in icx_programmes.items():
        programme_id = programme_ids[0]
        
        # Get all applications for this programme (not filtered by created_at)
        all_applications = ExpaApplication.objects.filter(
            programme_id=programme_id,
            
            home_lc_name_opportunity__icontains='ATHENS'  # Incoming to Greece
        )
        
        # Count by date ranges - each status counts applications that reached that stage in the date range
        
        # Applied: applications created in the date range
        applied = all_applications.filter(
            created_at__gte=start_date,
            created_at__lte=end_date
        ).count()
        
        # Accepted: applications that were matched/accepted in the date range
        accepted = all_applications.filter(
            date_matched__gte=start_date,
            date_matched__lte=end_date
        ).count()
        
        # Approved: applications that were approved in the date range
        approved = all_applications.filter(
            date_approved__gte=start_date,
            date_approved__lte=end_date
        ).count()
        
        # Realized: applications that were realized in the date range
        # For ICX, we use date_realized field since experience_end_date is not populated
        realized = all_applications.filter(
            date_realized__gte=start_date,
            date_realized__lte=end_date
        ).count()
        
        # Finished: applications that finished their experience in the date range
        # For ICX, we use date_realized as proxy since experience_end_date is not populated
        finished = all_applications.filter(
            date_realized__gte=start_date,
            date_realized__lte=end_date,
            status='finished'
        ).count()
        
        # Complete: applications that completed their experience in the date range
        # For ICX, we use date_realized as proxy since experience_end_date is not populated
        complete = all_applications.filter(
            date_realized__gte=start_date,
            date_realized__lte=end_date,
            status='completed'
        ).count()
        
        result['icx'][programme_name] = {
            'applied': applied,
            'accepted': accepted,
            'approved': approved,
            'realized': realized,
            'finished': finished,
            'complete': complete
        }
        
        # Calculate process times for ICX
        # For process times, we need applications created in the date range
        applications_created_in_range = all_applications.filter(
            created_at__gte=start_date,
            created_at__lte=end_date
        )
        process_times = calculate_icx_process_times(applications_created_in_range)
        result['process_times']['icx'][programme_name] = process_times
    
    return result

def calculate_ogx_process_times(applications):
    """
    Calculate average process times for OGX applications
    """
    from django.db.models import Avg
    from django.db.models import F, ExpressionWrapper, DurationField
    
    times = {
        'signup_to_app': 0,
        'app_to_acc': 0,
        'acc_to_apd': 0,
        'total': 0
    }
    
    # Calculate app to accepted time (created_at to date_matched)
    app_to_acc = applications.filter(
        created_at__isnull=False,
        date_matched__isnull=False
    ).aggregate(
        avg_days=Avg(
            ExpressionWrapper(
                F('date_matched') - F('created_at'),
                output_field=DurationField()
            )
        )
    )['avg_days']
    
    if app_to_acc:
        times['app_to_acc'] = app_to_acc.total_seconds() / (24 * 3600)  # Convert to days
    
    # Calculate accepted to approved time (date_matched to date_approved)
    acc_to_apd = applications.filter(
        date_matched__isnull=False,
        date_approved__isnull=False
    ).aggregate(
        avg_days=Avg(
            ExpressionWrapper(
                F('date_approved') - F('date_matched'),
                output_field=DurationField()
            )
        )
    )['avg_days']
    
    if acc_to_apd:
        times['acc_to_apd'] = acc_to_apd.total_seconds() / (24 * 3600)  # Convert to days
    
    # Calculate total process time (created_at to date_approved)
    total_time = applications.filter(
        created_at__isnull=False,
        date_approved__isnull=False
    ).aggregate(
        avg_days=Avg(
            ExpressionWrapper(
                F('date_approved') - F('created_at'),
                output_field=DurationField()
            )
        )
    )['avg_days']
    
    if total_time:
        times['total'] = total_time.total_seconds() / (24 * 3600)  # Convert to days
    
    return times

def calculate_icx_process_times(applications):
    """
    Calculate average process times for ICX applications
    """
    from django.db.models import Avg
    from django.db.models import F, ExpressionWrapper, DurationField
    
    times = {
        'app_to_acc': 0,
        'acc_to_apd': 0,
        'total': 0
    }
    
    # Calculate app to accepted time (created_at to date_matched)
    app_to_acc = applications.filter(
        created_at__isnull=False,
        date_matched__isnull=False
    ).aggregate(
        avg_days=Avg(
            ExpressionWrapper(
                F('date_matched') - F('created_at'),
                output_field=DurationField()
            )
        )
    )['avg_days']
    
    if app_to_acc:
        times['app_to_acc'] = app_to_acc.total_seconds() / (24 * 3600)  # Convert to days
    
    # Calculate accepted to approved time (date_matched to date_approved)
    acc_to_apd = applications.filter(
        date_matched__isnull=False,
        date_approved__isnull=False
    ).aggregate(
        avg_days=Avg(
            ExpressionWrapper(
                F('date_approved') - F('date_matched'),
                output_field=DurationField()
            )
        )
    )['avg_days']
    
    if acc_to_apd:
        times['acc_to_apd'] = acc_to_apd.total_seconds() / (24 * 3600)  # Convert to days
    
    # Calculate total process time (created_at to date_approved)
    total_time = applications.filter(
        created_at__isnull=False,
        date_approved__isnull=False
    ).aggregate(
        avg_days=Avg(
            ExpressionWrapper(
                F('date_approved') - F('created_at'),
                output_field=DurationField()
            )
        )
    )['avg_days']
    
    if total_time:
        times['total'] = total_time.total_seconds() / (24 * 3600)  # Convert to days
    
    return times



# LC AUTH analytics
@csrf_exempt
@require_http_methods(["POST"])
def lc_auth_analytics_api(request):
    """
    API endpoint to fetch LC AUTH analytics data based on date range
    """
    try:
        # Parse request body
        data = json.loads(request.body)
        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')
        
        if not start_date_str or not end_date_str:
            return JsonResponse({
                'success': False,
                'error': 'Both start_date and end_date are required'
            }, status=400)
        
        # Parse dates (DD/MM/YYYY format)
        try:
            start_date = datetime.strptime(start_date_str, '%d/%m/%Y')
            end_date = datetime.strptime(end_date_str, '%d/%m/%Y')
            
            # Set time to cover the entire day
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            # Make timezone aware
            start_date = timezone.make_aware(start_date, pytz.UTC)
            end_date = timezone.make_aware(end_date, pytz.UTC)
            
        except ValueError as e:
            return JsonResponse({
                'success': False,
                'error': f'Invalid date format. Use DD/MM/YYYY: {str(e)}'
            }, status=400)
        
        # Get analytics data
        analytics_data = get_lc_auth_analytics_data(start_date, end_date)
        
        return JsonResponse({
            'success': True,
            'data': analytics_data
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }, status=500)

def get_lc_auth_analytics_data(start_date, end_date):
    """
    Calculate LC AUTH analytics data for the given date range
    """
    # Programme mappings
    ogx_programmes = {
        'OGV': [7],      # Global Volunteer
        'OGTa': [8],     # Global Talent
        'OGTe': [9]      # Global Teacher
    }
    
    icx_programmes = {
        'IGV': [7],      # Incoming Global Volunteer  
        'IGTa': [8],     # Incoming Global Talent
    }
    
    # Initialize result structure
    result = {
        'ogx': {},
        'icx': {},
        'process_times': {'ogx': {}, 'icx': {}}
    }
    
    # Calculate OGX analytics (Outgoing - applications and signups from AUTH)
    for programme_name, programme_ids in ogx_programmes.items():
        programme_id = programme_ids[0]
        
        # Get signups for this programme in date range
        if programme_name == 'OGV':
            # For OGV: count signups with programme 7 OR empty/null selected_programmes
            signups = SignupPerson.objects.filter(
                created_at__gte=start_date,
                created_at__lte=end_date,
                home_lc_name__icontains='AUTH'
            ).filter(
                Q(selected_programmes__icontains=f'[{programme_id}]') |
                Q(selected_programmes__icontains=f'{programme_id}') |
                Q(selected_programmes__isnull=True) |
                Q(selected_programmes='') |
                Q(selected_programmes='[]')
            ).count()
        else:
            # For other programmes: only count explicit selections
            signups = SignupPerson.objects.filter(
                created_at__gte=start_date,
                created_at__lte=end_date,
                home_lc_name__icontains='AUTH'
            ).filter(
                Q(selected_programmes__icontains=f'[{programme_id}]') |
                Q(selected_programmes__icontains=f'{programme_id}')
            ).count()
        
        # Get all applications for this programme (not filtered by created_at)
        all_applications = ExpaApplication.objects.filter(
            programme_id=programme_id,
            home_lc_name__icontains='AUTH'  # Case-insensitive
        )
        
        # Count by date ranges - each status counts applications that reached that stage in the date range
        
        # Applied: applications created in the date range
        applied = all_applications.filter(
            created_at__gte=start_date,
            created_at__lte=end_date
        ).count()
        
        # Accepted: applications that were matched/accepted in the date range
        accepted = all_applications.filter(
            date_matched__gte=start_date,
            date_matched__lte=end_date
        ).count()
        
        # Approved: applications that were approved in the date range
        approved = all_applications.filter(
            date_approved__gte=start_date,
            date_approved__lte=end_date
        ).count()
        
        # Realized: applications that were realized in the date range
        realized = all_applications.filter(
            date_realized__gte=start_date,
            date_realized__lte=end_date
        ).count()
        
        # Finished: applications that ended their experience in the date range with 'finished' status
        finished = all_applications.filter(
            experience_end_date__gte=start_date,
            experience_end_date__lte=end_date,
            status='finished'
        ).count()
        
        # Complete: applications that ended their experience in the date range with 'completed' status
        complete = all_applications.filter(
            experience_end_date__gte=start_date,
            experience_end_date__lte=end_date,
            status='completed'
        ).count()
        
        result['ogx'][programme_name] = {
            'signups': signups,
            'applied': applied,
            'accepted': accepted,
            'approved': approved,
            'realized': realized,
            'finished': finished,
            'complete': complete
        }
        
        # Calculate process times for OGX
        # Calculate process times for applications in the date range
        applications_in_range = all_applications.filter(
            created_at__gte=start_date,
            created_at__lte=end_date
        )
        process_times = calculate_ogx_process_times(applications_in_range)
        result['process_times']['ogx'][programme_name] = process_times
    
    # Calculate ICX analytics (Incoming - applications TO AUTH)
    for programme_name, programme_ids in icx_programmes.items():
        programme_id = programme_ids[0]
        
        # Get all applications for this programme (not filtered by created_at)
        all_applications = ExpaApplication.objects.filter(
            programme_id=programme_id,
            home_lc_name_opportunity__icontains='AUTH'  # Incoming to AUTH
        )
        
        # Count by date ranges - each status counts applications that reached that stage in the date range
        
        # Applied: applications created in the date range
        applied = all_applications.filter(
            created_at__gte=start_date,
            created_at__lte=end_date
        ).count()
        
        # Accepted: applications that were matched/accepted in the date range
        accepted = all_applications.filter(
            date_matched__gte=start_date,
            date_matched__lte=end_date
        ).count()
        
        # Approved: applications that were approved in the date range
        approved = all_applications.filter(
            date_approved__gte=start_date,
            date_approved__lte=end_date
        ).count()
        
        # Realized: applications that were realized in the date range
        # For ICX, we use date_realized field since experience_end_date is not populated
        realized = all_applications.filter(
            date_realized__gte=start_date,
            date_realized__lte=end_date
        ).count()
        
        # Finished: applications that finished their experience in the date range
        # For ICX, we use date_realized as proxy since experience_end_date is not populated
        finished = all_applications.filter(
            date_realized__gte=start_date,
            date_realized__lte=end_date,
            status='finished'
        ).count()
        
        # Complete: applications that completed their experience in the date range
        # For ICX, we use date_realized as proxy since experience_end_date is not populated
        complete = all_applications.filter(
            date_realized__gte=start_date,
            date_realized__lte=end_date,
            status='completed'
        ).count()
        
        result['icx'][programme_name] = {
            'applied': applied,
            'accepted': accepted,
            'approved': approved,
            'realized': realized,
            'finished': finished,
            'complete': complete
        }
        
        # Calculate process times for ICX
        # For process times, we need applications created in the date range
        applications_created_in_range = all_applications.filter(
            created_at__gte=start_date,
            created_at__lte=end_date
        )
        process_times = calculate_icx_process_times(applications_created_in_range)
        result['process_times']['icx'][programme_name] = process_times
    
    return result

def calculate_ogx_process_times(applications):
    """
    Calculate average process times for OGX applications
    """
    from django.db.models import Avg
    from django.db.models import F, ExpressionWrapper, DurationField
    
    times = {
        'signup_to_app': 0,
        'app_to_acc': 0,
        'acc_to_apd': 0,
        'total': 0
    }
    
    # Calculate app to accepted time (created_at to date_matched)
    app_to_acc = applications.filter(
        created_at__isnull=False,
        date_matched__isnull=False
    ).aggregate(
        avg_days=Avg(
            ExpressionWrapper(
                F('date_matched') - F('created_at'),
                output_field=DurationField()
            )
        )
    )['avg_days']
    
    if app_to_acc:
        times['app_to_acc'] = app_to_acc.total_seconds() / (24 * 3600)  # Convert to days
    
    # Calculate accepted to approved time (date_matched to date_approved)
    acc_to_apd = applications.filter(
        date_matched__isnull=False,
        date_approved__isnull=False
    ).aggregate(
        avg_days=Avg(
            ExpressionWrapper(
                F('date_approved') - F('date_matched'),
                output_field=DurationField()
            )
        )
    )['avg_days']
    
    if acc_to_apd:
        times['acc_to_apd'] = acc_to_apd.total_seconds() / (24 * 3600)  # Convert to days
    
    # Calculate total process time (created_at to date_approved)
    total_time = applications.filter(
        created_at__isnull=False,
        date_approved__isnull=False
    ).aggregate(
        avg_days=Avg(
            ExpressionWrapper(
                F('date_approved') - F('created_at'),
                output_field=DurationField()
            )
        )
    )['avg_days']
    
    if total_time:
        times['total'] = total_time.total_seconds() / (24 * 3600)  # Convert to days
    
    return times

def calculate_icx_process_times(applications):
    """
    Calculate average process times for ICX applications
    """
    from django.db.models import Avg
    from django.db.models import F, ExpressionWrapper, DurationField
    
    times = {
        'app_to_acc': 0,
        'acc_to_apd': 0,
        'total': 0
    }
    
    # Calculate app to accepted time (created_at to date_matched)
    app_to_acc = applications.filter(
        created_at__isnull=False,
        date_matched__isnull=False
    ).aggregate(
        avg_days=Avg(
            ExpressionWrapper(
                F('date_matched') - F('created_at'),
                output_field=DurationField()
            )
        )
    )['avg_days']
    
    if app_to_acc:
        times['app_to_acc'] = app_to_acc.total_seconds() / (24 * 3600)  # Convert to days
    
    # Calculate accepted to approved time (date_matched to date_approved)
    acc_to_apd = applications.filter(
        date_matched__isnull=False,
        date_approved__isnull=False
    ).aggregate(
        avg_days=Avg(
            ExpressionWrapper(
                F('date_approved') - F('date_matched'),
                output_field=DurationField()
            )
        )
    )['avg_days']
    
    if acc_to_apd:
        times['acc_to_apd'] = acc_to_apd.total_seconds() / (24 * 3600)  # Convert to days
    
    # Calculate total process time (created_at to date_approved)
    total_time = applications.filter(
        created_at__isnull=False,
        date_approved__isnull=False
    ).aggregate(
        avg_days=Avg(
            ExpressionWrapper(
                F('date_approved') - F('created_at'),
                output_field=DurationField()
            )
        )
    )['avg_days']
    
    if total_time:
        times['total'] = total_time.total_seconds() / (24 * 3600)  # Convert to days
    
    return times


# LC Piraeus (UniPi) analytics


@csrf_exempt
@require_http_methods(["POST"])
def lc_unipi_analytics_api(request):
    """
    API endpoint to fetch LC UniPi analytics data based on date range
    """
    try:
        # Parse request body
        data = json.loads(request.body)
        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')
        
        if not start_date_str or not end_date_str:
            return JsonResponse({
                'success': False,
                'error': 'Both start_date and end_date are required'
            }, status=400)
        
        # Parse dates (DD/MM/YYYY format)
        try:
            start_date = datetime.strptime(start_date_str, '%d/%m/%Y')
            end_date = datetime.strptime(end_date_str, '%d/%m/%Y')
            
            # Set time to cover the entire day
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            # Make timezone aware
            start_date = timezone.make_aware(start_date, pytz.UTC)
            end_date = timezone.make_aware(end_date, pytz.UTC)
            
        except ValueError as e:
            return JsonResponse({
                'success': False,
                'error': f'Invalid date format. Use DD/MM/YYYY: {str(e)}'
            }, status=400)
        
        # Get analytics data
        analytics_data = get_lc_unipi_analytics_data(start_date, end_date)
        
        return JsonResponse({
            'success': True,
            'data': analytics_data
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }, status=500)

def get_lc_unipi_analytics_data(start_date, end_date):
    """
    Calculate LC UniPi analytics data for the given date range
    """
    # Programme mappings
    ogx_programmes = {
        'OGV': [7],      # Global Volunteer
        'OGTa': [8],     # Global Talent
        'OGTe': [9]      # Global Teacher
    }
    
    icx_programmes = {
        'IGV': [7],      # Incoming Global Volunteer  
        'IGTa': [8],     # Incoming Global Talent
    }
    
    # Initialize result structure
    result = {
        'ogx': {},
        'icx': {},
        'process_times': {'ogx': {}, 'icx': {}}
    }
    
    # Calculate OGX analytics (Outgoing - applications and signups from AUTH)
    for programme_name, programme_ids in ogx_programmes.items():
        programme_id = programme_ids[0]
        
        # Get signups for this programme in date range
        if programme_name == 'OGV':
            # For OGV: count signups with programme 7 OR empty/null selected_programmes
            signups = SignupPerson.objects.filter(
                created_at__gte=start_date,
                created_at__lte=end_date,
                home_lc_name__icontains='Piraeus (UniPi)'
            ).filter(
                Q(selected_programmes__icontains=f'[{programme_id}]') |
                Q(selected_programmes__icontains=f'{programme_id}') |
                Q(selected_programmes__isnull=True) |
                Q(selected_programmes='') |
                Q(selected_programmes='[]')
            ).count()
        else:
            # For other programmes: only count explicit selections
            signups = SignupPerson.objects.filter(
                created_at__gte=start_date,
                created_at__lte=end_date,
                home_lc_name__icontains='Piraeus (UniPi)'
            ).filter(
                Q(selected_programmes__icontains=f'[{programme_id}]') |
                Q(selected_programmes__icontains=f'{programme_id}')
            ).count()
        
        # Get all applications for this programme (not filtered by created_at)
        all_applications = ExpaApplication.objects.filter(
            programme_id=programme_id,
            home_lc_name__icontains='Piraeus (UniPi)'  # Case-insensitive
        )
        
        # Count by date ranges - each status counts applications that reached that stage in the date range
        
        # Applied: applications created in the date range
        applied = all_applications.filter(
            created_at__gte=start_date,
            created_at__lte=end_date
        ).count()
        
        # Accepted: applications that were matched/accepted in the date range
        accepted = all_applications.filter(
            date_matched__gte=start_date,
            date_matched__lte=end_date
        ).count()
        
        # Approved: applications that were approved in the date range
        approved = all_applications.filter(
            date_approved__gte=start_date,
            date_approved__lte=end_date
        ).count()
        
        # Realized: applications that were realized in the date range
        realized = all_applications.filter(
            date_realized__gte=start_date,
            date_realized__lte=end_date
        ).count()
        
        # Finished: applications that ended their experience in the date range with 'finished' status
        finished = all_applications.filter(
            experience_end_date__gte=start_date,
            experience_end_date__lte=end_date,
            status='finished'
        ).count()
        
        # Complete: applications that ended their experience in the date range with 'completed' status
        complete = all_applications.filter(
            experience_end_date__gte=start_date,
            experience_end_date__lte=end_date,
            status='completed'
        ).count()
        
        result['ogx'][programme_name] = {
            'signups': signups,
            'applied': applied,
            'accepted': accepted,
            'approved': approved,
            'realized': realized,
            'finished': finished,
            'complete': complete
        }
        
        # Calculate process times for OGX
        # Calculate process times for applications in the date range
        applications_in_range = all_applications.filter(
            created_at__gte=start_date,
            created_at__lte=end_date
        )
        process_times = calculate_ogx_process_times(applications_in_range)
        result['process_times']['ogx'][programme_name] = process_times
    
    # Calculate ICX analytics (Incoming - applications TO AUTH)
    for programme_name, programme_ids in icx_programmes.items():
        programme_id = programme_ids[0]
        
        # Get all applications for this programme (not filtered by created_at)
        all_applications = ExpaApplication.objects.filter(
            programme_id=programme_id,
            home_lc_name_opportunity__icontains='Piraeus (UniPi)'  # Incoming to AUTH
        )
        
        # Count by date ranges - each status counts applications that reached that stage in the date range
        
        # Applied: applications created in the date range
        applied = all_applications.filter(
            created_at__gte=start_date,
            created_at__lte=end_date
        ).count()
        
        # Accepted: applications that were matched/accepted in the date range
        accepted = all_applications.filter(
            date_matched__gte=start_date,
            date_matched__lte=end_date
        ).count()
        
        # Approved: applications that were approved in the date range
        approved = all_applications.filter(
            date_approved__gte=start_date,
            date_approved__lte=end_date
        ).count()
        
        # Realized: applications that were realized in the date range
        # For ICX, we use date_realized field since experience_end_date is not populated
        realized = all_applications.filter(
            date_realized__gte=start_date,
            date_realized__lte=end_date
        ).count()
        
        # Finished: applications that finished their experience in the date range
        # For ICX, we use date_realized as proxy since experience_end_date is not populated
        finished = all_applications.filter(
            date_realized__gte=start_date,
            date_realized__lte=end_date,
            status='finished'
        ).count()
        
        # Complete: applications that completed their experience in the date range
        # For ICX, we use date_realized as proxy since experience_end_date is not populated
        complete = all_applications.filter(
            date_realized__gte=start_date,
            date_realized__lte=end_date,
            status='completed'
        ).count()
        
        result['icx'][programme_name] = {
            'applied': applied,
            'accepted': accepted,
            'approved': approved,
            'realized': realized,
            'finished': finished,
            'complete': complete
        }
        
        # Calculate process times for ICX
        # For process times, we need applications created in the date range
        applications_created_in_range = all_applications.filter(
            created_at__gte=start_date,
            created_at__lte=end_date
        )
        process_times = calculate_icx_process_times(applications_created_in_range)
        result['process_times']['icx'][programme_name] = process_times
    
    return result



# LC Uom thessaloniki analytics

@csrf_exempt
@require_http_methods(["POST"])
def LC_UoM_Thessaloniki_analytics_api(request):
    """
    API endpoint to fetch LC UoM Thessaloniki analytics data based on date range
    """
    try:
        # Parse request body
        data = json.loads(request.body)
        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')
        
        if not start_date_str or not end_date_str:
            return JsonResponse({
                'success': False,
                'error': 'Both start_date and end_date are required'
            }, status=400)
        
        # Parse dates (DD/MM/YYYY format)
        try:
            start_date = datetime.strptime(start_date_str, '%d/%m/%Y')
            end_date = datetime.strptime(end_date_str, '%d/%m/%Y')
            
            # Set time to cover the entire day
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            # Make timezone aware
            start_date = timezone.make_aware(start_date, pytz.UTC)
            end_date = timezone.make_aware(end_date, pytz.UTC)
            
        except ValueError as e:
            return JsonResponse({
                'success': False,
                'error': f'Invalid date format. Use DD/MM/YYYY: {str(e)}'
            }, status=400)
        
        # Get analytics data
        analytics_data = get_LC_UoM_Thessaloniki_analytics_data(start_date, end_date)
        
        return JsonResponse({
            'success': True,
            'data': analytics_data
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }, status=500)

def get_LC_UoM_Thessaloniki_analytics_data(start_date, end_date):
    """
    Calculate LC UoM Thessaloniki analytics data for the given date range
    """
    # Programme mappings
    ogx_programmes = {
        'OGV': [7],      # Global Volunteer
        'OGTa': [8],     # Global Talent
        'OGTe': [9]      # Global Teacher
    }
    
    icx_programmes = {
        'IGV': [7],      # Incoming Global Volunteer  
        'IGTa': [8],     # Incoming Global Talent
    }
    
    # Initialize result structure
    result = {
        'ogx': {},
        'icx': {},
        'process_times': {'ogx': {}, 'icx': {}}
    }
    
    # Calculate OGX analytics (Outgoing - applications and signups from AUTH)
    for programme_name, programme_ids in ogx_programmes.items():
        programme_id = programme_ids[0]
        
        # Get signups for this programme in date range
        if programme_name == 'OGV':
            # For OGV: count signups with programme 7 OR empty/null selected_programmes
            signups = SignupPerson.objects.filter(
                created_at__gte=start_date,
                created_at__lte=end_date,
                home_lc_name__icontains='UoM THESSALONIKI'
            ).filter(
                Q(selected_programmes__icontains=f'[{programme_id}]') |
                Q(selected_programmes__icontains=f'{programme_id}') |
                Q(selected_programmes__isnull=True) |
                Q(selected_programmes='') |
                Q(selected_programmes='[]')
            ).count()
        else:
            # For other programmes: only count explicit selections
            signups = SignupPerson.objects.filter(
                created_at__gte=start_date,
                created_at__lte=end_date,
                home_lc_name__icontains='UoM THESSALONIKI'
            ).filter(
                Q(selected_programmes__icontains=f'[{programme_id}]') |
                Q(selected_programmes__icontains=f'{programme_id}')
            ).count()
        
        # Get all applications for this programme (not filtered by created_at)
        all_applications = ExpaApplication.objects.filter(
            programme_id=programme_id,
            home_lc_name__icontains='UoM THESSALONIKI'  # Case-insensitive
        )
        
        # Count by date ranges - each status counts applications that reached that stage in the date range
        
        # Applied: applications created in the date range
        applied = all_applications.filter(
            created_at__gte=start_date,
            created_at__lte=end_date
        ).count()
        
        # Accepted: applications that were matched/accepted in the date range
        accepted = all_applications.filter(
            date_matched__gte=start_date,
            date_matched__lte=end_date
        ).count()
        
        # Approved: applications that were approved in the date range
        approved = all_applications.filter(
            date_approved__gte=start_date,
            date_approved__lte=end_date
        ).count()
        
        # Realized: applications that were realized in the date range
        realized = all_applications.filter(
            date_realized__gte=start_date,
            date_realized__lte=end_date
        ).count()
        
        # Finished: applications that ended their experience in the date range with 'finished' status
        finished = all_applications.filter(
            experience_end_date__gte=start_date,
            experience_end_date__lte=end_date,
            status='finished'
        ).count()
        
        # Complete: applications that ended their experience in the date range with 'completed' status
        complete = all_applications.filter(
            experience_end_date__gte=start_date,
            experience_end_date__lte=end_date,
            status='completed'
        ).count()
        
        result['ogx'][programme_name] = {
            'signups': signups,
            'applied': applied,
            'accepted': accepted,
            'approved': approved,
            'realized': realized,
            'finished': finished,
            'complete': complete
        }
        
        # Calculate process times for OGX
        # Calculate process times for applications in the date range
        applications_in_range = all_applications.filter(
            created_at__gte=start_date,
            created_at__lte=end_date
        )
        process_times = calculate_ogx_process_times(applications_in_range)
        result['process_times']['ogx'][programme_name] = process_times
    
    # Calculate ICX analytics (Incoming - applications TO AUTH)
    for programme_name, programme_ids in icx_programmes.items():
        programme_id = programme_ids[0]
        
        # Get all applications for this programme (not filtered by created_at)
        all_applications = ExpaApplication.objects.filter(
            programme_id=programme_id,
            home_lc_name_opportunity__icontains='UoM THESSALONIKI'  # Incoming to AUTH
        )
        
        # Count by date ranges - each status counts applications that reached that stage in the date range
        
        # Applied: applications created in the date range
        applied = all_applications.filter(
            created_at__gte=start_date,
            created_at__lte=end_date
        ).count()
        
        # Accepted: applications that were matched/accepted in the date range
        accepted = all_applications.filter(
            date_matched__gte=start_date,
            date_matched__lte=end_date
        ).count()
        
        # Approved: applications that were approved in the date range
        approved = all_applications.filter(
            date_approved__gte=start_date,
            date_approved__lte=end_date
        ).count()
        
        # Realized: applications that were realized in the date range
        # For ICX, we use date_realized field since experience_end_date is not populated
        realized = all_applications.filter(
            date_realized__gte=start_date,
            date_realized__lte=end_date
        ).count()
        
        # Finished: applications that finished their experience in the date range
        # For ICX, we use date_realized as proxy since experience_end_date is not populated
        finished = all_applications.filter(
            date_realized__gte=start_date,
            date_realized__lte=end_date,
            status='finished'
        ).count()
        
        # Complete: applications that completed their experience in the date range
        # For ICX, we use date_realized as proxy since experience_end_date is not populated
        complete = all_applications.filter(
            date_realized__gte=start_date,
            date_realized__lte=end_date,
            status='completed'
        ).count()
        
        result['icx'][programme_name] = {
            'applied': applied,
            'accepted': accepted,
            'approved': approved,
            'realized': realized,
            'finished': finished,
            'complete': complete
        }
        
        # Calculate process times for ICX
        # For process times, we need applications created in the date range
        applications_created_in_range = all_applications.filter(
            created_at__gte=start_date,
            created_at__lte=end_date
        )
        process_times = calculate_icx_process_times(applications_created_in_range)
        result['process_times']['icx'][programme_name] = process_times
    
    return result



# IE UOI analytics

@csrf_exempt
@require_http_methods(["POST"])
def IE_UOI_analytics_api(request):
    """
    API endpoint to fetch IE UOI analytics data based on date range
    """
    try:
        # Parse request body
        data = json.loads(request.body)
        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')
        
        if not start_date_str or not end_date_str:
            return JsonResponse({
                'success': False,
                'error': 'Both start_date and end_date are required'
            }, status=400)
        
        # Parse dates (DD/MM/YYYY format)
        try:
            start_date = datetime.strptime(start_date_str, '%d/%m/%Y')
            end_date = datetime.strptime(end_date_str, '%d/%m/%Y')
            
            # Set time to cover the entire day
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            # Make timezone aware
            start_date = timezone.make_aware(start_date, pytz.UTC)
            end_date = timezone.make_aware(end_date, pytz.UTC)
            
        except ValueError as e:
            return JsonResponse({
                'success': False,
                'error': f'Invalid date format. Use DD/MM/YYYY: {str(e)}'
            }, status=400)
        
        # Get analytics data
        analytics_data = get_IE_UOI_analytics_data(start_date, end_date)
        
        return JsonResponse({
            'success': True,
            'data': analytics_data
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }, status=500)

def get_IE_UOI_analytics_data(start_date, end_date):
    """
    Calculate IE UOI analytics data for the given date range
    """
    # Programme mappings
    ogx_programmes = {
        'OGV': [7],      # Global Volunteer
        'OGTa': [8],     # Global Talent
        'OGTe': [9]      # Global Teacher
    }
    
    icx_programmes = {
        'IGV': [7],      # Incoming Global Volunteer  
        'IGTa': [8],     # Incoming Global Talent
    }
    
    # Initialize result structure
    result = {
        'ogx': {},
        'icx': {},
        'process_times': {'ogx': {}, 'icx': {}}
    }
    
    # Calculate OGX analytics (Outgoing - applications and signups from AUTH)
    for programme_name, programme_ids in ogx_programmes.items():
        programme_id = programme_ids[0]
        
        # Get signups for this programme in date range
        if programme_name == 'OGV':
            # For OGV: count signups with programme 7 OR empty/null selected_programmes
            signups = SignupPerson.objects.filter(
                created_at__gte=start_date,
                created_at__lte=end_date,
                home_lc_name__icontains='UoI (EXP)'
            ).filter(
                Q(selected_programmes__icontains=f'[{programme_id}]') |
                Q(selected_programmes__icontains=f'{programme_id}') |
                Q(selected_programmes__isnull=True) |
                Q(selected_programmes='') |
                Q(selected_programmes='[]')
            ).count()
        else:
            # For other programmes: only count explicit selections
            signups = SignupPerson.objects.filter(
                created_at__gte=start_date,
                created_at__lte=end_date,
                home_lc_name__icontains='UoI (EXP)'
            ).filter(
                Q(selected_programmes__icontains=f'[{programme_id}]') |
                Q(selected_programmes__icontains=f'{programme_id}')
            ).count()
        
        # Get all applications for this programme (not filtered by created_at)
        all_applications = ExpaApplication.objects.filter(
            programme_id=programme_id,
            home_lc_name__icontains='UoI (EXP)'  # Case-insensitive
        )
        
        # Count by date ranges - each status counts applications that reached that stage in the date range
        
        # Applied: applications created in the date range
        applied = all_applications.filter(
            created_at__gte=start_date,
            created_at__lte=end_date
        ).count()
        
        # Accepted: applications that were matched/accepted in the date range
        accepted = all_applications.filter(
            date_matched__gte=start_date,
            date_matched__lte=end_date
        ).count()
        
        # Approved: applications that were approved in the date range
        approved = all_applications.filter(
            date_approved__gte=start_date,
            date_approved__lte=end_date
        ).count()
        
        # Realized: applications that were realized in the date range
        realized = all_applications.filter(
            date_realized__gte=start_date,
            date_realized__lte=end_date
        ).count()
        
        # Finished: applications that ended their experience in the date range with 'finished' status
        finished = all_applications.filter(
            experience_end_date__gte=start_date,
            experience_end_date__lte=end_date,
            status='finished'
        ).count()
        
        # Complete: applications that ended their experience in the date range with 'completed' status
        complete = all_applications.filter(
            experience_end_date__gte=start_date,
            experience_end_date__lte=end_date,
            status='completed'
        ).count()
        
        result['ogx'][programme_name] = {
            'signups': signups,
            'applied': applied,
            'accepted': accepted,
            'approved': approved,
            'realized': realized,
            'finished': finished,
            'complete': complete
        }
        
        # Calculate process times for OGX
        # Calculate process times for applications in the date range
        applications_in_range = all_applications.filter(
            created_at__gte=start_date,
            created_at__lte=end_date
        )
        process_times = calculate_ogx_process_times(applications_in_range)
        result['process_times']['ogx'][programme_name] = process_times
    
    # Calculate ICX analytics (Incoming - applications TO AUTH)
    for programme_name, programme_ids in icx_programmes.items():
        programme_id = programme_ids[0]
        
        # Get all applications for this programme (not filtered by created_at)
        all_applications = ExpaApplication.objects.filter(
            programme_id=programme_id,
            home_lc_name_opportunity__icontains='UoI (EXP)'  # Incoming to AUTH
        )
        
        # Count by date ranges - each status counts applications that reached that stage in the date range
        
        # Applied: applications created in the date range
        applied = all_applications.filter(
            created_at__gte=start_date,
            created_at__lte=end_date
        ).count()
        
        # Accepted: applications that were matched/accepted in the date range
        accepted = all_applications.filter(
            date_matched__gte=start_date,
            date_matched__lte=end_date
        ).count()
        
        # Approved: applications that were approved in the date range
        approved = all_applications.filter(
            date_approved__gte=start_date,
            date_approved__lte=end_date
        ).count()
        
        # Realized: applications that were realized in the date range
        # For ICX, we use date_realized field since experience_end_date is not populated
        realized = all_applications.filter(
            date_realized__gte=start_date,
            date_realized__lte=end_date
        ).count()
        
        # Finished: applications that finished their experience in the date range
        # For ICX, we use date_realized as proxy since experience_end_date is not populated
        finished = all_applications.filter(
            date_realized__gte=start_date,
            date_realized__lte=end_date,
            status='finished'
        ).count()
        
        # Complete: applications that completed their experience in the date range
        # For ICX, we use date_realized as proxy since experience_end_date is not populated
        complete = all_applications.filter(
            date_realized__gte=start_date,
            date_realized__lte=end_date,
            status='completed'
        ).count()
        
        result['icx'][programme_name] = {
            'applied': applied,
            'accepted': accepted,
            'approved': approved,
            'realized': realized,
            'finished': finished,
            'complete': complete
        }
        
        # Calculate process times for ICX
        # For process times, we need applications created in the date range
        applications_created_in_range = all_applications.filter(
            created_at__gte=start_date,
            created_at__lte=end_date
        )
        process_times = calculate_icx_process_times(applications_created_in_range)
        result['process_times']['icx'][programme_name] = process_times
    
    return result


# LC Uom thessaloniki analytics

@csrf_exempt
@require_http_methods(["POST"])
def IE_Volos_analytics_api(request):
    """
    API endpoint to fetch LC UoM Thessaloniki analytics data based on date range
    """
    try:
        # Parse request body
        data = json.loads(request.body)
        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')
        
        if not start_date_str or not end_date_str:
            return JsonResponse({
                'success': False,
                'error': 'Both start_date and end_date are required'
            }, status=400)
        
        # Parse dates (DD/MM/YYYY format)
        try:
            start_date = datetime.strptime(start_date_str, '%d/%m/%Y')
            end_date = datetime.strptime(end_date_str, '%d/%m/%Y')
            
            # Set time to cover the entire day
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            # Make timezone aware
            start_date = timezone.make_aware(start_date, pytz.UTC)
            end_date = timezone.make_aware(end_date, pytz.UTC)
            
        except ValueError as e:
            return JsonResponse({
                'success': False,
                'error': f'Invalid date format. Use DD/MM/YYYY: {str(e)}'
            }, status=400)
        
        # Get analytics data
        analytics_data = get_IE_Volos_analytics_data(start_date, end_date)
        
        return JsonResponse({
            'success': True,
            'data': analytics_data
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }, status=500)

def get_IE_Volos_analytics_data(start_date, end_date):
    """
    Calculate IE Volos analytics data for the given date range
    """
    # Programme mappings
    ogx_programmes = {
        'OGV': [7],      # Global Volunteer
        'OGTa': [8],     # Global Talent
        'OGTe': [9]      # Global Teacher
    }
    
    icx_programmes = {
        'IGV': [7],      # Incoming Global Volunteer  
        'IGTa': [8],     # Incoming Global Talent
    }
    
    # Initialize result structure
    result = {
        'ogx': {},
        'icx': {},
        'process_times': {'ogx': {}, 'icx': {}}
    }
    
    # Calculate OGX analytics (Outgoing - applications and signups from AUTH)
    for programme_name, programme_ids in ogx_programmes.items():
        programme_id = programme_ids[0]
        
        # Get signups for this programme in date range
        if programme_name == 'OGV':
            # For OGV: count signups with programme 7 OR empty/null selected_programmes
            signups = SignupPerson.objects.filter(
                created_at__gte=start_date,
                created_at__lte=end_date,
                home_lc_name__icontains='Volos (EXP)'
            ).filter(
                Q(selected_programmes__icontains=f'[{programme_id}]') |
                Q(selected_programmes__icontains=f'{programme_id}') |
                Q(selected_programmes__isnull=True) |
                Q(selected_programmes='') |
                Q(selected_programmes='[]')
            ).count()
        else:
            # For other programmes: only count explicit selections
            signups = SignupPerson.objects.filter(
                created_at__gte=start_date,
                created_at__lte=end_date,
                home_lc_name__icontains='Volos (EXP)'
            ).filter(
                Q(selected_programmes__icontains=f'[{programme_id}]') |
                Q(selected_programmes__icontains=f'{programme_id}')
            ).count()
        
        # Get all applications for this programme (not filtered by created_at)
        all_applications = ExpaApplication.objects.filter(
            programme_id=programme_id,
            home_lc_name__icontains='Volos (EXP)'  # Case-insensitive
        )
        
        # Count by date ranges - each status counts applications that reached that stage in the date range
        
        # Applied: applications created in the date range
        applied = all_applications.filter(
            created_at__gte=start_date,
            created_at__lte=end_date
        ).count()
        
        # Accepted: applications that were matched/accepted in the date range
        accepted = all_applications.filter(
            date_matched__gte=start_date,
            date_matched__lte=end_date
        ).count()
        
        # Approved: applications that were approved in the date range
        approved = all_applications.filter(
            date_approved__gte=start_date,
            date_approved__lte=end_date
        ).count()
        
        # Realized: applications that were realized in the date range
        realized = all_applications.filter(
            date_realized__gte=start_date,
            date_realized__lte=end_date
        ).count()
        
        # Finished: applications that ended their experience in the date range with 'finished' status
        finished = all_applications.filter(
            experience_end_date__gte=start_date,
            experience_end_date__lte=end_date,
            status='finished'
        ).count()
        
        # Complete: applications that ended their experience in the date range with 'completed' status
        complete = all_applications.filter(
            experience_end_date__gte=start_date,
            experience_end_date__lte=end_date,
            status='completed'
        ).count()
        
        result['ogx'][programme_name] = {
            'signups': signups,
            'applied': applied,
            'accepted': accepted,
            'approved': approved,
            'realized': realized,
            'finished': finished,
            'complete': complete
        }
        
        # Calculate process times for OGX
        # Calculate process times for applications in the date range
        applications_in_range = all_applications.filter(
            created_at__gte=start_date,
            created_at__lte=end_date
        )
        process_times = calculate_ogx_process_times(applications_in_range)
        result['process_times']['ogx'][programme_name] = process_times
    
    # Calculate ICX analytics (Incoming - applications TO AUTH)
    for programme_name, programme_ids in icx_programmes.items():
        programme_id = programme_ids[0]
        
        # Get all applications for this programme (not filtered by created_at)
        all_applications = ExpaApplication.objects.filter(
            programme_id=programme_id,
            home_lc_name_opportunity__icontains='Volos (EXP)'  # Incoming to AUTH
        )
        
        # Count by date ranges - each status counts applications that reached that stage in the date range
        
        # Applied: applications created in the date range
        applied = all_applications.filter(
            created_at__gte=start_date,
            created_at__lte=end_date
        ).count()
        
        # Accepted: applications that were matched/accepted in the date range
        accepted = all_applications.filter(
            date_matched__gte=start_date,
            date_matched__lte=end_date
        ).count()
        
        # Approved: applications that were approved in the date range
        approved = all_applications.filter(
            date_approved__gte=start_date,
            date_approved__lte=end_date
        ).count()
        
        # Realized: applications that were realized in the date range
        # For ICX, we use date_realized field since experience_end_date is not populated
        realized = all_applications.filter(
            date_realized__gte=start_date,
            date_realized__lte=end_date
        ).count()
        
        # Finished: applications that finished their experience in the date range
        # For ICX, we use date_realized as proxy since experience_end_date is not populated
        finished = all_applications.filter(
            date_realized__gte=start_date,
            date_realized__lte=end_date,
            status='finished'
        ).count()
        
        # Complete: applications that completed their experience in the date range
        # For ICX, we use date_realized as proxy since experience_end_date is not populated
        complete = all_applications.filter(
            date_realized__gte=start_date,
            date_realized__lte=end_date,
            status='completed'
        ).count()
        
        result['icx'][programme_name] = {
            'applied': applied,
            'accepted': accepted,
            'approved': approved,
            'realized': realized,
            'finished': finished,
            'complete': complete
        }
        
        # Calculate process times for ICX
        # For process times, we need applications created in the date range
        applications_created_in_range = all_applications.filter(
            created_at__gte=start_date,
            created_at__lte=end_date
        )
        process_times = calculate_icx_process_times(applications_created_in_range)
        result['process_times']['icx'][programme_name] = process_times
    
    return result




# E2E section 



#MC E2E

@csrf_exempt
@require_http_methods(["GET"])
def e2e_entities_api(request):
    """
    API endpoint to fetch all available entities (MCs) for the E2E dropdown
    """
    try:
        # Get all MCs from the database (both opportunity and person home MCs) - excluding Greece
        ogx_entities = list(ExpaApplication.objects.values_list('home_mc_name_opportunity', flat=True).distinct().filter(home_mc_name_opportunity__isnull=False).exclude(home_mc_name_opportunity__iexact='Greece').order_by('home_mc_name_opportunity'))
        icx_entities = list(ExpaApplication.objects.values_list('home_mc_name', flat=True).distinct().filter(home_mc_name__isnull=False).exclude(home_mc_name__iexact='Greece').order_by('home_mc_name'))
        
        # Combine and deduplicate entities
        all_entities = sorted(list(set(ogx_entities + icx_entities)))
        
        return JsonResponse({
            'success': True,
            'entities': all_entities
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def e2e_mc_analytics_api(request):
    """
    API endpoint to fetch E2E MC analytics data based on date range
    """
    try:
        # Parse request body
        data = json.loads(request.body)
        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')
        
        if not start_date_str or not end_date_str:
            return JsonResponse({
                'success': False,
                'error': 'Both start_date and end_date are required'
            }, status=400)
        
        # Parse dates (DD/MM/YYYY format)
        try:
            start_date = datetime.strptime(start_date_str, '%d/%m/%Y')
            end_date = datetime.strptime(end_date_str, '%d/%m/%Y')
            
            # Set time to cover the entire day
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            # Make timezone aware
            start_date = timezone.make_aware(start_date, pytz.UTC)
            end_date = timezone.make_aware(end_date, pytz.UTC)
            
        except ValueError as e:
            return JsonResponse({
                'success': False,
                'error': f'Invalid date format. Use DD/MM/YYYY: {str(e)}'
            }, status=400)
        
        # Get E2E analytics data
        analytics_data = get_e2e_mc_analytics_data(start_date, end_date)
        
        return JsonResponse({
            'success': True,
            'data': analytics_data
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }, status=500)

def get_e2e_mc_analytics_data(start_date, end_date):
    """
    Get E2E analytics data for the specified date range
    """
    # Get all MCs from the database (both opportunity and person home MCs) - excluding Greece
    ogx_entities = list(ExpaApplication.objects.values_list('home_mc_name_opportunity', flat=True).distinct().filter(home_mc_name_opportunity__isnull=False).exclude(home_mc_name_opportunity__iexact='Greece').order_by('home_mc_name_opportunity'))
    icx_entities = list(ExpaApplication.objects.values_list('home_mc_name', flat=True).distinct().filter(home_mc_name__isnull=False).exclude(home_mc_name__iexact='Greece').order_by('home_mc_name'))
    
    # Combine and deduplicate entities
    all_entities = sorted(list(set(ogx_entities + icx_entities)))
    
    # Filter applications by date range
    applications = ExpaApplication.objects.filter(
        created_at__range=(start_date, end_date)
    )
    
    # Initialize data structure
    analytics_data = {
        'entities': all_entities,
        'ogv': get_e2e_funnel_data(applications, 7, 'home_mc_name_opportunity', 'home_lc_name_opportunity'),
        'ogta': get_e2e_funnel_data(applications, 8, 'home_mc_name_opportunity', 'home_lc_name_opportunity'),
        'ogte': get_e2e_funnel_data(applications, 9, 'home_mc_name_opportunity', 'home_lc_name_opportunity'),
        'igv': get_e2e_funnel_data(applications, 7, 'home_mc_name', 'home_lc_name'),
        'igta': get_e2e_funnel_data(applications, 8, 'home_mc_name', 'home_lc_name')
    }
    
    return analytics_data

def get_e2e_funnel_data(applications, programme_id, mc_field, lc_field):
    """
    Get E2E funnel data for a specific programme
    programme_id: programme ID to filter by (7=OGV/IGV, 8=OGTa/IGTa, 9=OGTe)
    mc_field: field to use for filtering by MC (home_mc_name_opportunity or home_mc_name)
    lc_field: field to use for counting by LC (home_lc_name_opportunity or home_lc_name)
    
    Returns data structure: {mc_name: {lc_name: {funnel_counts}}}
    """
    # Filter by programme ID and exclude Greece
    programme_apps = applications.filter(programme_id=programme_id).exclude(**{f'{mc_field}__iexact': 'Greece'})
    
    # Get all unique MCs for this programme (excluding Greece)
    mcs = list(programme_apps.values_list(mc_field, flat=True).distinct().filter(**{f'{mc_field}__isnull': False}).order_by(mc_field))
    
    data = {}
    
    for mc in mcs:
        # Filter applications by MC
        mc_apps = programme_apps.filter(**{mc_field: mc})
        
        # Get all LCs belonging to this MC
        lcs = list(mc_apps.values_list(lc_field, flat=True).distinct().filter(**{f'{lc_field}__isnull': False}).order_by(lc_field))
        
        data[mc] = {}
        
        for lc in lcs:
            # Filter applications by LC
            lc_apps = mc_apps.filter(**{lc_field: lc})
            
            # Count funnel stages based on current status
            applied_count = lc_apps.count()
            
            # Count applications that have reached each stage
            data[mc][lc] = {
                'applied': applied_count,
                'accepted': lc_apps.filter(status__in=['accepted', 'approved', 'realized', 'finished', 'completed']).count(),
                'approved': lc_apps.filter(status__in=['approved', 'realized', 'finished', 'completed']).count(),
                'realized': lc_apps.filter(status__in=['realized', 'finished', 'completed']).count(),
                'finished': lc_apps.filter(status__in=['finished', 'completed']).count(),
                'completed': lc_apps.filter(status='completed').count(),
                'total': applied_count
            }
    
    return data






#LC Athens E2E

@csrf_exempt
@require_http_methods(["POST"])
def e2e_LC_Athens_analytics_api(request):
    """
    API endpoint to fetch E2E LC Athens analytics data based on date range
    """
    try:
        # Parse request body
        data = json.loads(request.body)
        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')
        
        if not start_date_str or not end_date_str:
            return JsonResponse({
                'success': False,
                'error': 'Both start_date and end_date are required'
            }, status=400)
        
        # Parse dates (DD/MM/YYYY format)
        try:
            start_date = datetime.strptime(start_date_str, '%d/%m/%Y')
            end_date = datetime.strptime(end_date_str, '%d/%m/%Y')
            
            # Set time to cover the entire day
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            # Make timezone aware
            start_date = timezone.make_aware(start_date, pytz.UTC)
            end_date = timezone.make_aware(end_date, pytz.UTC)
            
        except ValueError as e:
            return JsonResponse({
                'success': False,
                'error': f'Invalid date format. Use DD/MM/YYYY: {str(e)}'
            }, status=400)
        
        # Get E2E analytics data
        analytics_data = get_e2e_LC_Athens_analytics_data(start_date, end_date)
        
        return JsonResponse({
            'success': True,
            'data': analytics_data
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }, status=500)
    

def get_e2e_LC_Athens_analytics_data(start_date, end_date):
    """
    Get E2E analytics data specifically for LC Athens
    Shows MCs that have interactions with Athens LC and their funnel data
    """
    # Filter applications by date range
    applications = ExpaApplication.objects.filter(
        created_at__range=(start_date, end_date)
    )
    
    # Get MCs that have Athens LC in their applications (OGX - person home LC)
    # For OGV, OGTa, OGTe: filter by person home LC = Athens
    ogx_entities = list(applications.filter(
        home_lc_name='ATHENS'
    ).values_list('home_mc_name_opportunity', flat=True).distinct()
    .exclude(home_mc_name_opportunity__iexact='Greece')
    .exclude(home_mc_name_opportunity__isnull=True)
    .order_by('home_mc_name_opportunity'))
    
    # Get MCs that have Athens LC in their applications (ICX - opportunity home LC)
    # For IGV, IGTa: filter by opportunity home LC = Athens
    icx_entities = list(applications.filter(
        home_lc_name_opportunity='ATHENS'
    ).values_list('home_mc_name', flat=True).distinct()
    .exclude(home_mc_name__iexact='Greece')
    .exclude(home_mc_name__isnull=True)
    .order_by('home_mc_name'))
    
    # Combine and deduplicate entities that interact with Athens
    all_entities = sorted(list(set(ogx_entities + icx_entities)))
    
    # Initialize data structure
    analytics_data = {
        'entities': all_entities,
        'lc_focus': 'ATHENS',
        'ogv': get_e2e_LC_Athens_funnel_data(applications, 7, 'home_mc_name_opportunity', 'home_lc_name_opportunity'),
        'ogta': get_e2e_LC_Athens_funnel_data(applications, 8, 'home_mc_name_opportunity', 'home_lc_name_opportunity'),
        'ogte': get_e2e_LC_Athens_funnel_data(applications, 9, 'home_mc_name_opportunity', 'home_lc_name_opportunity'),
        'igv': get_e2e_LC_Athens_funnel_data(applications, 7, 'home_mc_name', 'home_lc_name'),
        'igta': get_e2e_LC_Athens_funnel_data(applications, 8, 'home_mc_name', 'home_lc_name')
    }
    
    return analytics_data


def get_e2e_LC_Athens_funnel_data(applications, programme_id, mc_field, lc_field):
    """
    Get E2E funnel data for LC Athens - shows MCs that have Athens LC interactions
    programme_id: programme ID to filter by (7=OGV/IGV, 8=OGTa/IGTa, 9=OGTe)
    mc_field: field to use for filtering by MC (home_mc_name_opportunity or home_mc_name)
    lc_field: field to use for counting by LC (home_lc_name_opportunity or home_lc_name)
    
    Returns data structure: {mc_name: {'ATHENS': {funnel_counts}, 'other_lc': {funnel_counts}}}
    """
    # Filter by programme ID and exclude Greece MC
    programme_apps = applications.filter(programme_id=programme_id).exclude(**{f'{mc_field}__iexact': 'Greece'})
    
    # Add Athens LC filter based on programme type
    if lc_field == 'home_lc_name':  # ICX programmes (IGV, IGTa)
        # For ICX: filter by opportunity_home_lc = Athens
        programme_apps = programme_apps.filter(home_lc_name_opportunity='ATHENS')
    else:  # OGX programmes (OGV, OGTa, OGTe)
        # For OGX: filter by person_home_lc = Athens
        programme_apps = programme_apps.filter(home_lc_name='ATHENS')
    
    # Get all unique MCs that have Athens LC interactions
    mcs = list(programme_apps.values_list(mc_field, flat=True).distinct().filter(**{f'{mc_field}__isnull': False}).order_by(mc_field))
    
    data = {}
    
    for mc in mcs:
        # Filter applications by MC
        mc_apps = programme_apps.filter(**{mc_field: mc})
        
        data[mc] = {}
        
        # Always include Athens LC data (this is our focus)
        athens_apps = mc_apps.filter(**{lc_field: 'ATHENS'})
        if athens_apps.exists():
            applied_count = athens_apps.count()
            data[mc]['ATHENS'] = {
                'applied': applied_count,
                'accepted': athens_apps.filter(status__in=['accepted', 'approved', 'realized', 'finished', 'completed']).count(),
                'approved': athens_apps.filter(status__in=['approved', 'realized', 'finished', 'completed']).count(),
                'realized': athens_apps.filter(status__in=['realized', 'finished', 'completed']).count(),
                'finished': athens_apps.filter(status__in=['finished', 'completed']).count(),
                'completed': athens_apps.filter(status='completed').count(),
                'total': applied_count
            }
        
        # Include other LCs from this MC for comparison (if any exist)
        other_lcs = list(mc_apps.values_list(lc_field, flat=True).distinct().filter(**{f'{lc_field}__isnull': False}).exclude(**{f'{lc_field}__iexact': 'ATHENS'}).order_by(lc_field))
        
        for lc in other_lcs:
            # Filter applications by LC
            lc_apps = mc_apps.filter(**{lc_field: lc})
            
            # Count funnel stages based on current status
            applied_count = lc_apps.count()
            
            if applied_count > 0:  # Only include LCs with data
                data[mc][lc] = {
                    'applied': applied_count,
                    'accepted': lc_apps.filter(status__in=['accepted', 'approved', 'realized', 'finished', 'completed']).count(),
                    'approved': lc_apps.filter(status__in=['approved', 'realized', 'finished', 'completed']).count(),
                    'realized': lc_apps.filter(status__in=['realized', 'finished', 'completed']).count(),
                    'finished': lc_apps.filter(status__in=['finished', 'completed']).count(),
                    'completed': lc_apps.filter(status='completed').count(),
                    'total': applied_count
                }
    
    return data



#IE UOI E2E

@csrf_exempt
@require_http_methods(["POST"])
def e2e_IE_UOI_analytics_api(request):
    """
    API endpoint to fetch E2E IE UOI analytics data based on date range"""
    try:
        # Parse request body
        data = json.loads(request.body)
        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')
        
        if not start_date_str or not end_date_str:
            return JsonResponse({
                'success': False,
                'error': 'Both start_date and end_date are required'
            }, status=400)
        
        # Parse dates (DD/MM/YYYY format)
        try:
            start_date = datetime.strptime(start_date_str, '%d/%m/%Y')
            end_date = datetime.strptime(end_date_str, '%d/%m/%Y')
            
            # Set time to cover the entire day
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            # Make timezone aware
            start_date = timezone.make_aware(start_date, pytz.UTC)
            end_date = timezone.make_aware(end_date, pytz.UTC)
            
        except ValueError as e:
            return JsonResponse({
                'success': False,
                'error': f'Invalid date format. Use DD/MM/YYYY: {str(e)}'
            }, status=400)
        
        # Get E2E analytics data
        analytics_data = get_e2e_IE_UOI_analytics_data(start_date, end_date)
        
        return JsonResponse({
            'success': True,
            'data': analytics_data
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }, status=500)
    

def get_e2e_IE_UOI_analytics_data(start_date, end_date):
    """
    Get E2E analytics data specifically for IE UOI
    """
    # Filter applications by date range
    applications = ExpaApplication.objects.filter(
        created_at__range=(start_date, end_date)
    )
    
    # Get MCs that have UoI (EXP) in their applications (OGX - person home LC)
    # For OGV, OGTa, OGTe: filter by person home LC = UoI (EXP)
    ogx_entities = list(applications.filter(
        home_lc_name='UoI (EXP)'
    ).values_list('home_mc_name_opportunity', flat=True).distinct()
    .exclude(home_mc_name_opportunity__iexact='Greece')
    .exclude(home_mc_name_opportunity__isnull=True)
    .order_by('home_mc_name_opportunity'))
    
    # Get MCs that have 	UoI (EXP) in their applications (ICX - opportunity home LC)
    # For IGV, IGTa: filter by opportunity home LC = UoI (EXP)
    icx_entities = list(applications.filter(
        home_lc_name_opportunity='UoI (EXP)'
    ).values_list('home_mc_name', flat=True).distinct()
    .exclude(home_mc_name__iexact='Greece')
    .exclude(home_mc_name__isnull=True)
    .order_by('home_mc_name'))
    
    all_entities = sorted(list(set(ogx_entities + icx_entities)))
    
    # Initialize data structure
    analytics_data = {
        'entities': all_entities,
        'lc_focus': 'UoI (EXP)',
        'ogv': get_e2e_IE_UOI_funnel_data(applications, 7, 'home_mc_name_opportunity', 'home_lc_name_opportunity'),
        'ogta': get_e2e_IE_UOI_funnel_data(applications, 8, 'home_mc_name_opportunity', 'home_lc_name_opportunity'),
        'ogte': get_e2e_IE_UOI_funnel_data(applications, 9, 'home_mc_name_opportunity', 'home_lc_name_opportunity'),
        'igv': get_e2e_IE_UOI_funnel_data(applications, 7, 'home_mc_name', 'home_lc_name'),
        'igta': get_e2e_IE_UOI_funnel_data(applications, 8, 'home_mc_name', 'home_lc_name')
    }
    
    return analytics_data


def get_e2e_IE_UOI_funnel_data(applications, programme_id, mc_field, lc_field):
    
    # Filter by programme ID and exclude Greece MC
    programme_apps = applications.filter(programme_id=programme_id).exclude(**{f'{mc_field}__iexact': 'Greece'})
    
    if lc_field == 'home_lc_name':  # ICX programmes (IGV, IGTa)
        # For ICX: filter by opportunity_home_lc = UoI (EXP)
        programme_apps = programme_apps.filter(home_lc_name_opportunity='UoI (EXP)')
    else:  # OGX programmes (OGV, OGTa, OGTe)
        # For OGX: filter by person_home_lc = UoI (EXP)
        programme_apps = programme_apps.filter(home_lc_name='UoI (EXP)')

    # Get all unique MCs that have UoI (EXP) LC interactions
    mcs = list(programme_apps.values_list(mc_field, flat=True).distinct().filter(**{f'{mc_field}__isnull': False}).order_by(mc_field))
    
    data = {}
    
    for mc in mcs:
        # Filter applications by MC
        mc_apps = programme_apps.filter(**{mc_field: mc})
        
        data[mc] = {}

        # Always include UoI (EXP) LC data (this is our focus)
        ie_uoi_apps = mc_apps.filter(**{lc_field: 'UoI (EXP)'})
        if ie_uoi_apps.exists():
            applied_count = ie_uoi_apps.count()
            data[mc]['UoI (EXP)'] = {
                'applied': applied_count,
                'accepted': ie_uoi_apps.filter(status__in=['accepted', 'approved', 'realized', 'finished', 'completed']).count(),
                'approved': ie_uoi_apps.filter(status__in=['approved', 'realized', 'finished', 'completed']).count(),
                'realized': ie_uoi_apps.filter(status__in=['realized', 'finished', 'completed']).count(),
                'finished': ie_uoi_apps.filter(status__in=['finished', 'completed']).count(),
                'completed': ie_uoi_apps.filter(status='completed').count(),
                'total': applied_count
            }
        
        # Include other LCs from this MC for comparison (if any exist)
        other_lcs = list(mc_apps.values_list(lc_field, flat=True).distinct().filter(**{f'{lc_field}__isnull': False}).exclude(**{f'{lc_field}__iexact': 'UoI (EXP)'}).order_by(lc_field))
        
        for lc in other_lcs:
            # Filter applications by LC
            lc_apps = mc_apps.filter(**{lc_field: lc})
            
            # Count funnel stages based on current status
            applied_count = lc_apps.count()
            
            if applied_count > 0:  # Only include LCs with data
                data[mc][lc] = {
                    'applied': applied_count,
                    'accepted': lc_apps.filter(status__in=['accepted', 'approved', 'realized', 'finished', 'completed']).count(),
                    'approved': lc_apps.filter(status__in=['approved', 'realized', 'finished', 'completed']).count(),
                    'realized': lc_apps.filter(status__in=['realized', 'finished', 'completed']).count(),
                    'finished': lc_apps.filter(status__in=['finished', 'completed']).count(),
                    'completed': lc_apps.filter(status='completed').count(),
                    'total': applied_count
                }
    
    return data


#IE Volos E2E

@csrf_exempt
@require_http_methods(["POST"])
def e2e_IE_Volos_analytics_api(request):
    """
    API endpoint to fetch E2E IE Volos analytics data based on date range"""
    try:
        # Parse request body
        data = json.loads(request.body)
        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')
        
        if not start_date_str or not end_date_str:
            return JsonResponse({
                'success': False,
                'error': 'Both start_date and end_date are required'
            }, status=400)
        
        # Parse dates (DD/MM/YYYY format)
        try:
            start_date = datetime.strptime(start_date_str, '%d/%m/%Y')
            end_date = datetime.strptime(end_date_str, '%d/%m/%Y')
            
            # Set time to cover the entire day
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            # Make timezone aware
            start_date = timezone.make_aware(start_date, pytz.UTC)
            end_date = timezone.make_aware(end_date, pytz.UTC)
            
        except ValueError as e:
            return JsonResponse({
                'success': False,
                'error': f'Invalid date format. Use DD/MM/YYYY: {str(e)}'
            }, status=400)
        
        # Get E2E analytics data
        analytics_data = get_e2e_IE_Volos_analytics_data(start_date, end_date)
        
        return JsonResponse({
            'success': True,
            'data': analytics_data
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }, status=500)
    

def get_e2e_IE_Volos_analytics_data(start_date, end_date):
    """
    Get E2E analytics data specifically for IE Volos
    """
    # Filter applications by date range
    applications = ExpaApplication.objects.filter(
        created_at__range=(start_date, end_date)
    )
    
    # Get MCs that have Volos (EXP) in their applications (OGX - person home LC)
    # For OGV, OGTa, OGTe: filter by person home LC = Volos (EXP)
    ogx_entities = list(applications.filter(
        home_lc_name='Volos (EXP)'
    ).values_list('home_mc_name_opportunity', flat=True).distinct()
    .exclude(home_mc_name_opportunity__iexact='Greece')
    .exclude(home_mc_name_opportunity__isnull=True)
    .order_by('home_mc_name_opportunity'))

    # Get MCs that have Volos (EXP) in their applications (ICX - opportunity home LC)
    # For IGV, IGTa: filter by opportunity home LC = Volos (EXP)
    icx_entities = list(applications.filter(
        home_lc_name_opportunity='Volos (EXP)'
    ).values_list('home_mc_name', flat=True).distinct()
    .exclude(home_mc_name__iexact='Greece')
    .exclude(home_mc_name__isnull=True)
    .order_by('home_mc_name'))
    
    all_entities = sorted(list(set(ogx_entities + icx_entities)))
    
    # Initialize data structure
    analytics_data = {
        'entities': all_entities,
        'lc_focus': 'Volos (EXP)',
        'ogv': get_e2e_IE_Volos_funnel_data(applications, 7, 'home_mc_name_opportunity', 'home_lc_name_opportunity'),
        'ogta': get_e2e_IE_Volos_funnel_data(applications, 8, 'home_mc_name_opportunity', 'home_lc_name_opportunity'),
        'ogte': get_e2e_IE_Volos_funnel_data(applications, 9, 'home_mc_name_opportunity', 'home_lc_name_opportunity'),
        'igv': get_e2e_IE_Volos_funnel_data(applications, 7, 'home_mc_name', 'home_lc_name'),
        'igta': get_e2e_IE_Volos_funnel_data(applications, 8, 'home_mc_name', 'home_lc_name')
    }
    
    return analytics_data


def get_e2e_IE_Volos_funnel_data(applications, programme_id, mc_field, lc_field):
    
    # Filter by programme ID and exclude Greece MC
    programme_apps = applications.filter(programme_id=programme_id).exclude(**{f'{mc_field}__iexact': 'Greece'})
    
    if lc_field == 'home_lc_name':  # ICX programmes (IGV, IGTa)
        # For ICX: filter by opportunity_home_lc = Volos (EXP)
        programme_apps = programme_apps.filter(home_lc_name_opportunity='Volos (EXP)')
    else:  # OGX programmes (OGV, OGTa, OGTe)
        # For OGX: filter by person_home_lc = Volos (EXP)
        programme_apps = programme_apps.filter(home_lc_name='Volos (EXP)')

    # Get all unique MCs that have Volos (EXP) LC interactions
    mcs = list(programme_apps.values_list(mc_field, flat=True).distinct().filter(**{f'{mc_field}__isnull': False}).order_by(mc_field))
    
    data = {}
    
    for mc in mcs:
        # Filter applications by MC
        mc_apps = programme_apps.filter(**{mc_field: mc})
        
        data[mc] = {}

        # Always include Volos (EXP) LC data (this is our focus)
        ie_volos_apps = mc_apps.filter(**{lc_field: 'Volos (EXP)'})
        if ie_volos_apps.exists():
            applied_count = ie_volos_apps.count()
            data[mc]['Volos (EXP)'] = {
                'applied': applied_count,
                'accepted': ie_volos_apps.filter(status__in=['accepted', 'approved', 'realized', 'finished', 'completed']).count(),
                'approved': ie_volos_apps.filter(status__in=['approved', 'realized', 'finished', 'completed']).count(),
                'realized': ie_volos_apps.filter(status__in=['realized', 'finished', 'completed']).count(),
                'finished': ie_volos_apps.filter(status__in=['finished', 'completed']).count(),
                'completed': ie_volos_apps.filter(status='completed').count(),
                'total': applied_count
            }
        
        # Include other LCs from this MC for comparison (if any exist)
        other_lcs = list(mc_apps.values_list(lc_field, flat=True).distinct().filter(**{f'{lc_field}__isnull': False}).exclude(**{f'{lc_field}__iexact': 'Volos (EXP)'}).order_by(lc_field))
        
        for lc in other_lcs:
            # Filter applications by LC
            lc_apps = mc_apps.filter(**{lc_field: lc})
            
            # Count funnel stages based on current status
            applied_count = lc_apps.count()
            
            if applied_count > 0:  # Only include LCs with data
                data[mc][lc] = {
                    'applied': applied_count,
                    'accepted': lc_apps.filter(status__in=['accepted', 'approved', 'realized', 'finished', 'completed']).count(),
                    'approved': lc_apps.filter(status__in=['approved', 'realized', 'finished', 'completed']).count(),
                    'realized': lc_apps.filter(status__in=['realized', 'finished', 'completed']).count(),
                    'finished': lc_apps.filter(status__in=['finished', 'completed']).count(),
                    'completed': lc_apps.filter(status='completed').count(),
                    'total': applied_count
                }
    
    return data







#LC Auth E2E

@csrf_exempt
@require_http_methods(["POST"])
def e2e_LC_Auth_analytics_api(request):
    """
    API endpoint to fetch E2E LC Auth analytics data based on date range
    """
    try:
        # Parse request body
        data = json.loads(request.body)
        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')
        
        if not start_date_str or not end_date_str:
            return JsonResponse({
                'success': False,
                'error': 'Both start_date and end_date are required'
            }, status=400)
        
        # Parse dates (DD/MM/YYYY format)
        try:
            start_date = datetime.strptime(start_date_str, '%d/%m/%Y')
            end_date = datetime.strptime(end_date_str, '%d/%m/%Y')
            
            # Set time to cover the entire day
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            # Make timezone aware
            start_date = timezone.make_aware(start_date, pytz.UTC)
            end_date = timezone.make_aware(end_date, pytz.UTC)
            
        except ValueError as e:
            return JsonResponse({
                'success': False,
                'error': f'Invalid date format. Use DD/MM/YYYY: {str(e)}'
            }, status=400)
        
        # Get E2E analytics data
        analytics_data = get_e2e_LC_Auth_analytics_data(start_date, end_date)
        
        return JsonResponse({
            'success': True,
            'data': analytics_data
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }, status=500)
    

def get_e2e_LC_Auth_analytics_data(start_date, end_date):
    """
    Get E2E analytics data specifically for LC Auth
    Shows MCs that have interactions with Auth LC and their funnel data
    """
    # Filter applications by date range
    applications = ExpaApplication.objects.filter(
        created_at__range=(start_date, end_date)
    )

    # Get MCs that have Auth LC in their applications (OGX - person home LC)
    # For OGV, OGTa, OGTe: filter by person home LC = Auth
    ogx_entities = list(applications.filter(
        home_lc_name='AUTH'
    ).values_list('home_mc_name_opportunity', flat=True).distinct()
    .exclude(home_mc_name_opportunity__iexact='Greece')
    .exclude(home_mc_name_opportunity__isnull=True)
    .order_by('home_mc_name_opportunity'))

    # Get MCs that have Auth LC in their applications (ICX - opportunity home LC)
    # For IGV, IGTa: filter by opportunity home LC = Auth
    icx_entities = list(applications.filter(
        home_lc_name_opportunity='AUTH'
    ).values_list('home_mc_name', flat=True).distinct()
    .exclude(home_mc_name__iexact='Greece')
    .exclude(home_mc_name__isnull=True)
    .order_by('home_mc_name'))

    # Combine and deduplicate entities that interact with Auth
    all_entities = sorted(list(set(ogx_entities + icx_entities)))
    
    # Initialize data structure
    analytics_data = {
        'entities': all_entities,
        'lc_focus': 'AUTH',
        'ogv': get_e2e_LC_Auth_funnel_data(applications, 7, 'home_mc_name_opportunity', 'home_lc_name_opportunity'),
        'ogta': get_e2e_LC_Auth_funnel_data(applications, 8, 'home_mc_name_opportunity', 'home_lc_name_opportunity'),
        'ogte': get_e2e_LC_Auth_funnel_data(applications, 9, 'home_mc_name_opportunity', 'home_lc_name_opportunity'),
        'igv': get_e2e_LC_Auth_funnel_data(applications, 7, 'home_mc_name', 'home_lc_name'),
        'igta': get_e2e_LC_Auth_funnel_data(applications, 8, 'home_mc_name', 'home_lc_name')
    }
    
    return analytics_data


def get_e2e_LC_Auth_funnel_data(applications, programme_id, mc_field, lc_field):
    """
    Get E2E funnel data for LC Auth - shows MCs that have Auth LC interactions
    programme_id: programme ID to filter by (7=OGV/IGV, 8=OGTa/IGTa, 9=OGTe)
    mc_field: field to use for filtering by MC (home_mc_name_opportunity or home_mc_name)
    lc_field: field to use for counting by LC (home_lc_name_opportunity or home_lc_name)

    Returns data structure: {mc_name: {'AUTH': {funnel_counts}, 'other_lc': {funnel_counts}}}
    """
    # Filter by programme ID and exclude Greece MC
    programme_apps = applications.filter(programme_id=programme_id).exclude(**{f'{mc_field}__iexact': 'Greece'})

    # Add Auth LC filter based on programme type
    if lc_field == 'home_lc_name':  # ICX programmes (IGV, IGTa)
        # For ICX: filter by opportunity_home_lc = Auth
        programme_apps = programme_apps.filter(home_lc_name_opportunity='AUTH')
    else:  # OGX programmes (OGV, OGTa, OGTe)
        # For OGX: filter by person_home_lc = Auth
        programme_apps = programme_apps.filter(home_lc_name='AUTH')

    # Get all unique MCs that have Auth LC interactions
    mcs = list(programme_apps.values_list(mc_field, flat=True).distinct().filter(**{f'{mc_field}__isnull': False}).order_by(mc_field))
    
    data = {}
    
    for mc in mcs:
        # Filter applications by MC
        mc_apps = programme_apps.filter(**{mc_field: mc})
        
        data[mc] = {}
        
        # Always include Auth LC data (this is our focus)
        auth_apps = mc_apps.filter(**{lc_field: 'AUTH'})
        if auth_apps.exists():
            applied_count = auth_apps.count()
            data[mc]['AUTH'] = {
                'applied': applied_count,
                'accepted': auth_apps.filter(status__in=['accepted', 'approved', 'realized', 'finished', 'completed']).count(),
                'approved': auth_apps.filter(status__in=['approved', 'realized', 'finished', 'completed']).count(),
                'realized': auth_apps.filter(status__in=['realized', 'finished', 'completed']).count(),
                'finished': auth_apps.filter(status__in=['finished', 'completed']).count(),
                'completed': auth_apps.filter(status='completed').count(),
                'total': applied_count
            }
        
        # Include other LCs from this MC for comparison (if any exist)
        other_lcs = list(mc_apps.values_list(lc_field, flat=True).distinct().filter(**{f'{lc_field}__isnull': False}).exclude(**{f'{lc_field}__iexact': 'AUTH'}).order_by(lc_field))
        
        for lc in other_lcs:
            # Filter applications by LC
            lc_apps = mc_apps.filter(**{lc_field: lc})
            
            # Count funnel stages based on current status
            applied_count = lc_apps.count()
            
            if applied_count > 0:  # Only include LCs with data
                data[mc][lc] = {
                    'applied': applied_count,
                    'accepted': lc_apps.filter(status__in=['accepted', 'approved', 'realized', 'finished', 'completed']).count(),
                    'approved': lc_apps.filter(status__in=['approved', 'realized', 'finished', 'completed']).count(),
                    'realized': lc_apps.filter(status__in=['realized', 'finished', 'completed']).count(),
                    'finished': lc_apps.filter(status__in=['finished', 'completed']).count(),
                    'completed': lc_apps.filter(status='completed').count(),
                    'total': applied_count
                }
    
    return data

#LC Unipi E2E

@csrf_exempt
@require_http_methods(["GET"])
def LC_Unipi_entities_api(request):
    """
    API endpoint to fetch entities related to LC Unipi for E2E analytics
    Returns MCs that have interactions with Unipi LC
    """
    try:
        # Get MCs that have Unipi LC in their applications (OGX - person home LC)
        # For OGV, OGTa, OGTe: filter by person home LC = Piraeus (UniPi)
        ogx_entities = list(ExpaApplication.objects.filter(
            home_lc_name='Piraeus (UniPi)'
        ).values_list('home_mc_name_opportunity', flat=True).distinct()
        .exclude(home_mc_name_opportunity__iexact='Greece')
        .exclude(home_mc_name_opportunity__isnull=True)
        .order_by('home_mc_name_opportunity'))
        
        # Get MCs that have Unipi LC in their applications (ICX - opportunity home LC)
        # For IGV, IGTa: filter by opportunity home LC = Piraeus (UniPi)
        icx_entities = list(ExpaApplication.objects.filter(
            home_lc_name_opportunity='Piraeus (UniPi)'
        ).values_list('home_mc_name', flat=True).distinct()
        .exclude(home_mc_name__iexact='Greece')
        .exclude(home_mc_name__isnull=True)
        .order_by('home_mc_name'))
        
        # Combine and deduplicate entities that interact with Unipi
        all_entities = sorted(list(set(ogx_entities + icx_entities)))
        
        return JsonResponse({
            'success': True,
            'entities': all_entities,
            'lc_focus': 'Piraeus (UniPi)'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def e2e_LC_Unipi_analytics_api(request):
    """
    API endpoint to fetch E2E LC Unipi analytics data based on date range
    """
    try:
        # Parse request body
        data = json.loads(request.body)
        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')
        
        if not start_date_str or not end_date_str:
            return JsonResponse({
                'success': False,
                'error': 'Both start_date and end_date are required'
            }, status=400)
        
        # Parse dates (DD/MM/YYYY format)
        try:
            start_date = datetime.strptime(start_date_str, '%d/%m/%Y')
            end_date = datetime.strptime(end_date_str, '%d/%m/%Y')
            
            # Set time to cover the entire day
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            # Make timezone aware
            start_date = timezone.make_aware(start_date, pytz.UTC)
            end_date = timezone.make_aware(end_date, pytz.UTC)
            
        except ValueError as e:
            return JsonResponse({
                'success': False,
                'error': f'Invalid date format. Use DD/MM/YYYY: {str(e)}'
            }, status=400)
        
        # Get E2E analytics data
        analytics_data = get_e2e_LC_Unipi_analytics_data(start_date, end_date)
        
        return JsonResponse({
            'success': True,
            'data': analytics_data
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }, status=500)
    

def get_e2e_LC_Unipi_analytics_data(start_date, end_date):
    """
    Get E2E analytics data specifically for LC Unipi
    Shows MCs that have interactions with Unipi LC and their funnel data
    """
    # Filter applications by date range
    applications = ExpaApplication.objects.filter(
        created_at__range=(start_date, end_date)
    )

    # Get MCs that have Unipi LC in their applications (OGX - person home LC)
    # For OGV, OGTa, OGTe: filter by person home LC = Unipi
    ogx_entities = list(applications.filter(
        home_lc_name='Piraeus (UniPi)'
    ).values_list('home_mc_name_opportunity', flat=True).distinct()
    .exclude(home_mc_name_opportunity__iexact='Greece')
    .exclude(home_mc_name_opportunity__isnull=True)
    .order_by('home_mc_name_opportunity'))

    # Get MCs that have Unipi LC in their applications (ICX - opportunity home LC)
    # For IGV, IGTa: filter by opportunity home LC = unipi
    icx_entities = list(applications.filter(
        home_lc_name_opportunity='Piraeus (UniPi)'
    ).values_list('home_mc_name', flat=True).distinct()
    .exclude(home_mc_name__iexact='Greece')
    .exclude(home_mc_name__isnull=True)
    .order_by('home_mc_name'))

    # Combine and deduplicate entities that interact with Unipi
    all_entities = sorted(list(set(ogx_entities + icx_entities)))
    
    # Initialize data structure
    analytics_data = {
        'entities': all_entities,
        'lc_focus': 'Piraeus (UniPi)',
        'ogv': get_e2e_LC_Unipi_funnel_data(applications, 7, 'home_mc_name_opportunity', 'home_lc_name_opportunity'),
        'ogta': get_e2e_LC_Unipi_funnel_data(applications, 8, 'home_mc_name_opportunity', 'home_lc_name_opportunity'),
        'ogte': get_e2e_LC_Unipi_funnel_data(applications, 9, 'home_mc_name_opportunity', 'home_lc_name_opportunity'),
        'igv': get_e2e_LC_Unipi_funnel_data(applications, 7, 'home_mc_name', 'home_lc_name'),
        'igta': get_e2e_LC_Unipi_funnel_data(applications, 8, 'home_mc_name', 'home_lc_name')
    }
    
    return analytics_data


def get_e2e_LC_Unipi_funnel_data(applications, programme_id, mc_field, lc_field):
    """
    Get E2E funnel data for LC Unipi - shows MCs that have Unipi LC interactions
    programme_id: programme ID to filter by (7=OGV/IGV, 8=OGTa/IGTa, 9=OGTe)
    mc_field: field to use for filtering by MC (home_mc_name_opportunity or home_mc_name)
    lc_field: field to use for counting by LC (home_lc_name_opportunity or home_lc_name)

    Returns data structure: {mc_name: {'Piraeus (UniPi)': {funnel_counts}, 'other_lc': {funnel_counts}}}
    """
    # Filter by programme ID and exclude Greece MC
    programme_apps = applications.filter(programme_id=programme_id).exclude(**{f'{mc_field}__iexact': 'Greece'})

    # Add Unipi LC filter based on programme type
    if lc_field == 'home_lc_name':  # ICX programmes (IGV, IGTa)
        # For ICX: filter by opportunity_home_lc = Unipi
        programme_apps = programme_apps.filter(home_lc_name_opportunity='Piraeus (UniPi)')
    else:  # OGX programmes (OGV, OGTa, OGTe)
        # For OGX: filter by person_home_lc = Unipi
        programme_apps = programme_apps.filter(home_lc_name='Piraeus (UniPi)')

    # Get all unique MCs that have Unipi LC interactions
    mcs = list(programme_apps.values_list(mc_field, flat=True).distinct().filter(**{f'{mc_field}__isnull': False}).order_by(mc_field))
    
    data = {}
    
    for mc in mcs:
        # Filter applications by MC
        mc_apps = programme_apps.filter(**{mc_field: mc})
        
        data[mc] = {}
        
        # Always include Unipi LC data (this is our focus)
        unipi_apps = mc_apps.filter(**{lc_field: 'Piraeus (UniPi)'})
        if unipi_apps.exists():
            applied_count = unipi_apps.count()
            data[mc]['Piraeus (UniPi)'] = {
                'applied': applied_count,
                'accepted': unipi_apps.filter(status__in=['accepted', 'approved', 'realized', 'finished', 'completed']).count(),
                'approved': unipi_apps.filter(status__in=['approved', 'realized', 'finished', 'completed']).count(),
                'realized': unipi_apps.filter(status__in=['realized', 'finished', 'completed']).count(),
                'finished': unipi_apps.filter(status__in=['finished', 'completed']).count(),
                'completed': unipi_apps.filter(status='completed').count(),
                'total': applied_count
            }
        
        # Include other LCs from this MC for comparison (if any exist)
        other_lcs = list(mc_apps.values_list(lc_field, flat=True).distinct().filter(**{f'{lc_field}__isnull': False}).exclude(**{f'{lc_field}__iexact': 'Piraeus (UniPi)'}).order_by(lc_field))
        
        for lc in other_lcs:
            # Filter applications by LC
            lc_apps = mc_apps.filter(**{lc_field: lc})
            
            # Count funnel stages based on current status
            applied_count = lc_apps.count()
            
            if applied_count > 0:  # Only include LCs with data
                data[mc][lc] = {
                    'applied': applied_count,
                    'accepted': lc_apps.filter(status__in=['accepted', 'approved', 'realized', 'finished', 'completed']).count(),
                    'approved': lc_apps.filter(status__in=['approved', 'realized', 'finished', 'completed']).count(),
                    'realized': lc_apps.filter(status__in=['realized', 'finished', 'completed']).count(),
                    'finished': lc_apps.filter(status__in=['finished', 'completed']).count(),
                    'completed': lc_apps.filter(status='completed').count(),
                    'total': applied_count
                }
    
    return data

# LC UoM Thessaloniki E2E

@csrf_exempt
@require_http_methods(["GET"])
def LC_UoM_Thessaloniki_entities_api(request):
    """
    API endpoint to fetch entities related to LC UoM Thessaloniki for E2E analytics
    Returns MCs that have interactions with UoM Thessaloniki LC
    """
    try:
        # Get MCs that have UoM Thessaloniki LC in their applications (OGX - person home LC)
        # For OGV, OGTa, OGTe: filter by person home LC = UoM Thessaloniki
        ogx_entities = list(ExpaApplication.objects.filter(
            home_lc_name='UoM THESSALONIKI'
        ).values_list('home_mc_name_opportunity', flat=True).distinct()
        .exclude(home_mc_name_opportunity__iexact='Greece')
        .exclude(home_mc_name_opportunity__isnull=True)
        .order_by('home_mc_name_opportunity'))
        
        # Get MCs that have UoM Thessaloniki LC in their applications (ICX - opportunity home LC)
        # For IGV, IGTa: filter by opportunity home LC = UoM Thessaloniki
        icx_entities = list(ExpaApplication.objects.filter(
            home_lc_name_opportunity='UoM THESSALONIKI'
        ).values_list('home_mc_name', flat=True).distinct()
        .exclude(home_mc_name__iexact='Greece')
        .exclude(home_mc_name__isnull=True)
        .order_by('home_mc_name'))
        
        # Combine and deduplicate entities that interact with UoM Thessaloniki
        all_entities = sorted(list(set(ogx_entities + icx_entities)))
        
        return JsonResponse({
            'success': True,
            'entities': all_entities,
            'lc_focus': 'UoM THESSALONIKIi'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def e2e_LC_UoM_Thessaloniki_analytics_api(request):
    """
    API endpoint to fetch E2E LC UoM Thessaloniki analytics data based on date range
    """
    try:
        # Parse request body
        data = json.loads(request.body)
        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')
        
        if not start_date_str or not end_date_str:
            return JsonResponse({
                'success': False,
                'error': 'Both start_date and end_date are required'
            }, status=400)
        
        # Parse dates (DD/MM/YYYY format)
        try:
            start_date = datetime.strptime(start_date_str, '%d/%m/%Y')
            end_date = datetime.strptime(end_date_str, '%d/%m/%Y')
            
            # Set time to cover the entire day
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            # Make timezone aware
            start_date = timezone.make_aware(start_date, pytz.UTC)
            end_date = timezone.make_aware(end_date, pytz.UTC)
            
        except ValueError as e:
            return JsonResponse({
                'success': False,
                'error': f'Invalid date format. Use DD/MM/YYYY: {str(e)}'
            }, status=400)
        
        # Get E2E analytics data
        analytics_data = get_e2e_LC_UoM_Thessaloniki_analytics_data(start_date, end_date)
        
        return JsonResponse({
            'success': True,
            'data': analytics_data
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }, status=500)
    

def get_e2e_LC_UoM_Thessaloniki_analytics_data(start_date, end_date):
    """
    Get E2E analytics data specifically for LC UoM Thessaloniki
    Shows MCs that have interactions with UoM Thessaloniki and their funnel data
    """
    # Filter applications by date range
    applications = ExpaApplication.objects.filter(
        created_at__range=(start_date, end_date)
    )

    # Get MCs that have UoM Thessaloniki in their applications (OGX - person home LC)
    # For OGV, OGTa, OGTe: filter by person home LC = UoM Thessaloniki
    ogx_entities = list(applications.filter(
        home_lc_name='UoM THESSALONIKI'
    ).values_list('home_mc_name_opportunity', flat=True).distinct()
    .exclude(home_mc_name_opportunity__iexact='Greece')
    .exclude(home_mc_name_opportunity__isnull=True)
    .order_by('home_mc_name_opportunity'))

    # Get MCs that have UoM Thessaloniki in their applications (ICX - opportunity home LC)
    # For IGV, IGTa: filter by opportunity home LC = UoM Thessaloniki
    icx_entities = list(applications.filter(
        home_lc_name_opportunity='UoM THESSALONIKI'
    ).values_list('home_mc_name', flat=True).distinct()
    .exclude(home_mc_name__iexact='Greece')
    .exclude(home_mc_name__isnull=True)
    .order_by('home_mc_name'))

    # Combine and deduplicate entities that interact with UoM Thessaloniki
    all_entities = sorted(list(set(ogx_entities + icx_entities)))
    
    # Initialize data structure
    analytics_data = {
        'entities': all_entities,
        'lc_focus': 'UoM THESSALONIKI',
        'ogv': get_e2e_LC_UoM_Thessaloniki_funnel_data(applications, 7, 'home_mc_name_opportunity', 'home_lc_name_opportunity'),
        'ogta': get_e2e_LC_UoM_Thessaloniki_funnel_data(applications, 8, 'home_mc_name_opportunity', 'home_lc_name_opportunity'),
        'ogte': get_e2e_LC_UoM_Thessaloniki_funnel_data(applications, 9, 'home_mc_name_opportunity', 'home_lc_name_opportunity'),
        'igv': get_e2e_LC_UoM_Thessaloniki_funnel_data(applications, 7, 'home_mc_name', 'home_lc_name'),
        'igta': get_e2e_LC_UoM_Thessaloniki_funnel_data(applications, 8, 'home_mc_name', 'home_lc_name')
    }
    
    return analytics_data


def get_e2e_LC_UoM_Thessaloniki_funnel_data(applications, programme_id, mc_field, lc_field):
    """
    Get E2E funnel data for LC UoM Thessaloniki - shows MCs that have UoM Thessaloniki interactions
    programme_id: programme ID to filter by (7=OGV/IGV, 8=OGTa/IGTa, 9=OGTe)
    mc_field: field to use for filtering by MC (home_mc_name_opportunity or home_mc_name)
    lc_field: field to use for counting by LC (home_lc_name_opportunity or home_lc_name)

    Returns data structure: {mc_name: {'UoM Thessaloniki': {funnel_counts}, 'other_lc': {funnel_counts}}}
    """
    # Filter by programme ID and exclude Greece MC
    programme_apps = applications.filter(programme_id=programme_id).exclude(**{f'{mc_field}__iexact': 'Greece'})

    # Add UoM Thessaloniki LC filter based on programme type
    if lc_field == 'home_lc_name':  # ICX programmes (IGV, IGTa)
        # For ICX: filter by opportunity_home_lc = UoM Thessaloniki
        programme_apps = programme_apps.filter(home_lc_name_opportunity='UoM THESSALONIKI')
    else:  # OGX programmes (OGV, OGTa, OGTe)
        # For OGX: filter by person_home_lc = UoM Thessaloniki
        programme_apps = programme_apps.filter(home_lc_name='UoM THESSALONIKI')

    # Get all unique MCs that have UoM Thessaloniki interactions
    mcs = list(programme_apps.values_list(mc_field, flat=True).distinct().filter(**{f'{mc_field}__isnull': False}).order_by(mc_field))
    
    data = {}
    
    for mc in mcs:
        # Filter applications by MC
        mc_apps = programme_apps.filter(**{mc_field: mc})
        
        data[mc] = {}
        
        # Always include UoM Thessaloniki LC data (this is our focus)
        uom_apps = mc_apps.filter(**{lc_field: 'UoM THESSALONIKI'})
        if uom_apps.exists():
            applied_count = uom_apps.count()
            data[mc]['UoM THESSALONIKI'] = {
                'applied': applied_count,
                'accepted': uom_apps.filter(status__in=['accepted', 'approved', 'realized', 'finished', 'completed']).count(),
                'approved': uom_apps.filter(status__in=['approved', 'realized', 'finished', 'completed']).count(),
                'realized': uom_apps.filter(status__in=['realized', 'finished', 'completed']).count(),
                'finished': uom_apps.filter(status__in=['finished', 'completed']).count(),
                'completed': uom_apps.filter(status='completed').count(),
                'total': applied_count
            }
        
        # Include other LCs from this MC for comparison (if any exist)
        other_lcs = list(mc_apps.values_list(lc_field, flat=True).distinct().filter(**{f'{lc_field}__isnull': False}).exclude(**{f'{lc_field}__iexact': 'UoM THESSALONIKI'}).order_by(lc_field))

        for lc in other_lcs:
            # Filter applications by LC
            lc_apps = mc_apps.filter(**{lc_field: lc})
            
            # Count funnel stages based on current status
            applied_count = lc_apps.count()
            
            if applied_count > 0:  # Only include LCs with data
                data[mc][lc] = {
                    'applied': applied_count,
                    'accepted': lc_apps.filter(status__in=['accepted', 'approved', 'realized', 'finished', 'completed']).count(),
                    'approved': lc_apps.filter(status__in=['approved', 'realized', 'finished', 'completed']).count(),
                    'realized': lc_apps.filter(status__in=['realized', 'finished', 'completed']).count(),
                    'finished': lc_apps.filter(status__in=['finished', 'completed']).count(),
                    'completed': lc_apps.filter(status='completed').count(),
                    'total': applied_count
                }
    
    return data