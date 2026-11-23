import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import App from "./App";

describe("App", () => {
  it("labels the initial shell as a synthetic non-production prototype", () => {
    render(<App />);

    expect(screen.getByRole("heading", { name: "Horseracing Student Records" })).toBeTruthy();
    expect(screen.getByText("Synthetic data only — not production ready")).toBeTruthy();
  });
});
