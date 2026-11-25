
import { useState } from "react";
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

// Composant de démonstration pour valider l'environnement de test.
function TestCounter() {
  const [count, setCount] = useState(0);

  return (
    <button onClick={() => setCount((previous) => previous + 1)}>
      Incidents : {count}
    </button>
  );
}

describe("Configuration des tests React", () => {
  it("affiche correctement un composant", () => {
    render(<TestCounter />);

    expect(
      screen.getByRole("button", {
        name: "Incidents : 0",
      })
    ).toBeInTheDocument();
  });

  it("réagit correctement à un clic utilisateur", async () => {
    const user = userEvent.setup();

    render(<TestCounter />);

    const button = screen.getByRole("button", {
      name: "Incidents : 0",
    });

    await user.click(button);

    expect(
      screen.getByRole("button", {
        name: "Incidents : 1",
      })
    ).toBeInTheDocument();
  });

  it("gère plusieurs interactions successives", async () => {
    const user = userEvent.setup();

    render(<TestCounter />);

    const button = screen.getByRole("button");

    await user.click(button);
    await user.click(button);
    await user.click(button);

    expect(button).toHaveTextContent("Incidents : 3");
  });
});
