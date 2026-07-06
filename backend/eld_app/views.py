from rest_framework.decorators import api_view
from rest_framework.response import Response
import requests
import math

# FMCSA HOS Constants (70hr/8day property carrier)
MAX_DRIVING_HOURS = 11
MAX_ON_DUTY_HOURS = 14
MIN_REST_HOURS = 10
MAX_CYCLE_HOURS = 70
FUEL_INTERVAL_MILES = 1000
PICKUP_DROPOFF_HOURS = 1
AVERAGE_SPEED_MPH = 55


def get_route(origin, destination):
    """Get route distance and duration using OSRM (free, no API key)"""
    url = f"http://router.project-osrm.org/route/v1/driving/{origin[1]},{origin[0]};{destination[1]},{destination[0]}"
    params = {"overview": "full", "geometries": "geojson", "steps": "true"}
    try:
        res = requests.get(url, params=params, timeout=10)
        data = res.json()
        route = data["routes"][0]
        return {
            "distance_miles": route["distance"] * 0.000621371,
            "duration_hours": route["duration"] / 3600,
            "geometry": route["geometry"]["coordinates"],
        }
    except Exception as e:
        return None


def geocode(location):
    """Geocode a location string to [lat, lon] using Nominatim (free)"""
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": location, "format": "json", "limit": 1}
    headers = {"User-Agent": "ELD-Trip-Planner/1.0"}
    try:
        res = requests.get(url, params=params, headers=headers, timeout=10)
        data = res.json()
        if data:
            return [float(data[0]["lat"]), float(data[0]["lon"])]
        return None
    except:
        return None


def calculate_hos_schedule(total_miles, current_cycle_used):
    """
    Calculate HOS-compliant schedule and generate ELD log entries.
    Returns list of days with duty status changes.
    """
    remaining_cycle = MAX_CYCLE_HOURS - current_cycle_used
    miles_remaining = total_miles
    current_hour = 0  # hours since start of trip
    days = []
    day_num = 1
    fuel_miles = 0

    # Add pickup time at start
    events = []
    events.append({
        "status": "on_duty",
        "start": current_hour,
        "end": current_hour + PICKUP_DROPOFF_HOURS,
        "location": "Pickup Location",
        "note": "Pickup - loading"
    })
    current_hour += PICKUP_DROPOFF_HOURS
    on_duty_today = PICKUP_DROPOFF_HOURS
    driving_today = 0
    day_start_hour = 0

    while miles_remaining > 0:
        # Check if we need a 34hr restart
        if remaining_cycle <= 0:
            events.append({
                "status": "off_duty",
                "start": current_hour,
                "end": current_hour + 34,
                "location": "Rest Stop",
                "note": "34-hour restart"
            })
            current_hour += 34
            remaining_cycle = MAX_CYCLE_HOURS
            on_duty_today = 0
            driving_today = 0

        # Check if we've hit daily limits — need 10hr break
        if driving_today >= MAX_DRIVING_HOURS or on_duty_today >= MAX_ON_DUTY_HOURS:
            events.append({
                "status": "sleeper_berth",
                "start": current_hour,
                "end": current_hour + MIN_REST_HOURS,
                "location": "Rest Stop",
                "note": "Required 10-hour rest"
            })
            current_hour += MIN_REST_HOURS
            on_duty_today = 0
            driving_today = 0

        # How many hours can we drive this stretch?
        drive_hours_available = min(
            MAX_DRIVING_HOURS - driving_today,
            MAX_ON_DUTY_HOURS - on_duty_today,
            remaining_cycle
        )

        # 30 min break required after 8hrs driving
        if driving_today >= 8 and drive_hours_available > 0:
            events.append({
                "status": "off_duty",
                "start": current_hour,
                "end": current_hour + 0.5,
                "location": "Rest Area",
                "note": "30-minute required break"
            })
            current_hour += 0.5
            on_duty_today += 0.5
            drive_hours_available = min(drive_hours_available, MAX_DRIVING_HOURS - driving_today)

        if drive_hours_available <= 0:
            continue

        # Calculate miles we can cover
        max_miles_this_stretch = drive_hours_available * AVERAGE_SPEED_MPH

        # Check fueling stop
        miles_to_fuel = FUEL_INTERVAL_MILES - fuel_miles
        if miles_to_fuel < max_miles_this_stretch and miles_remaining > miles_to_fuel:
            # Drive to fuel stop
            drive_hours = miles_to_fuel / AVERAGE_SPEED_MPH
            events.append({
                "status": "driving",
                "start": current_hour,
                "end": current_hour + drive_hours,
                "location": "En Route",
                "note": f"Driving ({miles_to_fuel:.0f} miles)"
            })
            current_hour += drive_hours
            driving_today += drive_hours
            on_duty_today += drive_hours
            remaining_cycle -= drive_hours
            miles_remaining -= miles_to_fuel
            fuel_miles = 0

            # Fuel stop (on-duty, not driving)
            events.append({
                "status": "on_duty",
                "start": current_hour,
                "end": current_hour + 0.5,
                "location": "Fuel Stop",
                "note": "Fueling stop"
            })
            current_hour += 0.5
            on_duty_today += 0.5
            remaining_cycle -= 0.5
        else:
            # Drive remaining miles or until limit
            miles_this_stretch = min(miles_remaining, max_miles_this_stretch)
            drive_hours = miles_this_stretch / AVERAGE_SPEED_MPH
            events.append({
                "status": "driving",
                "start": current_hour,
                "end": current_hour + drive_hours,
                "location": "En Route",
                "note": f"Driving ({miles_this_stretch:.0f} miles)"
            })
            current_hour += drive_hours
            driving_today += drive_hours
            on_duty_today += drive_hours
            remaining_cycle -= drive_hours
            fuel_miles += miles_this_stretch
            miles_remaining -= miles_this_stretch

    # Dropoff
    events.append({
        "status": "on_duty",
        "start": current_hour,
        "end": current_hour + PICKUP_DROPOFF_HOURS,
        "location": "Dropoff Location",
        "note": "Dropoff - unloading"
    })
    current_hour += PICKUP_DROPOFF_HOURS

    # Final rest
    events.append({
        "status": "off_duty",
        "start": current_hour,
        "end": current_hour + MIN_REST_HOURS,
        "location": "Dropoff Location",
        "note": "End of trip rest"
    })

    # Group events into days (24hr blocks)
    total_hours = current_hour + MIN_REST_HOURS
    num_days = math.ceil(total_hours / 24)

    daily_logs = []
    for day in range(num_days):
        day_start = day * 24
        day_end = day_start + 24
        day_events = []
        for event in events:
            # Clip event to this day
            start = max(event["start"], day_start) - day_start
            end = min(event["end"], day_end) - day_start
            if end > start:
                day_events.append({
                    "status": event["status"],
                    "start_hour": round(start, 2),
                    "end_hour": round(end, 2),
                    "note": event["note"],
                    "location": event["location"],
                })
        if day_events:
            daily_logs.append({
                "day": day + 1,
                "date": f"Day {day + 1}",
                "events": day_events,
                "total_driving": round(sum(e["end_hour"] - e["start_hour"] for e in day_events if e["status"] == "driving"), 2),
                "total_on_duty": round(sum(e["end_hour"] - e["start_hour"] for e in day_events if e["status"] in ["driving", "on_duty"]), 2),
            })

    return daily_logs


@api_view(['POST'])
def plan_trip(request):
    data = request.data
    current_location = data.get('current_location')
    pickup_location = data.get('pickup_location')
    dropoff_location = data.get('dropoff_location')
    current_cycle_used = float(data.get('current_cycle_used', 0))

    if not all([current_location, pickup_location, dropoff_location]):
        return Response({'error': 'Missing required fields'}, status=400)

    # Geocode all locations
    current_coords = geocode(current_location)
    pickup_coords = geocode(pickup_location)
    dropoff_coords = geocode(dropoff_location)

    if not all([current_coords, pickup_coords, dropoff_coords]):
        return Response({'error': 'Could not geocode one or more locations'}, status=400)

    # Get routes
    to_pickup = get_route(current_coords, pickup_coords)
    to_dropoff = get_route(pickup_coords, dropoff_coords)

    if not to_pickup or not to_dropoff:
        return Response({'error': 'Could not calculate route'}, status=400)

    total_miles = to_pickup['distance_miles'] + to_dropoff['distance_miles']

    # Build full route geometry
    full_geometry = to_pickup['geometry'] + to_dropoff['geometry']

    # Calculate HOS schedule
    daily_logs = calculate_hos_schedule(total_miles, current_cycle_used)

    return Response({
        'route': {
            'total_miles': round(total_miles, 1),
            'total_driving_hours': round(to_pickup['duration_hours'] + to_dropoff['duration_hours'], 1),
            'geometry': full_geometry,
            'stops': [
                {'name': 'Current Location', 'coords': current_coords, 'type': 'start'},
                {'name': 'Pickup', 'coords': pickup_coords, 'type': 'pickup'},
                {'name': 'Dropoff', 'coords': dropoff_coords, 'type': 'dropoff'},
            ]
        },
        'daily_logs': daily_logs,
        'summary': {
            'total_miles': round(total_miles, 1),
            'num_days': len(daily_logs),
            'current_cycle_used': current_cycle_used,
        }
    })