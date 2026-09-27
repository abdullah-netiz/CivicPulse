import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";

const complaint = {
  id: "1",
  text: "Burst water pipe flooding the road",
  location: "Street 1",
  reporter_contact: null,
  category: "water",
  priority: "high",
  status: "open",
  ai_summary: "Burst water pipe flooding the road",
  triaged_by: "llm:gemini",
  triage_latency_ms: 80,
  created_at: "2026-09-26T00:00:00Z",
  updated_at: "2026-09-26T00:00:00Z",
};

function fillValidForm() {
  fireEvent.change(screen.getByLabelText("What happened?"), { target: { value: complaint.text } });
  fireEvent.change(screen.getByLabelText("Location"), { target: { value: complaint.location } });
}

describe("Submit view", () => {
  afterEach(() => cleanup());
  beforeEach(() => vi.restoreAllMocks());

  it("renders the empty form", () => {
    render(<App />);
    expect(screen.getByRole("button", { name: /submit complaint/i })).toBeInTheDocument();
    expect(screen.queryByText("Report received")).not.toBeInTheDocument();
  });

  it("shows client validation for a short complaint", () => {
    render(<App />);
    fireEvent.change(screen.getByLabelText("Location"), { target: { value: "Street 1" } });
    fireEvent.submit(screen.getByRole("button", { name: /submit complaint/i }));
    expect(screen.getByRole("alert")).toHaveTextContent("at least 10 characters");
  });

  it("shows the honest loading state", async () => {
    let resolveRequest!: (value: Response) => void;
    vi.stubGlobal("fetch", vi.fn(() => new Promise<Response>((resolve) => { resolveRequest = resolve; })));
    render(<App />);
    fillValidForm();
    fireEvent.submit(screen.getByRole("button", { name: /submit complaint/i }));
    expect(screen.getByRole("button")).toHaveTextContent("Analysing report");
    resolveRequest(new Response(JSON.stringify(complaint), { status: 201 }));
    await waitFor(() => expect(screen.getByText("Report received")).toBeInTheDocument());
  });

  it("renders the triage result and provider", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify(complaint), { status: 201 })));
    render(<App />);
    fillValidForm();
    fireEvent.submit(screen.getByRole("button", { name: /submit complaint/i }));
    expect(await screen.findByText("llm:gemini")).toBeInTheDocument();
    expect(screen.getByText("water")).toBeInTheDocument();
    expect(screen.getByText("high")).toBeInTheDocument();
  });

  it("shows server failures", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: "Rate limit exceeded" }), { status: 429 })));
    render(<App />);
    fillValidForm();
    fireEvent.submit(screen.getByRole("button", { name: /submit complaint/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Rate limit exceeded");
  });
});
