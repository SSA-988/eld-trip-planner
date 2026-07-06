import {
  MapContainer,
  TileLayer,
  Polyline,
  Marker,
  Popup,
} from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

// Fix leaflet default marker icons
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl:
    "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

const stopColors = {
  start: "#3b82f6",
  pickup: "#22c55e",
  dropoff: "#ef4444",
};

function TripMap({ routeData }) {
  const { geometry, stops, total_miles, total_driving_hours } = routeData;

  // geometry is [lon, lat] from OSRM — leaflet needs [lat, lon]
  const polylinePoints = geometry.map(([lon, lat]) => [lat, lon]);

  const center = polylinePoints[Math.floor(polylinePoints.length / 2)];

  const createIcon = (color) =>
    L.divIcon({
      className: "",
      html: `<div style="
      width:16px;height:16px;border-radius:50%;
      background:${color};border:3px solid white;
      box-shadow:0 2px 6px rgba(0,0,0,0.4)">
    </div>`,
      iconAnchor: [8, 8],
    });

  return (
    <div className="map-card">
      <h2>🗺️ Route Map</h2>
      <div className="map-stats">
        <span>📍 {total_miles} miles</span>
        <span>⏱️ {total_driving_hours} hrs driving</span>
        <span>🟢 Pickup → 🔴 Dropoff</span>
      </div>
      <MapContainer center={center} zoom={6} className="leaflet-map">
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution="© OpenStreetMap contributors"
        />
        <Polyline
          positions={polylinePoints}
          color="#3b82f6"
          weight={4}
          opacity={0.8}
        />
        {stops.map((stop) => (
          <Marker
            key={stop.type}
            position={[stop.coords[0], stop.coords[1]]}
            icon={createIcon(stopColors[stop.type])}
          >
            <Popup>
              <strong>{stop.name}</strong>
              <br />
              {stop.type.charAt(0).toUpperCase() + stop.type.slice(1)}
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  );
}

export default TripMap;
