"use client";

import { type FormEvent, useCallback, useEffect, useRef, useState } from "react";

import {
  changeUserRole,
  changeUserStatus,
  listUsers,
  resetUserPassword,
} from "@/features/identity/api/identity-api";
import { useAuth } from "@/features/identity/model/AuthProvider";
import {
  GeneratedPasswordDialog,
  type GeneratedPasswordDialogHandle,
} from "@/features/identity/ui/GeneratedPasswordDialog";
import { UserEditor } from "@/features/identity/ui/UserEditor";
import { ActionGroup } from "@/shared/ui/action-group";
import { Badge } from "@/shared/ui/badge";
import { Button } from "@/shared/ui/button";
import { Input, Select } from "@/shared/ui/form";
import { StatusBadge } from "@/shared/ui/status-badge";
import {
  IdentityFailureNotice,
  identityFailureView,
  type IdentityFailureView,
} from "@/features/identity/ui/IdentityFailure";

type DirectoryUser = Awaited<ReturnType<typeof listUsers>>["results"][number];
type DirectoryPage = Awaited<ReturnType<typeof listUsers>>;

function useActionError() {
  const [error, setError] = useState<IdentityFailureView>();
  const run = useCallback(async (action: () => Promise<void>) => {
    setError(undefined);
    try {
      await action();
    } catch (caught) {
      setError(identityFailureView(caught));
    }
  }, []);
  return { error, run };
}

function useInitialPage(
  enabled: boolean,
  showPage: (page: DirectoryPage) => void,
  run: (action: () => Promise<void>) => Promise<void>,
) {
  const initialized = useRef(false);
  useEffect(() => {
    if (!enabled || initialized.current) return;
    initialized.current = true;
    let active = true;
    void run(async () => {
      const page = await listUsers({});
      if (active) showPage(page);
    });
    return () => {
      active = false;
    };
  }, [enabled, run, showPage]);
}

async function toggleUserRole(user: DirectoryUser, reload: () => Promise<void>) {
  await changeUserRole(user.id, user.role === "LEADER" ? "HELPDESK" : "LEADER");
  await reload();
}

async function resetAndShow(userId: number, show: (value: string) => void) {
  show((await resetUserPassword(userId)).generated_password);
}

type FiltersProps = {
  query: string;
  role: string;
  active: string;
  onQuery: (value: string) => void;
  onRole: (value: string) => void;
  onActive: (value: string) => void;
  onSearch: (event: FormEvent) => void;
};

function DirectoryFilters(props: FiltersProps) {
  return (
    <form onSubmit={props.onSearch}>
      <label>
        Tìm kiếm
        <Input value={props.query} onChange={(event) => props.onQuery(event.target.value)} />
      </label>
      <label>
        Vai trò
        <Select value={props.role} onChange={(event) => props.onRole(event.target.value)}>
          <option value="">Tất cả</option>
          <option value="MANAGER">Manager</option>
          <option value="LEADER">Leader</option>
          <option value="HELPDESK">Helpdesk</option>
        </Select>
      </label>
      <label>
        Trạng thái
        <Select value={props.active} onChange={(event) => props.onActive(event.target.value)}>
          <option value="">Tất cả</option>
          <option value="true">Đang hoạt động</option>
          <option value="false">Đã khóa</option>
        </Select>
      </label>
      <ActionGroup>
        <Button variant="primary">Tìm</Button>
      </ActionGroup>
    </form>
  );
}

type UserListProps = {
  users: DirectoryUser[];
  canManage: boolean;
  canAssignRole: boolean;
  onEdit: (user: DirectoryUser) => void;
  onStatus: (user: DirectoryUser) => void;
  onReset: (userId: number) => void;
  onRole: (user: DirectoryUser) => void;
};

function UserList(props: UserListProps) {
  return (
    <ul>
      {props.users.map((user) => (
        <li key={user.id}>
          <span>
            {user.full_name} ({user.username}) <Badge tone="neutral">{user.role}</Badge>{" "}
            <StatusBadge tone={user.is_active ? "ready" : "critical"}>
              {user.is_active ? "Đang hoạt động" : "Đã khóa"}
            </StatusBadge>
          </span>
          {user.role !== "MANAGER" && props.canManage && (
            <>
              <Button onClick={() => props.onEdit(user)}>Sửa hồ sơ</Button>
              <Button onClick={() => props.onStatus(user)}>
                {user.is_active ? "Khóa" : "Mở khóa"}
              </Button>
              <Button onClick={() => props.onReset(user.id)}>Đặt lại mật khẩu</Button>
            </>
          )}
          {user.role !== "MANAGER" && props.canAssignRole && (
            <Button onClick={() => props.onRole(user)}>Đổi vai trò</Button>
          )}
        </li>
      ))}
    </ul>
  );
}

type PaginationProps = {
  page: number;
  hasNext: boolean;
  hasPrevious: boolean;
  onPage: (page: number) => void;
  onReload: () => void;
};

function Pagination(props: PaginationProps) {
  return (
    <nav aria-label="Phân trang người dùng">
      <Button disabled={!props.hasPrevious} onClick={() => props.onPage(props.page - 1)}>
        Trang trước
      </Button>
      <span>Trang {props.page}</span>
      <Button disabled={!props.hasNext} onClick={() => props.onPage(props.page + 1)}>
        Trang sau
      </Button>
      <Button type="button" onClick={props.onReload}>
        Tải trang
      </Button>
    </nav>
  );
}

function DirectoryEditors({
  canManage,
  editing,
  onGenerated,
  onSaved,
  onCancel,
}: {
  canManage: boolean;
  editing?: DirectoryUser;
  onGenerated(value: string): void;
  onSaved(): Promise<void>;
  onCancel(): void;
}) {
  return (
    <>
      {canManage ? <UserEditor onGenerated={onGenerated} onSaved={onSaved} /> : null}
      {editing ? <UserEditor user={editing} onSaved={onSaved} onCancel={onCancel} /> : null}
    </>
  );
}

type DirectoryResultsProps = {
  users: DirectoryUser[];
  canManage: boolean;
  canAssignRole: boolean;
  error?: IdentityFailureView;
  page: number;
  hasNext: boolean;
  hasPrevious: boolean;
  load(page?: number): Promise<void>;
  run(action: () => Promise<void>): Promise<void>;
  onEdit(user: DirectoryUser): void;
  onPage(page: number): void;
  onReset(userId: number): void;
};

function DirectoryResults(props: DirectoryResultsProps) {
  return (
    <>
      <IdentityFailureNotice failure={props.error} />
      <UserList
        users={props.users}
        canManage={props.canManage}
        canAssignRole={props.canAssignRole}
        onEdit={props.onEdit}
        onStatus={(user) =>
          void props.run(() => changeUserStatus(user.id, !user.is_active).then(() => props.load()))
        }
        onReset={props.onReset}
        onRole={(user) => void props.run(() => toggleUserRole(user, props.load))}
      />
      <Pagination
        page={props.page}
        hasNext={props.hasNext}
        hasPrevious={props.hasPrevious}
        onPage={(nextPage) => {
          props.onPage(nextPage);
          void props.run(() => props.load(nextPage));
        }}
        onReload={() => void props.run(() => props.load())}
      />
    </>
  );
}

export function UserDirectory() {
  const auth = useAuth();
  const dialog = useRef<GeneratedPasswordDialogHandle>(null);
  const [users, setUsers] = useState<DirectoryUser[]>([]);
  const [query, setQuery] = useState("");
  const [role, setRole] = useState("");
  const [activeFilter, setActiveFilter] = useState("");
  const [page, setPage] = useState(1);
  const [hasNext, setHasNext] = useState(false);
  const [hasPrevious, setHasPrevious] = useState(false);
  const [editing, setEditing] = useState<DirectoryUser>();
  const { error, run } = useActionError();
  const showPage = useCallback((result: DirectoryPage) => {
    setUsers(result.results);
    setHasNext(result.next !== null);
    setHasPrevious(result.previous !== null);
  }, []);
  const load = useCallback(
    async (requestedPage = page) => {
      const result = await listUsers({
        ...(query ? { q: query } : {}),
        ...(role ? { role } : {}),
        ...(activeFilter ? { is_active: activeFilter === "true" } : {}),
        page: requestedPage,
      });
      showPage(result);
    },
    [activeFilter, page, query, role, showPage],
  );
  const canView = auth.hasCapability("user.view");
  useInitialPage(canView, showPage, run);

  if (!canView) return <p>Bạn không có quyền xem danh bạ.</p>;
  async function search(event: FormEvent) {
    event.preventDefault();
    setPage(1);
    await run(() => load(1));
  }
  return (
    <>
      <DirectoryFilters
        query={query}
        role={role}
        active={activeFilter}
        onQuery={setQuery}
        onRole={setRole}
        onActive={setActiveFilter}
        onSearch={search}
      />
      <DirectoryEditors
        canManage={auth.hasCapability("user.manage")}
        editing={editing}
        onGenerated={(value) => dialog.current?.show(value)}
        onSaved={async () => {
          setEditing(undefined);
          await load();
        }}
        onCancel={() => setEditing(undefined)}
      />
      <DirectoryResults
        users={users}
        canManage={auth.hasCapability("user.manage")}
        canAssignRole={auth.hasCapability("user.assign_role")}
        error={error}
        page={page}
        hasNext={hasNext}
        hasPrevious={hasPrevious}
        load={load}
        run={run}
        onEdit={setEditing}
        onPage={setPage}
        onReset={(userId) =>
          void run(() => resetAndShow(userId, (value) => dialog.current?.show(value)))
        }
      />
      <GeneratedPasswordDialog ref={dialog} />
    </>
  );
}
