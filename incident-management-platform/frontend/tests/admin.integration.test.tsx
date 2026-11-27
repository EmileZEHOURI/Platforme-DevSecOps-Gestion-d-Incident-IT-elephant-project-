import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { UserManagement } from "@/components/user-management";
import { IncidentManagement } from "@/components/incident-management";
import { AuditManagement } from "@/components/audit-management";
import type { User } from "@/types/auth";
import { account, incident, dialogs, http, json } from "./helpers/integration";

const auth = vi.hoisted(() => ({ user: null as User | null }));
vi.mock("@/components/auth-provider", () => ({ useAuth: () => auth }));
vi.mock("next/navigation", () => ({ usePathname: () => "/dashboard/admin/users" }));
let users: User[];
let failure: number;
let fetchMock: ReturnType<typeof http>;
beforeEach(() => {
  dialogs(); auth.user = { ...account, role: "ADMIN" }; users = [{ ...account, role: "ADMIN" }, { ...account, id: 2, full_name: "Bob Technicien", role: "TECHNICIAN" }]; failure = 0;
  fetchMock = http((url, init) => {
    if (init.method === "PATCH") {
      if (failure) return json({ detail: "Liste non vide, impossibilité de désactivation" }, failure);
      if (url.pathname.includes("/users/")) { users[1] = { ...users[1], ...JSON.parse(String(init.body)) }; return json(users[1]); }
      return json({ ...incident, ...JSON.parse(String(init.body)) });
    }
    if (url.pathname.endsWith("/users")) return json(users.filter(u => (!url.searchParams.has("role") || u.role === url.searchParams.get("role")) && (!url.searchParams.has("is_active") || String(u.is_active) === url.searchParams.get("is_active"))));
    if (url.pathname.endsWith("/technicians")) return json([users[1]]);
    if (failure) return json({ detail: "INTERNAL_SECRET" }, failure);
    const page = Number(url.searchParams.get("page") ?? 1), size = Number(url.searchParams.get("page_size") ?? 20);
    const log = { id: 8, user_id: null, event_type: "LOGIN_FAILURE", result: "FAILURE", resource_type: null, resource_id: null, ip_address: null, user_agent: null, created_at: incident.created_at, details: { access_token: "TOKEN_SECRET", nested: [{ password: "PASSWORD_SECRET", count: 0 }], note: "<script>text</script>" } };
    return json({ items: url.pathname.endsWith("/audit-logs") ? [log] : [{ ...incident, id: page, reference: `INC-${page}` }], total: 41, page, page_size: size, total_pages: Math.ceil(41 / size), has_next: page * size < 41, has_previous: page > 1 });
  });
});
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });
const lastQuery = (path: string) => new URL(String(fetchMock.mock.calls.filter(([url]) => String(url).includes(path)).at(-1)?.[0]), "http://localhost").searchParams;

describe("Admin boundaries and integrated UI", () => {
  it.each(["USER", "TECHNICIAN"] as const)("denies all admin components to %s without API requests", role => {
    auth.user = { ...account, role }; render(<><UserManagement /><IncidentManagement /><AuditManagement /></>);
    expect(screen.getAllByRole("heading", { name: "Accès refusé" })).toHaveLength(3); expect(fetchMock).not.toHaveBeenCalled();
  });
  it("reads user details without an individual endpoint and protects admins", async () => {
    render(<UserManagement />); await screen.findByRole("button", { name: "Bob Technicien" });
    const adminRow = screen.getByRole("button", { name: account.full_name }).closest("tr")!;
    expect(within(adminRow).queryByRole("button", { name: "Désactiver" })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Bob Technicien" })); expect(within(screen.getByRole("dialog")).getByText(account.email)).toBeVisible();
    expect(fetchMock.mock.calls).toHaveLength(1);
  });
  it("confirms deactivation, keeps filters, then activates using a false query", async () => {
    render(<UserManagement />); await screen.findByRole("table"); await userEvent.selectOptions(screen.getByLabelText("Rôle"), "TECHNICIAN"); await userEvent.selectOptions(screen.getByLabelText("Statut"), "true");
    await screen.findByRole("button", { name: "Désactiver" }); await userEvent.click(screen.getByRole("button", { name: "Désactiver" }));
    await userEvent.click(screen.getByRole("button", { name: "Annuler" })); expect(fetchMock.mock.calls.some(([,init]) => init?.method === "PATCH")).toBe(false);
    await userEvent.click(screen.getByRole("button", { name: "Désactiver" })); await userEvent.click(screen.getByRole("button", { name: "Confirmer la désactivation" })); await screen.findByText("Aucun compte ne correspond à la sélection actuelle.");
    expect(lastQuery("/users").get("role")).toBe("TECHNICIAN"); expect(lastQuery("/users").get("is_active")).toBe("true");
    await userEvent.selectOptions(screen.getByLabelText("Statut"), "false"); await screen.findByRole("button", { name: "Activer" }); expect(lastQuery("/users").get("is_active")).toBe("false");
    await userEvent.click(screen.getByRole("button", { name: "Activer" })); await userEvent.click(screen.getByRole("button", { name: "Confirmer l’activation" })); await screen.findByText("Bob Technicien : compte activé.");
    const bodies = fetchMock.mock.calls.filter(([, init]) => init?.method === "PATCH").map(([,init]) => JSON.parse(String(init?.body))); expect(bodies).toEqual([{is_active:false},{is_active:true}]);
  });
  it("preserves user data and shows a blocking technician conflict", async () => {
    failure=409; render(<UserManagement />); await screen.findByRole("button", { name: "Désactiver" }); await userEvent.click(screen.getByRole("button", { name: "Désactiver" })); await userEvent.click(screen.getByRole("button", { name: "Confirmer la désactivation" }));
    expect(await screen.findByText(/Veuillez les réassigner/)).toBeVisible(); expect(screen.getByRole("table")).toBeVisible(); expect(screen.queryByText("Bob Technicien : compte désactivé.")).not.toBeInTheDocument();
  });
  it("pages admin incidents on the server and resets page when filters change", async () => {
    render(<IncidentManagement />); await screen.findByText("Page 1 sur 3"); await userEvent.selectOptions(screen.getByLabelText("Statut"), "OPEN"); await screen.findByText("Page 1 sur 3");
    await userEvent.click(screen.getByRole("button", { name: "Suivant" })); await screen.findByText("Page 2 sur 3"); expect(lastQuery("/incidents/all").get("status")).toBe("OPEN"); expect(lastQuery("/incidents/all").get("page")).toBe("2");
    await userEvent.selectOptions(screen.getByLabelText("Catégorie"), "SECURITY"); await screen.findByText("Page 1 sur 3"); expect(lastQuery("/incidents/all").get("category")).toBe("SECURITY"); expect(screen.getByRole("link", { name: "Voir le détail de INC-1" })).toBeVisible();
  });
  it("updates priority with the real dialog and refetches filtered results", async () => {
    render(<IncidentManagement />); await screen.findByRole("button", { name: "Modifier la priorité" }); await userEvent.click(screen.getByRole("button", { name: "Modifier la priorité" }));
    const dialog=screen.getByRole("dialog"); await userEvent.selectOptions(within(dialog).getByRole("combobox"), "HIGH"); await userEvent.click(within(dialog).getByRole("button", { name: /Confirmer/ }));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument()); expect(fetchMock.mock.calls.filter(([,init]) => init?.method === "PATCH").map(([,init]) => JSON.parse(String(init?.body)))).toEqual([{priority:"HIGH"}]);
  });
  it("shows null audit actor and redacts nested secrets without a detail request", async () => {
    render(<AuditManagement />); await screen.findByRole("button", { name: "Voir le journal 8" }); await userEvent.click(screen.getByRole("button", { name: "Voir le journal 8" }));
    const dialog=screen.getByRole("dialog"); expect(within(dialog).getByText("Utilisateur inconnu ou supprimé")).toBeVisible(); expect(dialog).not.toHaveTextContent("TOKEN_SECRET"); expect(dialog).not.toHaveTextContent("PASSWORD_SECRET"); expect(dialog).toHaveTextContent("[masqué]"); expect(dialog).toHaveTextContent("<script>text</script>");
    expect(fetchMock.mock.calls.some(([url]) => String(url).includes("/audit-logs/"))).toBe(false);
  });
  it("combines audit dates/result/actor, rejects inverted dates and keeps filters on pagination", async () => {
    render(<AuditManagement />); await screen.findByText("Page 1 sur 3");
    fireEvent.change(screen.getByLabelText("Date/heure de début"),{target:{value:"2026-11-01T12:00"}}); fireEvent.change(screen.getByLabelText("Date/heure de fin"),{target:{value:"2026-11-02T12:00"}});
    fireEvent.change(screen.getByLabelText("Identifiant utilisateur"),{target:{value:"0"}}); await userEvent.selectOptions(screen.getByLabelText("Résultat"), "DENIED"); await screen.findByText("Page 1 sur 3");
    expect(lastQuery("/audit-logs").get("user_id")).toBe("0"); expect(lastQuery("/audit-logs").get("date_from")).toBe(new Date("2026-11-01T12:00").toISOString());
    await userEvent.click(screen.getByRole("button", {name:"Suivant"})); await screen.findByText("Page 2 sur 3"); expect(lastQuery("/audit-logs").get("result")).toBe("DENIED");
    const count=fetchMock.mock.calls.length; fireEvent.change(screen.getByLabelText("Date/heure de début"),{target:{value:"2026-12-01T12:00"}}); expect(screen.getByRole("alert")).toHaveTextContent("La date de début doit être antérieure ou égale à la date de fin.");
    await new Promise(done=>setTimeout(done,300)); expect(fetchMock.mock.calls).toHaveLength(count); expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });
  it.each([403,422,500])("handles audit HTTP %i without exposing diagnostics", async code => {
    failure=code; render(<AuditManagement />); const alert=await screen.findByRole("alert"); expect(alert).not.toHaveTextContent("INTERNAL_SECRET"); expect(within(alert).getByRole("button",{name:"Réessayer"})).toBeVisible();
    failure=0; await userEvent.click(within(alert).getByRole("button",{name:"Réessayer"})); expect(await screen.findByRole("button",{name:"Voir le journal 8"})).toBeVisible();
  });
});
