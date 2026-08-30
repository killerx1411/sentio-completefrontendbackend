import { refreshSession } from "../services/authApi";

jest.mock("../config/env", () => ({
  AUTH_API_BASE: "http://localhost:5000",
}));

describe("refreshSession single-flight", () => {
  beforeEach(() => {
    global.fetch = jest.fn(() =>
      Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve({
            data: { access_token: "token-a" },
          }),
      })
    );
  });

  afterEach(() => {
    jest.resetAllMocks();
  });

  test("test_concurrent_refresh_single_flight", async () => {
    await Promise.all([refreshSession(), refreshSession()]);
    expect(global.fetch).toHaveBeenCalledTimes(1);
    expect(global.fetch.mock.calls[0][0]).toContain("/api/auth/refresh");
  });
});
