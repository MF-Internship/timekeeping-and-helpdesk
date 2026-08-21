"use client";

import { type FormEvent, useCallback, useEffect, useRef, useState } from "react";
import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import { ChevronLeft, ChevronRight, MoreVertical, RefreshCw } from "lucide-react";

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
import styles from "./UserDirectory.module.css";
import { clearUserCache, readUserCache, writeUserCache } from "@/shared/cache/user-resource-cache";

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

function useInitialPage(enabled: boolean, load: (offset?: number) => Promise<void>) {
  const initialized = useRef(false);
  useEffect(() => {
    if (!enabled || initialized.current) return;
    initialized.current = true;
    void load(0);
  }, [enabled, load]);
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
    <form className={styles.filters} onSubmit={props.onSearch}>
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
    <ul className={styles.list}>
      {props.users.map((user) => (
        <li key={user.id}>
          <span className={styles.identity}>
            <strong>{user.full_name}</strong>
            <span>@{user.username}</span>
            <span className={styles.badges}>
              <Badge tone="neutral">{user.role}</Badge>{" "}
              <StatusBadge tone={user.is_active ? "ready" : "critical"}>
                {user.is_active ? "Đang hoạt động" : "Đã khóa"}
              </StatusBadge>
            </span>
          </span>
          <UserActions user={user} {...props} />
        </li>
      ))}
    </ul>
  );
}

function UserActions(props: UserListProps & { user: DirectoryUser }) {
  if (props.user.role === "MANAGER" || (!props.canManage && !props.canAssignRole)) return null;
  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger asChild>
        <Button
          className={styles.actionTrigger}
          aria-label={`Thao tác với ${props.user.full_name}`}
        >
          <MoreVertical aria-hidden="true" />
        </Button>
      </DropdownMenu.Trigger>
      <DropdownMenu.Portal>
        <DropdownMenu.Content className={styles.menu} align="end">
          {props.canManage ? (
            <>
              <DropdownMenu.Item onSelect={() => props.onEdit(props.user)}>
                Sửa hồ sơ
              </DropdownMenu.Item>
              <DropdownMenu.Item onSelect={() => props.onStatus(props.user)}>
                {props.user.is_active ? "Khóa" : "Mở khóa"}
              </DropdownMenu.Item>
              <DropdownMenu.Item onSelect={() => props.onReset(props.user.id)}>
                Đặt lại mật khẩu
              </DropdownMenu.Item>
            </>
          ) : null}
          {props.canAssignRole ? (
            <DropdownMenu.Item onSelect={() => props.onRole(props.user)}>
              Đổi vai trò
            </DropdownMenu.Item>
          ) : null}
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}

type PaginationProps = {
  offset: number;
  limit: number;
  count: number;
  hasNext: boolean;
  hasPrevious: boolean;
  onOffset: (offset: number) => void;
  onReload: () => void;
};

function Pagination(props: PaginationProps) {
  const totalPages = Math.ceil(props.count / props.limit);
  const currentPage = props.count === 0 ? 0 : Math.floor(props.offset / props.limit) + 1;
  const firstItem = props.count === 0 ? 0 : props.offset + 1;
  const lastItem = Math.min(props.offset + props.limit, props.count);
  return (
    <nav className={styles.pagination} aria-label="Phân trang người dùng">
      <Button
        className={styles.pageButton}
        disabled={!props.hasPrevious}
        onClick={() => props.onOffset(Math.max(0, props.offset - props.limit))}
      >
        <ChevronLeft aria-hidden="true" />
        Trang trước
      </Button>
      <div className={styles.pageSummary} aria-live="polite">
        <strong>
          Trang {currentPage} <span>/ {totalPages}</span>
        </strong>
        <small>
          Hiển thị {firstItem}–{lastItem} trong {props.count} tài khoản
        </small>
      </div>
      <Button
        className={styles.pageButton}
        disabled={!props.hasNext}
        onClick={() => props.onOffset(props.offset + props.limit)}
      >
        Trang sau
        <ChevronRight aria-hidden="true" />
      </Button>
      <Button className={styles.reloadButton} type="button" onClick={props.onReload}>
        <RefreshCw aria-hidden="true" />
        Tải lại
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
  offset: number;
  limit: number;
  count: number;
  hasNext: boolean;
  hasPrevious: boolean;
  load(offset?: number): Promise<void>;
  run(action: () => Promise<void>): Promise<void>;
  onEdit(user: DirectoryUser): void;
  onOffset(offset: number): void;
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
        offset={props.offset}
        limit={props.limit}
        count={props.count}
        hasNext={props.hasNext}
        hasPrevious={props.hasPrevious}
        onOffset={(nextOffset) => {
          props.onOffset(nextOffset);
          void props.run(() => props.load(nextOffset));
        }}
        onReload={() => void props.run(() => props.load())}
      />
    </>
  );
}

// Directory orchestration intentionally keeps filters, cache and mutations in one auditable scope.
// eslint-disable-next-line max-lines-per-function
export function UserDirectory() {
  const auth = useAuth();
  const dialog = useRef<GeneratedPasswordDialogHandle>(null);
  const [users, setUsers] = useState<DirectoryUser[]>([]);
  const [query, setQuery] = useState("");
  const [role, setRole] = useState("");
  const [activeFilter, setActiveFilter] = useState("");
  const limit = 20;
  const [offset, setOffset] = useState(0);
  const [count, setCount] = useState(0);
  const [hasNext, setHasNext] = useState(false);
  const [hasPrevious, setHasPrevious] = useState(false);
  const [editing, setEditing] = useState<DirectoryUser>();
  const { error, run } = useActionError();
  const showPage = useCallback((result: DirectoryPage) => {
    setUsers(result.results);
    setCount(result.count ?? result.results.length);
    setHasNext(result.next !== null);
    setHasPrevious(result.previous !== null);
  }, []);
  const accountId = auth.state?.kind === "authenticated" ? auth.state.account.id : undefined;
  const load = useCallback(
    async (requestedOffset = offset) => {
      const queryParams = {
        ...(query ? { q: query } : {}),
        ...(role ? { role } : {}),
        ...(activeFilter ? { is_active: activeFilter === "true" } : {}),
        offset: requestedOffset,
        limit,
      };
      const cacheKey = `users:${JSON.stringify(queryParams)}`;
      const cached = readUserCache<DirectoryPage>(accountId, cacheKey);
      if (cached) showPage(cached);
      try {
        const result = await listUsers(queryParams);
        writeUserCache(accountId, cacheKey, result);
        showPage(result);
      } catch (error) {
        if (!cached) throw error;
      }
    },
    [accountId, activeFilter, offset, query, role, showPage],
  );
  const canView = auth.hasCapability("user.view");
  useInitialPage(canView, load);

  if (!canView) return <p>Bạn không có quyền xem danh bạ.</p>;
  async function search(event: FormEvent) {
    event.preventDefault();
    setOffset(0);
    await run(() => load(0));
  }
  return (
    <div className={styles.directory}>
      <section className={styles.section} aria-labelledby="user-search-title">
        <header>
          <h2 id="user-search-title">Tìm kiếm người dùng</h2>
          <p>Lọc nhanh theo tên, vai trò hoặc trạng thái tài khoản.</p>
        </header>
        <DirectoryFilters
          query={query}
          role={role}
          active={activeFilter}
          onQuery={setQuery}
          onRole={setRole}
          onActive={setActiveFilter}
          onSearch={search}
        />
      </section>
      <section className={styles.section} aria-label="Tạo và chỉnh sửa người dùng">
        <DirectoryEditors
          canManage={auth.hasCapability("user.manage")}
          editing={editing}
          onGenerated={(value) => dialog.current?.show(value)}
          onSaved={async () => {
            setEditing(undefined);
            clearUserCache(accountId, "users:");
            await load();
          }}
          onCancel={() => setEditing(undefined)}
        />
      </section>
      <section className={styles.section} aria-labelledby="user-list-title">
        <header className={styles.listHeader}>
          <div>
            <h2 id="user-list-title">Danh sách người dùng</h2>
            <p>Dữ liệu được tải tự động và lưu tạm theo tài khoản quản lý.</p>
          </div>
          <strong>{count} tài khoản</strong>
        </header>
        <DirectoryResults
          users={users}
          canManage={auth.hasCapability("user.manage")}
          canAssignRole={auth.hasCapability("user.assign_role")}
          error={error}
          offset={offset}
          limit={limit}
          count={count}
          hasNext={hasNext}
          hasPrevious={hasPrevious}
          load={load}
          run={run}
          onEdit={setEditing}
          onOffset={setOffset}
          onReset={(userId) =>
            void run(() => resetAndShow(userId, (value) => dialog.current?.show(value)))
          }
        />
      </section>
      <GeneratedPasswordDialog ref={dialog} />
    </div>
  );
}
