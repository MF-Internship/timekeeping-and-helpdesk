import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AsyncState, EmptyState, ErrorState, LoadingState } from "@/shared/ui/async-state";

describe("AsyncState", () => {
  it("renders loading and empty as distinct status states", () => {
    const { rerender } = render(<AsyncState state={{ kind: "loading" }} />);
    expect(screen.getByRole("status")).toHaveTextContent(/đang tải/i);
    rerender(<AsyncState state={{ kind: "empty" }} />);
    expect(screen.getByRole("status")).toHaveTextContent(/không có dữ liệu/i);
  });

  it.each(["unexpected_response", "network"] as const)("renders %s as an alert", (kind) => {
    render(<AsyncState state={{ kind }} />);
    expect(screen.getByRole("alert")).toBeVisible();
  });

  it("renders canonical details and support request ID safely", () => {
    render(
      <AsyncState
        state={{
          kind: "canonical",
          message: "Dữ liệu không hợp lệ.",
          details: { field_name: ["Giá trị không hợp lệ."] },
          requestId: "00000000-0000-4000-8000-000000000000",
        }}
      />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("Dữ liệu không hợp lệ.");
    fireEvent.click(screen.getByText("Thông tin hỗ trợ"));
    expect(screen.getByText(/00000000-0000-4000-8000-000000000000/)).toBeVisible();
  });

  it("offers retry only when supplied", () => {
    const retry = vi.fn();
    const { rerender } = render(<AsyncState state={{ kind: "network" }} />);
    expect(screen.queryByRole("button")).toBeNull();
    rerender(<AsyncState state={{ kind: "network" }} onRetry={retry} />);
    fireEvent.click(screen.getByRole("button"));
    expect(retry).toHaveBeenCalledOnce();
  });

  it("offers reusable loading, empty, and recoverable error compositions", () => {
    const retry = vi.fn();
    const { rerender } = render(<LoadingState message="Đang chuẩn bị" />);
    expect(screen.getByRole("status")).toHaveAttribute("aria-busy", "true");
    rerender(<EmptyState message="Không có địa điểm" />);
    expect(screen.getByRole("status")).toHaveTextContent("Không có địa điểm");
    rerender(<ErrorState message="Không tải được" onRetry={retry} />);
    fireEvent.click(screen.getByRole("button", { name: "Thử lại" }));
    expect(retry).toHaveBeenCalledOnce();
  });
});
