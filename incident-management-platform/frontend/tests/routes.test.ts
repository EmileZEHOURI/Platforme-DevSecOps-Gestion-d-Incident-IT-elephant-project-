
import { describe, expect, it } from "vitest";
import { existsSync, readdirSync } from "node:fs";
import path from "node:path";

const projectRoot = process.cwd();

const possibleAppDirectories = [
  path.join(projectRoot, "app"),
  path.join(projectRoot, "src", "app"),
];

const appDirectory = possibleAppDirectories.find(
  (directory) => existsSync(directory)
);

if (!appDirectory) {
  throw new Error("Dossier Next.js app/ ou src/app/ introuvable");
}

function collectPageRoutes(
  directory: string,
  segments: string[] = [],
): string[] {
  const routes: string[] = [];

  for (const entry of readdirSync(directory, {
    withFileTypes: true,
  })) {
    if (entry.isFile() && /^page\.(tsx|ts|jsx|js)$/.test(entry.name)) {
      routes.push(`/${segments.join("/")}`);
      continue;
    }

    if (!entry.isDirectory()) {
      continue;
    }

    // Les slots parallèles ne correspondent pas à des routes publiques.
    if (entry.name.startsWith("@")) {
      continue;
    }

    // Les groupes Next.js (auth), (dashboard), etc.
    // n'apparaissent pas dans les URL.
    const isRouteGroup =
      entry.name.startsWith("(") &&
      entry.name.endsWith(")");

    const nextSegments = isRouteGroup
      ? segments
      : [...segments, entry.name];

    routes.push(
      ...collectPageRoutes(
        path.join(directory, entry.name),
        nextSegments,
      ),
    );
  }

  return routes;
}

const availableRoutes = new Set(
  collectPageRoutes(appDirectory),
);

describe("Routes principales de l'application", () => {
  it.each([
    "/",
    "/login",
    "/dashboard",
    "/dashboard/account",
    "/dashboard/incidents",
    "/dashboard/incidents/new",
    "/dashboard/incidents/[id]",
    "/dashboard/incidents/assigned",
    "/dashboard/admin/incidents",
    "/dashboard/admin/users",
    "/dashboard/admin/audit-logs",
    "/dashboard/services",
  ])("possède la page %s", (route) => {
    expect(availableRoutes.has(route)).toBe(true);
  });
});
