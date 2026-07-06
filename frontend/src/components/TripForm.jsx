import axios from "axios";

const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

function TripForm({ setTripData, setLoading, setError, loading }) {
  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setTripData(null);

    const form = e.target;
    const payload = {
      current_location: form.current_location.value,
      pickup_location: form.pickup_location.value,
      dropoff_location: form.dropoff_location.value,
      current_cycle_used: parseFloat(form.current_cycle_used.value) || 0,
    };

    try {
      const res = await axios.post(`${API_URL}/api/trip/`, payload);
      setTripData(res.data);
    } catch (err) {
      setError(
        err.response?.data?.error || "Something went wrong. Please try again.",
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="form-card">
      <h2>Plan Your Trip</h2>
      <form onSubmit={handleSubmit} className="trip-form">
        <div className="form-group">
          <label>Current Location</label>
          <input
            name="current_location"
            placeholder="e.g. Chicago, IL"
            required
          />
        </div>
        <div className="form-group">
          <label>Pickup Location</label>
          <input
            name="pickup_location"
            placeholder="e.g. St. Louis, MO"
            required
          />
        </div>
        <div className="form-group">
          <label>Dropoff Location</label>
          <input
            name="dropoff_location"
            placeholder="e.g. Nashville, TN"
            required
          />
        </div>
        <div className="form-group">
          <label>Current Cycle Used (hrs)</label>
          <input
            name="current_cycle_used"
            type="number"
            min="0"
            max="70"
            step="0.5"
            placeholder="e.g. 10"
            defaultValue="0"
            required
          />
        </div>
        <button type="submit" disabled={loading} className="submit-btn">
          {loading ? "⏳ Calculating Route..." : "🗺️ Plan Trip"}
        </button>
      </form>
    </div>
  );
}

export default TripForm;
