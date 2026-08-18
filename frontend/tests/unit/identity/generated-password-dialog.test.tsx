import { createRef } from "react";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import {
  GeneratedPasswordDialog,
  type GeneratedPasswordDialogHandle,
} from "@/features/identity/ui/GeneratedPasswordDialog";
import { setSessionState } from "@/features/identity/model/session-store";

afterEach(cleanup);

describe("GeneratedPasswordDialog", () => {
  it("holds the generated value only until explicit dismissal", async () => {
    const ref = createRef<GeneratedPasswordDialogHandle>();
    render(<GeneratedPasswordDialog ref={ref} />);
    act(() => ref.current?.show("OneTimeValue123!"));
    expect(screen.getByRole("dialog")).toHaveTextContent("OneTimeValue123!");
    fireEvent.click(screen.getByRole("button", { name: "Đã lưu, đóng" }));
    await waitFor(() => expect(screen.queryByText("OneTimeValue123!")).not.toBeInTheDocument());
  });

  it("removes the value when unmounted", () => {
    const ref = createRef<GeneratedPasswordDialogHandle>();
    const view = render(<GeneratedPasswordDialog ref={ref} />);
    act(() => ref.current?.show("UnmountValue123!"));
    view.unmount();
    expect(screen.queryByText("UnmountValue123!")).not.toBeInTheDocument();
  });

  it("clears on logout or account-state changes", async () => {
    const ref = createRef<GeneratedPasswordDialogHandle>();
    render(<GeneratedPasswordDialog ref={ref} />);
    act(() => ref.current?.show("AccountValue123!"));
    act(() => setSessionState({ kind: "anonymous" }));
    await waitFor(() => expect(screen.queryByText("AccountValue123!")).not.toBeInTheDocument());
  });
});
