export type Account = {
  id: number;
  username: string;
  full_name: string;
  phone: string | null;
  email: string | null;
  role: string;
  is_active: boolean;
  must_change_password: boolean;
  capabilities: string[];
};

export type SessionState =
  | { kind: "loading" }
  | { kind: "anonymous" }
  | { kind: "inactive" }
  | { kind: "forced_change"; account?: Account }
  | { kind: "authenticated"; account: Account };

let state: SessionState = { kind: "loading" };
const listeners = new Set<() => void>();

export function getSessionState(): SessionState {
  return state;
}

export function setSessionState(next: SessionState): void {
  state = next;
  listeners.forEach((listener) => listener());
}

export function subscribeSession(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function clearSession(): void {
  setSessionState({ kind: "anonymous" });
}
