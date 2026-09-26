export type Complaint = {
  id: string;
  text: string;
  location: string;
  reporter_contact: string | null;
  category: string;
  priority: string;
  status: string;
  ai_summary: string | null;
  triaged_by: string;
  triage_latency_ms: number;
  created_at: string;
  updated_at: string;
};

export type ComplaintInput = {
  text: string;
  location: string;
  reporter_contact?: string;
};

export async function submitComplaint(input: ComplaintInput): Promise<Complaint> {
  const response = await fetch("/api/complaints", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: "Unable to submit complaint" }));
    throw new Error(typeof body.detail === "string" ? body.detail : "Unable to submit complaint");
  }
  return response.json() as Promise<Complaint>;
}
