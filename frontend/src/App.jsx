import { useState } from "react";
import TripForm from "./components/TripForm";
import TripMap from "./components/TripMap";
import ELDLogs from "./components/ELDLogs";
import "./App.css";

function App() {
  const [tripData, setTripData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  return (
    <div className="app">
      <header className="app-header">
        <h1>🚛 ELD Trip Planner</h1>
        <p>FMCSA HOS Compliant Route & Log Generator</p>
      </header>
      <main className="app-main">
        <TripForm
          setTripData={setTripData}
          setLoading={setLoading}
          setError={setError}
          loading={loading}
        />
        {error && <div className="error-banner">{error}</div>}
        {tripData && (
          <>
            <TripMap routeData={tripData.route} />
            <ELDLogs logs={tripData.daily_logs} summary={tripData.summary} />
          </>
        )}
      </main>
    </div>
  );
}

export default App;
