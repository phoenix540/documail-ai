const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";
let token = localStorage.getItem("token");

export const setToken = (t) => {
  token = t;
  t ? localStorage.setItem("token", t) : localStorage.removeItem("token");
};
export const hasToken = () => !!token;

async function request(path, { method = "GET", json, form } = {}) {
  const headers = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  if (json) headers["Content-Type"] = "application/json";
  const res = await fetch(BASE + path, { method, headers, body: json ? JSON.stringify(json) : form });
  if (res.status === 204) return null;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = Array.isArray(data.detail) ? data.detail.map((d) => d.msg).join(", ") : data.detail;
    const err = new Error(detail || `Request failed (${res.status})`);
    err.status = res.status;
    throw err;
  }
  return data;
}

export const api = {
  login: (email, password) => request("/auth/login", { method: "POST", json: { email, password } }),
  register: (email, password) => request("/auth/register", { method: "POST", json: { email, password } }),
  me: () => request("/auth/me"),
  documents: () => request("/documents"),
  upload: (file) => {
    const form = new FormData();
    form.append("file", file);
    return request("/documents", { method: "POST", form });
  },
  removeDocument: (id) => request(`/documents/${id}`, { method: "DELETE" }),
  chat: (message) => request("/chat", { method: "POST", json: { message } }),
  sendMail: (payload) => request("/mail/send", { method: "POST", json: payload }),
  mailJobs: () => request("/mail/jobs"),
  stats: () => request("/stats"),
};
