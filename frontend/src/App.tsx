import { useEffect, useRef, useState, type FormEvent } from "react";
import { ApiError, InstitutionScope, schoolsFor, sessionRequest, type Session } from "./session";
import "./index.css";

const dashboardPath = "/app/dashboard";
const loginPath = "/login";
const connectionError = "Check your connection and try again.";
const loginErrors: Record<number, string> = {
  400: "Check your email address and password.",
  401: "Invalid email or password.",
  403: "Sign-in could not be verified. Please try again.",
  429: "Too many failed login attempts. Wait a few minutes and try again.",
};

type View =
  | { page: "loading"; message: string }
  | { page: "retry"; action: "session" | "logout"; message: string; preferred?: string }
  | { page: "login"; message?: string }
  | { page: "workspace"; schools: ReturnType<typeof schoolsFor>; selected?: string; message?: string };

export default function App() {
  const [view, setView] = useState<View>({ page: "loading", message: "Checking your session…" });
  const [signingIn, setSigningIn] = useState(false);
  const operation = useRef<AbortController | null>(null);
  const scope = useRef<InstitutionScope | null>(null);
  const selected = useRef<string | undefined>(undefined);
  const userId = useRef<string | undefined>(undefined);
  const signingOut = useRef(false);
  const idleTimer = useRef<number | undefined>(undefined);
  const heading = useRef<HTMLHeadingElement>(null);

  function clearWorkspace() {
    scope.current?.clear();
    scope.current = null;
    window.clearTimeout(idleTimer.current);
  }

  function scheduleSessionCheck() {
    window.clearTimeout(idleTimer.current);
    // Check at the idle boundary, not on a short polling interval that extends the session.
    idleTimer.current = window.setTimeout(() => void refresh(), 3_601_000);
  }

  function showSession(session: Session, preferred?: string, previous?: string, denied = false) {
    const sameUser = userId.current === session.user?.id;
    userId.current = session.authenticated ? session.user?.id : undefined;
    if (!session.authenticated) {
      selected.current = undefined;
      if (window.location.pathname !== loginPath) window.history.replaceState(null, "", loginPath);
      setView({ page: "login", message: previous ? "Your session expired. Sign in again." : undefined });
      return;
    }

    const schools = schoolsFor(session);
    const code = schools.find(({ organisation }) => sameUser && organisation.code === preferred)
      ?.organisation.code ?? schools[0]?.organisation.code;
    const revoked = sameUser && preferred && !schools.some(({ organisation }) => organisation.code === preferred);
    selected.current = code;
    if (code) scope.current = new InstitutionScope(code, () => refresh(code, true), scheduleSessionCheck);
    scheduleSessionCheck();
    if (window.location.pathname !== dashboardPath) window.history.replaceState(null, "", dashboardPath);
    setView({
      page: "workspace", schools, selected: code,
      message: revoked ? "Your institution access changed." :
        denied ? "You do not have permission for that action." : undefined,
    });
  }

  async function refresh(preferred = selected.current, denied = false) {
    if (operation.current || signingOut.current) return;
    const controller = new AbortController();
    operation.current = controller;
    const previous = userId.current;
    clearWorkspace();
    setView({ page: "loading", message: "Checking your session…" });
    try {
      const session = await sessionRequest("session", controller.signal);
      if (!controller.signal.aborted) showSession(session, preferred, previous, denied);
    } catch {
      if (!controller.signal.aborted) setView({
        page: "retry", action: "session", preferred, message: `Could not check your session. ${connectionError}`,
      });
    } finally {
      if (operation.current === controller) operation.current = null;
    }
  }

  useEffect(() => {
    const restore = (event: PageTransitionEvent) => { if (event.persisted) void refresh(); };
    const navigate = () => void refresh();
    void refresh();
    window.addEventListener("pageshow", restore);
    window.addEventListener("popstate", navigate);
    return () => {
      window.removeEventListener("pageshow", restore);
      window.removeEventListener("popstate", navigate);
      operation.current?.abort();
      operation.current = null;
      clearWorkspace();
    };
  }, []);

  useEffect(() => {
    if (view.page !== "loading") heading.current?.focus();
  }, [view.page, view.page === "workspace" ? view.selected : undefined]);

  async function login(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (operation.current) return;
    const form = event.currentTarget;
    const values = new FormData(form);
    const controller = new AbortController();
    operation.current = controller;
    setSigningIn(true);
    setView({ page: "login" });
    try {
      const session = await sessionRequest("login", controller.signal, {
        email: String(values.get("email")).trim(), password: String(values.get("password")),
      });
      if (!controller.signal.aborted) {
        form.reset();
        showSession(session);
      }
    } catch (error) {
      if (controller.signal.aborted) return;
      let message = error instanceof ApiError
        ? loginErrors[error.status] ?? `Sign-in is unavailable. ${connectionError}`
        : `Could not sign in. ${connectionError}`;
      if (error instanceof ApiError && error.status === 403) {
        try {
          await sessionRequest("session", controller.signal);
        } catch {
          message = `Could not verify sign-in. ${connectionError}`;
        }
      }
      if (!controller.signal.aborted) setView({ page: "login", message });
    } finally {
      if (operation.current === controller) {
        operation.current = null;
        setSigningIn(false);
      }
    }
  }

  async function logout(retry = false) {
    if (operation.current) return;
    const controller = new AbortController();
    operation.current = controller;
    signingOut.current = true;
    clearWorkspace();
    selected.current = undefined;
    userId.current = undefined;
    setView({ page: "loading", message: "Signing out…" });
    try {
      if (retry) await sessionRequest("session", controller.signal);
      const session = await sessionRequest("logout", controller.signal);
      if (!controller.signal.aborted) {
        signingOut.current = false;
        showSession(session);
      }
    } catch {
      if (!controller.signal.aborted) setView({
        page: "retry", action: "logout", message: `Could not confirm sign-out. ${connectionError}`,
      });
    } finally {
      if (operation.current === controller) operation.current = null;
    }
  }

  function switchInstitution(code: string) {
    if (view.page !== "workspace" || code === selected.current ||
      !view.schools.some(({ organisation }) => organisation.code === code)) return;
    void refresh(code);
  }

  const current = view.page === "workspace"
    ? view.schools.find(({ organisation }) => organisation.code === view.selected)
    : undefined;

  return (
    <>
      <a className="skip-link" href="#main">Skip to main content</a>
      <header className="masthead">
        <div className="masthead-inner">
          <div>
            <p className="brand">Horseracing Student Records</p>
            <p className="notice">Synthetic data only — not production ready</p>
          </div>
          {view.page === "workspace" && (
            <button className="secondary" onClick={() => void logout()}>Sign out</button>
          )}
        </div>
      </header>
      {view.page === "workspace" && current && (
        <div className="workspace-bar">
          <nav aria-label="Institution navigation">
            <a href={dashboardPath} aria-current="page" onClick={(event) => {
              if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
              event.preventDefault();
              void refresh();
            }}>Dashboard</a>
          </nav>
          <div className="switcher">
            <label htmlFor="institution">Institution</label>
            <select id="institution" value={view.selected} onChange={(event) => switchInstitution(event.target.value)}>
              {view.schools.map(({ organisation }) => (
                <option key={organisation.id} value={organisation.code}>{organisation.name}</option>
              ))}
            </select>
          </div>
        </div>
      )}
      <main id="main" tabIndex={-1} className={view.page === "workspace" ? "workspace" : "auth-panel"}>
        {view.page === "loading" && <p role="status">{view.message}</p>}
        {view.page === "retry" && (
          <>
            <h1 ref={heading} tabIndex={-1}>Connection problem</h1>
            <p role="alert">{view.message}</p>
            <button onClick={() => void (view.action === "logout" ? logout(true) : refresh(view.preferred))}>Retry</button>
          </>
        )}
        {view.page === "login" && (
          <>
            <h1 ref={heading} tabIndex={-1}>Sign in</h1>
            <p>Use your demo staff account.</p>
            <form onSubmit={login} aria-busy={signingIn}>
              <label htmlFor="email">Email address</label>
              <input id="email" name="email" type="email" autoComplete="username" required />
              <label htmlFor="password">Password</label>
              <input id="password" name="password" type="password" autoComplete="current-password" required />
              <button type="submit" disabled={signingIn}>Sign in</button>
            </form>
            {signingIn && <p role="status">Signing in…</p>}
            {view.message && <p className="feedback" role="alert">{view.message}</p>}
          </>
        )}
        {view.page === "workspace" && (
          <>
            <h1 ref={heading} tabIndex={-1}>{current?.organisation.name ?? "No institution access"}</h1>
            {view.message && <p role="status">{view.message}</p>}
            {current ? <p>Institution dashboard</p> :
              <p>Your account has no active institution membership. Contact your institution administrator if you need access.</p>}
          </>
        )}
      </main>
    </>
  );
}
