from django.shortcuts import render

from django.shortcuts import render, redirect
from django.contrib import messages
from .models import FoodDonation

def food_donation_form(request):
    if request.method == 'POST':
        food_name = request.POST.get('food_name')
        quantity = request.POST.get('quantity')
        category = request.POST.get('category')
        expiry_date = request.POST.get('expiry_date')
        location = request.POST.get('location')
        food_image = request.FILES.get('food_image')

        # Validate required fields
        if not (food_name and quantity and category and expiry_date and location):
            messages.error(request, "Please fill out all required fields.")
        else:
            # Save donation to database
            food_donation = FoodDonation(
                food_name=food_name,
                quantity=quantity,
                category=category,
                expiry_date=expiry_date,
                location=location,
                food_image=food_image,
            )
            food_donation.save()
            messages.success(request, "Your food donation has been submitted successfully.")
            return redirect('food_donations_list')

    return render(request, 'donation/food_donation.html')


def ngo_list(request):
    return render(request, 'donation/ngo_map.html')


from django.shortcuts import render
from .models import FoodDonation

def food_donations_list(request):
    donations = FoodDonation.objects.all()  # Fetch all food donations
    return render(request, 'donation/order_list.html', {'donations': donations})

from django.shortcuts import render
from django.http import JsonResponse
from django.template.loader import render_to_string
from geopy.distance import geodesic
import folium
import json

# Create the IndianFoodDeliverySystem class to manage the logic
class IndianFoodDeliverySystem:
    def __init__(self):
        self.locations = {
            'Food Banks': [
                {'name': 'Roti Bank', 'lat': 19.0760, 'lon': 72.8777, 'capacity': 800},  # Mumbai
                {'name': 'Annapurna Rasoi', 'lat': 19.2183, 'lon': 72.8479, 'capacity': 500},  # Navi Mumbai
                {'name': 'Sewa Sadan', 'lat': 18.9972, 'lon': 72.8344, 'capacity': 400}  # Mumbai
            ],
            'Restaurants & Hotels': [
                {'name': 'Taj Hotel Kitchen', 'lat': 18.9217, 'lon': 72.8330, 'surplus': 50},  # Mumbai
                {'name': 'Hyatt Regency', 'lat': 19.1173, 'lon': 72.8647, 'surplus': 75},  # Navi Mumbai
                {'name': 'ITC Maratha', 'lat': 19.1096, 'lon': 72.8494, 'surplus': 100}  # Mumbai
            ],
            'NGOs & Shelters': [
                {'name': 'Goonj Center', 'lat': 19.0760, 'lon': 72.8777, 'needs': 175},  # Mumbai
                {'name': 'Helping Hands', 'lat': 19.0272, 'lon': 72.8579, 'needs': 120},  # Mumbai
                {'name': 'Akshaya Patra', 'lat': 19.1302, 'lon': 72.8746, 'needs': 200}  # Navi Mumbai
            ],
            'Community Kitchens': [
                {'name': 'Mumbai Dabbawalas', 'lat': 19.0821, 'lon': 72.8805, 'capacity': 250},  # Mumbai
                {'name': 'Thane Roti Bank', 'lat': 19.2011, 'lon': 72.9648, 'capacity': 300},  # Thane
                {'name': 'Kalyan Seva Sadan', 'lat': 19.2456, 'lon': 73.1238, 'capacity': 180}  # Kalyan
            ]
        }

    def calculate_distance(self, point1, point2):
        return geodesic(point1, point2).kilometers

    def create_delivery_route(self, start_location, destinations):
        route = [start_location]
        remaining_destinations = destinations.copy()
        
        while remaining_destinations:
            current = route[-1]
            current_pos = (current['lat'], current['lon'])
            nearest = min(remaining_destinations, key=lambda x: self.calculate_distance(current_pos, (x['lat'], x['lon'])))
            route.append(nearest)
            remaining_destinations.remove(nearest)
        
        return route

def create_map(delivery_system, selected_route=None):
    # Generate folium map
    all_lats = [loc['lat'] for category in delivery_system.locations.values() for loc in category]
    all_lons = [loc['lon'] for category in delivery_system.locations.values() for loc in category]
    
    center_lat, center_lon = sum(all_lats) / len(all_lats), sum(all_lons) / len(all_lons)
    m = folium.Map(location=[center_lat, center_lon], zoom_start=10)
    
    colors = {'Food Banks': 'green', 'Restaurants & Hotels': 'red', 'NGOs & Shelters': 'blue', 'Community Kitchens': 'purple'}
    icons = {'Food Banks': 'home', 'Restaurants & Hotels': 'cutlery', 'NGOs & Shelters': 'heart', 'Community Kitchens': 'fire'}
    
    for category, locations in delivery_system.locations.items():
        for loc in locations:
            popup_content = f"{loc['name']}, {category}"
            folium.Marker(
                [loc['lat'], loc['lon']], 
                popup=popup_content,
                icon=folium.Icon(color=colors[category], icon=icons[category], prefix='fa')
            ).add_to(m)
    
    if selected_route:
        route_coords = [(loc['lat'], loc['lon']) for loc in selected_route]
        folium.PolyLine(route_coords, color="red", weight=2.5, opacity=1).add_to(m)
        
    return m

def index(request):
    delivery_system = IndianFoodDeliverySystem()
    m = create_map(delivery_system)
    return render(request, 'donation/route.html', {'map_html': m._repr_html_()})

def get_locations(request):
    delivery_system = IndianFoodDeliverySystem()
    locations = {
        category: [{"name": loc["name"], "lat": loc["lat"], "lon": loc["lon"]} for loc in locs]
        for category, locs in delivery_system.locations.items()
    }
    return JsonResponse(locations)

def generate_route(request):
    data = json.loads(request.body)
    start_location_name = data["start"]
    destination_names = data["destinations"]

    delivery_system = IndianFoodDeliverySystem()
    
    start_location = next((loc for category in delivery_system.locations.values() for loc in category if loc["name"] == start_location_name), None)
    destinations = [loc for category in delivery_system.locations.values() for loc in category if loc["name"] in destination_names]

    if not start_location or not destinations:
        return JsonResponse({"error": "Invalid locations selected."}, status=400)

    route = delivery_system.create_delivery_route(start_location, destinations)
    m = create_map(delivery_system, route)
    
    return JsonResponse({"map_html": m._repr_html_()})
