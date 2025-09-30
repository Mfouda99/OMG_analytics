import requests
import json
from django.http import JsonResponse
from .models import ExpaApplication, SignupPerson ,Opportunity  
from django.shortcuts import render
from django.db.models import Count, Q, F, Sum
from django.db.models.functions import TruncMonth
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.csrf import csrf_exempt
import requests
import threading
import time
import logging
from django.conf import settings



# Sync EXPA data (applications)
def sync_expa_data(request):
    url = "https://gis-api.aiesec.org/graphql"

    headers = {
        "Authorization": "qqco7qaP3EE8r5mTL679u2S5RGed7kYinrqN6NpzQeY",  # Use your token
        "Content-Type": "application/json"
    }

    # Updated GraphQL query with date filters
    query = """
    query {
      allOpportunityApplication(
        page: 1,
        per_page: 5000,
        filters: {
          created_at: {
            from: "2025-09-01"
          }
        }
      ) {
        data {
          id
          status
          current_status
          created_at
          date_matched       
          date_approved      
          date_realized      
          experience_end_date
          person {
            id
            full_name
            email
            created_at
            profile_photo
            home_lc {
              id
              name
            }
            home_mc {
              id
              name
            }
          }
          opportunity {
            id
            title
            duration
            earliest_start_date
            latest_end_date
            programme {
              id
              short_name
            }
            home_lc {
              id
              name
            }
            home_mc {
              id
              name
            }
            host_lc {
              id
              name
            }
          }
        }
      }
    }
    """

    response = requests.post(url, json={'query': query}, headers=headers)

    if response.status_code == 200:
        data = response.json()
        print("Response Data:", data)
        applications = data.get('data', {}).get('allOpportunityApplication', {}).get('data', [])

        for app in applications:
            print("Processing Application:", app)

            # Parse dates safely, set to None if not present
            created_at = None
            experience_end_date = None
            date_matched = None
            date_approved = None
            date_realized = None

            # Parse date_matched
            if app.get('date_matched'):
                try:
                    matched_naive = datetime.fromisoformat(app['date_matched'].replace("Z", "+00:00")).date()
                    date_matched = timezone.make_aware(datetime.combine(matched_naive, datetime.min.time()))
                except Exception as e:
                    print(f"Invalid date_matched format: {app['date_matched']}, Error: {e}")
            # Parse date_approved
            if app.get('date_approved'):
                try:
                    approved_naive = datetime.fromisoformat(app['date_approved'].replace("Z", "+00:00")).date()
                    date_approved = timezone.make_aware(datetime.combine(approved_naive, datetime.min.time()))
                except Exception as e:
                    print(f"Invalid date_approved format: {app['date_approved']}, Error: {e}")
            # Parse date_realized
            if app.get('date_realized'):
                try:
                    realized_naive = datetime.fromisoformat(app['date_realized'].replace("Z", "+00:00")).date()
                    date_realized = timezone.make_aware(datetime.combine(realized_naive, datetime.min.time()))
                except Exception as e:
                    print(f"Invalid date_realized format: {app['date_realized']}, Error: {e}")
            # Parse created_at
            if app.get('created_at'):
                try:
                    created_at_naive = datetime.fromisoformat(app['created_at'].replace("Z", "+00:00")).date()
                    created_at = timezone.make_aware(datetime.combine(created_at_naive, datetime.min.time()))
                except Exception as e:
                    print(f"Invalid created_at format: {app['created_at']}, Error: {e}")
            # Parse experience_end_date
            if app.get('experience_end_date'):
                try:
                    experience_end_date_naive = datetime.fromisoformat(app['experience_end_date'].replace("Z", "+00:00")).date()
                    experience_end_date = timezone.make_aware(experience_end_date_naive)
                except Exception as e:
                    print(f"Invalid experience_end_date format: {app['experience_end_date']}, Error: {e}")

            # Update or create the application record in the database
            ExpaApplication.objects.update_or_create(
                ep_id=app['id'],
                defaults={
                    'status': app['status'],
                    'current_status': app['current_status'],
                    'created_at': created_at,
                    'signuped_at': app['person']['created_at'],
                    'experience_end_date': experience_end_date,
                    'date_matched': date_matched,
                    'date_approved': date_approved,
                    'date_realized': date_realized,
                    'full_name': app['person']['full_name'],
                    'email': app['person']['email'],
                    'profile_photo': app['person'].get('profile_photo', ''),
                    'home_lc_name': app['person']['home_lc']['name'],
                    'home_mc_name': app['person']['home_mc']['name'],
                    'opportunity_title': app['opportunity']['title'],
                    'opportunity_duration': app['opportunity']['duration'],
                    'opportunity_earliest_start_date': app['opportunity']['earliest_start_date'],
                    'opportunity_latest_end_date': app['opportunity']['latest_end_date'],
                    'programme_short_name': app['opportunity']['programme']['short_name'],
                    'programme_id': app['opportunity']['programme']['id'],
                    'home_lc_name_opportunity': app['opportunity']['home_lc']['name'],
                    'home_mc_name_opportunity': app['opportunity']['home_mc']['name'],
                    'host_lc_name': app['opportunity']['host_lc']['name'] if app['opportunity'].get('host_lc') else ''
                }
            )

            print(f"Inserted/Updated: {app['id']}")

        return JsonResponse({"status": "Data synced successfully"})
    else:
        return JsonResponse({"error": "Failed to fetch data from EXPA", "details": response.text})


# Funnel Dashboard (for tracking status counts)

# Sync Signup People
def sync_signup_people(request):
    url = "https://gis-api.aiesec.org/graphql"
    headers = {
        "Authorization": "qqco7qaP3EE8r5mTL679u2S5RGed7kYinrqN6NpzQeY",  # Use your token
        "Content-Type": "application/json"
    }

    query = """
query {
  people
    (page: 1,
    per_page:5000,
      filters: {
          registered: {
            from: "2025-09-01"
          }
          }
            ){
    data {
      id
      full_name
      email
      created_at
      profile_photo
      home_lc {
        id
        name
      }
      home_mc {
        id
        name
      }
      person_profile {
        selected_programmes
      }
    }
  }
}
"""

    response = requests.post(url, json={'query': query}, headers=headers)
    print("Status Code:", response.status_code)
    print("Response Text:", response.text)

    if response.status_code == 200:
        people = response.json().get("data", {}).get("people", {}).get("data", [])
        print("Fetched People:", people)

        for person in people:
            created_at = None
            try:
                 if person.get('created_at'):
                    created_at = parse_datetime(person['created_at'])  # This handles timezone too
            except Exception as e:

             print(f"[ERROR] Could not parse created_at for person ID {person['id']}: {e}")

            # Handle person_profile safely
            person_profile = person.get('person_profile') or {}
            selected_programmes = person_profile.get('selected_programmes') or []
            
            SignupPerson.objects.update_or_create(
                ep_id=person['id'],
                defaults={
                    'full_name': person['full_name'],
                    'email': person['email'],
                    'created_at': created_at,
                    'profile_photo': person.get('profile_photo'),
                    'home_lc_name': person['home_lc']['name'] if person.get('home_lc') else '',
                    'home_mc_name': person['home_mc']['name'] if person.get('home_mc') else '',
                    'selected_programmes': ", ".join(str(programme) for programme in selected_programmes)
                }
            )

        return JsonResponse({"status": "Signup people synced successfully"})
    else:
        return JsonResponse({"error": "Failed to fetch signup people", "details": response.text})
     




def parse_date(date_str):
    if not date_str:
        return None
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return timezone.make_aware(dt)
    except Exception as e:
        print(f"Date parsing error: {e}")
        return None










# Timeline Methods

def format_timeline_data(applications, signups, programme_id):
    """Helper function to format timeline data"""
    timeline = defaultdict(lambda: {"SU": 0, "APP": 0, "ACC": 0, "APD": 0, "REA": 0})

    for item in signups:
        month = item["month"].strftime("%Y-%m")
        timeline[month]["SU"] = item["count"]

    for ep in applications:
        if ep.created_at:
            month = ep.created_at.strftime("%Y-%m")
            timeline[month]["APP"] += 1
        if ep.date_matched:
            month = ep.date_matched.strftime("%Y-%m")
            timeline[month]["ACC"] += 1
        if ep.date_approved:
            month = ep.date_approved.strftime("%Y-%m")
            timeline[month]["APD"] += 1
        if ep.date_realized:
            month = ep.date_realized.strftime("%Y-%m")
            timeline[month]["REA"] += 1

    return sorted([
        {
            "date": month,
            "SU": data["SU"],
            "APP": data["APP"],
            "ACC": data["ACC"],
            "APD": data["APD"],
            "REA": data["REA"],
        }
        for month, data in timeline.items()
    ], key=lambda x: x["date"])


def get_ogv_timeline(request):
    """OGV Timeline: Programme ID 7 + Person Home MC Greece"""
    try:
        # Get date filters from request
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        
        # Base queryset
        applications = ExpaApplication.objects.filter(programme_id=7) \
            .filter(home_mc_name__icontains='Greece')
        
        signups = SignupPerson.objects.exclude(
            Q(selected_programmes__icontains='8') | Q(selected_programmes__icontains='9')
        )
        
        # Apply date filters if provided
        if start_date:
            try:
                start_datetime = parse_datetime(start_date) or timezone.make_aware(datetime.strptime(start_date, '%Y-%m-%d'))
                applications = applications.filter(created_at__gte=start_datetime)
                signups = signups.filter(created_at__gte=start_datetime)
            except (ValueError, TypeError):
                pass
        
        if end_date:
            try:
                end_datetime = parse_datetime(end_date) or timezone.make_aware(datetime.strptime(end_date, '%Y-%m-%d'))
                # Add one day to include the end date
                end_datetime = end_datetime + timedelta(days=1)
                applications = applications.filter(created_at__lt=end_datetime)
                signups = signups.filter(created_at__lt=end_datetime)
            except (ValueError, TypeError):
                pass

        # Get signups aggregated by month
        signups_data = signups.annotate(month=TruncMonth("created_at")).values("month").annotate(count=Count("id"))

        timeline = format_timeline_data(applications, signups_data, programme_id=7)
        return JsonResponse({"timeline": timeline})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def get_ogta_timeline(request):
    """OGTa Timeline: Programme ID 8 + Person Home MC Greece"""
    try:
        # Get date filters from request
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        
        # Base queryset
        applications = ExpaApplication.objects.filter(programme_id=8) \
            .filter(home_mc_name__icontains='Greece')
        
        signups = SignupPerson.objects.exclude(
            Q(selected_programmes__icontains='7') | Q(selected_programmes__icontains='9')
        )
        
        # Apply date filters if provided
        if start_date:
            try:
                start_datetime = parse_datetime(start_date) or timezone.make_aware(datetime.strptime(start_date, '%Y-%m-%d'))
                applications = applications.filter(created_at__gte=start_datetime)
                signups = signups.filter(created_at__gte=start_datetime)
            except (ValueError, TypeError):
                pass
        
        if end_date:
            try:
                end_datetime = parse_datetime(end_date) or timezone.make_aware(datetime.strptime(end_date, '%Y-%m-%d'))
                # Add one day to include the end date
                end_datetime = end_datetime + timedelta(days=1)
                applications = applications.filter(created_at__lt=end_datetime)
                signups = signups.filter(created_at__lt=end_datetime)
            except (ValueError, TypeError):
                pass

        # Get signups aggregated by month
        signups_data = signups.annotate(month=TruncMonth("created_at")).values("month").annotate(count=Count("id"))

        timeline = format_timeline_data(applications, signups_data, programme_id=8)
        return JsonResponse({"timeline": timeline})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def get_ogte_timeline(request):
    """OGTe Timeline: Programme ID 9 + Person Home MC Greece"""
    try:
        # Get date filters from request
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        
        # Base queryset
        applications = ExpaApplication.objects.filter(programme_id=9) \
            .filter(home_mc_name__icontains='Greece')
        
        signups = SignupPerson.objects.exclude(
            Q(selected_programmes__icontains='7') | Q(selected_programmes__icontains='8')
        )
        
        # Apply date filters if provided
        if start_date:
            try:
                start_datetime = parse_datetime(start_date) or timezone.make_aware(datetime.strptime(start_date, '%Y-%m-%d'))
                applications = applications.filter(created_at__gte=start_datetime)
                signups = signups.filter(created_at__gte=start_datetime)
            except (ValueError, TypeError):
                pass
        
        if end_date:
            try:
                end_datetime = parse_datetime(end_date) or timezone.make_aware(datetime.strptime(end_date, '%Y-%m-%d'))
                # Add one day to include the end date
                end_datetime = end_datetime + timedelta(days=1)
                applications = applications.filter(created_at__lt=end_datetime)
                signups = signups.filter(created_at__lt=end_datetime)
            except (ValueError, TypeError):
                pass

        # Get signups aggregated by month
        signups_data = signups.annotate(month=TruncMonth("created_at")).values("month").annotate(count=Count("id"))

        timeline = format_timeline_data(applications, signups_data, programme_id=9)
        return JsonResponse({"timeline": timeline})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def get_igv_timeline(request):
    """IGV Timeline: Programme ID 7 + Opportunity Home MC Greece"""
    try:
        timeline = defaultdict(lambda: {"APP": 0, "ACC": 0, "APD": 0, "REA": 0})

        # Applications (APP)
        applied = ExpaApplication.objects.filter(programme_id=7) \
            .filter(home_mc_name_opportunity__icontains='Greece') \
            .exclude(created_at=None) \
            .annotate(month=TruncMonth("created_at")).values("month").annotate(count=Count("id"))
        
        for item in applied:
            month = item["month"].strftime("%Y-%m")
            timeline[month]["APP"] += item["count"]

        # Accepted (ACC)
        accepted = ExpaApplication.objects.filter(programme_id=7) \
            .filter(home_mc_name_opportunity__icontains='Greece') \
            .exclude(date_matched=None) \
            .annotate(month=TruncMonth("date_matched")).values("month").annotate(count=Count("id"))

        for item in accepted:
            month = item["month"].strftime("%Y-%m")
            timeline[month]["ACC"] += item["count"]

        # Approved (APD)
        approved = ExpaApplication.objects.filter(programme_id=7) \
            .filter(home_mc_name_opportunity__icontains='Greece') \
            .exclude(date_approved=None) \
            .annotate(month=TruncMonth("date_approved")).values("month").annotate(count=Count("id"))

        for item in approved:
            month = item["month"].strftime("%Y-%m")
            timeline[month]["APD"] += item["count"]

        # Realized (REA)
        realized = ExpaApplication.objects.filter(programme_id=7) \
            .filter(home_mc_name_opportunity__icontains='Greece') \
            .exclude(date_realized=None) \
            .annotate(month=TruncMonth("date_realized")).values("month").annotate(count=Count("id"))

        for item in realized:
            month = item["month"].strftime("%Y-%m")
            timeline[month]["REA"] += item["count"]

        # Convert to sorted list
        timeline_list = [
            {
                "date": month,
                "APP": data["APP"],
                "ACC": data["ACC"],
                "APD": data["APD"],
                "REA": data["REA"],
            }
            for month, data in sorted(timeline.items())
        ]

        return JsonResponse({"timeline": timeline_list})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def get_igta_timeline(request):
    """IGTa Timeline: Programme ID 8 + Opportunity Home MC Greece"""
    try:
        timeline = defaultdict(lambda: {"APP": 0, "ACC": 0, "APD": 0, "REA": 0})

        # Applications (APP)
        applied = ExpaApplication.objects.filter(programme_id=8) \
            .filter(home_mc_name_opportunity__icontains='Greece') \
            .exclude(created_at=None) \
            .annotate(month=TruncMonth("created_at")).values("month").annotate(count=Count("id"))
        
        for item in applied:
            month = item["month"].strftime("%Y-%m")
            timeline[month]["APP"] += item["count"]

        # Accepted (ACC)
        accepted = ExpaApplication.objects.filter(programme_id=8) \
            .filter(home_mc_name_opportunity__icontains='Greece') \
            .exclude(date_matched=None) \
            .annotate(month=TruncMonth("date_matched")).values("month").annotate(count=Count("id"))

        for item in accepted:
            month = item["month"].strftime("%Y-%m")
            timeline[month]["ACC"] += item["count"]

        # Approved (APD)
        approved = ExpaApplication.objects.filter(programme_id=8) \
            .filter(home_mc_name_opportunity__icontains='Greece') \
            .exclude(date_approved=None) \
            .annotate(month=TruncMonth("date_approved")).values("month").annotate(count=Count("id"))

        for item in approved:
            month = item["month"].strftime("%Y-%m")
            timeline[month]["APD"] += item["count"]

        # Realized (REA)
        realized = ExpaApplication.objects.filter(programme_id=8) \
            .filter(home_mc_name_opportunity__icontains='Greece') \
            .exclude(date_realized=None) \
            .annotate(month=TruncMonth("date_realized")).values("month").annotate(count=Count("id"))

        for item in realized:
            month = item["month"].strftime("%Y-%m")
            timeline[month]["REA"] += item["count"]

        # Convert to sorted list
        timeline_list = [
            {
                "date": month,
                "APP": data["APP"],
                "ACC": data["ACC"],
                "APD": data["APD"],
                "REA": data["REA"],
            }
            for month, data in sorted(timeline.items())
        ]

        return JsonResponse({"timeline": timeline_list})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)




# LC athens Chart
 

def format_timeline_data(applications, signups, programme_id):
    """Helper function to format timeline data"""
    timeline = defaultdict(lambda: {"SU": 0, "APP": 0, "ACC": 0, "APD": 0, "REA": 0})

    for item in signups:
        month = item["month"].strftime("%Y-%m")
        timeline[month]["SU"] = item["count"]

    for ep in applications:
        if ep.created_at:
            month = ep.created_at.strftime("%Y-%m")
            timeline[month]["APP"] += 1
        if ep.date_matched:
            month = ep.date_matched.strftime("%Y-%m")
            timeline[month]["ACC"] += 1
        if ep.date_approved:
            month = ep.date_approved.strftime("%Y-%m")
            timeline[month]["APD"] += 1
        if ep.date_realized:
            month = ep.date_realized.strftime("%Y-%m")
            timeline[month]["REA"] += 1

    return sorted([
        {
            "date": month,
            "SU": data["SU"],
            "APP": data["APP"],
            "ACC": data["ACC"],
            "APD": data["APD"],
            "REA": data["REA"],
        }
        for month, data in timeline.items()
    ], key=lambda x: x["date"])


def get_lc_athens_ogv_timeline(request):
    """OGV Timeline: Programme ID 7 + Person Home LC Athens"""
    try:
        # Get date filters from request
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        
        # Base queryset
        applications = ExpaApplication.objects.filter(programme_id=7) \
            .filter(home_lc_name__icontains='ATHENS')
        
        signups = SignupPerson.objects.exclude(
            Q(selected_programmes__icontains='8') | Q(selected_programmes__icontains='9')
        )
        
        # Apply date filters if provided
        if start_date:
            try:
                start_datetime = parse_datetime(start_date) or timezone.make_aware(datetime.strptime(start_date, '%Y-%m-%d'))
                applications = applications.filter(created_at__gte=start_datetime)
                signups = signups.filter(created_at__gte=start_datetime)
            except (ValueError, TypeError):
                pass
        
        if end_date:
            try:
                end_datetime = parse_datetime(end_date) or timezone.make_aware(datetime.strptime(end_date, '%Y-%m-%d'))
                # Add one day to include the end date
                end_datetime = end_datetime + timedelta(days=1)
                applications = applications.filter(created_at__lt=end_datetime)
                signups = signups.filter(created_at__lt=end_datetime)
            except (ValueError, TypeError):
                pass

        # Get signups aggregated by month
        signups_data = signups.annotate(month=TruncMonth("created_at")).values("month").annotate(count=Count("id"))

        timeline = format_timeline_data(applications, signups_data, programme_id=7)
        return JsonResponse({"timeline": timeline})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def get_lc_athens_ogta_timeline(request):
    """OGTa Timeline: Programme ID 8 + Person Home LC Athens"""
    try:
        # Get date filters from request
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        
        # Base queryset
        applications = ExpaApplication.objects.filter(programme_id=8) \
            .filter(home_lc_name__icontains='ATHENS')
        
        signups = SignupPerson.objects.exclude(
            Q(selected_programmes__icontains='7') | Q(selected_programmes__icontains='9')
        )
        
        # Apply date filters if provided
        if start_date:
            try:
                start_datetime = parse_datetime(start_date) or timezone.make_aware(datetime.strptime(start_date, '%Y-%m-%d'))
                applications = applications.filter(created_at__gte=start_datetime)
                signups = signups.filter(created_at__gte=start_datetime)
            except (ValueError, TypeError):
                pass
        
        if end_date:
            try:
                end_datetime = parse_datetime(end_date) or timezone.make_aware(datetime.strptime(end_date, '%Y-%m-%d'))
                # Add one day to include the end date
                end_datetime = end_datetime + timedelta(days=1)
                applications = applications.filter(created_at__lt=end_datetime)
                signups = signups.filter(created_at__lt=end_datetime)
            except (ValueError, TypeError):
                pass

        # Get signups aggregated by month
        signups_data = signups.annotate(month=TruncMonth("created_at")).values("month").annotate(count=Count("id"))

        timeline = format_timeline_data(applications, signups_data, programme_id=8)
        return JsonResponse({"timeline": timeline})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def get_lc_athens_ogte_timeline(request):
    """OGTe Timeline: Programme ID 9 + Person Home LC Athens"""
    try:
        # Get date filters from request
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        
        # Base queryset
        applications = ExpaApplication.objects.filter(programme_id=9) \
            .filter(home_lc_name__icontains='ATHENS')
        
        signups = SignupPerson.objects.exclude(
            Q(selected_programmes__icontains='7') | Q(selected_programmes__icontains='8')
        )
        
        # Apply date filters if provided
        if start_date:
            try:
                start_datetime = parse_datetime(start_date) or timezone.make_aware(datetime.strptime(start_date, '%Y-%m-%d'))
                applications = applications.filter(created_at__gte=start_datetime)
                signups = signups.filter(created_at__gte=start_datetime)
            except (ValueError, TypeError):
                pass
        
        if end_date:
            try:
                end_datetime = parse_datetime(end_date) or timezone.make_aware(datetime.strptime(end_date, '%Y-%m-%d'))
                # Add one day to include the end date
                end_datetime = end_datetime + timedelta(days=1)
                applications = applications.filter(created_at__lt=end_datetime)
                signups = signups.filter(created_at__lt=end_datetime)
            except (ValueError, TypeError):
                pass

        # Get signups aggregated by month
        signups_data = signups.annotate(month=TruncMonth("created_at")).values("month").annotate(count=Count("id"))

        timeline = format_timeline_data(applications, signups_data, programme_id=9)
        return JsonResponse({"timeline": timeline})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def get_lc_athens_igv_timeline(request):
    """IGV Timeline: Programme ID 7 + Opportunity Home LC Athens"""
    try:
        timeline = defaultdict(lambda: {"APP": 0, "ACC": 0, "APD": 0, "REA": 0})

        # Applications (APP)
        applied = ExpaApplication.objects.filter(programme_id=7) \
            .filter(home_lc_name_opportunity__icontains='ATHENS') \
            .exclude(created_at=None) \
            .annotate(month=TruncMonth("created_at")).values("month").annotate(count=Count("id"))
        
        for item in applied:
            month = item["month"].strftime("%Y-%m")
            timeline[month]["APP"] += item["count"]

        # Accepted (ACC)
        accepted = ExpaApplication.objects.filter(programme_id=7) \
            .filter(home_lc_name_opportunity__icontains='ATHENS') \
            .exclude(date_matched=None) \
            .annotate(month=TruncMonth("date_matched")).values("month").annotate(count=Count("id"))

        for item in accepted:
            month = item["month"].strftime("%Y-%m")
            timeline[month]["ACC"] += item["count"]

        # Approved (APD)
        approved = ExpaApplication.objects.filter(programme_id=7) \
            .filter(home_lc_name_opportunity__icontains='ATHENS') \
            .exclude(date_approved=None) \
            .annotate(month=TruncMonth("date_approved")).values("month").annotate(count=Count("id"))

        for item in approved:
            month = item["month"].strftime("%Y-%m")
            timeline[month]["APD"] += item["count"]

        # Realized (REA)
        realized = ExpaApplication.objects.filter(programme_id=7) \
            .filter(home_lc_name_opportunity__icontains='ATHENS') \
            .exclude(date_realized=None) \
            .annotate(month=TruncMonth("date_realized")).values("month").annotate(count=Count("id"))

        for item in realized:
            month = item["month"].strftime("%Y-%m")
            timeline[month]["REA"] += item["count"]

        # Convert to sorted list
        timeline_list = [
            {
                "date": month,
                "APP": data["APP"],
                "ACC": data["ACC"],
                "APD": data["APD"],
                "REA": data["REA"],
            }
            for month, data in sorted(timeline.items())
        ]

        return JsonResponse({"timeline": timeline_list})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def get_lc_athens_igta_timeline(request):
    """IGTa Timeline: Programme ID 8 + Opportunity Home LC Athens"""
    try:
        timeline = defaultdict(lambda: {"APP": 0, "ACC": 0, "APD": 0, "REA": 0})

        # Applications (APP)
        applied = ExpaApplication.objects.filter(programme_id=8) \
            .filter(home_lc_name_opportunity__icontains='ATHENS') \
            .exclude(created_at=None) \
            .annotate(month=TruncMonth("created_at")).values("month").annotate(count=Count("id"))
        
        for item in applied:
            month = item["month"].strftime("%Y-%m")
            timeline[month]["APP"] += item["count"]

        # Accepted (ACC)
        accepted = ExpaApplication.objects.filter(programme_id=8) \
            .filter(home_lc_name_opportunity__icontains='ATHENS') \
            .exclude(date_matched=None) \
            .annotate(month=TruncMonth("date_matched")).values("month").annotate(count=Count("id"))

        for item in accepted:
            month = item["month"].strftime("%Y-%m")
            timeline[month]["ACC"] += item["count"]

        # Approved (APD)
        approved = ExpaApplication.objects.filter(programme_id=8) \
            .filter(home_lc_name_opportunity__icontains='ATHENS') \
            .exclude(date_approved=None) \
            .annotate(month=TruncMonth("date_approved")).values("month").annotate(count=Count("id"))

        for item in approved:
            month = item["month"].strftime("%Y-%m")
            timeline[month]["APD"] += item["count"]

        # Realized (REA)
        realized = ExpaApplication.objects.filter(programme_id=8) \
            .filter(home_lc_name_opportunity__icontains='ATHENS') \
            .exclude(date_realized=None) \
            .annotate(month=TruncMonth("date_realized")).values("month").annotate(count=Count("id"))

        for item in realized:
            month = item["month"].strftime("%Y-%m")
            timeline[month]["REA"] += item["count"]

        # Convert to sorted list
        timeline_list = [
            {
                "date": month,
                "APP": data["APP"],
                "ACC": data["ACC"],
                "APD": data["APD"],
                "REA": data["REA"],
            }
            for month, data in sorted(timeline.items())
        ]

        return JsonResponse({"timeline": timeline_list})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# LC AUTH Chart

def format_timeline_data(applications, signups, programme_id):
    """Helper function to format timeline data"""
    timeline = defaultdict(lambda: {"SU": 0, "APP": 0, "ACC": 0, "APD": 0, "REA": 0})

    for item in signups:
        month = item["month"].strftime("%Y-%m")
        timeline[month]["SU"] = item["count"]

    for ep in applications:
        if ep.created_at:
            month = ep.created_at.strftime("%Y-%m")
            timeline[month]["APP"] += 1
        if ep.date_matched:
            month = ep.date_matched.strftime("%Y-%m")
            timeline[month]["ACC"] += 1
        if ep.date_approved:
            month = ep.date_approved.strftime("%Y-%m")
            timeline[month]["APD"] += 1
        if ep.date_realized:
            month = ep.date_realized.strftime("%Y-%m")
            timeline[month]["REA"] += 1

    return sorted([
        {
            "date": month,
            "SU": data["SU"],
            "APP": data["APP"],
            "ACC": data["ACC"],
            "APD": data["APD"],
            "REA": data["REA"],
        }
        for month, data in timeline.items()
    ], key=lambda x: x["date"])


def get_lc_auth_ogv_timeline(request):
    """OGV Timeline: Programme ID 7 + Person Home LC AUTH"""
    try:
        # Get date filters from request
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        
        # Base queryset
        applications = ExpaApplication.objects.filter(programme_id=7) \
            .filter(home_lc_name__icontains='AUTH')
        
        signups = SignupPerson.objects.exclude(
            Q(selected_programmes__icontains='8') | Q(selected_programmes__icontains='9')
        )
        
        # Apply date filters if provided
        if start_date:
            try:
                start_datetime = parse_datetime(start_date) or timezone.make_aware(datetime.strptime(start_date, '%Y-%m-%d'))
                applications = applications.filter(created_at__gte=start_datetime)
                signups = signups.filter(created_at__gte=start_datetime)
            except (ValueError, TypeError):
                pass
        
        if end_date:
            try:
                end_datetime = parse_datetime(end_date) or timezone.make_aware(datetime.strptime(end_date, '%Y-%m-%d'))
                # Add one day to include the end date
                end_datetime = end_datetime + timedelta(days=1)
                applications = applications.filter(created_at__lt=end_datetime)
                signups = signups.filter(created_at__lt=end_datetime)
            except (ValueError, TypeError):
                pass

        # Get signups aggregated by month
        signups_data = signups.annotate(month=TruncMonth("created_at")).values("month").annotate(count=Count("id"))

        timeline = format_timeline_data(applications, signups_data, programme_id=7)
        return JsonResponse({"timeline": timeline})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def get_lc_auth_ogta_timeline(request):
    """OGTa Timeline: Programme ID 8 + Person Home LC AUTH"""
    try:
        # Get date filters from request
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        
        # Base queryset
        applications = ExpaApplication.objects.filter(programme_id=8) \
            .filter(home_lc_name__icontains='AUTH')
        
        signups = SignupPerson.objects.exclude(
            Q(selected_programmes__icontains='7') | Q(selected_programmes__icontains='9')
        )
        
        # Apply date filters if provided
        if start_date:
            try:
                start_datetime = parse_datetime(start_date) or timezone.make_aware(datetime.strptime(start_date, '%Y-%m-%d'))
                applications = applications.filter(created_at__gte=start_datetime)
                signups = signups.filter(created_at__gte=start_datetime)
            except (ValueError, TypeError):
                pass
        
        if end_date:
            try:
                end_datetime = parse_datetime(end_date) or timezone.make_aware(datetime.strptime(end_date, '%Y-%m-%d'))
                # Add one day to include the end date
                end_datetime = end_datetime + timedelta(days=1)
                applications = applications.filter(created_at__lt=end_datetime)
                signups = signups.filter(created_at__lt=end_datetime)
            except (ValueError, TypeError):
                pass

        # Get signups aggregated by month
        signups_data = signups.annotate(month=TruncMonth("created_at")).values("month").annotate(count=Count("id"))

        timeline = format_timeline_data(applications, signups_data, programme_id=8)
        return JsonResponse({"timeline": timeline})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def get_lc_auth_ogte_timeline(request):
    """OGTe Timeline: Programme ID 9 + Person Home LC AUTH"""
    try:
        # Get date filters from request
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        
        # Base queryset
        applications = ExpaApplication.objects.filter(programme_id=9) \
            .filter(home_lc_name__icontains='AUTH')
        
        signups = SignupPerson.objects.exclude(
            Q(selected_programmes__icontains='7') | Q(selected_programmes__icontains='8')
        )
        
        # Apply date filters if provided
        if start_date:
            try:
                start_datetime = parse_datetime(start_date) or timezone.make_aware(datetime.strptime(start_date, '%Y-%m-%d'))
                applications = applications.filter(created_at__gte=start_datetime)
                signups = signups.filter(created_at__gte=start_datetime)
            except (ValueError, TypeError):
                pass
        
        if end_date:
            try:
                end_datetime = parse_datetime(end_date) or timezone.make_aware(datetime.strptime(end_date, '%Y-%m-%d'))
                # Add one day to include the end date
                end_datetime = end_datetime + timedelta(days=1)
                applications = applications.filter(created_at__lt=end_datetime)
                signups = signups.filter(created_at__lt=end_datetime)
            except (ValueError, TypeError):
                pass

        # Get signups aggregated by month
        signups_data = signups.annotate(month=TruncMonth("created_at")).values("month").annotate(count=Count("id"))

        timeline = format_timeline_data(applications, signups_data, programme_id=9)
        return JsonResponse({"timeline": timeline})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def get_lc_auth_igv_timeline(request):
    """IGV Timeline: Programme ID 7 + Opportunity Home LC AUTH"""
    try:
        timeline = defaultdict(lambda: {"APP": 0, "ACC": 0, "APD": 0, "REA": 0})

        # Applications (APP)
        applied = ExpaApplication.objects.filter(programme_id=7) \
            .filter(home_lc_name_opportunity__icontains='AUTH') \
            .exclude(created_at=None) \
            .annotate(month=TruncMonth("created_at")).values("month").annotate(count=Count("id"))
        
        for item in applied:
            month = item["month"].strftime("%Y-%m")
            timeline[month]["APP"] += item["count"]

        # Accepted (ACC)
        accepted = ExpaApplication.objects.filter(programme_id=7) \
            .filter(home_lc_name_opportunity__icontains='AUTH') \
            .exclude(date_matched=None) \
            .annotate(month=TruncMonth("date_matched")).values("month").annotate(count=Count("id"))

        for item in accepted:
            month = item["month"].strftime("%Y-%m")
            timeline[month]["ACC"] += item["count"]

        # Approved (APD)
        approved = ExpaApplication.objects.filter(programme_id=7) \
            .filter(home_lc_name_opportunity__icontains='AUTH') \
            .exclude(date_approved=None) \
            .annotate(month=TruncMonth("date_approved")).values("month").annotate(count=Count("id"))

        for item in approved:
            month = item["month"].strftime("%Y-%m")
            timeline[month]["APD"] += item["count"]

        # Realized (REA)
        realized = ExpaApplication.objects.filter(programme_id=7) \
            .filter(home_lc_name_opportunity__icontains='AUTH') \
            .exclude(date_realized=None) \
            .annotate(month=TruncMonth("date_realized")).values("month").annotate(count=Count("id"))

        for item in realized:
            month = item["month"].strftime("%Y-%m")
            timeline[month]["REA"] += item["count"]

        # Convert to sorted list
        timeline_list = [
            {
                "date": month,
                "APP": data["APP"],
                "ACC": data["ACC"],
                "APD": data["APD"],
                "REA": data["REA"],
            }
            for month, data in sorted(timeline.items())
        ]

        return JsonResponse({"timeline": timeline_list})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def get_lc_auth_igta_timeline(request):
    """IGTa Timeline: Programme ID 8 + Opportunity Home LC AUTH"""
    try:
        timeline = defaultdict(lambda: {"APP": 0, "ACC": 0, "APD": 0, "REA": 0})

        # Applications (APP)
        applied = ExpaApplication.objects.filter(programme_id=8) \
            .filter(home_lc_name_opportunity__icontains='AUTH') \
            .exclude(created_at=None) \
            .annotate(month=TruncMonth("created_at")).values("month").annotate(count=Count("id"))
        
        for item in applied:
            month = item["month"].strftime("%Y-%m")
            timeline[month]["APP"] += item["count"]

        # Accepted (ACC)
        accepted = ExpaApplication.objects.filter(programme_id=8) \
            .filter(home_lc_name_opportunity__icontains='AUTH') \
            .exclude(date_matched=None) \
            .annotate(month=TruncMonth("date_matched")).values("month").annotate(count=Count("id"))

        for item in accepted:
            month = item["month"].strftime("%Y-%m")
            timeline[month]["ACC"] += item["count"]

        # Approved (APD)
        approved = ExpaApplication.objects.filter(programme_id=8) \
            .filter(home_lc_name_opportunity__icontains='AUTH') \
            .exclude(date_approved=None) \
            .annotate(month=TruncMonth("date_approved")).values("month").annotate(count=Count("id"))

        for item in approved:
            month = item["month"].strftime("%Y-%m")
            timeline[month]["APD"] += item["count"]

        # Realized (REA)
        realized = ExpaApplication.objects.filter(programme_id=8) \
            .filter(home_lc_name_opportunity__icontains='AUTH') \
            .exclude(date_realized=None) \
            .annotate(month=TruncMonth("date_realized")).values("month").annotate(count=Count("id"))

        for item in realized:
            month = item["month"].strftime("%Y-%m")
            timeline[month]["REA"] += item["count"]

        # Convert to sorted list
        timeline_list = [
            {
                "date": month,
                "APP": data["APP"],
                "ACC": data["ACC"],
                "APD": data["APD"],
                "REA": data["REA"],
            }
            for month, data in sorted(timeline.items())
        ]

        return JsonResponse({"timeline": timeline_list})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
    

# LC Piraeus (UniPi) Chart

def format_timeline_data(applications, signups, programme_id):
    """Helper function to format timeline data"""
    timeline = defaultdict(lambda: {"SU": 0, "APP": 0, "ACC": 0, "APD": 0, "REA": 0})

    for item in signups:
        month = item["month"].strftime("%Y-%m")
        timeline[month]["SU"] = item["count"]

    for ep in applications:
        if ep.created_at:
            month = ep.created_at.strftime("%Y-%m")
            timeline[month]["APP"] += 1
        if ep.date_matched:
            month = ep.date_matched.strftime("%Y-%m")
            timeline[month]["ACC"] += 1
        if ep.date_approved:
            month = ep.date_approved.strftime("%Y-%m")
            timeline[month]["APD"] += 1
        if ep.date_realized:
            month = ep.date_realized.strftime("%Y-%m")
            timeline[month]["REA"] += 1

    return sorted([
        {
            "date": month,
            "SU": data["SU"],
            "APP": data["APP"],
            "ACC": data["ACC"],
            "APD": data["APD"],
            "REA": data["REA"],
        }
        for month, data in timeline.items()
    ], key=lambda x: x["date"])


def get_lc_unipi_ogv_timeline(request):
    """OGV Timeline: Programme ID 7 + Person Home LC Piraeus (UniPi)"""
    try:
        # Get date filters from request
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        
        # Base queryset
        applications = ExpaApplication.objects.filter(programme_id=7) \
            .filter(home_lc_name='Piraeus (UniPi)')
        
        signups = SignupPerson.objects.exclude(
            Q(selected_programmes__icontains='8') | Q(selected_programmes__icontains='9')
        )
        
        # Apply date filters if provided
        if start_date:
            try:
                start_datetime = parse_datetime(start_date) or timezone.make_aware(datetime.strptime(start_date, '%Y-%m-%d'))
                applications = applications.filter(created_at__gte=start_datetime)
                signups = signups.filter(created_at__gte=start_datetime)
            except (ValueError, TypeError):
                pass
        
        if end_date:
            try:
                end_datetime = parse_datetime(end_date) or timezone.make_aware(datetime.strptime(end_date, '%Y-%m-%d'))
                # Add one day to include the end date
                end_datetime = end_datetime + timedelta(days=1)
                applications = applications.filter(created_at__lt=end_datetime)
                signups = signups.filter(created_at__lt=end_datetime)
            except (ValueError, TypeError):
                pass

        # Get signups aggregated by month
        signups_data = signups.annotate(month=TruncMonth("created_at")).values("month").annotate(count=Count("id"))

        timeline = format_timeline_data(applications, signups_data, programme_id=7)
        return JsonResponse({"timeline": timeline})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def get_lc_unipi_ogta_timeline(request):
    """OGTa Timeline: Programme ID 8 + Person Home LC Piraeus (UniPi)"""
    try:
        # Get date filters from request
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        
        # Base queryset
        applications = ExpaApplication.objects.filter(programme_id=8) \
            .filter(home_lc_name='Piraeus (UniPi)')
        
        signups = SignupPerson.objects.exclude(
            Q(selected_programmes__icontains='7') | Q(selected_programmes__icontains='9')
        )
        
        # Apply date filters if provided
        if start_date:
            try:
                start_datetime = parse_datetime(start_date) or timezone.make_aware(datetime.strptime(start_date, '%Y-%m-%d'))
                applications = applications.filter(created_at__gte=start_datetime)
                signups = signups.filter(created_at__gte=start_datetime)
            except (ValueError, TypeError):
                pass
        
        if end_date:
            try:
                end_datetime = parse_datetime(end_date) or timezone.make_aware(datetime.strptime(end_date, '%Y-%m-%d'))
                # Add one day to include the end date
                end_datetime = end_datetime + timedelta(days=1)
                applications = applications.filter(created_at__lt=end_datetime)
                signups = signups.filter(created_at__lt=end_datetime)
            except (ValueError, TypeError):
                pass

        # Get signups aggregated by month
        signups_data = signups.annotate(month=TruncMonth("created_at")).values("month").annotate(count=Count("id"))

        timeline = format_timeline_data(applications, signups_data, programme_id=8)
        return JsonResponse({"timeline": timeline})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def get_lc_unipi_ogte_timeline(request):
    """OGTe Timeline: Programme ID 9 + Person Home LC Piraeus (UniPi)"""
    try:
        # Get date filters from request
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        
        # Base queryset
        applications = ExpaApplication.objects.filter(programme_id=9) \
            .filter(home_lc_name='Piraeus (UniPi)')
        
        signups = SignupPerson.objects.exclude(
            Q(selected_programmes__icontains='7') | Q(selected_programmes__icontains='8')
        )
        
        # Apply date filters if provided
        if start_date:
            try:
                start_datetime = parse_datetime(start_date) or timezone.make_aware(datetime.strptime(start_date, '%Y-%m-%d'))
                applications = applications.filter(created_at__gte=start_datetime)
                signups = signups.filter(created_at__gte=start_datetime)
            except (ValueError, TypeError):
                pass
        
        if end_date:
            try:
                end_datetime = parse_datetime(end_date) or timezone.make_aware(datetime.strptime(end_date, '%Y-%m-%d'))
                # Add one day to include the end date
                end_datetime = end_datetime + timedelta(days=1)
                applications = applications.filter(created_at__lt=end_datetime)
                signups = signups.filter(created_at__lt=end_datetime)
            except (ValueError, TypeError):
                pass

        # Get signups aggregated by month
        signups_data = signups.annotate(month=TruncMonth("created_at")).values("month").annotate(count=Count("id"))

        timeline = format_timeline_data(applications, signups_data, programme_id=9)
        return JsonResponse({"timeline": timeline})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def get_lc_unipi_igv_timeline(request):
    """IGV Timeline: Programme ID 7 + Opportunity Home LC Piraeus (UniPi)"""
    try:
        timeline = defaultdict(lambda: {"APP": 0, "ACC": 0, "APD": 0, "REA": 0})

        # Applications (APP)
        applied = ExpaApplication.objects.filter(programme_id=7) \
            .filter(home_lc_name_opportunity='Piraeus (UniPi)') \
            .exclude(created_at=None) \
            .annotate(month=TruncMonth("created_at")).values("month").annotate(count=Count("id"))
        
        for item in applied:
            month = item["month"].strftime("%Y-%m")
            timeline[month]["APP"] += item["count"]

        # Accepted (ACC)
        accepted = ExpaApplication.objects.filter(programme_id=7) \
            .filter(home_lc_name_opportunity='Piraeus (UniPi)') \
            .exclude(date_matched=None) \
            .annotate(month=TruncMonth("date_matched")).values("month").annotate(count=Count("id"))

        for item in accepted:
            month = item["month"].strftime("%Y-%m")
            timeline[month]["ACC"] += item["count"]

        # Approved (APD)
        approved = ExpaApplication.objects.filter(programme_id=7) \
            .filter(home_lc_name_opportunity='Piraeus (UniPi)') \
            .exclude(date_approved=None) \
            .annotate(month=TruncMonth("date_approved")).values("month").annotate(count=Count("id"))

        for item in approved:
            month = item["month"].strftime("%Y-%m")
            timeline[month]["APD"] += item["count"]

        # Realized (REA)
        realized = ExpaApplication.objects.filter(programme_id=7) \
            .filter(home_lc_name_opportunity='Piraeus (UniPi)') \
            .exclude(date_realized=None) \
            .annotate(month=TruncMonth("date_realized")).values("month").annotate(count=Count("id"))

        for item in realized:
            month = item["month"].strftime("%Y-%m")
            timeline[month]["REA"] += item["count"]

        # Convert to sorted list
        timeline_list = [
            {
                "date": month,
                "APP": data["APP"],
                "ACC": data["ACC"],
                "APD": data["APD"],
                "REA": data["REA"],
            }
            for month, data in sorted(timeline.items())
        ]

        return JsonResponse({"timeline": timeline_list})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def get_lc_unipi_igta_timeline(request):
    """IGTa Timeline: Programme ID 8 + Opportunity Home LC Piraeus (UniPi)"""
    try:
        timeline = defaultdict(lambda: {"APP": 0, "ACC": 0, "APD": 0, "REA": 0})

        # Applications (APP)
        applied = ExpaApplication.objects.filter(programme_id=8) \
            .filter(home_lc_name_opportunity='Piraeus (UniPi)') \
            .exclude(created_at=None) \
            .annotate(month=TruncMonth("created_at")).values("month").annotate(count=Count("id"))
        
        for item in applied:
            month = item["month"].strftime("%Y-%m")
            timeline[month]["APP"] += item["count"]

        # Accepted (ACC)
        accepted = ExpaApplication.objects.filter(programme_id=8) \
            .filter(home_lc_name_opportunity='Piraeus (UniPi)') \
            .exclude(date_matched=None) \
            .annotate(month=TruncMonth("date_matched")).values("month").annotate(count=Count("id"))

        for item in accepted:
            month = item["month"].strftime("%Y-%m")
            timeline[month]["ACC"] += item["count"]

        # Approved (APD)
        approved = ExpaApplication.objects.filter(programme_id=8) \
            .filter(home_lc_name_opportunity='Piraeus (UniPi)') \
            .exclude(date_approved=None) \
            .annotate(month=TruncMonth("date_approved")).values("month").annotate(count=Count("id"))

        for item in approved:
            month = item["month"].strftime("%Y-%m")
            timeline[month]["APD"] += item["count"]

        # Realized (REA)
        realized = ExpaApplication.objects.filter(programme_id=8) \
            .filter(home_lc_name_opportunity='Piraeus (UniPi)') \
            .exclude(date_realized=None) \
            .annotate(month=TruncMonth("date_realized")).values("month").annotate(count=Count("id"))

        for item in realized:
            month = item["month"].strftime("%Y-%m")
            timeline[month]["REA"] += item["count"]

        # Convert to sorted list
        timeline_list = [
            {
                "date": month,
                "APP": data["APP"],
                "ACC": data["ACC"],
                "APD": data["APD"],
                "REA": data["REA"],
            }
            for month, data in sorted(timeline.items())
        ]

        return JsonResponse({"timeline": timeline_list})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)    


#LC uom thessaloniki Chart

def format_timeline_data(applications, signups, programme_id):
    """Helper function to format timeline data"""
    timeline = defaultdict(lambda: {"SU": 0, "APP": 0, "ACC": 0, "APD": 0, "REA": 0})

    for item in signups:
        month = item["month"].strftime("%Y-%m")
        timeline[month]["SU"] = item["count"]

    for ep in applications:
        if ep.created_at:
            month = ep.created_at.strftime("%Y-%m")
            timeline[month]["APP"] += 1
        if ep.date_matched:
            month = ep.date_matched.strftime("%Y-%m")
            timeline[month]["ACC"] += 1
        if ep.date_approved:
            month = ep.date_approved.strftime("%Y-%m")
            timeline[month]["APD"] += 1
        if ep.date_realized:
            month = ep.date_realized.strftime("%Y-%m")
            timeline[month]["REA"] += 1

    return sorted([
        {
            "date": month,
            "SU": data["SU"],
            "APP": data["APP"],
            "ACC": data["ACC"],
            "APD": data["APD"],
            "REA": data["REA"],
        }
        for month, data in timeline.items()
    ], key=lambda x: x["date"])


def get_LC_UoM_Thessaloniki_ogv_timeline(request):
    try:
        # Get date filters from request
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        
        # Base queryset
        applications = ExpaApplication.objects.filter(programme_id=7) \
            .filter(home_lc_name='UoM THESSALONIKI')
        
        signups = SignupPerson.objects.exclude(
            Q(selected_programmes__icontains='8') | Q(selected_programmes__icontains='9')
        )
        
        # Apply date filters if provided
        if start_date:
            try:
                start_datetime = parse_datetime(start_date) or timezone.make_aware(datetime.strptime(start_date, '%Y-%m-%d'))
                applications = applications.filter(created_at__gte=start_datetime)
                signups = signups.filter(created_at__gte=start_datetime)
            except (ValueError, TypeError):
                pass
        
        if end_date:
            try:
                end_datetime = parse_datetime(end_date) or timezone.make_aware(datetime.strptime(end_date, '%Y-%m-%d'))
                # Add one day to include the end date
                end_datetime = end_datetime + timedelta(days=1)
                applications = applications.filter(created_at__lt=end_datetime)
                signups = signups.filter(created_at__lt=end_datetime)
            except (ValueError, TypeError):
                pass

        # Get signups aggregated by month
        signups_data = signups.annotate(month=TruncMonth("created_at")).values("month").annotate(count=Count("id"))

        timeline = format_timeline_data(applications, signups_data, programme_id=7)
        return JsonResponse({"timeline": timeline})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def get_LC_UoM_Thessaloniki_ogta_timeline(request):
    try:
        # Get date filters from request
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        
        # Base queryset
        applications = ExpaApplication.objects.filter(programme_id=8) \
            .filter(home_lc_name='UoM THESSALONIKI')
        
        signups = SignupPerson.objects.exclude(
            Q(selected_programmes__icontains='7') | Q(selected_programmes__icontains='9')
        )
        
        # Apply date filters if provided
        if start_date:
            try:
                start_datetime = parse_datetime(start_date) or timezone.make_aware(datetime.strptime(start_date, '%Y-%m-%d'))
                applications = applications.filter(created_at__gte=start_datetime)
                signups = signups.filter(created_at__gte=start_datetime)
            except (ValueError, TypeError):
                pass
        
        if end_date:
            try:
                end_datetime = parse_datetime(end_date) or timezone.make_aware(datetime.strptime(end_date, '%Y-%m-%d'))
                # Add one day to include the end date
                end_datetime = end_datetime + timedelta(days=1)
                applications = applications.filter(created_at__lt=end_datetime)
                signups = signups.filter(created_at__lt=end_datetime)
            except (ValueError, TypeError):
                pass

        # Get signups aggregated by month
        signups_data = signups.annotate(month=TruncMonth("created_at")).values("month").annotate(count=Count("id"))

        timeline = format_timeline_data(applications, signups_data, programme_id=8)
        return JsonResponse({"timeline": timeline})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def get_LC_UoM_Thessaloniki_ogte_timeline(request):
    """OGTe Timeline: Programme ID 9 + Person Home LC UoM THESSALONIKI"""
    try:
        # Get date filters from request
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        
        # Base queryset
        applications = ExpaApplication.objects.filter(programme_id=9) \
            .filter(home_lc_name='UoM THESSALONIKI')
        
        signups = SignupPerson.objects.exclude(
            Q(selected_programmes__icontains='7') | Q(selected_programmes__icontains='8')
        )
        
        # Apply date filters if provided
        if start_date:
            try:
                start_datetime = parse_datetime(start_date) or timezone.make_aware(datetime.strptime(start_date, '%Y-%m-%d'))
                applications = applications.filter(created_at__gte=start_datetime)
                signups = signups.filter(created_at__gte=start_datetime)
            except (ValueError, TypeError):
                pass
        
        if end_date:
            try:
                end_datetime = parse_datetime(end_date) or timezone.make_aware(datetime.strptime(end_date, '%Y-%m-%d'))
                # Add one day to include the end date
                end_datetime = end_datetime + timedelta(days=1)
                applications = applications.filter(created_at__lt=end_datetime)
                signups = signups.filter(created_at__lt=end_datetime)
            except (ValueError, TypeError):
                pass

        # Get signups aggregated by month
        signups_data = signups.annotate(month=TruncMonth("created_at")).values("month").annotate(count=Count("id"))

        timeline = format_timeline_data(applications, signups_data, programme_id=9)
        return JsonResponse({"timeline": timeline})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def get_lc_UoM_Thessaloniki_igv_timeline(request):
    """IGV Timeline: Programme ID 7 + Opportunity Home LC UoM THESSALONIKI"""
    try:
        timeline = defaultdict(lambda: {"APP": 0, "ACC": 0, "APD": 0, "REA": 0})

        # Applications (APP)
        applied = ExpaApplication.objects.filter(programme_id=7) \
            .filter(home_lc_name_opportunity='UoM THESSALONIKI') \
            .exclude(created_at=None) \
            .annotate(month=TruncMonth("created_at")).values("month").annotate(count=Count("id"))
        
        for item in applied:
            month = item["month"].strftime("%Y-%m")
            timeline[month]["APP"] += item["count"]

        # Accepted (ACC)
        accepted = ExpaApplication.objects.filter(programme_id=7) \
            .filter(home_lc_name_opportunity='UoM THESSALONIKI') \
            .exclude(date_matched=None) \
            .annotate(month=TruncMonth("date_matched")).values("month").annotate(count=Count("id"))

        for item in accepted:
            month = item["month"].strftime("%Y-%m")
            timeline[month]["ACC"] += item["count"]

        # Approved (APD)
        approved = ExpaApplication.objects.filter(programme_id=7) \
            .filter(home_lc_name_opportunity='UoM THESSALONIKI') \
            .exclude(date_approved=None) \
            .annotate(month=TruncMonth("date_approved")).values("month").annotate(count=Count("id"))

        for item in approved:
            month = item["month"].strftime("%Y-%m")
            timeline[month]["APD"] += item["count"]

        # Realized (REA)
        realized = ExpaApplication.objects.filter(programme_id=7) \
            .filter(home_lc_name_opportunity='UoM THESSALONIKI') \
            .exclude(date_realized=None) \
            .annotate(month=TruncMonth("date_realized")).values("month").annotate(count=Count("id"))

        for item in realized:
            month = item["month"].strftime("%Y-%m")
            timeline[month]["REA"] += item["count"]

        # Convert to sorted list
        timeline_list = [
            {
                "date": month,
                "APP": data["APP"],
                "ACC": data["ACC"],
                "APD": data["APD"],
                "REA": data["REA"],
            }
            for month, data in sorted(timeline.items())
        ]

        return JsonResponse({"timeline": timeline_list})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def get_lc_UoM_Thessaloniki_igta_timeline(request):
    """IGTa Timeline: Programme ID 8 + Opportunity Home LC UoM THESSALONIKI"""
    try:
        timeline = defaultdict(lambda: {"APP": 0, "ACC": 0, "APD": 0, "REA": 0})

        # Applications (APP)
        applied = ExpaApplication.objects.filter(programme_id=8) \
            .filter(home_lc_name_opportunity='UoM THESSALONIKI') \
            .exclude(created_at=None) \
            .annotate(month=TruncMonth("created_at")).values("month").annotate(count=Count("id"))
        
        for item in applied:
            month = item["month"].strftime("%Y-%m")
            timeline[month]["APP"] += item["count"]

        # Accepted (ACC)
        accepted = ExpaApplication.objects.filter(programme_id=8) \
            .filter(home_lc_name_opportunity='UoM THESSALONIKI') \
            .exclude(date_matched=None) \
            .annotate(month=TruncMonth("date_matched")).values("month").annotate(count=Count("id"))

        for item in accepted:
            month = item["month"].strftime("%Y-%m")
            timeline[month]["ACC"] += item["count"]

        # Approved (APD)
        approved = ExpaApplication.objects.filter(programme_id=8) \
            .filter(home_lc_name_opportunity='UoM THESSALONIKI') \
            .exclude(date_approved=None) \
            .annotate(month=TruncMonth("date_approved")).values("month").annotate(count=Count("id"))

        for item in approved:
            month = item["month"].strftime("%Y-%m")
            timeline[month]["APD"] += item["count"]

        # Realized (REA)
        realized = ExpaApplication.objects.filter(programme_id=8) \
            .filter(home_lc_name_opportunity='UoM THESSALONIKI') \
            .exclude(date_realized=None) \
            .annotate(month=TruncMonth("date_realized")).values("month").annotate(count=Count("id"))

        for item in realized:
            month = item["month"].strftime("%Y-%m")
            timeline[month]["REA"] += item["count"]

        # Convert to sorted list
        timeline_list = [
            {
                "date": month,
                "APP": data["APP"],
                "ACC": data["ACC"],
                "APD": data["APD"],
                "REA": data["REA"],
            }
            for month, data in sorted(timeline.items())
        ]

        return JsonResponse({"timeline": timeline_list})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

#IE Volos Chart

def format_timeline_data(applications, signups, programme_id):
    """Helper function to format timeline data"""
    timeline = defaultdict(lambda: {"SU": 0, "APP": 0, "ACC": 0, "APD": 0, "REA": 0})

    for item in signups:
        month = item["month"].strftime("%Y-%m")
        timeline[month]["SU"] = item["count"]

    for ep in applications:
        if ep.created_at:
            month = ep.created_at.strftime("%Y-%m")
            timeline[month]["APP"] += 1
        if ep.date_matched:
            month = ep.date_matched.strftime("%Y-%m")
            timeline[month]["ACC"] += 1
        if ep.date_approved:
            month = ep.date_approved.strftime("%Y-%m")
            timeline[month]["APD"] += 1
        if ep.date_realized:
            month = ep.date_realized.strftime("%Y-%m")
            timeline[month]["REA"] += 1

    return sorted([
        {
            "date": month,
            "SU": data["SU"],
            "APP": data["APP"],
            "ACC": data["ACC"],
            "APD": data["APD"],
            "REA": data["REA"],
        }
        for month, data in timeline.items()
    ], key=lambda x: x["date"])


def get_IE_Volos_ogv_timeline(request):
    try:
        # Get date filters from request
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        
        # Base queryset
        applications = ExpaApplication.objects.filter(programme_id=7) \
            .filter(home_lc_name='Volos (EXP)')
        
        signups = SignupPerson.objects.exclude(
            Q(selected_programmes__icontains='8') | Q(selected_programmes__icontains='9')
        )
        
        # Apply date filters if provided
        if start_date:
            try:
                start_datetime = parse_datetime(start_date) or timezone.make_aware(datetime.strptime(start_date, '%Y-%m-%d'))
                applications = applications.filter(created_at__gte=start_datetime)
                signups = signups.filter(created_at__gte=start_datetime)
            except (ValueError, TypeError):
                pass
        
        if end_date:
            try:
                end_datetime = parse_datetime(end_date) or timezone.make_aware(datetime.strptime(end_date, '%Y-%m-%d'))
                # Add one day to include the end date
                end_datetime = end_datetime + timedelta(days=1)
                applications = applications.filter(created_at__lt=end_datetime)
                signups = signups.filter(created_at__lt=end_datetime)
            except (ValueError, TypeError):
                pass

        # Get signups aggregated by month
        signups_data = signups.annotate(month=TruncMonth("created_at")).values("month").annotate(count=Count("id"))

        timeline = format_timeline_data(applications, signups_data, programme_id=7)
        return JsonResponse({"timeline": timeline})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def get_IE_Volos_ogta_timeline(request):
    try:
        # Get date filters from request
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        
        # Base queryset
        applications = ExpaApplication.objects.filter(programme_id=8) \
            .filter(home_lc_name='Volos (EXP)')
        
        signups = SignupPerson.objects.exclude(
            Q(selected_programmes__icontains='7') | Q(selected_programmes__icontains='9')
        )
        
        # Apply date filters if provided
        if start_date:
            try:
                start_datetime = parse_datetime(start_date) or timezone.make_aware(datetime.strptime(start_date, '%Y-%m-%d'))
                applications = applications.filter(created_at__gte=start_datetime)
                signups = signups.filter(created_at__gte=start_datetime)
            except (ValueError, TypeError):
                pass
        
        if end_date:
            try:
                end_datetime = parse_datetime(end_date) or timezone.make_aware(datetime.strptime(end_date, '%Y-%m-%d'))
                # Add one day to include the end date
                end_datetime = end_datetime + timedelta(days=1)
                applications = applications.filter(created_at__lt=end_datetime)
                signups = signups.filter(created_at__lt=end_datetime)
            except (ValueError, TypeError):
                pass

        # Get signups aggregated by month
        signups_data = signups.annotate(month=TruncMonth("created_at")).values("month").annotate(count=Count("id"))

        timeline = format_timeline_data(applications, signups_data, programme_id=8)
        return JsonResponse({"timeline": timeline})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def get_IE_Volos_ogte_timeline(request):
    """OGTe Timeline: Programme ID 9 + Person Home LC Volos (EXP)"""
    try:
        # Get date filters from request
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        
        # Base queryset
        applications = ExpaApplication.objects.filter(programme_id=9) \
            .filter(home_lc_name='Volos (EXP)')
        
        signups = SignupPerson.objects.exclude(
            Q(selected_programmes__icontains='7') | Q(selected_programmes__icontains='8')
        )
        
        # Apply date filters if provided
        if start_date:
            try:
                start_datetime = parse_datetime(start_date) or timezone.make_aware(datetime.strptime(start_date, '%Y-%m-%d'))
                applications = applications.filter(created_at__gte=start_datetime)
                signups = signups.filter(created_at__gte=start_datetime)
            except (ValueError, TypeError):
                pass
        
        if end_date:
            try:
                end_datetime = parse_datetime(end_date) or timezone.make_aware(datetime.strptime(end_date, '%Y-%m-%d'))
                # Add one day to include the end date
                end_datetime = end_datetime + timedelta(days=1)
                applications = applications.filter(created_at__lt=end_datetime)
                signups = signups.filter(created_at__lt=end_datetime)
            except (ValueError, TypeError):
                pass

        # Get signups aggregated by month
        signups_data = signups.annotate(month=TruncMonth("created_at")).values("month").annotate(count=Count("id"))

        timeline = format_timeline_data(applications, signups_data, programme_id=9)
        return JsonResponse({"timeline": timeline})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def get_IE_Volos_igv_timeline(request):
    """IGV Timeline: Programme ID 7 + Opportunity Home LC Volos (EXP)"""
    try:
        timeline = defaultdict(lambda: {"APP": 0, "ACC": 0, "APD": 0, "REA": 0})

        # Applications (APP)
        applied = ExpaApplication.objects.filter(programme_id=7) \
            .filter(home_lc_name_opportunity='Volos (EXP)') \
            .exclude(created_at=None) \
            .annotate(month=TruncMonth("created_at")).values("month").annotate(count=Count("id"))
        
        for item in applied:
            month = item["month"].strftime("%Y-%m")
            timeline[month]["APP"] += item["count"]

        # Accepted (ACC)
        accepted = ExpaApplication.objects.filter(programme_id=7) \
            .filter(home_lc_name_opportunity='Volos (EXP)') \
            .exclude(date_matched=None) \
            .annotate(month=TruncMonth("date_matched")).values("month").annotate(count=Count("id"))

        for item in accepted:
            month = item["month"].strftime("%Y-%m")
            timeline[month]["ACC"] += item["count"]

        # Approved (APD)
        approved = ExpaApplication.objects.filter(programme_id=7) \
            .filter(home_lc_name_opportunity='Volos (EXP)') \
            .exclude(date_approved=None) \
            .annotate(month=TruncMonth("date_approved")).values("month").annotate(count=Count("id"))

        for item in approved:
            month = item["month"].strftime("%Y-%m")
            timeline[month]["APD"] += item["count"]

        # Realized (REA)
        realized = ExpaApplication.objects.filter(programme_id=7) \
            .filter(home_lc_name_opportunity='Volos (EXP)') \
            .exclude(date_realized=None) \
            .annotate(month=TruncMonth("date_realized")).values("month").annotate(count=Count("id"))

        for item in realized:
            month = item["month"].strftime("%Y-%m")
            timeline[month]["REA"] += item["count"]

        # Convert to sorted list
        timeline_list = [
            {
                "date": month,
                "APP": data["APP"],
                "ACC": data["ACC"],
                "APD": data["APD"],
                "REA": data["REA"],
            }
            for month, data in sorted(timeline.items())
        ]

        return JsonResponse({"timeline": timeline_list})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def get_IE_Volos_igta_timeline(request):
    """IGTa Timeline: Programme ID 8 + Opportunity Home LC Volos (EXP)"""
    try:
        timeline = defaultdict(lambda: {"APP": 0, "ACC": 0, "APD": 0, "REA": 0})

        # Applications (APP)
        applied = ExpaApplication.objects.filter(programme_id=8) \
            .filter(home_lc_name_opportunity='Volos (EXP)') \
            .exclude(created_at=None) \
            .annotate(month=TruncMonth("created_at")).values("month").annotate(count=Count("id"))
        
        for item in applied:
            month = item["month"].strftime("%Y-%m")
            timeline[month]["APP"] += item["count"]

        # Accepted (ACC)
        accepted = ExpaApplication.objects.filter(programme_id=8) \
            .filter(home_lc_name_opportunity='Volos (EXP)') \
            .exclude(date_matched=None) \
            .annotate(month=TruncMonth("date_matched")).values("month").annotate(count=Count("id"))

        for item in accepted:
            month = item["month"].strftime("%Y-%m")
            timeline[month]["ACC"] += item["count"]

        # Approved (APD)
        approved = ExpaApplication.objects.filter(programme_id=8) \
            .filter(home_lc_name_opportunity='Volos (EXP)') \
            .exclude(date_approved=None) \
            .annotate(month=TruncMonth("date_approved")).values("month").annotate(count=Count("id"))

        for item in approved:
            month = item["month"].strftime("%Y-%m")
            timeline[month]["APD"] += item["count"]

        # Realized (REA)
        realized = ExpaApplication.objects.filter(programme_id=8) \
            .filter(home_lc_name_opportunity='Volos (EXP)') \
            .exclude(date_realized=None) \
            .annotate(month=TruncMonth("date_realized")).values("month").annotate(count=Count("id"))

        for item in realized:
            month = item["month"].strftime("%Y-%m")
            timeline[month]["REA"] += item["count"]

        # Convert to sorted list
        timeline_list = [
            {
                "date": month,
                "APP": data["APP"],
                "ACC": data["ACC"],
                "APD": data["APD"],
                "REA": data["REA"],
            }
            for month, data in sorted(timeline.items())
        ]

        return JsonResponse({"timeline": timeline_list})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)




#IE UOI Chart

def format_timeline_data(applications, signups, programme_id):
    """Helper function to format timeline data"""
    timeline = defaultdict(lambda: {"SU": 0, "APP": 0, "ACC": 0, "APD": 0, "REA": 0})

    for item in signups:
        month = item["month"].strftime("%Y-%m")
        timeline[month]["SU"] = item["count"]

    for ep in applications:
        if ep.created_at:
            month = ep.created_at.strftime("%Y-%m")
            timeline[month]["APP"] += 1
        if ep.date_matched:
            month = ep.date_matched.strftime("%Y-%m")
            timeline[month]["ACC"] += 1
        if ep.date_approved:
            month = ep.date_approved.strftime("%Y-%m")
            timeline[month]["APD"] += 1
        if ep.date_realized:
            month = ep.date_realized.strftime("%Y-%m")
            timeline[month]["REA"] += 1

    return sorted([
        {
            "date": month,
            "SU": data["SU"],
            "APP": data["APP"],
            "ACC": data["ACC"],
            "APD": data["APD"],
            "REA": data["REA"],
        }
        for month, data in timeline.items()
    ], key=lambda x: x["date"])


def get_IE_UOI_ogv_timeline(request):
    try:
        # Get date filters from request
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        
        # Base queryset
        applications = ExpaApplication.objects.filter(programme_id=7) \
            .filter(home_lc_name='UoI (EXP)')
        
        signups = SignupPerson.objects.exclude(
            Q(selected_programmes__icontains='8') | Q(selected_programmes__icontains='9')
        )
        
        # Apply date filters if provided
        if start_date:
            try:
                start_datetime = parse_datetime(start_date) or timezone.make_aware(datetime.strptime(start_date, '%Y-%m-%d'))
                applications = applications.filter(created_at__gte=start_datetime)
                signups = signups.filter(created_at__gte=start_datetime)
            except (ValueError, TypeError):
                pass
        
        if end_date:
            try:
                end_datetime = parse_datetime(end_date) or timezone.make_aware(datetime.strptime(end_date, '%Y-%m-%d'))
                # Add one day to include the end date
                end_datetime = end_datetime + timedelta(days=1)
                applications = applications.filter(created_at__lt=end_datetime)
                signups = signups.filter(created_at__lt=end_datetime)
            except (ValueError, TypeError):
                pass

        # Get signups aggregated by month
        signups_data = signups.annotate(month=TruncMonth("created_at")).values("month").annotate(count=Count("id"))

        timeline = format_timeline_data(applications, signups_data, programme_id=7)
        return JsonResponse({"timeline": timeline})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def get_IE_UOI_ogta_timeline(request):
    try:
        # Get date filters from request
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        
        # Base queryset
        applications = ExpaApplication.objects.filter(programme_id=8) \
            .filter(home_lc_name='UoI (EXP)')
        
        signups = SignupPerson.objects.exclude(
            Q(selected_programmes__icontains='7') | Q(selected_programmes__icontains='9')
        )
        
        # Apply date filters if provided
        if start_date:
            try:
                start_datetime = parse_datetime(start_date) or timezone.make_aware(datetime.strptime(start_date, '%Y-%m-%d'))
                applications = applications.filter(created_at__gte=start_datetime)
                signups = signups.filter(created_at__gte=start_datetime)
            except (ValueError, TypeError):
                pass
        
        if end_date:
            try:
                end_datetime = parse_datetime(end_date) or timezone.make_aware(datetime.strptime(end_date, '%Y-%m-%d'))
                # Add one day to include the end date
                end_datetime = end_datetime + timedelta(days=1)
                applications = applications.filter(created_at__lt=end_datetime)
                signups = signups.filter(created_at__lt=end_datetime)
            except (ValueError, TypeError):
                pass

        # Get signups aggregated by month
        signups_data = signups.annotate(month=TruncMonth("created_at")).values("month").annotate(count=Count("id"))

        timeline = format_timeline_data(applications, signups_data, programme_id=8)
        return JsonResponse({"timeline": timeline})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def get_IE_UOI_ogte_timeline(request):
    """OGTe Timeline: Programme ID 9 + Person Home LC Volos (EXP)"""
    try:
        # Get date filters from request
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        
        # Base queryset
        applications = ExpaApplication.objects.filter(programme_id=9) \
            .filter(home_lc_name='UoI (EXP)')
        
        signups = SignupPerson.objects.exclude(
            Q(selected_programmes__icontains='7') | Q(selected_programmes__icontains='8')
        )
        
        # Apply date filters if provided
        if start_date:
            try:
                start_datetime = parse_datetime(start_date) or timezone.make_aware(datetime.strptime(start_date, '%Y-%m-%d'))
                applications = applications.filter(created_at__gte=start_datetime)
                signups = signups.filter(created_at__gte=start_datetime)
            except (ValueError, TypeError):
                pass
        
        if end_date:
            try:
                end_datetime = parse_datetime(end_date) or timezone.make_aware(datetime.strptime(end_date, '%Y-%m-%d'))
                # Add one day to include the end date
                end_datetime = end_datetime + timedelta(days=1)
                applications = applications.filter(created_at__lt=end_datetime)
                signups = signups.filter(created_at__lt=end_datetime)
            except (ValueError, TypeError):
                pass

        # Get signups aggregated by month
        signups_data = signups.annotate(month=TruncMonth("created_at")).values("month").annotate(count=Count("id"))

        timeline = format_timeline_data(applications, signups_data, programme_id=9)
        return JsonResponse({"timeline": timeline})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def get_IE_UOI_igv_timeline(request):
    """IGV Timeline: Programme ID 7 + Opportunity Home LC Volos (EXP)"""
    try:
        timeline = defaultdict(lambda: {"APP": 0, "ACC": 0, "APD": 0, "REA": 0})

        # Applications (APP)
        applied = ExpaApplication.objects.filter(programme_id=7) \
            .filter(home_lc_name_opportunity='UoI (EXP)') \
            .exclude(created_at=None) \
            .annotate(month=TruncMonth("created_at")).values("month").annotate(count=Count("id"))
        
        for item in applied:
            month = item["month"].strftime("%Y-%m")
            timeline[month]["APP"] += item["count"]

        # Accepted (ACC)
        accepted = ExpaApplication.objects.filter(programme_id=7) \
            .filter(home_lc_name_opportunity='UoI (EXP)') \
            .exclude(date_matched=None) \
            .annotate(month=TruncMonth("date_matched")).values("month").annotate(count=Count("id"))

        for item in accepted:
            month = item["month"].strftime("%Y-%m")
            timeline[month]["ACC"] += item["count"]

        # Approved (APD)
        approved = ExpaApplication.objects.filter(programme_id=7) \
            .filter(home_lc_name_opportunity='UoI (EXP)') \
            .exclude(date_approved=None) \
            .annotate(month=TruncMonth("date_approved")).values("month").annotate(count=Count("id"))

        for item in approved:
            month = item["month"].strftime("%Y-%m")
            timeline[month]["APD"] += item["count"]

        # Realized (REA)
        realized = ExpaApplication.objects.filter(programme_id=7) \
            .filter(home_lc_name_opportunity='UoI (EXP)') \
            .exclude(date_realized=None) \
            .annotate(month=TruncMonth("date_realized")).values("month").annotate(count=Count("id"))

        for item in realized:
            month = item["month"].strftime("%Y-%m")
            timeline[month]["REA"] += item["count"]

        # Convert to sorted list
        timeline_list = [
            {
                "date": month,
                "APP": data["APP"],
                "ACC": data["ACC"],
                "APD": data["APD"],
                "REA": data["REA"],
            }
            for month, data in sorted(timeline.items())
        ]

        return JsonResponse({"timeline": timeline_list})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def get_IE_UOI_igta_timeline(request):
    """IGTa Timeline: Programme ID 8 + Opportunity Home LC UoI (EXP)"""
    try:
        timeline = defaultdict(lambda: {"APP": 0, "ACC": 0, "APD": 0, "REA": 0})

        # Applications (APP)
        applied = ExpaApplication.objects.filter(programme_id=8) \
            .filter(home_lc_name_opportunity='UoI (EXP)') \
            .exclude(created_at=None) \
            .annotate(month=TruncMonth("created_at")).values("month").annotate(count=Count("id"))
        
        for item in applied:
            month = item["month"].strftime("%Y-%m")
            timeline[month]["APP"] += item["count"]

        # Accepted (ACC)
        accepted = ExpaApplication.objects.filter(programme_id=8) \
            .filter(home_lc_name_opportunity='UoI (EXP)') \
            .exclude(date_matched=None) \
            .annotate(month=TruncMonth("date_matched")).values("month").annotate(count=Count("id"))

        for item in accepted:
            month = item["month"].strftime("%Y-%m")
            timeline[month]["ACC"] += item["count"]

        # Approved (APD)
        approved = ExpaApplication.objects.filter(programme_id=8) \
            .filter(home_lc_name_opportunity='UoI (EXP)') \
            .exclude(date_approved=None) \
            .annotate(month=TruncMonth("date_approved")).values("month").annotate(count=Count("id"))

        for item in approved:
            month = item["month"].strftime("%Y-%m")
            timeline[month]["APD"] += item["count"]

        # Realized (REA)
        realized = ExpaApplication.objects.filter(programme_id=8) \
            .filter(home_lc_name_opportunity='UoI (EXP)') \
            .exclude(date_realized=None) \
            .annotate(month=TruncMonth("date_realized")).values("month").annotate(count=Count("id"))

        for item in realized:
            month = item["month"].strftime("%Y-%m")
            timeline[month]["REA"] += item["count"]

        # Convert to sorted list
        timeline_list = [
            {
                "date": month,
                "APP": data["APP"],
                "ACC": data["ACC"],
                "APD": data["APD"],
                "REA": data["REA"],
            }
            for month, data in sorted(timeline.items())
        ]

        return JsonResponse({"timeline": timeline_list})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)







# Background Scheduler for Automatic Data Sync
logger = logging.getLogger(__name__)
scheduler_thread = None
scheduler_running = False

def run_auto_sync():
    """Background task that runs sync every 12 hours"""
    global scheduler_running
    
    while scheduler_running:
        try:
            logger.info("🔄 Starting automatic EXPA data sync...")
            
            # Run sync_expa_data
            try:
                from django.test import RequestFactory
                factory = RequestFactory()
                request = factory.get('/api/sync-expa-data/')
                result = sync_expa_data(request)
                logger.info("✅ EXPA Applications sync completed")
            except Exception as e:
                logger.error(f"❌ EXPA Applications sync failed: {str(e)}")
            
            # Run sync_signup_people
            try:
                request = factory.get('/api/sync_signup_people/')
                result = sync_signup_people(request)
                logger.info("✅ Signup People sync completed")
            except Exception as e:
                logger.error(f"❌ Signup People sync failed: {str(e)}")
            
            logger.info("🎉 Automatic sync cycle completed successfully!")
            
            # Wait for 12 hours (43200 seconds)
            time.sleep(43200)
            
        except Exception as e:
            logger.error(f"❌ Error in auto sync: {str(e)}")
            time.sleep(3600)  # Wait 1 hour before retrying if there's an error

def start_auto_sync_scheduler():
    """Start the background scheduler"""
    global scheduler_thread, scheduler_running
    
    if not scheduler_running:
        scheduler_running = True
        scheduler_thread = threading.Thread(target=run_auto_sync, daemon=True)
        scheduler_thread.start()
        logger.info("🚀 Auto sync scheduler started - syncing every 12 hours")
        return True
    return False

def stop_auto_sync_scheduler():
    """Stop the background scheduler"""
    global scheduler_running
    scheduler_running = False
    logger.info("🛑 Auto sync scheduler stopped")
    return True

# Views for scheduler control
@csrf_exempt
def start_scheduler_view(request):
    """API endpoint to start the scheduler"""
    try:
        if start_auto_sync_scheduler():
            return JsonResponse({
                "status": "success", 
                "message": "Auto sync scheduler started - syncing every 12 hours"
            })
        else:
            return JsonResponse({
                "status": "info", 
                "message": "Auto sync scheduler is already running"
            })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
def stop_scheduler_view(request):
    """API endpoint to stop the scheduler"""
    try:
        stop_auto_sync_scheduler()
        return JsonResponse({
            "status": "success", 
            "message": "Auto sync scheduler stopped"
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

def scheduler_status_view(request):
    """API endpoint to check scheduler status"""
    global scheduler_running, scheduler_thread
    return JsonResponse({
        "running": scheduler_running,
        "thread_alive": scheduler_thread.is_alive() if scheduler_thread else False,
        "message": "Scheduler is running - syncing every 12 hours" if scheduler_running else "Scheduler is stopped"
    })

def manual_sync_view(request):
    """API endpoint to trigger manual sync immediately"""
    try:
        logger.info("🔄 Manual sync triggered...")
        
        # Run both sync functions
        from django.test import RequestFactory
        factory = RequestFactory()
        
        # Sync applications
        request_apps = factory.get('/api/sync-expa-data/')
        result_apps = sync_expa_data(request_apps)
        
        # Sync people
        request_people = factory.get('/api/sync_signup_people/')
        result_people = sync_signup_people(request_people)
        
        return JsonResponse({
            "status": "success",
            "message": "Manual sync completed successfully",
            "applications_sync": "completed",
            "people_sync": "completed"
        })
        
    except Exception as e:
        logger.error(f"❌ Manual sync failed: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)