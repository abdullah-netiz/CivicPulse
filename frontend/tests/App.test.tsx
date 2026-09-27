import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { act } from "react";
import { createRoot } from "react-dom/client";
import App from "../src/App";
import * as api from "../src/api";
import { ErrorBoundary } from "../src/ErrorBoundary";

// Setup DOM container for React 18 testing without needing external testing-library dependencies
let container: HTMLDivElement | null = null;
let root: ReturnType<typeof createRoot> | null = null;

beforeEach(() => {
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
  vi.restoreAllMocks();
  return () => {
    if (root && container) {
      act(() => {
        root?.unmount();
      });
      container.remove();
      container = null;
      root = null;
    }
  };
});

describe("CivicPulse Frontend Component Tests", () => {
  it("renders the complaint intake form with inputs and submit button", async () => {
    await act(async () => {
      root!.render(<App />);
    });

    expect(container?.querySelector("h1")?.textContent).toBe("Make the issue visible.");
    const textarea = container?.querySelector("textarea");
    expect(textarea).not.toBeNull();
    expect(textarea?.placeholder).toContain("A burst water pipe");

    const submitBtn = container?.querySelector("button[type='submit']");
    expect(submitBtn).not.toBeNull();
    expect(submitBtn?.textContent).toContain("Submit complaint");
  });

  it("validates client-side minimum length for complaint description (<10 chars)", async () => {
    await act(async () => {
      root!.render(<App />);
    });

    const form = container?.querySelector("form");
    const textarea = container?.querySelector("textarea")!;
    const locationInput = container?.querySelectorAll("input")[0]!;

    // Set short description
    await act(async () => {
      // Simulate typing text less than 10 characters
      const nativeTextareaValueSetter = Object.getOwnPropertyDescriptor(
        window.HTMLTextAreaElement.prototype,
        "value"
      )?.set;
      nativeTextareaValueSetter?.call(textarea, "Short");
      textarea.dispatchEvent(new Event("input", { bubbles: true }));

      const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
        window.HTMLInputElement.prototype,
        "value"
      )?.set;
      nativeInputValueSetter?.call(locationInput, "Street 10, F-8");
      locationInput.dispatchEvent(new Event("input", { bubbles: true }));
    });

    await act(async () => {
      form?.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    });

    const alert = container?.querySelector(".alert");
    expect(alert).not.toBeNull();
    expect(alert?.textContent).toContain("Please describe the issue in at least 10 characters");
  });

  it("validates client-side location input (<3 chars)", async () => {
    await act(async () => {
      root!.render(<App />);
    });

    const form = container?.querySelector("form");
    const textarea = container?.querySelector("textarea")!;
    const locationInput = container?.querySelectorAll("input")[0]!;

    await act(async () => {
      const nativeTextareaValueSetter = Object.getOwnPropertyDescriptor(
        window.HTMLTextAreaElement.prototype,
        "value"
      )?.set;
      nativeTextareaValueSetter?.call(textarea, "This is a valid long description of a water problem");
      textarea.dispatchEvent(new Event("input", { bubbles: true }));

      const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
        window.HTMLInputElement.prototype,
        "value"
      )?.set;
      nativeInputValueSetter?.call(locationInput, "ab"); // < 3 characters
      locationInput.dispatchEvent(new Event("input", { bubbles: true }));
    });

    await act(async () => {
      form?.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    });

    const alert = container?.querySelector(".alert");
    expect(alert).not.toBeNull();
    expect(alert?.textContent).toContain("Please provide a location");
  });

  it("displays honest loading state while AI triage is in-flight", async () => {
    // Create an unresolved promise to inspect loading state
    let resolvePromise: (value: any) => void;
    const pendingPromise = new Promise((resolve) => {
      resolvePromise = resolve;
    });

    vi.spyOn(api, "submitComplaint").mockImplementation(() => pendingPromise as any);

    await act(async () => {
      root!.render(<App />);
    });

    const form = container?.querySelector("form");
    const textarea = container?.querySelector("textarea")!;
    const locationInput = container?.querySelectorAll("input")[0]!;

    await act(async () => {
      const nativeTextareaValueSetter = Object.getOwnPropertyDescriptor(
        window.HTMLTextAreaElement.prototype,
        "value"
      )?.set;
      nativeTextareaValueSetter?.call(textarea, "Water main burst and flooding houses");
      textarea.dispatchEvent(new Event("input", { bubbles: true }));

      const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
        window.HTMLInputElement.prototype,
        "value"
      )?.set;
      nativeInputValueSetter?.call(locationInput, "Islamabad F-8");
      locationInput.dispatchEvent(new Event("input", { bubbles: true }));
    });

    await act(async () => {
      form?.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    });

    const submitBtn = container?.querySelector("button[type='submit']") as HTMLButtonElement;
    expect(submitBtn.disabled).toBe(true);
    expect(submitBtn.textContent).toContain("Analysing report...");

    // Resolve the promise to clean up
    await act(async () => {
      resolvePromise!({
        id: "123e4567-e89b-12d3-a456-426614174000",
        text: "Water main burst and flooding houses",
        location: "Islamabad F-8",
        reporter_contact: null,
        category: "water",
        priority: "high",
        status: "open",
        ai_summary: "Burst water main flooding residential area.",
        triaged_by: "rules",
        triage_latency_ms: 120,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      });
    });
  });

  it("renders triaged result with category, priority, ai_summary, and provider", async () => {
    const mockComplaint: api.Complaint = {
      id: "abc-123-def",
      text: "Power transformer on fire with sparks",
      location: "Gulberg Lahore",
      reporter_contact: "03001234567",
      category: "electricity",
      priority: "high",
      status: "open",
      ai_summary: "Transformer on fire with sparks dropping on street.",
      triaged_by: "llm:gemini",
      triage_latency_ms: 320,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    vi.spyOn(api, "submitComplaint").mockResolvedValue(mockComplaint);

    await act(async () => {
      root!.render(<App />);
    });

    const form = container?.querySelector("form");
    const textarea = container?.querySelector("textarea")!;
    const locationInput = container?.querySelectorAll("input")[0]!;

    await act(async () => {
      const nativeTextareaValueSetter = Object.getOwnPropertyDescriptor(
        window.HTMLTextAreaElement.prototype,
        "value"
      )?.set;
      nativeTextareaValueSetter?.call(textarea, "Power transformer on fire with sparks");
      textarea.dispatchEvent(new Event("input", { bubbles: true }));

      const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
        window.HTMLInputElement.prototype,
        "value"
      )?.set;
      nativeInputValueSetter?.call(locationInput, "Gulberg Lahore");
      locationInput.dispatchEvent(new Event("input", { bubbles: true }));
    });

    await act(async () => {
      form?.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    });

    const resultSection = container?.querySelector(".result");
    expect(resultSection).not.toBeNull();
    expect(resultSection?.textContent).toContain("Transformer on fire with sparks");
    expect(resultSection?.textContent).toContain("electricity");
    expect(resultSection?.textContent).toContain("high");
    expect(resultSection?.textContent).toContain("llm:gemini");
  });

  it("ErrorBoundary renders fallback UI when a child component throws an error", () => {
    const ProblemChild = () => {
      throw new Error("Simulated rendering crash");
    };

    // Suppress console.error during intentional error boundary test
    const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    act(() => {
      root!.render(
        <ErrorBoundary>
          <ProblemChild />
        </ErrorBoundary>
      );
    });

    expect(container?.textContent).toContain("Something went wrong");
    expect(container?.textContent).toContain("Please reload the report form");

    consoleSpy.mockRestore();
  });
});
