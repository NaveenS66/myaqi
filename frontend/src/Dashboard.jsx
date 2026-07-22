import React, { useState, useEffect, useCallback } from 'react';
import MapComponent from './MapComponent.jsx';

const AQI_API = '/api/aqi/current';
const ENFORCE_API = '/api/agent/enforce';
const ATTRIBUTION_API = '/api/attribution';
const FORECAST_API = '/api/forecast';
const METADATA_API = '/api/metadata';

const CATEGORY_COLORS = {
  'Good': 'bg-aqi-good text-black',
  'Moderate': 'bg-aqi-moderate text-black',
  'Unhealthy for Sensitive Groups': 'bg-aqi-sensitive text-white',
  'Unhealthy': 'bg-aqi-unhealthy text-white',
  'Very Unhealthy': 'bg-aqi-veryunhealthy text-white',
  'Hazardous': 'bg-aqi-hazardous text-white',
};

const LANGUAGE_OPTIONS = [
  { label: 'English', code: 'en' },
  { label: 'Hindi (à¤¹à¤¿à¤¨à¥à¤¦à¥€)', code: 'hi' },
  { label: 'Kannada (à²•à²¨à³à²¨à²¡)', code: 'kn' },
  { label: 'Tamil (à®¤à®®à®¿à®´à¯)', code: 'ta' },
];

const LANGUAGE_MAP = { en: 'English', hi: 'Hindi', kn: 'Kannada', ta: 'Tamil' };

function RiskBadge({ level }) {
  const colors = {
    critical: 'bg-red-600', high: 'bg-orange-500',
    medium: 'bg-yellow-500 text-black', low: 'bg-green-500',
  };
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-xs font-bold ${colors[level?.toLowerCase()] || 'bg-gray-500'}`}>
      {level?.toUpperCase() || 'UNKNOWN'}
    </span>
  );
}

function SourceChart({ categories }) {
  if (!categories) return null;
  const items = Object.entries(categories).filter(([k]) => k !== 'background');
  const colors = { traffic: '#3B82F6', industry: '#EF4444', construction: '#F97316', biomass_burning: '#A855F7' };
  return (
    <div className="space-y-1">
      {items.map(([key, val]) => (
        <div key={key} className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: colors[key] || '#6B7280' }} />
          <span className="text-[10px] text-gray-400 w-20 capitalize">{key.replace('_', ' ')}</span>
          <div className="flex-1 h-2 bg-gray-700 rounded-full overflow-hidden">
            <div className="h-full rounded-full transition-all duration-500"
                 style={{ width: `${val.percentage}%`, backgroundColor: colors[key] || '#6B7280' }} />
          </div>
          <span className="text-[10px] text-gray-400 w-10 text-right">{val.percentage}%</span>
          <span className="text-[9px] text-gray-600 w-12 text-right">c:{val.confidence}</span>
        </div>
      ))}
    </div>
  );
}

export default function Dashboard() {
  const [aqiData, setAqiData] = useState(null);
  const [enforcementResult, setEnforcementResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [enforcing, setEnforcing] = useState(false);
  const [error, setError] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [selectedLanguage, setSelectedLanguage] = useState('en');
  const [advisory, setAdvisory] = useState(null);
  const [activeStation, setActiveStation] = useState(null);
  const [showMumbai, setShowMumbai] = useState(false);
  const [metadata, setMetadata] = useState(null);
  const [forecastData, setForecastData] = useState(null);

  // Fetch AQI data on mount
  useEffect(() => {
    fetch(AQI_API)
      .then(res => res.json())
      .then(json => {
        if (json.status === 'ok') setAqiData(json.data);
        else setError('Failed to fetch AQI data');
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));

    fetch(METADATA_API)
      .then(res => res.json())
      .then(d => setMetadata(d))
      .catch(() => {});
  }, []);

  // Fetch forecast when station selected
  useEffect(() => {
    if (!activeStation) return;
    fetch(`${FORECAST_API}/${encodeURIComponent(activeStation)}?hours=72`)
      .then(res => res.json())
      .then(json => {
        if (json.status === 'ok') setForecastData(json);
      })
      .catch(() => {});
  }, [activeStation]);

  // Fetch advisory when language changes
  useEffect(() => {
    const city = activeStation || 'Anand Vihar';
    fetch(`/api/advisory/${encodeURIComponent(city)}?language=${selectedLanguage}`)
      .then(res => res.json())
      .then(json => { if (json.status === 'ok') setAdvisory(json); })
      .catch(() => {});
  }, [selectedLanguage, activeStation]);

  const handleLanguageChange = useCallback((e) => setSelectedLanguage(e.target.value), []);
  const toggleMumbai = useCallback(() => setShowMumbai(v => !v), []);

  // Handle station click
  const handleStationClick = useCallback(async (stationName, latlng) => {
    setActiveStation(stationName);
    setEnforcing(true);
    setEnforcementResult(null);
    try {
      const res = await fetch(ENFORCE_API, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lat: latlng.lat, lon: latlng.lng, radius_km: 15.0, language: selectedLanguage }),
      });
      const json = await res.json();
      if (json.status === 'ok') {
        setEnforcementResult(json);
        setSidebarOpen(true);
      } else {
        setError({
          severity: 'notice',
          message: json.message || 'Live evidence is unavailable at this location. No enforcement recommendation was generated.',
        });
      }
    } catch (err) {
      setError({ severity: 'error', message: `Enforcement connection error: ${err.message}` });
    } finally {
      setEnforcing(false);
    }
  }, [selectedLanguage]);

  // Handle map click
  const handleEnforceTrigger = useCallback(async (latlng) => {
    setEnforcing(true);
    setEnforcementResult(null);
    try {
      const res = await fetch(ENFORCE_API, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lat: latlng.lat, lon: latlng.lng, radius_km: 15.0, language: selectedLanguage }),
      });
      const json = await res.json();
      if (json.status === 'ok') {
        setEnforcementResult(json);
        setSidebarOpen(true);
      } else {
        setError({
          severity: 'notice',
          message: json.message || 'Live evidence is unavailable at this location. No enforcement recommendation was generated.',
        });
      }
    } catch (err) {
      setError({ severity: 'error', message: `Enforcement connection error: ${err.message}` });
    } finally {
      setEnforcing(false);
    }
  }, [selectedLanguage]);

  const forecastChart = forecastData?.forecast?.slice(0, 72) || [];
  const minAqi = forecastChart.length ? Math.min(...forecastChart.map(f => f.aqi)) : 0;
  const maxAqi = forecastChart.length ? Math.max(...forecastChart.map(f => f.aqi)) : 400;

  return (
    <div className="h-screen w-screen flex flex-col overflow-hidden bg-gray-900">
      {/* â”€â”€ Header â”€â”€ */}
      <header className="bg-gray-800/95 border-b border-gray-700 px-6 py-2.5 flex items-center justify-between shrink-0 backdrop-blur-sm z-10">
        <div className="flex items-center gap-3">
          <div className="w-7 h-7 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-xs font-bold">AQ</div>
          <div>
            <h1 className="text-base font-bold text-white tracking-tight">Urban Air Quality Intelligence</h1>
            <p className="text-[10px] text-gray-500 -mt-0.5">Station signals Â· Forecasting Â· Source attribution Â· Intervention</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {loading && <span className="text-gray-400 text-xs animate-pulse">Loading station observationsâ€¦</span>}

          {/* City toggle */}
          <button onClick={toggleMumbai}
            className={`text-xs px-2.5 py-1 rounded-lg border transition-colors ${
              showMumbai ? 'bg-blue-600 border-blue-500 text-white' : 'bg-gray-700 border-gray-600 text-gray-400 hover:text-white'
            }`}>
            {showMumbai ? 'Delhi + Mumbai' : 'Delhi'}
          </button>

          {/* Language selector */}
          <div className="relative">
            <select value={selectedLanguage} onChange={handleLanguageChange}
              className="appearance-none bg-gray-700 hover:bg-gray-600 text-gray-200 text-xs px-2.5 py-1 pr-7 rounded-lg border border-gray-600 cursor-pointer focus:outline-none focus:ring-2 focus:ring-blue-500">
              {LANGUAGE_OPTIONS.map(o => <option key={o.code} value={o.code}>{o.label}</option>)}
            </select>
            <svg className="absolute right-1.5 top-1/2 -translate-y-1/2 w-3 h-3 text-gray-400 pointer-events-none" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </div>

          <button onClick={() => setSidebarOpen(!sidebarOpen)}
            className="text-gray-400 hover:text-white text-xs bg-gray-700 px-2.5 py-1 rounded-lg border border-gray-600 transition-colors">
            {sidebarOpen ? 'Hide Panel' : 'Show Panel'}
          </button>
        </div>
      </header>

      {/* â”€â”€ Main Content â”€â”€ */}
      <div className="flex flex-1 overflow-hidden">
        <div className={`flex-1 relative transition-all duration-300 ${sidebarOpen ? 'w-2/3' : 'w-full'}`}>
          {error && (
            <div className={`absolute top-4 left-1/2 -translate-x-1/2 z-[1000] backdrop-blur-sm text-white px-4 py-2 rounded-lg text-sm shadow-lg ${
              error.severity === 'notice' ? 'bg-amber-600/90' : 'bg-red-600/90'
            }`}>
              {error.message}
              <button onClick={() => setError(null)} className="ml-3 text-white/70 hover:text-white">âœ•</button>
            </div>
          )}

          {aqiData && (
            <div className="absolute top-3 left-3 z-[700] max-w-sm rounded-lg border border-slate-600 bg-slate-900/95 px-3 py-2 text-[10px] text-slate-300 shadow-lg">
              <strong className="text-slate-100">Evidence-aware demo</strong>
              <span className="ml-1">Observed stations are shown as data arrives; unavailable values are never simulated as live readings.</span>
            </div>
          )}

          <MapComponent
            onEnforceTrigger={handleEnforceTrigger}
            onStationClick={handleStationClick}
            aqiData={aqiData}
            showMumbai={showMumbai}
          />

          {enforcing && (
            <div className="absolute inset-0 z-[500] bg-black/40 flex items-center justify-center">
              <div className="bg-gray-800 rounded-xl px-8 py-6 shadow-2xl border border-gray-700 text-center">
                <div className="animate-spin w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full mx-auto mb-3" />
                <p className="text-gray-300 text-sm">Running agent pipeline: Forecast â†’ Attribution â†’ Enforcement â†’ Advisory</p>
              </div>
            </div>
          )}
        </div>

        {/* â”€â”€ Sidebar â”€â”€ */}
        {sidebarOpen && (
          <aside className="w-[440px] bg-gray-800 border-l border-gray-700 flex flex-col overflow-hidden shrink-0">
            <div className="flex-1 overflow-y-auto sidebar-scroll">
              {/* City AQI Overview */}
              <div className="p-4 border-b border-gray-700">
                <h2 className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider mb-2.5">CAAQMS Station Overview</h2>
                {loading ? (
                  <div className="space-y-1.5">
                    {[1,2,3,4,5].map(i => <div key={i} className="h-8 bg-gray-700/50 rounded-lg animate-pulse" />)}
                  </div>
                ) : (
                  <div className="space-y-1">
                    {aqiData && Object.entries(aqiData).map(([city, wards]) =>
                      Array.isArray(wards) && wards.map((w, i) => (
                        <div key={`${city}-${i}`}
                          onClick={() => handleStationClick(w.ward || w.station, { lat: w.lat, lng: w.lon })}
                          className="flex items-center justify-between bg-gray-700/30 px-2.5 py-1.5 rounded-lg cursor-pointer hover:bg-gray-700/60 transition-colors">
                          <div className="flex items-center gap-2 min-w-0">
                            <div className="w-2 h-2 rounded-full shrink-0" style={{
                              backgroundColor: w.aqi <= 50 ? '#00E400' : w.aqi <= 100 ? '#FFFF00' :
                                w.aqi <= 150 ? '#FF7E00' : w.aqi <= 200 ? '#FF0000' : w.aqi <= 300 ? '#8F3F97' : '#7E0023'
                            }} />
                            <div className="min-w-0">
                              <p className="text-xs font-medium text-gray-200 truncate">{w.ward || w.station}</p>
                              <p className="text-[9px] text-gray-500">{city}</p>
                            </div>
                          </div>
                          <div className="flex items-center gap-1.5 shrink-0">
                            <span className="text-sm font-bold"
                              style={{ color: w.aqi <= 50 ? '#00E400' : w.aqi <= 100 ? '#FFFF00' :
                                w.aqi <= 150 ? '#FF7E00' : w.aqi <= 200 ? '#FF0000' : w.aqi <= 300 ? '#8F3F97' : '#7E0023' }}>
                              {w.data_status === 'observed' ? w.aqi : 'â€”'}
                            </span>
                            <span className={`text-[9px] px-1 py-0.5 rounded font-medium ${CATEGORY_COLORS[w.category] || 'bg-gray-500 text-white'}`}>
                              {w.data_status === 'observed' ? (w.category === 'Unhealthy for Sensitive Groups' ? 'Sensitive' : w.category) : 'No live data'}
                            </span>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                )}
              </div>

              {/* AI Enforcement Insights */}
              <div className="p-4">
                <h2 className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider mb-2.5">
                  AI Enforcement Insights
                  {activeStation && <span className="text-blue-400 normal-case ml-1.5">Â· {activeStation}</span>}
                </h2>

                {!enforcementResult && !enforcing && (
                  <div className="text-center py-8 text-gray-500">
                    <svg className="w-10 h-10 mx-auto mb-2 opacity-30" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
                    </svg>
                    <p className="text-xs">Click a station marker or anywhere on the map</p>
                    <p className="text-[10px] text-gray-600 mt-0.5">Signal â†’ Attribution â†’ Enforcement â†’ Advisory in ~90s</p>
                  </div>
                )}

                {enforcementResult && (
                  <div className="space-y-3">
                    {/* Evidence status */}
                    <div className={`rounded-lg border p-2.5 text-[11px] ${enforcementResult.evidence_status === 'persistence_baseline' ? 'border-amber-800/60 bg-amber-900/20 text-amber-200' : 'border-emerald-800/60 bg-emerald-900/20 text-emerald-200'}`}>
                      <strong>Decision-support evidence:</strong> {enforcementResult.evidence_note || 'Field verification is required before enforcement.'}
                    </div>

                    {/* Query Info */}
                    <div className="bg-gray-700/40 rounded-lg p-2.5 text-[11px] text-gray-400">
                      <strong className="text-gray-300">Query point:</strong> {enforcementResult.query_coordinates.lat.toFixed(4)}, {enforcementResult.query_coordinates.lon.toFixed(4)}
                      <br />
                      <strong className="text-gray-300">Nearest city:</strong> {enforcementResult.nearest_city}
                      <span className="ml-2 text-gray-600">|</span>
                      <strong className="text-gray-300 ml-2">Stations:</strong> {enforcementResult.stations_found}
                      {enforcementResult.total_plume_contribution_ugm3 > 0 && (
                        <><br /><strong className="text-gray-300">Plume contribution:</strong> {enforcementResult.total_plume_contribution_ugm3.toFixed(1)} Âµg/mÂ³</>
                      )}
                    </div>

                    {/* Citizen Advisory */}
                    {enforcementResult.citizen_advisory && (
                      <div className="bg-gradient-to-r from-red-900/40 via-red-800/30 to-red-900/40 rounded-lg p-2.5 border border-red-800/40">
                        <div className="flex items-start gap-2">
                          <span className="text-red-400 text-sm shrink-0">ðŸ«</span>
                          <div>
                            <p className="text-[10px] text-red-300 font-medium uppercase tracking-wider">
                              {enforcementResult.citizen_advisory.level} Â· {LANGUAGE_MAP[advisory?.language] || 'English'}
                            </p>
                            <p className="text-xs text-red-100/90">{enforcementResult.citizen_advisory.message}</p>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Concrete Recommendation */}
                    {enforcementResult.concrete_recommendation && (
                      <div className="bg-blue-900/30 border border-blue-800/50 rounded-lg p-2.5">
                        <h3 className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-1">Concrete Municipal Recommendation</h3>
                        <p className="text-xs text-gray-300 leading-relaxed">{enforcementResult.concrete_recommendation}</p>
                      </div>
                    )}

                    {/* Inspection Tasks */}
                    {enforcementResult.inspection_tasks?.length > 0 && (
                      <div>
                        <h3 className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-1.5">
                          Ranked Action List ({enforcementResult.inspection_tasks.length} items)
                        </h3>
                        {enforcementResult.inspection_tasks.map((task, idx) => (
                          <div key={idx} className={`rounded-lg border p-2.5 mb-2 ${
                            task.risk_level === 'CRITICAL' ? 'border-red-800/60 bg-red-900/15' :
                            task.risk_level === 'HIGH' ? 'border-orange-800/60 bg-orange-900/15' :
                            task.risk_level === 'MODERATE' ? 'border-yellow-800/40 bg-yellow-900/10' :
                            'border-gray-700 bg-gray-700/20'
                          }`}>
                            <div className="flex items-start justify-between mb-1.5">
                              <div>
                                <p className="text-xs font-semibold text-gray-200">{task.station_name}</p>
                                <p className="text-[10px] text-gray-500">AQI {task.current_aqi} â†’ {task.forecast_aqi_48h} in 48h</p>
                              </div>
                              <div className="flex items-center gap-1.5">
                                <RiskBadge level={task.risk_level} />
                                <span className="text-[10px] text-gray-500 bg-gray-700/60 px-1.5 py-0.5 rounded">
                                  P{task.priority_score}
                                </span>
                              </div>
                            </div>

                            {/* Trend indicator */}
                            <div className="mb-1.5 flex items-center gap-2 text-[10px]">
                              <span className={`font-medium ${task.aqi_trend === 'rising' ? 'text-red-400' : task.aqi_trend === 'falling' ? 'text-green-400' : 'text-gray-400'}`}>
                                {task.aqi_trend === 'rising' ? 'â†‘ Rising' : task.aqi_trend === 'falling' ? 'â†“ Falling' : 'â†’ Stable'}
                              </span>
                              <span className="text-gray-600">|</span>
                              <span className="text-gray-500">Source: <strong className="text-gray-300 capitalize">{task.dominant_source}</strong></span>
                              <span className="text-gray-600">|</span>
                              <span className="text-gray-500">Conf: {task.attribution_confidence.toFixed(2)}</span>
                            </div>

                            {/* Source breakdown */}
                            {task.source_breakdown && <SourceChart categories={task.source_breakdown} />}

                            {/* Action */}
                            <div className="mt-1.5">
                              <h4 className="text-[9px] font-semibold text-gray-600 uppercase mb-0.5">Action</h4>
                              <p className="text-[11px] text-gray-300">{task.recommended_action}</p>
                            </div>

                            {/* Officer note (LLM narrative) */}
                            <details className="group mt-1.5">
                              <summary className="text-[10px] text-blue-400 cursor-pointer hover:text-blue-300 select-none">
                                View officer narrative â†’
                              </summary>
                              <p className="mt-1 text-[10px] text-gray-400 leading-relaxed">{task.officer_note}</p>
                              <p className="text-[9px] text-gray-600 mt-1">
                                {task.legal_reference} Â· Respond within {task.response_timeframe}
                              </p>
                            </details>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Agent Notes */}
                    {enforcementResult.agent_notes && (
                      <div className="bg-blue-900/20 border border-blue-800/30 rounded-lg p-2.5">
                        <h3 className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-1">Agent Pipeline Log</h3>
                        <p className="text-[10px] text-blue-300/80 whitespace-pre-line leading-relaxed">{enforcementResult.agent_notes}</p>
                      </div>
                    )}

                    {/* Forecast Chart (mini sparkline) */}
                    {forecastChart.length > 0 && (
                      <div className="bg-gray-700/40 rounded-lg p-2.5">
                        <div className="flex items-center justify-between gap-2 mb-1.5">
                          <h3 className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider">72-Hour Forecast</h3>
                          <span className={`text-[9px] px-1.5 py-0.5 rounded border ${
                            forecastData?.metadata?.data_status === 'demo_synthetic'
                              ? 'border-amber-700/60 bg-amber-900/30 text-amber-300'
                              : forecastData?.metadata?.metrics_status === 'measured_holdout'
                                ? 'border-emerald-700/60 bg-emerald-900/30 text-emerald-300'
                                : 'border-gray-600 bg-gray-700 text-gray-400'
                          }`}>
                            {forecastData?.metadata?.data_status === 'demo_synthetic'
                              ? 'DEMO FORECAST'
                              : forecastData?.metadata?.metrics_status === 'measured_holdout'
                                ? 'HOLDOUT EVALUATED'
                                : 'METRICS PENDING'}
                          </span>
                        </div>
                        {forecastData?.metadata?.data_status === 'demo_synthetic' && (
                          <p className="text-[10px] leading-relaxed text-amber-300/80 mb-2">
                            Demo fallback â€” interactive scenario, not a validated forecast.
                          </p>
                        )}
                        {forecastData?.metadata?.metrics_status === 'measured_holdout' && (
                          <p className="text-[10px] leading-relaxed text-emerald-300/80 mb-2">
                            Held-out RMSE: {forecastData.metadata.model_rmse} Â· Persistence: {forecastData.metadata.persistence_rmse}
                          </p>
                        )}
                        <div className="relative h-12">
                          <svg viewBox={`0 0 ${forecastChart.length} 100`} className="w-full h-full" preserveAspectRatio="none">
                            <defs>
                              <linearGradient id="aqiGradient" x1="0" x2="0" y1="0" y2="1">
                                <stop offset="0%" stopColor="#EF4444" stopOpacity="0.6" />
                                <stop offset="100%" stopColor="#EF4444" stopOpacity="0.05" />
                              </linearGradient>
                            </defs>
                            <polyline
                              fill="url(#aqiGradient)"
                              stroke="#EF4444"
                              strokeWidth="1.5"
                              points={forecastChart.map((f, i) => `${i},${100 - ((f.aqi - minAqi) / Math.max(maxAqi - minAqi, 1)) * 90}`).join(' ')}
                            />
                            <polyline
                              fill="none"
                              stroke="#EF4444"
                              strokeWidth="1.5"
                              points={forecastChart.map((f, i) => `${i},${100 - ((f.aqi - minAqi) / Math.max(maxAqi - minAqi, 1)) * 90}`).join(' ')}
                            />
                          </svg>
                          <div className="flex justify-between text-[9px] text-gray-600 mt-0.5">
                            <span>Now</span>
                            <span>+24h</span>
                            <span>+48h</span>
                            <span>+72h</span>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* Bottom: metadata bar */}
            {metadata && (
              <div className="px-4 py-2 border-t border-gray-700 bg-gray-800/50">
                <div className="flex items-center justify-between text-[9px] text-gray-600">
                  <span>Prototype decision-support system</span>
                  <span>Forecast card shows evaluation status</span>
                  <span>{metadata.cities_supported?.join(', ')}</span>
                </div>
              </div>
            )}
          </aside>
        )}
      </div>
    </div>
  );
}

