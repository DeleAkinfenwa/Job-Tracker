import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import LoginPage from "./LoginPage.jsx";

const auth = { login: vi.fn(), loginAsDemo: vi.fn() };
vi.mock("../auth.jsx", () => ({ useAuth: () => auth }));

const renderPage = () =>
  render(
    <MemoryRouter>
      <LoginPage />
    </MemoryRouter>,
  );

describe("LoginPage", () => {
  it("logs in to the demo with one click", async () => {
    renderPage();
    await userEvent.click(screen.getByRole("button", { name: "Explore the demo" }));
    expect(auth.loginAsDemo).toHaveBeenCalled();
  });

  it("shows a friendly message for a wrong password", async () => {
    auth.login.mockRejectedValueOnce(Object.assign(new Error("No active account"), { status: 401 }));
    renderPage();

    await userEvent.type(screen.getByLabelText("Email"), "ada@example.com");
    await userEvent.type(screen.getByLabelText("Password"), "wrong");
    await userEvent.click(screen.getByRole("button", { name: "Log in" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("don't match an account");
  });
});
