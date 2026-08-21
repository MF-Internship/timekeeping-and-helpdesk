"use client";

import { type FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { useAuth } from "@/features/identity/model/AuthProvider";
import {
  IdentityFailureNotice,
  identityFailureView,
  type IdentityFailureView,
} from "@/features/identity/ui/IdentityFailure";
import { Button } from "@/shared/ui/button";
import { ActionGroup } from "@/shared/ui/action-group";
import { Input } from "@/shared/ui/form";

function PasswordFields({ fields }: { fields: Record<string, string> }) {
  const currentError = fields.current_password;
  const newError = fields.new_password;
  return (
    <>
      <div>
        <label htmlFor="current-password">Mật khẩu hiện tại</label>
        <Input
          id="current-password"
          name="current_password"
          type="password"
          required
          aria-describedby={currentError ? "current-password-error" : undefined}
        />
        {currentError ? <span id="current-password-error">{currentError}</span> : null}
      </div>
      <div>
        <label htmlFor="new-password">Mật khẩu mới</label>
        <Input
          id="new-password"
          name="new_password"
          type="password"
          minLength={12}
          required
          aria-describedby={newError ? "new-password-error" : "password-guidance"}
        />
        <small id="password-guidance">Tối thiểu 12 ký tự.</small>
        {newError ? <span id="new-password-error">{newError}</span> : null}
      </div>
    </>
  );
}

export function ChangePasswordForm() {
  const auth = useAuth();
  const router = useRouter();
  const [error, setError] = useState<IdentityFailureView>();

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(undefined);
    const data = new FormData(event.currentTarget);
    try {
      await auth.changePassword(
        String(data.get("current_password") ?? ""),
        String(data.get("new_password") ?? ""),
      );
      router.replace("/");
    } catch (caught) {
      setError(identityFailureView(caught));
    }
  }

  return (
    <form className="account-form" onSubmit={submit}>
      <PasswordFields fields={error?.fields ?? {}} />
      <IdentityFailureNotice failure={error} />
      <ActionGroup>
        <Button type="submit" variant="primary">
          Đổi mật khẩu
        </Button>
      </ActionGroup>
    </form>
  );
}
