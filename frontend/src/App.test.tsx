import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";

const anonymous = { authenticated: false, user: null, memberships: [] };
const school = (code: string, name: string) => ({
  role: "admin_staff", organisation: { id: code, code, name, type: "institution" },
});
const oversight = {
  role: "bha_user",
  organisation: { id: "BHA", code: "BHA", name: "Demo Oversight", type: "oversight" },
};
const north = school("NORTH", "North Demo School");
const south = school("SOUTH", "South Demo School");
const signedIn = (memberships = [north, south, oversight]) => ({
  authenticated: true, user: { id: "demo", email: "staff@example.invalid" }, memberships,
});
const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status });
const fetchMock = vi.fn<typeof fetch>();

beforeEach(() => {
  window.history.replaceState(null, "", "/app/dashboard");
  document.cookie = "csrftoken=initial; Path=/";
  fetchMock.mockReset();
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

async function submitLogin() {
  fireEvent.change(await screen.findByLabelText("Email address"), { target: { value: "staff@example.invalid" } });
  fireEvent.change(screen.getByLabelText("Password"), { target: { value: "synthetic" } });
  fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
}

describe("App", () => {
  it("guards direct navigation, signs in, and logs out using the rotated cookie", async () => {
    fetchMock.mockResolvedValueOnce(json(anonymous)).mockImplementationOnce(async () => {
      document.cookie = "csrftoken=rotated; Path=/";
      return json(signedIn());
    }).mockResolvedValueOnce(json(anonymous));
    render(<App />);

    await screen.findByRole("heading", { name: "Sign in" });
    expect(window.location.pathname).toBe("/login");
    expect(screen.queryByRole("navigation")).toBeNull();
    await submitLogin();
    await screen.findByRole("heading", { name: "North Demo School" });
    expect(window.location.pathname).toBe("/app/dashboard");
    expect(fetchMock).toHaveBeenNthCalledWith(2, "/api/v1/auth/login/", expect.objectContaining({
      method: "POST", headers: expect.objectContaining({ "X-CSRFToken": "initial" }),
    }));
    fireEvent.click(screen.getByRole("button", { name: "Sign out" }));
    await screen.findByRole("heading", { name: "Sign in" });
    expect(screen.queryByText("North Demo School")).toBeNull();
    expect(fetchMock).toHaveBeenNthCalledWith(3, "/api/v1/auth/logout/", expect.objectContaining({
      method: "POST", headers: expect.objectContaining({ "X-CSRFToken": "rotated" }),
    }));
  });

  it.each([
    [400, "Check your email address and password."],
    [401, "Invalid email or password."],
    [403, "Sign-in could not be verified. Please try again."],
    [429, "Too many failed login attempts. Wait a few minutes and try again."],
  ])("shows safe feedback for login status %s", async (status, message) => {
    fetchMock.mockResolvedValueOnce(json(anonymous))
      .mockResolvedValueOnce(new Response("<html>Rejected</html>", { status }))
      .mockResolvedValueOnce(json(anonymous));
    render(<App />);
    await submitLogin();
    expect((await screen.findByRole("alert")).textContent).toBe(message);
  });

  it("lets staff retry if the initial session request fails", async () => {
    fetchMock.mockRejectedValueOnce(new TypeError("offline")).mockResolvedValueOnce(json(anonymous));
    render(<App />);
    expect((await screen.findByRole("alert")).textContent).toMatch(/connection/i);
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    await screen.findByRole("heading", { name: "Sign in" });
  });

  it("shows a connection error if login fails to reach the server", async () => {
    fetchMock.mockResolvedValueOnce(json(anonymous)).mockRejectedValueOnce(new TypeError("offline"));
    render(<App />);
    await submitLogin();
    expect((await screen.findByRole("alert")).textContent).toMatch(/connection/i);
  });

  it.each([[[]], [[oversight]]])("shows no access without an institution %#", async (memberships) => {
    fetchMock.mockResolvedValueOnce(json(signedIn(memberships)));
    render(<App />);
    await screen.findByRole("heading", { name: "No institution access" });
    expect(screen.queryByLabelText("Institution")).toBeNull();
    expect(screen.queryByRole("navigation")).toBeNull();
    expect(screen.getByRole("button", { name: "Sign out" })).toBeTruthy();
  });

  it("restores the session, switches schools, and clears a revoked membership", async () => {
    fetchMock.mockResolvedValueOnce(json(signedIn())).mockResolvedValueOnce(json(signedIn()))
      .mockResolvedValueOnce(json(signedIn([north])));
    const app = render(<App />);
    await screen.findByRole("heading", { name: "North Demo School" });
    const selector = screen.getByLabelText("Institution");
    expect(screen.queryByRole("option", { name: "Demo Oversight" })).toBeNull();
    fireEvent.change(selector, { target: { value: "SOUTH" } });
    await screen.findByRole("heading", { name: "South Demo School" });
    expect(screen.queryByRole("heading", { name: "North Demo School" })).toBeNull();
    fireEvent.click(screen.getByRole("link", { name: "Dashboard" }));
    await screen.findByRole("heading", { name: "North Demo School" });
    expect(screen.queryByRole("option", { name: "South Demo School" })).toBeNull();
    app.unmount();
    fetchMock.mockResolvedValueOnce(json(signedIn([north])));
    render(<App />);
    await screen.findByRole("heading", { name: "North Demo School" });
  });

  it("clears the workspace and prompts sign-in on expiry", async () => {
    fetchMock.mockResolvedValueOnce(json(signedIn())).mockResolvedValueOnce(json(anonymous));
    render(<App />);
    await screen.findByRole("heading", { name: "North Demo School" });
    fireEvent.click(screen.getByRole("link", { name: "Dashboard" }));
    await waitFor(() => expect(window.location.pathname).toBe("/login"));
    expect((await screen.findByRole("alert")).textContent).toMatch(/session expired/i);
    expect(screen.queryByText("North Demo School")).toBeNull();
  });
});
