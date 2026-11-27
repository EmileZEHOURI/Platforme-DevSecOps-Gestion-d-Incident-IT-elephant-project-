import { vi } from "vitest";
import type { User } from "@/types/auth";
import type { IncidentResponse } from "@/types/incident";

export const account: User = { id: 1, full_name: "Alice Test", email: "alice@example.com", role: "USER", is_active: true, created_at: "2026-11-01T12:00:00Z" };
export const incident: IncidentResponse = { id: 42, reference: "INC-42", title: "Panne du portail", description: "Le portail est inaccessible.", category: "ANOMALY", priority: "MEDIUM", status: "OPEN", created_by_id: 1, assigned_to_id: null, resolution: null, created_at: "2026-11-01T12:00:00Z", updated_at: "2026-11-01T12:00:00Z", resolved_at: null, closed_at: null };
export function json(body: unknown, status = 200) { return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } }); }
export function deferred<T>() { let resolve!: (value: T) => void; const promise = new Promise<T>(done => { resolve = done; }); return { promise, resolve }; }
export function http(handler: (url: URL, init: RequestInit) => Response | Promise<Response>) {
  const fetch = vi.fn((input: string | URL | Request, init: RequestInit = {}) => handler(new URL(String(input), "http://localhost"), init));
  vi.stubGlobal("fetch", fetch); return fetch;
}
// jsdom does not implement native modal presentation; keep the real dialog/form.
export function dialogs() {
  if (!HTMLDialogElement.prototype.showModal) Object.defineProperty(HTMLDialogElement.prototype, "showModal", { configurable: true, writable: true, value() {} });
  if (!HTMLDialogElement.prototype.close) Object.defineProperty(HTMLDialogElement.prototype, "close", { configurable: true, writable: true, value() {} });
  vi.spyOn(HTMLDialogElement.prototype, "showModal").mockImplementation(function(this: HTMLDialogElement) { this.setAttribute("open", ""); });
  vi.spyOn(HTMLDialogElement.prototype, "close").mockImplementation(function(this: HTMLDialogElement) { this.removeAttribute("open"); });
}

