import { FormEvent, useEffect, useState } from "react";
import {
  Complaint,
  StatsResponse,
  fetchComplaints,
  fetchStats,
  submitComplaint,
  updateComplaintStatus,
} from "./api";
import "./styles.css";

const initialForm = { text: "", location: "", reporter_contact: "" };

export default function App() {
  const [activeTab, setActiveTab] = useState<"submit" | "dashboard" | "stats">("submit");

  // Submit view state
  const [form, setForm] = useState(initialForm);
  const [result, setResult] = useState<Complaint | null>(null);
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Dashboard view state
  const [complaints, setComplaints] = useState<Complaint[]>([]);
  const [totalComplaints, setTotalComplaints] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);
  const [filterCategory, setFilterCategory] = useState("");
  const [filterPriority, setFilterPriority] = useState("");
  const [filterStatus, setFilterStatus] = useState("");
  const [dashboardError, setDashboardError] = useState("");
  const [isLoadingDashboard, setIsLoadingDashboard] = useState(false);

  // Stats view state
  const [statsData, setStatsData] = useState<StatsResponse | null>(null);
  const [cacheHeader, setCacheHeader] = useState<string>("UNKNOWN");
  const [statsError, setStatsError] = useState("");
  const [isLoadingStats, setIsLoadingStats] = useState(false);

  async function loadComplaints() {
    setIsLoadingDashboard(true);
    setDashboardError("");
    try {
      const data = await fetchComplaints({
        category: filterCategory || undefined,
        priority: filterPriority || undefined,
        status: filterStatus || undefined,
        page,
        page_size: pageSize,
      });
      setComplaints(data.items);
      setTotalComplaints(data.total);
    } catch (err) {
      setDashboardError(err instanceof Error ? err.message : "Failed to load complaints");
    } finally {
      setIsLoadingDashboard(false);
    }
  }

  async function loadStats() {
    setIsLoadingStats(true);
    setStatsError("");
    try {
      const res = await fetchStats();
      setStatsData(res.stats);
      setCacheHeader(res.cacheHeader);
    } catch (err) {
      setStatsError(err instanceof Error ? err.message : "Failed to load stats");
    } finally {
      setIsLoadingStats(false);
    }
  }

  useEffect(() => {
    if (activeTab === "dashboard") {
      loadComplaints();
    } else if (activeTab === "stats") {
      loadStats();
    }
  }, [activeTab, page, filterCategory, filterPriority, filterStatus]);

  async function handleStatusChange(complaintId: string, newStatus: string) {
    setDashboardError("");
    try {
      await updateComplaintStatus(complaintId, newStatus);
      await loadComplaints();
    } catch (err: any) {
      // Surface server's 409 message verbatim
      setDashboardError(err.message || "Failed to update status");
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setResult(null);
    if (form.text.trim().length < 10) {
      setError("Please describe the issue in at least 10 characters.");
      return;
    }
    if (form.location.trim().length < 3) {
      setError("Please provide a location.");
      return;
    }
    setIsSubmitting(true);
    try {
      setResult(await submitComplaint(form));
      setForm(initialForm);
    } catch (submissionError) {
      setError(submissionError instanceof Error ? submissionError.message : "Unable to submit complaint.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="page-shell">
      <header className="masthead">
        <div>
          <span className="eyebrow">CIVICPULSE / INTAKE & OPERATIONS</span>
          <h1>Make the issue visible.</h1>
        </div>
        <span className="status-dot">TRIAGE ONLINE</span>
      </header>

      <nav className="nav-tabs" aria-label="Views">
        <button
          className={`tab-btn ${activeTab === "submit" ? "active" : ""}`}
          onClick={() => setActiveTab("submit")}
        >
          Submit Complaint
        </button>
        <button
          className={`tab-btn ${activeTab === "dashboard" ? "active" : ""}`}
          onClick={() => {
            setActiveTab("dashboard");
            setPage(1);
          }}
        >
          Operations Dashboard
        </button>
        <button
          className={`tab-btn ${activeTab === "stats" ? "active" : ""}`}
          onClick={() => setActiveTab("stats")}
        >
          Aggregate Stats
        </button>
      </nav>

      {activeTab === "submit" && (
        <>
          <section className="content-grid">
            <div className="intro">
              <p className="kicker">Citizen report</p>
              <h2>Tell us what is happening in your area.</h2>
              <p className="lede">
                Your description is triaged automatically so the operations team can see urgent problems sooner.
              </p>
              <div className="signal">
                <span>01</span>
                <p>Write naturally. You do not need to choose a category.</p>
              </div>
              <div className="signal">
                <span>02</span>
                <p>Include a precise location so the right team can respond.</p>
              </div>
            </div>
            <form className="complaint-form" onSubmit={handleSubmit}>
              <label>
                What happened?
                <textarea
                  value={form.text}
                  onChange={(event) => setForm({ ...form, text: event.target.value })}
                  placeholder="Example: A burst water pipe is flooding the road near..."
                  maxLength={2000}
                  required
                />
              </label>
              <div className="field-row">
                <label>
                  Location
                  <input
                    value={form.location}
                    onChange={(event) => setForm({ ...form, location: event.target.value })}
                    placeholder="Street, neighbourhood or landmark"
                    maxLength={200}
                    required
                  />
                </label>
                <label>
                  Contact <span>(optional)</span>
                  <input
                    value={form.reporter_contact}
                    onChange={(event) => setForm({ ...form, reporter_contact: event.target.value })}
                    placeholder="Phone or email"
                    maxLength={200}
                  />
                </label>
              </div>
              {error && (
                <div className="alert" role="alert">
                  {error}
                </div>
              )}
              <button type="submit" disabled={isSubmitting}>
                {isSubmitting ? "Analysing report..." : "Submit complaint"}
                <span>↗</span>
              </button>
              <p className="privacy-note">
                We use your report to coordinate municipal response. Contact details are optional.
              </p>
            </form>
          </section>
          {result && (
            <section className="result" aria-live="polite">
              <div>
                <p className="kicker">Report received</p>
                <h2>{result.ai_summary}</h2>
              </div>
              <div className="result-meta">
                <span>
                  <b>Category</b>
                  {result.category}
                </span>
                <span>
                  <b>Priority</b>
                  <em className={result.priority}>{result.priority}</em>
                </span>
                <span>
                  <b>Triaged by</b>
                  {result.triaged_by}
                </span>
              </div>
            </section>
          )}
        </>
      )}

      {activeTab === "dashboard" && (
        <section className="dashboard-shell">
          <div className="filter-bar">
            <div className="filter-group">
              <label>Category</label>
              <select value={filterCategory} onChange={(e) => { setFilterCategory(e.target.value); setPage(1); }}>
                <option value="">All Categories</option>
                <option value="water">Water</option>
                <option value="electricity">Electricity</option>
                <option value="sanitation">Sanitation</option>
                <option value="roads">Roads</option>
                <option value="streetlights">Streetlights</option>
                <option value="other">Other</option>
              </select>
            </div>
            <div className="filter-group">
              <label>Priority</label>
              <select value={filterPriority} onChange={(e) => { setFilterPriority(e.target.value); setPage(1); }}>
                <option value="">All Priorities</option>
                <option value="high">High</option>
                <option value="normal">Normal</option>
                <option value="low">Low</option>
              </select>
            </div>
            <div className="filter-group">
              <label>Status</label>
              <select value={filterStatus} onChange={(e) => { setFilterStatus(e.target.value); setPage(1); }}>
                <option value="">All Statuses</option>
                <option value="open">Open</option>
                <option value="in_progress">In Progress</option>
                <option value="resolved">Resolved</option>
                <option value="rejected">Rejected</option>
              </select>
            </div>
          </div>

          {dashboardError && (
            <div className="alert" role="alert" style={{ marginBottom: "20px" }}>
              {dashboardError}
            </div>
          )}

          {isLoadingDashboard ? (
            <p>Loading complaints...</p>
          ) : (
            <>
              <div className="data-table-container">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Summary / Description</th>
                      <th>Location</th>
                      <th>Category</th>
                      <th>Priority</th>
                      <th>Status</th>
                      <th>Triaged By</th>
                      <th>Advance Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {complaints.length === 0 ? (
                      <tr>
                        <td colSpan={7} style={{ textAlign: "center", padding: "24px" }}>
                          No complaints found.
                        </td>
                      </tr>
                    ) : (
                      complaints.map((c) => (
                        <tr key={c.id}>
                          <td>
                            <strong>{c.ai_summary || c.text.slice(0, 60)}</strong>
                            <div style={{ fontSize: "12px", color: "#666" }}>{c.text.slice(0, 90)}...</div>
                          </td>
                          <td>{c.location}</td>
                          <td>{c.category}</td>
                          <td>
                            <span className={`priority-${c.priority}`}>{c.priority}</span>
                          </td>
                          <td>
                            <span className={`status-badge status-${c.status}`}>{c.status}</span>
                          </td>
                          <td>{c.triaged_by}</td>
                          <td>
                            <select
                              className="action-select"
                              value={c.status}
                              onChange={(e) => handleStatusChange(c.id, e.target.value)}
                            >
                              <option value="open" disabled>Open</option>
                              <option value="in_progress">In Progress</option>
                              <option value="resolved">Resolved</option>
                              <option value="rejected">Rejected</option>
                            </select>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>

              <div className="pagination">
                <span>
                  Showing {complaints.length} of {totalComplaints} complaints (Page {page})
                </span>
                <div style={{ display: "flex", gap: "10px" }}>
                  <button disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
                    ← Previous
                  </button>
                  <button
                    disabled={page * pageSize >= totalComplaints}
                    onClick={() => setPage((p) => p + 1)}
                  >
                    Next →
                  </button>
                </div>
              </div>
            </>
          )}
        </section>
      )}

      {activeTab === "stats" && (
        <section className="stats-shell">
          <div className="stats-header">
            <div>
              <p className="kicker">Real-time Metrics</p>
              <h2>Aggregate Platform Statistics</h2>
            </div>
            <div>
              <span className={`cache-badge ${cacheHeader === "HIT" ? "cache-hit" : "cache-miss"}`}>
                X-Cache: {cacheHeader}
              </span>
            </div>
          </div>

          {statsError && <div className="alert">{statsError}</div>}

          {isLoadingStats ? (
            <p>Loading metrics...</p>
          ) : statsData ? (
            <div className="stats-grid">
              <div className="stats-card">
                <h3>Total Complaints</h3>
                <div className="total-stat-box">{statsData.total}</div>
                <p style={{ marginTop: "12px", color: "#666" }}>Across all municipal categories</p>
                <button style={{ width: "auto", padding: "8px 14px", marginTop: "12px" }} onClick={loadStats}>
                  Refresh Stats
                </button>
              </div>

              <div className="stats-card">
                <h3>By Category</h3>
                <ul className="stats-list">
                  {Object.entries(statsData.by_category).map(([cat, count]) => (
                    <li key={cat}>
                      <span>{cat}</span>
                      <strong>{count}</strong>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="stats-card">
                <h3>By Priority</h3>
                <ul className="stats-list">
                  {Object.entries(statsData.by_priority).map(([prio, count]) => (
                    <li key={prio}>
                      <span className={`priority-${prio}`}>{prio}</span>
                      <strong>{count}</strong>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          ) : null}
        </section>
      )}
    </main>
  );
}
