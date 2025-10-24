import requests
import json
from django.http import JsonResponse
from .models import ExpaApplication, SignupPerson, Opportunity, PodioSignupOGV, PodioSignupOGTa, PodioSignupOGTe
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


# Podio API Integration Functions
from .podio_utils import PodioService

# Podio API Configuration - Using your correct credentials
PODIO_CLIENT_ID = 'ogx-api'
PODIO_CLIENT_SECRET = '3kKrIxJarIExCyaO5dz8ITEwmreW9aDIXByOPrsJqulYJbe9qdANmEUHK3kE1gLG'
PODIO_USERNAME = 'mahmoud.fouda2@aiesec.net'
PODIO_PASSWORD = 'Mahmoud_2002'

PODIO_APPS = {
    'OGV': {
        'app_id': '19029784',
        'app_token': 'f1c78d50aada4a489a2ec48b5db20d53',
        'model': PodioSignupOGV
    },
    'OGTa': {
        'app_id': '24852426',
        'app_token': 'b9fc7bc8d6c446d198cff3ee567187d5',
        'model': PodioSignupOGTa
    },
    'OGTe': {
        'app_id': '24852685',
        'app_token': 'c96f7af4826d4c82933ae5650cbf0406',
        'model': PodioSignupOGTe
    }
}

def sync_podio_data(request, programme, max_items=None):
    """Sync data from Podio for a specific programme (OGV, OGTa, or OGTe)"""
    
    if programme not in PODIO_APPS:
        return JsonResponse({"error": f"Invalid programme: {programme}. Must be one of: {list(PODIO_APPS.keys())}"}, status=400)
    
    config = PODIO_APPS[programme]
    app_id = config['app_id']
    app_token = config['app_token']
    model_class = config['model']
    
    try:
        # Initialize PodioService with proper app token authentication
        podio_service = PodioService(
            auth_method='app_token',
            app_id=app_id,
            app_token=app_token,
            client_id=PODIO_CLIENT_ID,
            client_secret=PODIO_CLIENT_SECRET
        )
        
        # Test connection first
        logger.info(f"Testing Podio connection for {programme} (app_id: {app_id})")
        success, test_result = podio_service.test_connection(app_id=app_id)
        if not success:
            logger.error(f"Podio connection test failed for {programme}: {test_result}")
            return JsonResponse({
                "error": f"Podio connection failed for {programme}",
                "details": test_result
            }, status=500)
        
        # Get items from Podio using pagination to fetch more records
        logger.info(f"Fetching items from Podio app {app_id} for {programme} (max_items: {max_items})")
        success, result = podio_service.get_all_items(app_id, max_items=max_items)
        
        logger.info(f"DEBUG: get_all_items returned - success: {success}, result type: {type(result)}")
        logger.info(f"DEBUG: result content: {str(result)[:200]}...")
        
        if not success:
            logger.error(f"DEBUG: get_all_items failed - success={success}, result={result}")
            return JsonResponse({
                "error": f"Failed to fetch data from Podio API for {programme}",
                "details": result
            }, status=500)
        
        # Result should be the items list directly from get_all_items
        items = result
        
        logger.info(f"DEBUG: Items assigned - type: {type(items)}, length: {len(items) if items else 'None'}")
        logger.info(f"DEBUG: Items truthy check: {bool(items)}")
        
        if items:
            logger.info(f"DEBUG: Processing {len(items)} items - type of first item: {type(items[0])}")
            logger.info(f"DEBUG: First item keys: {list(items[0].keys()) if isinstance(items[0], dict) else 'Not a dict'}")
            logger.info(f"DEBUG: First item sample: {str(items[0])[:500]}...")
        else:
            logger.warning(f"DEBUG: No items to process - items is falsy")
            return JsonResponse({
                "status": "success",
                "message": f"{programme} data synced successfully (no new items)",
                "new_records": 0,
                "updated_records": 0,
                "total_processed": 0
            })
        
        synced_count = 0
        updated_count = 0
        
        logger.info(f"DEBUG: Starting to process {len(items)} items")
        for i, item in enumerate(items):
            logger.info(f"DEBUG: Processing item {i+1}/{len(items)}")
            try:
                # Extract item ID - check different possible fields
                item_id = None
                if isinstance(item, dict):
                    item_id = item.get('item_id') or item.get('id') or item.get('item', {}).get('id')
                    logger.info(f"DEBUG: Item ID found: {item_id}")
                    logger.info(f"DEBUG: Item keys: {list(item.keys())}")
                else:
                    logger.error(f"DEBUG: Item is not a dict, type: {type(item)}")
                    continue
                
                if not item_id:
                    logger.error(f"DEBUG: No item_id found in item: {item}")
                    continue
                
                item_id = str(item_id)
                
                # Debug: Print the complete item structure
                logger.info(f"DEBUG: Processing item {item_id}: {str(item)[:1000]}...")
                
                # Extract fields from Podio item
                fields = item.get('fields', [])
                logger.info(f"DEBUG: Found {len(fields)} fields in item {item_id}")
                
                field_data = {}
                
                # Map field external_ids and field_ids to our model fields
                field_mapping = {
                    # External IDs
                    'first-name': 'first_name',
                    'full-name': 'first_name',
                    'first_name': 'first_name',
                    'last-name': 'last_name',
                    'last-name-2': 'last_name',
                    'last_name': 'last_name',
                    'home-lc': 'home_lc',
                    'home-lc-4': 'home_lc',
                    'home_lc': 'home_lc',
                    'ep-id': 'ep_id',
                    'ep_id': 'ep_id',
                    'expa-id': 'ep_id',
                    # Field IDs (based on your Podio apps)
                    '193998525': 'first_name',    # First Name field ID
                    '241267894': 'last_name',     # Last Name field ID
                    '193793510': 'home_lc',       # Home LC field ID
                    '193794283': 'ep_id',         # EP ID field ID
                }
                
                for field in fields:
                    field_external_id = field.get('external_id', '').lower()
                    field_id = str(field.get('field_id', ''))
                    field_values = field.get('values', [])
                    
                    # Check both external_id and field_id
                    model_field = None
                    if field_external_id in field_mapping:
                        model_field = field_mapping[field_external_id]
                    elif field_id in field_mapping:
                        model_field = field_mapping[field_id]
                    
                    if field_values and model_field:
                        # Get the value based on field type
                        first_value = field_values[0]
                        
                        # Handle different value formats
                        if isinstance(first_value, dict):
                            value = first_value.get('value', '')
                            
                            # For category/app reference fields, get the text
                            if not value and 'text' in first_value:
                                value = first_value.get('text', '')
                            
                            # For app reference fields (like Home LC), get the title
                            if model_field == 'home_lc' and isinstance(value, dict):
                                value = value.get('title', '') or value.get('name', '')
                        else:
                            # Handle direct string values
                            value = str(first_value) if first_value else ''
                        
                        field_data[model_field] = str(value) if value else ''
                
                # Parse creation date
                created_at = None
                if item.get('created_on'):
                    try:
                        created_at = parse_datetime(item['created_on'])
                    except Exception as e:
                        logger.warning(f"Error parsing date for item {item_id}: {e}")
                
                # Create or update the record
                obj, created = model_class.objects.update_or_create(
                    podio_item_id=item_id,
                    defaults={
                        'first_name': field_data.get('first_name', ''),
                        'last_name': field_data.get('last_name', ''),
                        'created_at': created_at,
                        'home_lc': field_data.get('home_lc', ''),
                        'ep_id': field_data.get('ep_id', ''),
                    }
                )
                
                if created:
                    synced_count += 1
                    logger.info(f"Created new {programme} signup: {field_data.get('first_name', '')} {field_data.get('last_name', '')}")
                else:
                    updated_count += 1
                    logger.info(f"Updated {programme} signup: {field_data.get('first_name', '')} {field_data.get('last_name', '')}")
            
            except Exception as e:
                logger.error(f"Error processing item {item.get('item_id', 'unknown')}: {e}")
                continue
        
        return JsonResponse({
            "status": "success",
            "message": f"{programme} data synced successfully",
            "new_records": synced_count,
            "updated_records": updated_count,
            "total_processed": len(items)
        })
    
    except Exception as e:
        logger.error(f"Error syncing {programme} data: {str(e)}")
        return JsonResponse({"error": f"Error syncing {programme} data: {str(e)}"}, status=500)

def sync_podio_ogv(request, max_items=None):
    """Sync OGV signups from Podio"""
    return sync_podio_data(request, 'OGV', max_items=max_items)

def sync_podio_ogta(request, max_items=None):
    """Sync OGTa signups from Podio"""
    return sync_podio_data(request, 'OGTa', max_items=max_items)

def sync_podio_ogte(request, max_items=None):
    """Sync OGTe signups from Podio"""
    return sync_podio_data(request, 'OGTe', max_items=max_items)

def sync_all_podio_data(request):
    """Sync all Podio data (OGV, OGTa, OGTe)"""
    results = {}
    
    for programme in PODIO_APPS.keys():
        try:
            # Create a dummy request for each sync
            from django.test import RequestFactory
            factory = RequestFactory()
            dummy_request = factory.get(f'/api/sync-podio-{programme.lower()}/')
            
            # Call the sync function
            result = sync_podio_data(dummy_request, programme)
            
            if hasattr(result, 'content'):
                # If it's a JsonResponse, get the content
                result_data = json.loads(result.content.decode('utf-8'))
                results[programme] = result_data
            else:
                results[programme] = {"error": "Unknown response format"}
                
        except Exception as e:
            results[programme] = {"error": str(e)}
    
    # Check if all syncs were successful
    all_successful = all(result.get('status') == 'success' for result in results.values())
    
    return JsonResponse({
        "status": "success" if all_successful else "partial_success",
        "message": "All Podio data sync completed",
        "results": results
    })

def get_podio_signup_counts(request):
    """Get signup counts for all Podio programmes"""
    try:
        counts = {
            'OGV': PodioSignupOGV.objects.count(),
            'OGTa': PodioSignupOGTa.objects.count(),
            'OGTe': PodioSignupOGTe.objects.count(),
        }
        
        total = sum(counts.values())
        
        return JsonResponse({
            "status": "success",
            "counts": counts,
            "total": total
        })
    
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)