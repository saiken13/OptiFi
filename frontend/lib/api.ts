import axios from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const api = axios.create({
  baseURL: API_URL,
  withCredentials: true,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error.response?.status === 401) {
      if (typeof window !== "undefined") {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

// Auth
export const authApi = {
  register: (data: { email: string; password: string; name?: string }) =>
    api.post("/auth/register", data),
  login: (data: { email: string; password: string }) =>
    api.post("/auth/login", data),
  logout: () => api.post("/auth/logout"),
  me: () => api.get("/auth/me"),
  registerDevice: (player_id: string) =>
    api.post("/auth/register-device", { player_id }),
};

// Goals
export const goalsApi = {
  list: () => api.get("/goals"),
  create: (data: object) => api.post("/goals", data),
  update: (id: string, data: object) => api.patch(`/goals/${id}`, data),
  delete: (id: string) => api.delete(`/goals/${id}`),
};

// Budgets
export const budgetsApi = {
  list: (month?: number, year?: number) =>
    api.get("/budgets", { params: { month, year } }),
  create: (data: object) => api.post("/budgets", data),
  update: (id: string, data: object) => api.patch(`/budgets/${id}`, data),
  delete: (id: string) => api.delete(`/budgets/${id}`),
};

// Loans
export const loansApi = {
  list: () => api.get("/loans"),
  create: (data: object) => api.post("/loans", data),
  update: (id: string, data: object) => api.patch(`/loans/${id}`, data),
  delete: (id: string) => api.delete(`/loans/${id}`),
};

// Transactions
export const transactionsApi = {
  list: (params?: { month?: number; year?: number; category?: string; limit?: number }) =>
    api.get("/transactions", { params }),
  upload: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return api.post("/transactions/upload", form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },
  create: (data: object) => api.post("/transactions", data),
  summary: (month?: number, year?: number) =>
    api.get("/transactions/summary", { params: { month, year } }),
};

// Alerts
export const alertsApi = {
  list: (unread_only = false) =>
    api.get("/alerts", { params: { unread_only } }),
  markRead: (alert_ids: string[]) =>
    api.post("/alerts/mark-read", { alert_ids }),
};

// Chat
export const chatApi = {
  send: (message: string, context?: Record<string, unknown>) =>
    api.post("/chat", { message, context }),
  history: (limit = 50) => api.get("/chat/history", { params: { limit } }),
};

// Cards
export const cardsApi = {
  list: () => api.get("/cards"),
  create: (data: object) => api.post("/cards", data),
  delete: (id: string) => api.delete(`/cards/${id}`),
  importSearch: (card_name: string, issuer: string) =>
    api.post("/cards/import/search", { card_name, issuer }),
  importExtract: (job_id: string, selected_url: string) =>
    api.post("/cards/import/extract", { job_id, selected_url }),
  importConfirm: (data: object) => api.post("/cards/import/confirm", data),
};

// Memberships
export const membershipsApi = {
  list: () => api.get("/memberships"),
  create: (data: object) => api.post("/memberships", data),
  delete: (id: string) => api.delete(`/memberships/${id}`),
};

// Purchase
export const purchaseApi = {
  optimize: (query: string, budget?: number) =>
    api.post("/purchase/optimize", { query, budget }),
};

// Weekly Review
export const weeklyReviewApi = {
  run: () => api.post("/weekly-review/run"),
  latest: () => api.get("/weekly-review/latest"),
};

// Tax
export const taxApi = {
  analyze: (tax_year?: number) => api.get("/tax/analysis", { params: { tax_year } }),
  emailReport: (tax_year?: number) => api.post("/tax/email-report", null, { params: { tax_year } }),
};
