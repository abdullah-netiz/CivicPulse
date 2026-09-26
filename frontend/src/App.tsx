import { FormEvent, useState } from "react";
import { Complaint, submitComplaint } from "./api";
import "./styles.css";

const initialForm = { text: "", location: "", reporter_contact: "" };

export default function App() {
  const [form, setForm] = useState(initialForm);
  const [result, setResult] = useState<Complaint | null>(null);
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

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
        <div><span className="eyebrow">CIVICPULSE / INTAKE</span><h1>Make the issue visible.</h1></div>
        <span className="status-dot">TRIAGE ONLINE</span>
      </header>
      <section className="content-grid">
        <div className="intro">
          <p className="kicker">Citizen report</p>
          <h2>Tell us what is happening in your area.</h2>
          <p className="lede">Your description is triaged automatically so the operations team can see urgent problems sooner.</p>
          <div className="signal"><span>01</span><p>Write naturally. You do not need to choose a category.</p></div>
          <div className="signal"><span>02</span><p>Include a precise location so the right team can respond.</p></div>
        </div>
        <form className="complaint-form" onSubmit={handleSubmit}>
          <label>What happened?<textarea value={form.text} onChange={(event) => setForm({ ...form, text: event.target.value })} placeholder="Example: A burst water pipe is flooding the road near..." maxLength={2000} required /></label>
          <div className="field-row"><label>Location<input value={form.location} onChange={(event) => setForm({ ...form, location: event.target.value })} placeholder="Street, neighbourhood or landmark" maxLength={200} required /></label><label>Contact <span>(optional)</span><input value={form.reporter_contact} onChange={(event) => setForm({ ...form, reporter_contact: event.target.value })} placeholder="Phone or email" maxLength={200} /></label></div>
          {error && <div className="alert" role="alert">{error}</div>}
          <button type="submit" disabled={isSubmitting}>{isSubmitting ? "Analysing report..." : "Submit complaint"}<span>↗</span></button>
          <p className="privacy-note">We use your report to coordinate municipal response. Contact details are optional.</p>
        </form>
      </section>
      {result && <section className="result" aria-live="polite"><div><p className="kicker">Report received</p><h2>{result.ai_summary}</h2></div><div className="result-meta"><span><b>Category</b>{result.category}</span><span><b>Priority</b><em className={result.priority}>{result.priority}</em></span><span><b>Triaged by</b>{result.triaged_by}</span></div></section>}
    </main>
  );
}
