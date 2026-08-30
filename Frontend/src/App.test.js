import { render, screen } from "@testing-library/react";
import App from "./App";

jest.mock("./context/SessionContext", () => ({
  SessionProvider: ({ children }) => children,
  useSession: () => ({
    isAuthenticated: false,
    initializing: false,
    user: null,
    loginWithCredentials: jest.fn(),
    completeMfaLogin: jest.fn(),
    logout: jest.fn(),
    refreshUser: jest.fn(),
  }),
}));

// App owns its data router (createBrowserRouter), so it is rendered directly —
// wrapping it in another router would nest two routers.
test("renders login page at root route", () => {
  window.history.pushState({}, "", "/");
  render(<App />);
  expect(
    screen.getByText(/sign in to your sentio mind account/i)
  ).toBeInTheDocument();
});
