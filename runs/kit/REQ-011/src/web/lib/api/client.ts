/* eslint-disable @typescript-eslint/no-explicit-any */
const DEFAULT_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export interface ApiClientOptions {
  baseUrl?: string;
  fetcher?: typeof fetch;
}

export class ApiClient {
  private readonly baseUrl: string;

  private readonly fetcher: typeof fetch;

  constructor(options: ApiClientOptions = {}) {
    this.baseUrl = options.baseUrl ?? DEFAULT_BASE_URL;
    this.fetcher = options.fetcher ?? fetch;
  }

  private buildUrl(path: string, params?: Record<string, string | number | undefined>) {
    const url = new URL(path, this.baseUrl);
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value === undefined || value === null) return;
        url.searchParams.set(key, String(value));
      });
    }
    return url.toString();
  }

  private async request<T>(path: string, init?: RequestInit, params?: Record<string, string | number | undefined>): Promise<T> {
    const response = await this.fetcher(this.buildUrl(path, params), {
      credentials: "include",
      ...init,
      headers: {
        "Content-Type": init?.body instanceof FormData ? undefined : "application/json",
        ...init?.headers
      }
    });

    if (!response.ok) {
      const body = await response.text();
      throw new Error(`API request failed: ${response.status} ${body}`);
    }

    if (response.status === 204) {
      return undefined as T;
    }

    const contentType = response.headers.get("content-type");
    if (contentType?.includes("text/csv")) {
      return (await response.blob()) as T;
    }

    return (await response.json()) as T;
  }

  listCampaigns(query?: import("./types").CampaignListQuery) {
    return this.request<import("./types").PaginatedResult<import("./types").Campaign>>("/api/campaigns", { method: "GET" }, query);
  }

  getCampaign(id: string) {
    return this.request<import("./types").Campaign>(`/api/campaigns/${id}`, { method: "GET" });
  }

  createCampaign(payload: import("./types").CampaignPayload) {
    return this.request<import("./types").Campaign>("/api/campaigns", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  }

  updateCampaign(id: string, payload: import("./types").CampaignPayload) {
    return this.request<import("./types").Campaign>(`/api/campaigns/${id}`, {
      method: "PUT",
      body: JSON.stringify(payload)
    });
  }

  activateCampaign(id: string) {
    return this.request<void>(`/api/campaigns/${id}/activate`, { method: "POST" });
  }

  fetchDashboard(id: string, params?: { page?: number; page_size?: number }) {
    return this.request<import("./types").DashboardResponse>(`/api/campaigns/${id}/stats`, { method: "GET" }, params);
  }

  uploadContacts(id: string, file: File) {
    const form = new FormData();
    form.append("file", file);
    return this.request<import("./types").UploadSummary>(`/api/campaigns/${id}/contacts/upload`, {
      method: "POST",
      body: form
    });
  }

  exportContacts(id: string) {
    return this.request<Blob>(`/api/campaigns/${id}/export`, { method: "GET" });
  }

  getCurrentUser() {
    return this.request<import("./types").User>("/api/auth/me", { method: "GET" });
  }
}

export const apiClient = new ApiClient();