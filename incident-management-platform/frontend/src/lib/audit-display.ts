// Display defence only: the API must also exclude secrets from audit responses.
export function redactAuditDetails(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(redactAuditDetails);
  if (value && typeof value === "object") return Object.fromEntries(Object.entries(value).map(([key, item]) => [key,
    /password|passwd|pwd|token|secret|authorization|cookie|api.?key|private.?key|credential/i.test(key) ? "[masqué]" : redactAuditDetails(item)]));
  if (typeof value === "string") return value
    .replace(/Bearer\s+[^\s"']+/gi, "Bearer [masqué]")
    .replace(/eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+/g, "[masqué]");
  return value;
}
export function auditDate(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Date indisponible" : new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium", timeStyle: "long" }).format(date);
}
