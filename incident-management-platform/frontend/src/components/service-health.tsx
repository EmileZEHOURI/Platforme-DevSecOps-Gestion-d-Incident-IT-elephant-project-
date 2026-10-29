"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Badge, Button } from "@/components/ui";
type Health = "loading" | "ok" | "error";
export function ServiceHealth() {
  const [checks, setChecks] = useState<{ api: Health; database: Health }>({
    api: "loading",
    database: "loading",
  });
  const [run, setRun] = useState(0);
  useEffect(() => {
    let active = true;
    const check = async (key: "api" | "database", path: string) => {
      try {
        const result = await api<{ status: string; database?: string }>(path);
        if (active)
          setChecks((old) => ({
            ...old,
            [key]:
              result.status === "ok" &&
              (key !== "database" || result.database === "connected")
                ? "ok"
                : "error",
          }));
      } catch {
        if (active) setChecks((old) => ({ ...old, [key]: "error" }));
      }
    };
    void check("api", "/health");
    void check("database", "/health/database");
    return () => {
      active = false;
    };
  }, [run]);
  return (
    <section className="panel">
      <div className="panel-heading">
        <h2>État des services</h2>
        <Button
          variant="ghost"
          disabled={checks.api === "loading" || checks.database === "loading"}
          onClick={() => {
            setChecks({ api: "loading", database: "loading" });
            setRun(run + 1);
          }}
        >
          Actualiser ↻
        </Button>
      </div>
      <div aria-live="polite">
        {(
          [
            ["api", "API applicative", "FastAPI"],
            ["database", "Base de données", "PostgreSQL"],
          ] as const
        ).map(([key, title, subtitle]) => (
          <div className="service-row" key={key}>
            <span className="service-icon" aria-hidden="true">
              {key === "api" ? "⌘" : "▤"}
            </span>
            <div>
              <strong>{title}</strong>
              <small>{subtitle}</small>
            </div>
            <Badge
              tone={
                checks[key] === "ok"
                  ? "success"
                  : checks[key] === "error"
                    ? "warning"
                    : "neutral"
              }
            >
              {checks[key] === "loading"
                ? "Vérification…"
                : checks[key] === "ok"
                  ? "Disponible"
                  : "Indisponible"}
            </Badge>
          </div>
        ))}
      </div>
      <p className="panel-note">
        Disponibilité vérifiée à l’ouverture de la page et à chaque
        actualisation.
      </p>
    </section>
  );
}
