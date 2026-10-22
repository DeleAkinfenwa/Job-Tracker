import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, request, requestAll, setSessionExpiredHandler, tokens } from "./client.js";

const json = (status, body) => new Response(body === undefined ? null : JSON.stringify(body), { status });

describe("request", () => {
  beforeEach(() => {
    localStorage.clear();
    tokens.save({ access: "old-access", refresh: "refresh-token" });
  });
  afterEach(() => vi.unstubAllGlobals());

  it("sends the access token", async () => {
    const fetch = vi.fn().mockResolvedValue(json(200, { ok: true }));
    vi.stubGlobal("fetch", fetch);

    await request("/api/companies/");
    expect(fetch.mock.calls[0][1].headers.Authorization).toBe("Bearer old-access");
  });

  it("refreshes an expired token and retries once", async () => {
    const fetch = vi
      .fn()
      .mockResolvedValueOnce(json(401, { detail: "expired" }))
      .mockResolvedValueOnce(json(200, { access: "new-access" }))
      .mockResolvedValueOnce(json(200, { id: 1 }));
    vi.stubGlobal("fetch", fetch);

    expect(await request("/api/auth/me/")).toEqual({ id: 1 });
    expect(fetch.mock.calls[1][0]).toMatch(/token\/refresh\/$/);
    expect(fetch.mock.calls[2][1].headers.Authorization).toBe("Bearer new-access");
    expect(tokens.access).toBe("new-access");
  });

  it("logs out when the refresh token is also expired", async () => {
    const expired = vi.fn();
    setSessionExpiredHandler(expired);
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(json(401, { detail: "expired" }))
        .mockResolvedValueOnce(json(401, { detail: "expired" })),
    );

    await expect(request("/api/auth/me/")).rejects.toBeInstanceOf(ApiError);
    expect(expired).toHaveBeenCalled();
    expect(tokens.access).toBeNull();
  });

  it("exposes field errors from the API", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(json(400, { name: ["This field is required."] })));

    const error = await request("/api/companies/", { method: "POST", body: {} }).catch((e) => e);
    expect(error.status).toBe(400);
    expect(error.fields.name).toEqual(["This field is required."]);
  });
});

describe("requestAll", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("follows the next links until every page is loaded", async () => {
    const fetch = vi
      .fn()
      .mockResolvedValueOnce(json(200, { results: [1, 2], next: "http://api.test/api/companies/?limit=100&offset=100" }))
      .mockResolvedValueOnce(json(200, { results: [3], next: null }));
    vi.stubGlobal("fetch", fetch);

    expect(await requestAll("/api/companies/")).toEqual([1, 2, 3]);
    expect(fetch.mock.calls[1][0]).toMatch(/\/api\/companies\/\?limit=100&offset=100$/);
  });
});
