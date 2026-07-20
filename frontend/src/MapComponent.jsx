import React, { useEffect, useState, useCallback, useRef } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Circle, useMapEvents } from 'react-leaflet';
import L from 'leaflet';

// Fix default marker icons
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

const cityIcon = new L.Icon({
  iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-blue.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

const hotspotIcon = new L.Icon({
  iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-red.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

const DELHI_STATIONS = [
  { name: 'Anand Vihar', lat: 28.646, lon: 77.315 },
  { name: 'RK Puram', lat: 28.567, lon: 77.180 },
  { name: 'Dwarka', lat: 28.590, lon: 77.040 },
  { name: 'ITO', lat: 28.629, lon: 77.240 },
  { name: 'Punjabi Bagh', lat: 28.670, lon: 77.130 },
  { name: 'Okhla Phase 2', lat: 28.540, lon: 77.270 },
  { name: 'Noida', lat: 28.610, lon: 77.360 },
  { name: 'Gurugram', lat: 28.440, lon: 77.020 },
  { name: 'Ghaziabad', lat: 28.670, lon: 77.440 },
  { name: 'Faridabad', lat: 28.410, lon: 77.310 },
  { name: 'Bawana', lat: 28.780, lon: 77.030 },
  { name: 'Mundka', lat: 28.680, lon: 77.020 },
];

const MUMBAI_STATIONS = [
  { name: 'Bandra', lat: 19.060, lon: 72.840 },
  { name: 'Colaba', lat: 18.910, lon: 72.810 },
  { name: 'Andheri', lat: 19.120, lon: 72.860 },
  { name: 'Worli', lat: 19.020, lon: 72.810 },
  { name: 'Mazgaon', lat: 18.970, lon: 72.840 },
];

function getAQIColor(aqi) {
  if (aqi <= 50) return '#00E400';
  if (aqi <= 100) return '#FFFF00';
  if (aqi <= 150) return '#FF7E00';
  if (aqi <= 200) return '#FF0000';
  if (aqi <= 300) return '#8F3F97';
  return '#7E0023';
}

function MapClickHandler({ onMapClick, onStationClick }) {
  useMapEvents({
    click: (e) => {
      if (onMapClick) onMapClick(e.latlng);
    },
  });
  return null;
}

export default function MapComponent({ aqiData, onEnforceTrigger, onStationClick, showMumbai = false }) {
  const [clickedPos, setClickedPos] = useState(null);
  const [forecastSlider, setForecastSlider] = useState(0);
  const mapRef = useRef(null);

  const handleMapClick = useCallback((latlng) => {
    setClickedPos(latlng);
    if (onEnforceTrigger) onEnforceTrigger(latlng);
  }, [onEnforceTrigger]);

  const handleStationMarkClick = useCallback((station, latlng) => {
    setClickedPos(latlng);
    // Station selection already starts the enforcement query in Dashboard.
    // Avoid a second call here, which would duplicate a costly agent run.
    if (onStationClick) onStationClick(station, latlng);
  }, [onEnforceTrigger, onStationClick]);

  // Extract station data from aqiData
  const allStations = [];
  if (aqiData) {
    Object.entries(aqiData).forEach(([city, wards]) => {
      if (Array.isArray(wards)) {
        wards.forEach(w => {
          allStations.push({ ...w, city });
        });
      }
    });
  }

  const stations = showMumbai
    ? [...DELHI_STATIONS, ...MUMBAI_STATIONS]
    : DELHI_STATIONS;

  return (
    <div className="relative w-full h-full">
      <MapContainer
        center={[28.6139, 77.2090]}
        zoom={10}
        className="w-full h-full"
        zoomControl={true}
        ref={mapRef}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        <MapClickHandler onMapClick={handleMapClick} />

        {/* Delhi stations */}
        {stations.map((s) => {
          const stationData = allStations.find(w => w.station === s.name || w.ward === s.name);
          const aqi = stationData?.aqi || 200;
          const cat = stationData?.category || 'Very Unhealthy';
          return (
            <React.Fragment key={s.name}>
              <Circle
                center={[s.lat, s.lon]}
                radius={3000}
                pathOptions={{
                  color: getAQIColor(aqi),
                  fillColor: getAQIColor(aqi),
                  fillOpacity: 0.2,
                  weight: 2,
                }}
              />
              <Marker
                position={[s.lat, s.lon]}
                icon={aqi >= 200 ? hotspotIcon : cityIcon}
                eventHandlers={{
                  click: () => handleStationMarkClick(s.name, { lat: s.lat, lng: s.lon }),
                }}
              >
                <Popup>
                  <div className="text-gray-900 min-w-[180px]">
                    <strong className="text-base">{s.name}</strong><br />
                    <span className="text-sm">
                      AQI: <span style={{ color: getAQIColor(aqi), fontWeight: 'bold' }}>{aqi}</span>
                    </span><br />
                    <span className="text-xs text-gray-500">{cat}</span><br />
                    <span className="text-blue-600 text-[10px]">Click to run AI Enforcement →</span>
                  </div>
                </Popup>
              </Marker>
            </React.Fragment>
          );
        })}

        {/* Clicked position marker */}
        {clickedPos && (
          <Marker position={[clickedPos.lat, clickedPos.lng]}>
            <Popup>Enforcement query point</Popup>
          </Marker>
        )}
      </MapContainer>

      {/* Honest interaction cue: forecast detail is shown after selecting a station. */}
      <div className="absolute bottom-4 left-4 z-[1000] bg-gray-900/80 backdrop-blur-sm px-3 py-2 rounded-lg border border-gray-700">
        <p className="text-[11px] font-medium text-gray-200">Select a station to inspect its 72-hour forecast</p>
        <p className="text-[10px] text-gray-500 mt-0.5">Then run the evidence-to-intervention pipeline.</p>
      </div>

      {/* Map overlay hint */}
      <div className="absolute top-4 left-4 z-[1000] bg-gray-900/80 backdrop-blur-sm px-3 py-1.5 rounded-lg text-[11px] text-gray-300 border border-gray-700">
        {showMumbai ? 'Delhi + Mumbai · CAAQMS Stations' : 'Delhi · 12 CAAQMS Stations'}
      </div>
    </div>
  );
}