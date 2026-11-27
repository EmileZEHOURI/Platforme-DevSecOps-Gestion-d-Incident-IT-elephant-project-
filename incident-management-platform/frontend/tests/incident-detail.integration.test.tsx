import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { IncidentDetail } from "@/components/incident-detail";
import { account, incident, json, http, deferred, dialogs } from "./helpers/integration";
import type { User } from "@/types/auth";
import type { IncidentResponse } from "@/types/incident";

const auth = vi.hoisted(() => ({ user: null as User | null }));
vi.mock("@/components/auth-provider", () => ({ useAuth: () => auth }));
vi.mock("next/navigation", () => ({ usePathname: () => "/dashboard/incidents/42" }));
let item: IncidentResponse;
let historyGets: number;
let detailCode: number;
let mutationCode: number;
let fetchMock: ReturnType<typeof http>;
beforeEach(() => {
  auth.user = { ...account }; item = { ...incident }; historyGets = 0; detailCode = 200; mutationCode = 200; dialogs();
  fetchMock = http((url, init) => {
    if (url.pathname.endsWith("/history")) { historyGets++; return json([{ id: 9, incident_id: 42, actor_id: 1, action: "INCIDENT_CREATED", field_name: null, old_value: null, new_value: null, created_at: incident.created_at }]); }
    if (url.pathname.endsWith("/technicians")) return json([]);
    if (init.method === "PATCH" || init.method === "POST") {
      if (mutationCode !== 200) return json({ detail: "Internal diagnostic" }, mutationCode);
      const body = init.body ? JSON.parse(String(init.body)) : {};
      if (url.pathname.endsWith("/comments")) return json({ id: 5, incident_id: 42, author_id: 1, content: body.content, created_at: incident.created_at, updated_at: incident.created_at }, 201);
      if (url.pathname.endsWith("/status")) item = { ...item, status: "IN_PROGRESS" };
      if (url.pathname.endsWith("/resolve")) item = { ...item, status: "RESOLVED", resolution: body.resolution, resolved_at: incident.created_at };
      if (url.pathname.endsWith("/close")) item = { ...item, status: "CLOSED", closed_at: incident.created_at };
      if (url.pathname.endsWith("/assignment")) item = { ...item, assigned_to_id: body.assigned_to_id };
      return json(item);
    }
    return json(detailCode === 200 ? item : { detail: "diagnostic" }, detailCode);
  });
});
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });
async function open() { render(<IncidentDetail id="42" />); await screen.findByRole("heading", { name: incident.title }); await screen.findByText("Incident créé"); }
const mutations = () => fetchMock.mock.calls.filter(([, init]) => init?.method === "PATCH" || init?.method === "POST");

describe("IncidentDetail with real children, permissions, services and HTTP client", () => {
  it("does not load without a session", () => { auth.user = null; render(<IncidentDetail id="42" />); expect(fetchMock).not.toHaveBeenCalled(); });
  it("shows loading, details, nullable fields and cookie request", async () => {
    await open(); expect(screen.getByText(incident.description)).toBeVisible(); expect(screen.getByText("Non attribué")).toBeVisible(); expect(screen.getByText("Non résolu")).toBeVisible();
    expect(fetchMock.mock.calls[0]).toEqual(["/api/backend/incidents/42", expect.objectContaining({ credentials: "include", method: "GET", cache: "no-store" })]);
  });
  it.each([[401,"Session expirée"],[403,"Accès refusé"],[404,"Incident introuvable ou inaccessible"],[422,"Incident introuvable ou inaccessible"],[500,"Impossible de charger l’incident"]])("handles HTTP %i", async (code, title) => {
    detailCode = Number(code); render(<IncidentDetail id="42" />); expect(await screen.findByRole("heading", { name: String(title) })).toBeVisible();
    if (code === 401) { expect(screen.getByRole("link", { name: "Se reconnecter" })).toHaveAttribute("href", "/login?next=%2Fdashboard%2Fincidents%2F42"); expect(historyGets).toBe(0); }
    else expect(await screen.findByText("Incident créé")).toBeVisible();
  });
  it("retries a failed detail request", async () => {
    detailCode = 500; render(<IncidentDetail id="42" />); await screen.findByRole("button", { name: "Réessayer" }); detailCode = 200;
    await userEvent.click(screen.getByRole("button", { name: "Réessayer" })); expect(await screen.findByRole("heading", { name: incident.title })).toBeVisible();
  });
  it("aborts old requests and ignores a late result when route changes", async () => {
    const old = deferred<Response>(); fetchMock.mockImplementationOnce(() => old.promise);
    const view = render(<IncidentDetail id="42" />); expect(screen.getByText("Chargement de l’incident…")).toBeVisible();
    const signal = fetchMock.mock.calls[0][1]?.signal; item = { ...item, id: 43, title: "Nouvel incident" }; view.rerender(<IncidentDetail id="43" />);
    await screen.findByRole("heading", { name: "Nouvel incident" }); expect(signal?.aborted).toBe(true);
    await act(async () => old.resolve(json(incident))); expect(screen.queryByRole("heading", { name: incident.title })).not.toBeInTheDocument();
  });
  it("posts only trimmed comment content and refreshes real history", async () => {
    await open(); const before = historyGets; await userEvent.type(screen.getByLabelText("Ajouter un commentaire"), "  Suivi du problème  ");
    await userEvent.click(screen.getByRole("button", { name: "Ajouter le commentaire" })); await screen.findByText("Commentaire ajouté avec succès.");
    expect(screen.getByText("Suivi du problème")).toBeVisible(); expect(screen.getByText("Alice Test (vous)")).toBeVisible(); expect(JSON.parse(String(mutations()[0][1]?.body))).toEqual({ content: "Suivi du problème" });
    await waitFor(() => expect(historyGets).toBe(before + 1));
  });
  it.each(["   ", "x".repeat(5001)])("rejects empty or oversized comment (%#)", async content => {
    await open(); fireEvent.change(screen.getByLabelText("Ajouter un commentaire"), { target: { value: content } }); fireEvent.click(screen.getByRole("button", { name: "Ajouter le commentaire" }));
    expect(screen.getByText(/Saisissez un commentaire de 1/)).toBeVisible(); expect(mutations()).toHaveLength(0);
  });
  it("preserves a rejected comment and does not announce success", async () => {
    mutationCode = 500; await open(); await userEvent.type(screen.getByLabelText("Ajouter un commentaire"), "À conserver"); await userEvent.click(screen.getByRole("button", { name: "Ajouter le commentaire" }));
    await screen.findByText(/Le commentaire n’a pas pu être confirmé/); expect(screen.getByLabelText("Ajouter un commentaire")).toHaveValue("À conserver"); expect(screen.queryByText("Commentaire ajouté avec succès.")).not.toBeInTheDocument();
  });
  it("blocks comments when backend reports CLOSED", async () => {
    mutationCode = 409; await open(); await userEvent.type(screen.getByLabelText("Ajouter un commentaire"), "Suivi"); await userEvent.click(screen.getByRole("button", { name: "Ajouter le commentaire" }));
    await screen.findByText("Cet incident est fermé et ne peut plus recevoir de commentaire."); expect(screen.getByRole("button", { name: "Ajouter le commentaire" })).toBeDisabled();
  });
  it("runs start, resolve and close through real dialogs and updates display", async () => {
    auth.user = { ...account, role: "TECHNICIAN" }; item.assigned_to_id = 1; await open();
    await userEvent.click(screen.getByRole("button", { name: "Commencer le traitement" })); await screen.findByRole("button", { name: "Résoudre l’incident" });
    await userEvent.click(screen.getByRole("button", { name: "Résoudre l’incident" })); const resolve = screen.getByRole("dialog");
    await userEvent.click(within(resolve).getByRole("button", { name: "Confirmer la résolution" })); expect(within(resolve).getByRole("alert")).toHaveTextContent("le champ ne peut pas être vide"); expect(mutations()).toHaveLength(1);
    await userEvent.type(within(resolve).getByLabelText("Description de la résolution"), "  Correctif vérifié  "); await userEvent.click(within(resolve).getByRole("button", { name: "Confirmer la résolution" }));
    await screen.findByText("Correctif vérifié"); expect(JSON.parse(String(mutations()[1][1]?.body))).toEqual({ resolution: "Correctif vérifié" });
    await userEvent.click(screen.getByRole("button", { name: "Clôturer l’incident" })); await userEvent.click(screen.getByRole("button", { name: "Annuler" })); expect(mutations()).toHaveLength(2);
    await userEvent.click(screen.getByRole("button", { name: "Clôturer l’incident" })); await userEvent.click(screen.getByRole("button", { name: "Confirmer la clôture" }));
    await screen.findByText("INC-42 : incident clôturé."); expect(mutations()[2][1]?.body).toBeUndefined(); expect(screen.getByLabelText("Ajouter un commentaire")).toBeDisabled(); expect(screen.getByText("Correctif vérifié")).toBeVisible();
  });
  it.each(["USER", "TECHNICIAN"] as const)("hides start and admin assignment for non-assigned %s", async role => {
    auth.user = { ...account, role }; item.assigned_to_id = 2; await open(); expect(screen.queryByRole("button", { name: "Commencer le traitement" })).not.toBeInTheDocument(); expect(screen.queryByRole("button", { name: "Réassigner" })).not.toBeInTheDocument();
  });
  it("assigns through the real admin dialog and updates history", async () => {
    auth.user = { ...account, role: "ADMIN" }; await open(); await userEvent.click(screen.getByRole("button", { name: "Assigner" }));
    await userEvent.selectOptions(screen.getByLabelText("Nouveau responsable"), "1"); await userEvent.click(screen.getByRole("button", { name: "Confirmer" }));
    await screen.findByText("Assignation enregistrée."); expect(JSON.parse(String(mutations()[0][1]?.body))).toEqual({ assigned_to_id: 1 }); expect(screen.getByRole("button", { name: "Commencer le traitement" })).toBeVisible();
  });
  it("prevents duplicate start requests while pending", async () => {
    auth.user = { ...account, role: "TECHNICIAN" }; item.assigned_to_id = 1; await open();
    const pending = deferred<Response>(); fetchMock.mockImplementationOnce(() => pending.promise);
    fireEvent.click(screen.getByRole("button", { name: "Commencer le traitement" })); expect(screen.getByRole("button", { name: "Démarrage…" })).toBeDisabled(); fireEvent.click(screen.getByRole("button", { name: "Démarrage…" })); expect(mutations()).toHaveLength(1);
    await act(async () => pending.resolve(json({ ...item, status: "IN_PROGRESS" }))); expect(await screen.findByRole("button", { name: "Résoudre l’incident" })).toBeVisible();
  });
});
