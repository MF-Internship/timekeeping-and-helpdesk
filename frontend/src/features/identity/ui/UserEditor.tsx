"use client";

import { type FormEvent, useState } from "react";

import { createUser, updateUser } from "@/features/identity/api/identity-api";
import {
  IdentityFailureNotice,
  identityFailureView,
  type IdentityFailureView,
} from "@/features/identity/ui/IdentityFailure";
import { Button } from "@/shared/ui/button";
import { ActionGroup } from "@/shared/ui/action-group";
import { Input, Select } from "@/shared/ui/form";

type EditableUser = {
  id: number;
  full_name: string;
  phone: string | null;
  email: string | null;
};

type UserEditorProps = {
  user?: EditableUser;
  onGenerated?(value: string): void;
  onSaved(): void | Promise<void>;
  onCancel?(): void;
};

function optionalContact(data: FormData, field: "phone" | "email"): string | null {
  return String(data.get(field) ?? "").trim() || null;
}

function profileInput(data: FormData) {
  return {
    full_name: String(data.get("full_name") ?? "").trim(),
    phone: optionalContact(data, "phone"),
    email: optionalContact(data, "email"),
  };
}

function FieldError({ failure, field }: { failure?: IdentityFailureView; field: string }) {
  const message = failure?.fields[field];
  return message ? <span>{message}</span> : null;
}

function ProfileFields({ user, failure }: { user?: EditableUser; failure?: IdentityFailureView }) {
  return (
    <>
      <label>
        Họ tên
        <Input name="full_name" required defaultValue={user?.full_name} />
        <FieldError failure={failure} field="full_name" />
      </label>
      <label>
        Điện thoại
        <Input name="phone" defaultValue={user?.phone ?? ""} />
        <FieldError failure={failure} field="phone" />
      </label>
      <label>
        Email
        <Input name="email" type="email" defaultValue={user?.email ?? ""} />
        <FieldError failure={failure} field="email" />
      </label>
    </>
  );
}

function CreateUserEditor(props: UserEditorProps) {
  const [failure, setFailure] = useState<IdentityFailureView>();
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    setFailure(undefined);
    try {
      const result = await createUser({
        ...profileInput(data),
        username: String(data.get("username") ?? "").trim(),
        role: String(data.get("role") ?? ""),
      });
      props.onGenerated?.(result.generated_password);
      form.reset();
      await props.onSaved();
    } catch (error) {
      setFailure(identityFailureView(error));
    }
  }
  return (
    <form onSubmit={submit} aria-label="Tạo người dùng">
      <h2>Tạo người dùng</h2>
      <label>
        Tên đăng nhập
        <Input name="username" required />
        <FieldError failure={failure} field="username" />
      </label>
      <ProfileFields failure={failure} />
      <label>
        Vai trò
        <Select name="role" required>
          <option value="HELPDESK">Helpdesk</option>
          <option value="LEADER">Leader</option>
        </Select>
        <FieldError failure={failure} field="role" />
      </label>
      <IdentityFailureNotice failure={failure} />
      <ActionGroup>
        <Button type="submit" variant="primary">
          Tạo
        </Button>
      </ActionGroup>
    </form>
  );
}

function EditUserEditor(props: UserEditorProps & { user: EditableUser }) {
  const [failure, setFailure] = useState<IdentityFailureView>();
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFailure(undefined);
    try {
      await updateUser(props.user.id, profileInput(new FormData(event.currentTarget)));
      await props.onSaved();
    } catch (error) {
      setFailure(identityFailureView(error));
    }
  }
  return (
    <form onSubmit={submit} aria-label="Sửa hồ sơ người dùng">
      <h2>Sửa hồ sơ</h2>
      <ProfileFields user={props.user} failure={failure} />
      <IdentityFailureNotice failure={failure} />
      <ActionGroup>
        <Button type="submit" variant="primary">
          Lưu hồ sơ
        </Button>
        <Button type="button" onClick={props.onCancel}>
          Hủy
        </Button>
      </ActionGroup>
    </form>
  );
}

export function UserEditor(props: UserEditorProps) {
  return props.user ? (
    <EditUserEditor {...props} user={props.user} />
  ) : (
    <CreateUserEditor {...props} />
  );
}
