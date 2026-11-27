import { act, render, screen, within, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";
import { IncidentMetrics } from "@/components/incident-metrics";
import { notifyIncidentUpdate } from "@/lib/incident-updates";
import { createIncident } from "@/services/incident.service";
import { account, incident, json, http, deferred } from "./helpers/integration";
import type { User } from "@/types/auth";

const auth = vi.hoisted(() => ({ user: null as User | null }));
vi.mock("@/components/auth-provider", () => ({ useAuth: () => auth }));
beforeEach(() => { auth.user = { ...account }; });
function response(total: number) {
  return json({ items: total ? [incident] : [], total, page: 1, page_size: 1, total_pages: total, has_next: total > 1, has_previous: false });
}
function count(url: URL) {
  const status = url.searchParams.get("status");
  if (url.searchParams.get("priority") === "CRITICAL") return status === "OPEN" ? 12 : 3;
  return status === "OPEN" ? 123 : status === "IN_PROGRESS" ? 24 : status === "RESOLVED" ? 56 : 999;
}
const card = (name: string) => within(screen.getByRole("region", { name }));
it.each(["USER", "TECHNICIAN", "ADMIN"] as const)("counts all pages with the correct scope for %s", async role => {
  auth.user = { ...account, role };
  const fetch = http((url, init) => {
    expect(url.pathname).toBe(role === "ADMIN" ? "/api/backend/incidents/all" : role === "TECHNICIAN" ? "/api/backend/incidents/assigned" : "/api/backend/incidents");
    expect(url.searchParams.get("page_size")).toBe("1");
    expect(url.searchParams.get("page")).toBe("1");
    expect(url.searchParams.has("created_by_id")).toBe(false);
    expect(init.credentials).toBe("include");
    return response(count(url));
  });
  render(<IncidentMetrics />);
  expect(await card("Incidents ouverts").findByText("123")).toBeVisible();
  expect(card("En cours").getByText("24")).toBeVisible();
  expect(card("Critiques actifs").getByText("15")).toBeVisible();
  expect(card("Résolus").getByText("56")).toBeVisible();
  expect(fetch).toHaveBeenCalledTimes(5);
});
it("shows actual zero totals", async () => {
  http(() => response(0));
  render(<IncidentMetrics />);
  expect(await screen.findAllByText("0")).toHaveLength(4);
});
it("shows loading without fictitious zeros", async () => {
  const pending = deferred<Response>();
  http(() => pending.promise.then(r => r.clone()));
  render(<IncidentMetrics />);
  expect(screen.getByText("Chargement des indicateurs…")).toBeVisible();
  expect(screen.queryByText("0")).not.toBeInTheDocument();
  await act(async () => pending.resolve(response(0)));
  expect(await screen.findAllByText("0")).toHaveLength(4);
});
it("handles partial API failure and retry", async () => {
  let fail = true;
  http(url => fail && url.searchParams.get("status") === "RESOLVED" ? json({}, 500) : response(count(url)));
  render(<IncidentMetrics />);
  await screen.findByRole("alert");
  expect(screen.queryByText("123")).not.toBeInTheDocument();
  fail = false;
  await userEvent.click(screen.getByRole("button", { name: "Réessayer les indicateurs" }));
  expect(await screen.findByText("123")).toBeVisible();
});
it("does not retry an expired session on focus or mutations", async () => {
  const fetch = http(() => json({}, 401));
  render(<IncidentMetrics />);
  await screen.findByRole("alert");
  expect(screen.getByRole("link", { name: "Se reconnecter" })).toHaveAttribute("href", "/login?next=%2Fdashboard");
  await act(async () => { window.dispatchEvent(new Event("focus")); notifyIncidentUpdate(42, incident); });
  expect(fetch).toHaveBeenCalledTimes(5);
});
it("refreshes after mutations and explicit reload", async () => {
  let total = 1;
  http(() => response(total));
  render(<IncidentMetrics />);
  await card("Incidents ouverts").findByText("1");
  total = 8;
  await act(async () => { notifyIncidentUpdate(42, incident); });
  expect(await card("Incidents ouverts").findByText("8")).toBeVisible();
  total = 9;
  await userEvent.click(screen.getByRole("button", { name: "Actualiser les indicateurs" }));
  expect(await card("Incidents ouverts").findByText("9")).toBeVisible();
});
it("invalidates metrics after successful creation", async () => {
  let total = 0;
  http((_url, init) => {
    if (init.method === "POST") { total = 1; return json(incident, 201); }
    return response(total);
  });
  render(<IncidentMetrics />);
  await card("Incidents ouverts").findByText("0");
  await act(async () => { await createIncident(incident); });
  expect(await card("Incidents ouverts").findByText("1")).toBeVisible();
});
it("resets identity and ignores outdated requests", async () => {
  const old = deferred<Response>();
  http(url => url.pathname.endsWith("/all") ? response(7) : old.promise.then(r => r.clone()));
  const view = render(<IncidentMetrics />);
  await waitFor(() => expect(screen.getByText("Chargement des indicateurs…")).toBeVisible());
  auth.user = { ...account, id: 22, role: "ADMIN" };
  view.rerender(<IncidentMetrics />);
  await card("Incidents ouverts").findByText("7");
  await act(async () => old.resolve(response(99)));
  expect(card("Incidents ouverts").getByText("7")).toBeVisible();
  expect(screen.queryByText("99")).not.toBeInTheDocument();
});
