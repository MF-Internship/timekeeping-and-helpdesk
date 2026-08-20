"use client";

import { type FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { useAuth } from "@/features/identity/model/AuthProvider";
import { getSessionState } from "@/features/identity/model/session-store";
import {
  IdentityFailureNotice,
  identityFailureView,
  type IdentityFailureView,
} from "@/features/identity/ui/IdentityFailure";
import { Button } from "@/shared/ui/button";
import { ActionGroup } from "@/shared/ui/action-group";
import { Input } from "@/shared/ui/form";

export function LoginForm() {
  const auth = useAuth();
  const router = useRouter();
  const [error, setError] = useState<IdentityFailureView>();

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(undefined);
    const data = new FormData(event.currentTarget);
    try {
      await auth.login(String(data.get("username") ?? ""), String(data.get("password") ?? ""));
      router.replace(getSessionState().kind === "forced_change" ? "/change-password" : "/");
    } catch (caught) {
      setError(identityFailureView(caught));
    }
  }

  return (
    <form onSubmit={submit}>
      <label>
        Tên đăng nhập
        <Input name="username" required autoComplete="username" />
      </label>
      <label>
        Mật khẩu
        <Input name="password" type="password" required autoComplete="current-password" />
      </label>
      <IdentityFailureNotice failure={error} />
      <ActionGroup>
        <Button type="submit" variant="primary">
          Đăng nhập
        </Button>
      </ActionGroup>
    </form>
  );
}
