import { afterEach, expect, it, vi } from "vitest";

import { InstitutionScope } from "./session";

afterEach(() => vi.unstubAllGlobals());

it("discards a delayed response even if the transport ignores cancellation", async () => {
  let deliver!: (response: Response) => void;
  const fetchMock = vi.fn<typeof fetch>()
    .mockReturnValueOnce(new Promise((resolve) => { deliver = resolve; }))
    .mockResolvedValueOnce(Response.json({ name: "South demo record" }));
  vi.stubGlobal("fetch", fetchMock);
  const reconcile = vi.fn();
  const north = new InstitutionScope("NORTH", reconcile, vi.fn());
  const old = north.request("/api/v1/students/");
  north.clear();
  const south = new InstitutionScope("SOUTH", reconcile, vi.fn());
  await expect(south.request("/api/v1/students/")).resolves.toEqual({ name: "South demo record" });
  deliver(Response.json({ name: "North demo record" }));
  await expect(old).rejects.toMatchObject({ name: "AbortError" });
  expect(new Headers(fetchMock.mock.calls[0][1]?.headers).get("X-Organisation-Code")).toBe("NORTH");
  expect(new Headers(fetchMock.mock.calls[1][1]?.headers).get("X-Organisation-Code")).toBe("SOUTH");
  expect(fetchMock.mock.calls[0][1]?.signal?.aborted).toBe(true);
  expect(reconcile).not.toHaveBeenCalled();
});

it("invalidates the current scope before reconciling a denial", async () => {
  const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(new Response(null, { status: 403 }));
  vi.stubGlobal("fetch", fetchMock);
  const reconcile = vi.fn(async () => {
    expect(fetchMock.mock.calls[0][1]?.signal?.aborted).toBe(true);
  });
  const scope = new InstitutionScope("NORTH", reconcile, vi.fn());
  await expect(scope.request("/api/v1/students/")).rejects.toMatchObject({ status: 403 });
  expect(reconcile).toHaveBeenCalledOnce();
  await expect(scope.request("/api/v1/students/")).rejects.toMatchObject({ name: "AbortError" });
  expect(fetchMock).toHaveBeenCalledOnce();
});
