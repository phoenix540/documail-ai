import { Component, useCallback, useEffect, useRef, useState } from "react";
import { api, hasToken, setToken } from "./api.js";

/* ---------- Sign in ---------- */
function Login({ onDone }) {
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const res = await (mode === "login" ? api.login : api.register)(email, password);
      setToken(res.access_token);
      onDone(res.user);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="auth">
      <form onSubmit={submit} className="auth-form">
        <h1>DocuMail AI</h1>
        <p className="muted">Ask questions about your documents, then email the answer.</p>
        <label>Email<input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoFocus /></label>
        <label>Password<input type="password" value={password} onChange={(e) => setPassword(e.target.value)} minLength={8} required /></label>
        {error && <p className="error" role="alert">{error}</p>}
        <button className="primary" disabled={busy}>{mode === "login" ? "Sign in" : "Create account"}</button>
        <button type="button" className="link" onClick={() => setMode(mode === "login" ? "register" : "login")}>
          {mode === "login" ? "Create an account" : "I already have an account"}
        </button>
        {mode === "register" && <p className="muted small">The first account created becomes the administrator.</p>}
      </form>
    </main>
  );
}

/* ---------- Document library ---------- */
function Library({ docs, reload }) {
  const input = useRef();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function onFiles(e) {
    setBusy(true);
    setError("");
    for (const file of e.target.files) {
      try {
        await api.upload(file);
      } catch (err) {
        setError(`${file.name}: ${err.message}`);
      }
    }
    e.target.value = "";
    setBusy(false);
    reload();
  }

  return (
    <aside className="library" aria-label="Documents">
      <h2>Documents</h2>
      <button className="primary" onClick={() => input.current.click()} disabled={busy}>
        {busy ? "Indexing…" : "Add documents"}
      </button>
      <input ref={input} type="file" multiple accept=".pdf,.docx,.txt,.md" hidden onChange={onFiles} />
      {error && <p className="error small" role="alert">{error}</p>}
      {docs.length === 0 ? (
        <p className="muted small">No documents yet. Add a PDF or DOCX to start asking questions.</p>
      ) : (
        <ul>
          {docs.map((d) => (
            <li key={d.id}>
              <span className="doc-name" title={d.filename}>{d.filename}</span>
              <span className="muted small">{d.n_chunks} passages</span>
              <button className="link small" onClick={async () => { await api.removeDocument(d.id); reload(); }}>Remove</button>
            </li>
          ))}
        </ul>
      )}
    </aside>
  );
}

/* ---------- Email draft confirmation ---------- */
function EmailDraft({ draft, onSent }) {
  const [to, setTo] = useState(draft.recipients.join(", "));
  const [subject, setSubject] = useState(draft.subject);
  const [body, setBody] = useState(draft.body);
  const [state, setState] = useState({ phase: "edit", error: "", job: null });

  async function send() {
    setState({ phase: "sending", error: "", job: null });
    try {
      const recipients = to.split(/[,\s;]+/).filter(Boolean);
      const job = await api.sendMail({ recipients, subject, body });
      setState({ phase: "sent", error: "", job });
      onSent?.();
    } catch (err) {
      setState({ phase: "edit", error: err.message, job: null });
    }
  }

  if (state.phase === "sent") {
    return <p className="notice">Email queued for {state.job.recipients.length} recipient(s). Check the Activity tab for delivery status.</p>;
  }
  return (
    <div className="draft">
      <label>To<input value={to} onChange={(e) => setTo(e.target.value)} /></label>
      <label>Subject<input value={subject} onChange={(e) => setSubject(e.target.value)} /></label>
      <label>Message<textarea rows={6} value={body} onChange={(e) => setBody(e.target.value)} /></label>
      {state.error && <p className="error small" role="alert">{state.error}</p>}
      <button className="primary" onClick={send} disabled={state.phase === "sending"}>Send email</button>
    </div>
  );
}

/* ---------- Chat ---------- */
function Chat({ hasDocs, onSources, onSent }) {
  const [messages, setMessages] = useState([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const end = useRef();

  useEffect(() => {
    end.current?.scrollIntoView?.({ behavior: "smooth" });
  }, [messages, busy]);

  async function ask(e) {
    e.preventDefault();
    const q = text.trim();
    if (!q || busy) return;
    setText("");
    setMessages((m) => [...m, { role: "user", text: q }]);
    setBusy(true);
    try {
      const r = await api.chat(q);
      setMessages((m) => [...m, { role: "assistant", ...r }]);
      onSources(r.sources);
    } catch (err) {
      setMessages((m) => [...m, { role: "assistant", text: err.message, failed: true }]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="chat" aria-label="Conversation">
      <div className="thread" aria-live="polite">
        {messages.length === 0 && (
          <div className="empty">
            <h2>Ask your documents</h2>
            <p className="muted">
              {hasDocs ? "Try “What is the remote work policy?” or “Send the summary to sara@company.com”." : "Add a document on the left, then ask a question about it."}
            </p>
          </div>
        )}
        {messages.map((m, i) =>
          m.role === "user" ? (
            <p key={i} className="msg user">{m.text}</p>
          ) : (
            <div key={i} className={`msg bot ${m.failed ? "failed" : ""}`}>
              <p>{m.answer ?? m.text}</p>
              {m.email_draft && <EmailDraft draft={m.email_draft} onSent={onSent} />}
            </div>
          )
        )}
        {busy && <p className="msg bot muted">Searching your documents…</p>}
        <div ref={end} />
      </div>
      <form className="composer" onSubmit={ask}>
        <input value={text} onChange={(e) => setText(e.target.value)} placeholder="Ask a question or request an email" aria-label="Message" />
        <button className="primary" disabled={busy || !text.trim()}>Ask</button>
      </form>
    </section>
  );
}

/* ---------- Sources (cited passages) ---------- */
function Sources({ sources }) {
  return (
    <aside className="sources" aria-label="Sources">
      <h2>Passages used</h2>
      {sources.length === 0 ? (
        <p className="muted small">The passages behind each answer appear here, so you can check them.</p>
      ) : (
        <ol>
          {sources.map((s, i) => (
            <li key={i}>
              <div className="src-head">
                <strong>[{i + 1}] {s.filename}</strong>
                <span className="muted small">{Math.round(s.score * 100)}% match</span>
              </div>
              <div className="bar" aria-hidden="true"><i style={{ width: `${Math.max(4, s.score * 100)}%` }} /></div>
              <p>{s.text}</p>
            </li>
          ))}
        </ol>
      )}
    </aside>
  );
}

/* ---------- Activity ---------- */
function Activity() {
  const [stats, setStats] = useState(null);
  const [jobs, setJobs] = useState([]);
  useEffect(() => { api.stats().then(setStats); api.mailJobs().then(setJobs); }, []);
  if (!stats) return <p className="muted pad">Loading activity…</p>;
  const max = Math.max(1, ...stats.per_day.map((d) => d.count));
  return (
    <section className="activity">
      <dl className="figures">
        <div><dt>Documents</dt><dd>{stats.documents}</dd></div>
        <div><dt>Questions</dt><dd>{stats.questions}</dd></div>
        <div><dt>Avg. response</dt><dd>{(stats.avg_latency_ms / 1000).toFixed(1)} s</dd></div>
        <div><dt>Emails sent</dt><dd>{stats.emails.sent}</dd></div>
        <div><dt>Emails failed</dt><dd>{stats.emails.failed}</dd></div>
      </dl>
      <h2>Questions per day</h2>
      {stats.per_day.length === 0 ? <p className="muted small">No questions yet.</p> : (
        <div className="days">
          {stats.per_day.map((d) => (
            <div key={d.day} className="day"><span className="n">{d.count}</span><i style={{ height: `${(d.count / max) * 100}%` }} /><span className="small muted">{d.day.slice(5)}</span></div>
          ))}
        </div>
      )}
      <h2>Request types</h2>
      <ul className="plain">{Object.entries(stats.by_intent).map(([k, v]) => <li key={k}>{k}: {v}</li>)}</ul>
      <h2>Email batches</h2>
      {jobs.length === 0 ? <p className="muted small">No emails sent yet.</p> : (
        <ul className="plain">
          {jobs.map((j) => (
            <li key={j.id}>
              <strong>{j.subject}</strong>
              <span className="muted small"> {j.recipients.filter((r) => r.status === "sent").length}/{j.recipients.length} delivered</span>
              {j.recipients.filter((r) => r.status === "failed").map((r) => <span key={r.email} className="error small"> · {r.email}: {r.error}</span>)}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

/* ---------- Crash screen ---------- */
class ErrorBoundary extends Component {
  state = { error: null };
  static getDerivedStateFromError(error) { return { error }; }
  render() {
    if (!this.state.error) return this.props.children;
    return (
      <main className="auth">
        <div className="auth-form">
          <h1>Something went wrong</h1>
          <p className="error" role="alert">{String(this.state.error?.message || this.state.error)}</p>
          <p className="muted small">Send this message when you report the problem, then reload the page.</p>
          <button className="primary" onClick={() => window.location.reload()}>Reload</button>
        </div>
      </main>
    );
  }
}

/* ---------- Shell ---------- */
function Shell() {
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(!hasToken());
  const [docs, setDocs] = useState([]);
  const [sources, setSources] = useState([]);
  const [tab, setTab] = useState("chat");

  useEffect(() => {
    if (hasToken()) api.me().then(setUser).catch(() => setToken(null)).finally(() => setReady(true));
  }, []);

  const reload = useCallback(() => api.documents().then(setDocs).catch(() => {}), []);
  useEffect(() => { if (user) reload(); }, [user, reload]);

  if (!ready) return null;
  if (!user) return <Login onDone={setUser} />;

  return (
    <div className="app">
      <header>
        <strong className="brand">DocuMail AI</strong>
        <nav aria-label="Views">
          <button className={tab === "chat" ? "on" : ""} onClick={() => setTab("chat")}>Chat</button>
          <button className={tab === "activity" ? "on" : ""} onClick={() => setTab("activity")}>Activity</button>
        </nav>
        <span className="muted small who">{user.email} ({user.role})</span>
        <button className="link" onClick={() => { setToken(null); setUser(null); setDocs([]); setSources([]); }}>Sign out</button>
      </header>
      {tab === "chat" ? (
        <div className="workspace">
          <Library docs={docs} reload={reload} />
          <Chat hasDocs={docs.length > 0} onSources={setSources} onSent={() => {}} />
          <Sources sources={sources} />
        </div>
      ) : (
        <Activity />
      )}
    </div>
  );
}

export default function App() {
  return (
    <ErrorBoundary>
      <Shell />
    </ErrorBoundary>
  );
}
