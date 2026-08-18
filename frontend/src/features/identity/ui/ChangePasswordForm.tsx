"use client";

import { type FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { useAuth } from "@/features/identity/model/AuthProvider";
import {
  IdentityFailureNotice,
  identityFailureView,
  type IdentityFailureView,
} from "@/features/identity/ui/IdentityFailure";

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
    <form onSubmit={submit}>
      <label>
        Mật khẩu hiện tại
        <input name="current_password" type="password" required />
        {error?.fields.current_password ? <span>{error.fields.current_password}</span> : null}
      </label>
      <label>
        Mật khẩu mới
        <input name="new_password" type="password" minLength={12} required />
        {error?.fields.new_password ? <span>{error.fields.new_password}</span> : null}
      </label>
      <IdentityFailureNotice failure={error} />
      <button type="submit">Đổi mật khẩu</button>
    </form>
  );
}
