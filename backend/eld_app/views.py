from rest_framework.decorators import api_view
from rest_framework.response import Response
import requests
import math
import time

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
        res = requests.get(url, params=params, timeout=30)
        data = res.json()
        if "routes" not in data or len(data["routes"]) == 0:
            return None
        route = data["routes"][0]
        return {
            "distance_miles": route["distance"] * 0.000621371,
            "duration_hours": route["duration"] / 3600,
            "geometry": route["geometry"]["coordinates"],
        }
    except Exception as e:
        print(f"Route error: {e}")
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
    remaining_cycle = MAX_CYCLE_HOURS - current_cycle_used
    miles_remaining = total_miles
    current_hour = 0
    fuel_miles = 0
    on_duty_today = 0
    driving_today = 0
    events = []

    # Pickup
    events.append({
        "status": "on_duty",
        "start": current_hour,
        "end": current_hour + PICKUP_DROPOFF_HOURS,
        "note": "Pickup - loading",
        "location": "Pickup Location"
    })
    current_hour += PICKUP_DROPOFF_HOURS
    on_duty_today += PICKUP_DROPOFF_HOURS

    max_iterations = 1000
    iteration = 0

    while miles_remaining > 0.1 and iteration < max_iterations:
        iteration += 1

        # Need 34hr restart?
        if remaining_cycle <= 0:
            events.append({"status": "off_duty", "start": current_hour, "end": current_hour + 34, "note": "34-hour restart", "location": "Rest Stop"})
            current_hour += 34
            remaining_cycle = MAX_CYCLE_HOURS
            on_duty_today = 0
            driving_today = 0
            continue

        # Need 10hr rest?
        if driving_today >= MAX_DRIVING_HOURS or on_duty_today >= MAX_ON_DUTY_HOURS:
            events.append({"status": "sleeper_berth", "start": current_hour, "end": current_hour + MIN_REST_HOURS, "note": "Required 10-hour rest", "location": "Rest Stop"})
            current_hour += MIN_REST_HOURS
            on_duty_today = 0
            driving_today = 0
            continue

        # 30 min break after 8hrs driving
        if driving_today >= 8:
            events.append({"status": "off_duty", "start": current_hour, "end": current_hour + 0.5, "note": "30-minute required break", "location": "Rest Area"})
            current_hour += 0.5
            on_duty_today += 0.5
            driving_today = 0
            continue

        # How much can we drive?
        drive_hours_available = min(
            MAX_DRIVING_HOURS - driving_today,
            MAX_ON_DUTY_HOURS - on_duty_today,
            remaining_cycle
        )

        if drive_hours_available <= 0:
            continue

        # Fuel stop needed?
        miles_to_fuel = FUEL_INTERVAL_MILES - fuel_miles
        miles_this_stretch = min(miles_remaining, drive_hours_available * AVERAGE_SPEED_MPH)

        if miles_to_fuel < miles_this_stretch:
            miles_this_stretch = miles_to_fuel
            drive_hours = miles_this_stretch / AVERAGE_SPEED_MPH
            events.append({"status": "driving", "start": current_hour, "end": current_hour + drive_hours, "note": f"Driving ({miles_this_stretch:.0f} miles)", "location": "En Route"})
            current_hour += drive_hours
            driving_today += drive_hours
            on_duty_today += drive_hours
            remaining_cycle -= drive_hours
            miles_remaining -= miles_this_stretch
            fuel_miles = 0

            # Fuel stop
            events.append({"status": "on_duty", "start": current_hour, "end": current_hour + 0.5, "note": "Fueling stop", "location": "Fuel Stop"})
            current_hour += 0.5
            on_duty_today += 0.5
            remaining_cycle -= 0.5
        else:
            drive_hours = miles_this_stretch / AVERAGE_SPEED_MPH
            events.append({"status": "driving", "start": current_hour, "end": current_hour + drive_hours, "note": f"Driving ({miles_this_stretch:.0f} miles)", "location": "En Route"})
            current_hour += drive_hours
            driving_today += drive_hours
            on_duty_today += drive_hours
            remaining_cycle -= drive_hours
            fuel_miles += miles_this_stretch
            miles_remaining -= miles_this_stretch

    # Dropoff
    events.append({"status": "on_duty", "start": current_hour, "end": current_hour + PICKUP_DROPOFF_HOURS, "note": "Dropoff - unloading", "location": "Dropoff Location"})
    current_hour += PICKUP_DROPOFF_HOURS

    # Final rest
    events.append({"status": "off_duty", "start": current_hour, "end": current_hour + MIN_REST_HOURS, "note": "End of trip rest", "location": "Dropoff Location"})
    current_hour += MIN_REST_HOURS

    # Group into days
    import math
    num_days = math.ceil(current_hour / 24)
    daily_logs = []

    for day in range(num_days):
        day_start = day * 24
        day_end = day_start + 24
        day_events = []
        for event in events:
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
    time.sleep(1)
    pickup_coords = geocode(pickup_location)
    time.sleep(1)
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