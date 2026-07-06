const STATUS_COLORS = {
  off_duty: "#6b7280",
  sleeper_berth: "#8b5cf6",
  driving: "#22c55e",
  on_duty: "#f59e0b",
};

const STATUS_LABELS = {
  off_duty: "Off Duty",
  sleeper_berth: "Sleeper Berth",
  driving: "Driving",
  on_duty: "On Duty (Not Driving)",
};

const STATUS_ROW = {
  off_duty: 0,
  sleeper_berth: 1,
  driving: 2,
  on_duty: 3,
};

function LogGrid({ events }) {
  const GRID_WIDTH = 700;
  const ROW_HEIGHT = 40;
  const ROWS = 4;
  const LEFT_MARGIN = 0;

  return (
    <svg
      width="100%"
      viewBox={`0 0 ${GRID_WIDTH} ${ROWS * ROW_HEIGHT + 30}`}
      className="log-grid"
    >
      {/* Hour labels */}
      {Array.from({ length: 25 }, (_, i) => (
        <text
          key={i}
          x={LEFT_MARGIN + (i / 24) * GRID_WIDTH}
          y={12}
          fontSize="9"
          textAnchor="middle"
          fill="#6b7280"
        >
          {i === 0 ? "M" : i === 12 ? "N" : i === 24 ? "M" : i}
        </text>
      ))}

      {/* Grid lines */}
      {Array.from({ length: 25 }, (_, i) => (
        <line
          key={i}
          x1={LEFT_MARGIN + (i / 24) * GRID_WIDTH}
          y1={16}
          x2={LEFT_MARGIN + (i / 24) * GRID_WIDTH}
          y2={ROWS * ROW_HEIGHT + 16}
          stroke={i % 6 === 0 ? "#9ca3af" : "#e5e7eb"}
          strokeWidth={i % 6 === 0 ? 1 : 0.5}
        />
      ))}

      {/* Row backgrounds */}
      {Array.from({ length: ROWS }, (_, i) => (
        <rect
          key={i}
          x={LEFT_MARGIN}
          y={16 + i * ROW_HEIGHT}
          width={GRID_WIDTH}
          height={ROW_HEIGHT}
          fill={i % 2 === 0 ? "#f9fafb" : "#ffffff"}
          stroke="#e5e7eb"
          strokeWidth={0.5}
        />
      ))}

      {/* Events */}
      {events.map((event, idx) => {
        const row = STATUS_ROW[event.status];
        const x = LEFT_MARGIN + (event.start_hour / 24) * GRID_WIDTH;
        const width = ((event.end_hour - event.start_hour) / 24) * GRID_WIDTH;
        const y = 16 + row * ROW_HEIGHT;

        return (
          <g key={idx}>
            <rect
              x={x}
              y={y + 4}
              width={Math.max(width, 2)}
              height={ROW_HEIGHT - 8}
              fill={STATUS_COLORS[event.status]}
              rx={3}
              opacity={0.85}
            />
            {width > 40 && (
              <text
                x={x + width / 2}
                y={y + ROW_HEIGHT / 2 + 5}
                fontSize="8"
                textAnchor="middle"
                fill="white"
                fontWeight="bold"
              >
                {(event.end_hour - event.start_hour).toFixed(1)}h
              </text>
            )}
          </g>
        );
      })}
    </svg>
  );
}

function ELDLogs({ logs, summary }) {
  return (
    <div className="logs-card">
      <h2>📋 Driver's Daily Logs</h2>

      <div className="summary-stats">
        <div className="stat">
          <span className="stat-value">{summary.total_miles}</span>
          <span className="stat-label">Total Miles</span>
        </div>
        <div className="stat">
          <span className="stat-value">{summary.num_days}</span>
          <span className="stat-label">Days</span>
        </div>
        <div className="stat">
          <span className="stat-value">{summary.current_cycle_used}h</span>
          <span className="stat-label">Cycle Used</span>
        </div>
      </div>

      <div className="legend">
        {Object.entries(STATUS_LABELS).map(([key, label]) => (
          <div key={key} className="legend-item">
            <div
              className="legend-dot"
              style={{ background: STATUS_COLORS[key] }}
            />
            <span>{label}</span>
          </div>
        ))}
      </div>

      {logs.map((log) => (
        <div key={log.day} className="log-day">
          <div className="log-day-header">
            <h3>Day {log.day}</h3>
            <div className="log-day-stats">
              <span>🚗 Driving: {log.total_driving}h</span>
              <span>⚡ On Duty: {log.total_on_duty}h</span>
            </div>
          </div>

          <div className="log-row-labels">
            {Object.values(STATUS_LABELS).map((label) => (
              <div key={label} className="row-label">
                {label}
              </div>
            ))}
          </div>

          <LogGrid events={log.events} />

          <div className="log-events">
            {log.events.map((event, idx) => (
              <div key={idx} className="event-item">
                <div
                  className="event-dot"
                  style={{ background: STATUS_COLORS[event.status] }}
                />
                <span className="event-time">
                  {event.start_hour.toFixed(1)}h – {event.end_hour.toFixed(1)}h
                </span>
                <span className="event-note">{event.note}</span>
                <span className="event-location">{event.location}</span>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

export default ELDLogs;
