import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";
import { IncidentOverview } from "@/components/incident-overview";
import { account, incident, json, http, deferred } from "./helpers/integration";
import type { User } from "@/types/auth";

const auth = vi.hoisted(() => ({ user: null as User | null }));
vi.mock("@/components/auth-provider", () => ({ useAuth: () => auth }));
beforeEach(() => { auth.user = { ...account }; });
const result = (page = 1) => ({ items: [{ ...incident, id: page === 1 ? 42 : 43, reference: page === 1 ? "INC-42" : "INC-43" }], total: 11, page, page_size: 10, total_pages: 2, has_next: page === 1, has_previous: page > 1 });

it.each(["USER", "TECHNICIAN", "ADMIN"] as const)("uses authorized endpoint and title for %s", async role => {
  auth.user = { ...account, role };
  const fetch = http((url, init) => {
    expect(url.pathname).toBe(role === "ADMIN" ? "/api/backend/incidents/all" : role === "TECHNICIAN" ? "/api/backend/incidents/assigned" : "/api/backend/incidents");
    expect(url.searchParams.get("page_size")).toBe("10");
    expect(url.searchParams.has("created_by_id")).toBe(false);
    expect(init.credentials).toBe("include");
    return json(result());
  });
  render(<IncidentOverview />);
  expect(screen.getByRole("heading", { name: role === "ADMIN" ? "Suivi des incidents" : "Mes incidents" })).toBeVisible();
  expect(await screen.findByText(incident.title)).toBeVisible();
  const table = screen.getByRole("table");
  expect(within(table).getByText("Ouvert")).toBeVisible();
  expect(within(table).getByText("Modérée")).toBeVisible();
  expect(screen.getByRole("link", { name: "Voir le détail de INC-42" })).toHaveAttribute("href", "/dashboard/incidents/42");
  expect(fetch).toHaveBeenCalledTimes(1);
});

it("paginates and resets page when filters or size change", async () => {
  const urls: URL[] = [];
  http(url => { urls.push(url); return json(result(Number(url.searchParams.get("page")))); });
  const user = userEvent.setup();
  render(<IncidentOverview />);
  await screen.findByText("INC-42");
  await user.click(screen.getByRole("button", { name: "Suivant" }));
  await screen.findByText("INC-43");
  expect(urls.at(-1)?.searchParams.get("page")).toBe("2");
  await user.selectOptions(screen.getByLabelText("Statut"), "CLOSED");
  await screen.findByText("INC-42");
  expect(urls.at(-1)?.searchParams.get("page")).toBe("1");
  expect(urls.at(-1)?.searchParams.get("status")).toBe("CLOSED");
  await user.selectOptions(screen.getByLabelText("Priorité"), "HIGH");
  await waitFor(() => expect(urls.at(-1)?.searchParams.get("priority")).toBe("HIGH"));
  await user.selectOptions(screen.getByLabelText("Incidents par page"), "20");
  await waitFor(() => expect(urls.at(-1)?.searchParams.get("page_size")).toBe("20"));
});

it.each([
  ["USER", "Aucun incident pour le moment."],
  ["TECHNICIAN", "Aucun incident ne vous est actuellement attribué."],
  ["ADMIN", "Aucun incident enregistré pour le moment."],
] as const)("shows role-specific empty state for %s", async (role, message) => {
  auth.user = { ...account, role };
  http(() => json({ ...result(), items: [], total: 0, total_pages: 0, has_next: false }));
  render(<IncidentOverview />);
  expect(await screen.findByText(message)).toBeVisible();
});

it("shows loading then data", async () => {
  const pending = deferred<Response>();
  http(() => pending.promise);
  render(<IncidentOverview />);
  expect(screen.getByText("Chargement des incidents…")).toBeVisible();
  await act(async () => pending.resolve(json(result())));
  expect(await screen.findByText("INC-42")).toBeVisible();
});

it("retries a failed request without displaying an empty state", async () => {
  let attempts = 0;
  http(() => ++attempts === 1 ? json({}, 500) : json(result()));
  render(<IncidentOverview />);
  await screen.findByText("Impossible de charger les incidents");
  expect(screen.queryByText("Aucun incident pour le moment.")).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Réessayer" }));
  expect(await screen.findByText("INC-42")).toBeVisible();
});

it("offers reconnection on 401 without automatic retries", async () => {
  const fetch = http(() => json({}, 401));
  render(<IncidentOverview />);
  expect(await screen.findByText("Session expirée")).toBeVisible();
  expect(screen.getByRole("link", { name: "Se reconnecter" })).toHaveAttribute("href", "/login?next=%2Fdashboard");
  expect(screen.queryByRole("button", { name: "Réessayer" })).not.toBeInTheDocument();
  expect(fetch).toHaveBeenCalledTimes(1);
});

it("switches technician scope and clears data when identity changes", async () => {
  auth.user = { ...account, role: "TECHNICIAN" };
  const urls: URL[] = [];
  http(url => { urls.push(url); return json(result()); });
  const view = render(<IncidentOverview />);
  await screen.findByText("INC-42");
  await userEvent.click(screen.getByRole("button", { name: "Mes déclarations" }));
  await waitFor(() => expect(urls.at(-1)?.pathname).toBe("/api/backend/incidents"));
  auth.user = { ...account, id: 99, role: "ADMIN" };
  view.rerender(<IncidentOverview />);
  await waitFor(() => expect(urls.at(-1)?.pathname).toBe("/api/backend/incidents/all"));
  expect(screen.getByRole("heading", { name: "Suivi des incidents" })).toBeVisible();
});

it("ignores stale responses after a scope switch", async () => {
  auth.user = { ...account, role: "TECHNICIAN" };
  const pending = deferred<Response>();
  http(url => url.pathname.endsWith("/assigned") ? pending.promise : json({ ...result(), items: [{ ...incident, title: "Déclaration personnelle" }] }));
  render(<IncidentOverview />);
  await userEvent.click(screen.getByRole("button", { name: "Mes déclarations" }));
  await screen.findByText("Déclaration personnelle");
  await act(async () => pending.resolve(json(result())));
  expect(screen.queryByText(incident.title)).not.toBeInTheDocument();
});
