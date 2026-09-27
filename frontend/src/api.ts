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

export type ComplaintListResponse = {
  items: Complaint[];
  total: number;
  page: number;
  page_size: number;
};

export type StatsResponse = {
  total: number;
  by_category: Record<string, number>;
  by_priority: Record<string, number>;
};

export type StatsWithCache = {
  stats: StatsResponse;
  cacheHeader: string;
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

export async function fetchComplaints(
  params: { category?: string; priority?: string; status?: string; page?: number; page_size?: number } = {}
): Promise<ComplaintListResponse> {
  const query = new URLSearchParams();
  if (params.category) query.set("category", params.category);
  if (params.priority) query.set("priority", params.priority);
  if (params.status) query.set("status", params.status);
  if (params.page) query.set("page", String(params.page));
  if (params.page_size) query.set("page_size", String(params.page_size));

  const url = `/api/complaints${query.toString() ? `?${query.toString()}` : ""}`;
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error("Unable to fetch complaints list");
  }
  return response.json() as Promise<ComplaintListResponse>;
}

export async function updateComplaintStatus(complaintId: string, status: string): Promise<Complaint> {
  const response = await fetch(`/api/complaints/${complaintId}/status`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status }),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: "Status update failed" }));
    const errorMsg = typeof body.detail === "string" ? body.detail : JSON.stringify(body);
    const err = new Error(errorMsg);
    (err as any).status = response.status;
    throw err;
  }
  return response.json() as Promise<Complaint>;
}

export async function fetchStats(): Promise<StatsWithCache> {
  const response = await fetch("/api/stats");
  if (!response.ok) {
    throw new Error("Unable to fetch statistics");
  }
  const cacheHeader = response.headers.get("X-Cache") || "UNKNOWN";
  const stats = (await response.json()) as StatsResponse;
  return { stats, cacheHeader };
}
