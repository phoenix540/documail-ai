// @vitest-environment jsdom
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
vi.hoisted(() => localStorage.setItem("token", "t"));
import App from "./App.jsx";

const json = (data, status = 200) => Promise.resolve({ ok: status < 400, status, json: () => Promise.resolve(data) });

Element.prototype.scrollIntoView = () => {};

describe("chat flow", () => {
  it("renders an answer with sources and an email draft without crashing", async () => {
    global.fetch = vi.fn((url, opts = {}) => {
      if (url.endsWith("/auth/me")) return json({ id: 1, email: "a@b.io", role: "admin" });
      if (url.endsWith("/documents")) return json([{ id: 1, filename: "policy.pdf", n_chunks: 3, created_at: "2026-10-11T10:00:00Z" }]);
      if (url.endsWith("/chat")) return json({
        intent: "email", answer: "I drafted an email.", email_draft: { recipients: ["x@y.io"], subject: "S", body: "Hello" },
        sources: [{ filename: "policy.pdf", chunk: 0, score: 0.73, text: "Remote work up to three days." }],
      });
      if (url.endsWith("/stats")) return json({ documents: 1, questions: 1, by_intent: { email: 1 }, per_day: [{ day: "2026-10-11", count: 1 }], avg_latency_ms: 4200, emails: { sent: 0, failed: 0, queued: 0 } });
      if (url.endsWith("/mail/jobs")) return json([]);
      return json({});
    });
    render(<App />);
    const input = await screen.findByLabelText("Message");
    fireEvent.change(input, { target: { value: "send policy to x@y.io" } });
    fireEvent.click(screen.getByText("Ask"));
    await screen.findByText("I drafted an email.");
    expect(screen.getByText(/Remote work up to three days/)).toBeTruthy();
    expect(screen.getByText("Send email")).toBeTruthy();
    fireEvent.click(screen.getByText("Activity"));
    await screen.findByText("Questions per day");
  });
});
