type Membership = {
  role: string;
  organisation: { id: string; code: string; name: string; type: string };
};

export type Session = {
  authenticated: boolean;
  user: { id: string; email: string } | null;
  memberships: Membership[];
};

export function schoolsFor(session: Session) {
  return session.authenticated ? session.memberships.filter(({ organisation, role }) =>
    organisation.type === "institution" &&
    ["institution_admin", "admin_staff", "read_only"].includes(role)
  ) : [];
}

export class ApiError extends Error {
  constructor(readonly status: number) {
    super(`Request failed (${status})`);
  }
}

function csrfToken() {
  return document.cookie.split(";").map((cookie) => cookie.trim())
    .find((cookie) => cookie.startsWith("csrftoken="))?.slice("csrftoken=".length) ?? "";
}

export async function sessionRequest(
  action: "session" | "login" | "logout",
  signal: AbortSignal,
  body: { email: string; password: string } | Record<string, never> = {},
): Promise<Session> {
  const response = await fetch(`/api/v1/auth/${action}/`, {
    credentials: "same-origin",
    cache: "no-store",
    signal,
    ...(action === "session" ? {} : {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken() },
      body: JSON.stringify(body),
    }),
  });
  if (!response.ok) throw new ApiError(response.status);
  return response.json();
}

// The workspace owns a scope for one selection. Never reuse it after clearing it.
export class InstitutionScope {
  private readonly controller = new AbortController();
  readonly signal = this.controller.signal;

  constructor(
    readonly code: string,
    private readonly onDenied: () => void | Promise<void>,
    private readonly onActivity: () => void,
  ) {}

  clear() {
    this.controller.abort();
  }

  async request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const url = new URL(path, window.location.origin);
    if (url.origin !== window.location.origin || !url.pathname.startsWith("/api/v1/students/")) {
      throw new TypeError("An institution request must use the same-origin student API.");
    }
    const signal = init.signal ? AbortSignal.any([this.signal, init.signal]) : this.signal;
    signal.throwIfAborted();
    const headers = new Headers(init.headers);
    headers.set("X-Organisation-Code", this.code);
    if (!["GET", "HEAD", "OPTIONS", "TRACE"].includes((init.method ?? "GET").toUpperCase())) {
      headers.set("X-CSRFToken", csrfToken());
    }
    const response = await fetch(url.pathname + url.search, {
      ...init, headers, signal, credentials: "same-origin", cache: "no-store", redirect: "error",
    });
    signal.throwIfAborted();
    if (response.status === 403 || response.status === 401) {
      this.clear();
      await this.onDenied();
    }
    if (!response.ok) throw new ApiError(response.status);
    const data: T = await response.json();
    signal.throwIfAborted();
    this.onActivity();
    return data;
  }
}
