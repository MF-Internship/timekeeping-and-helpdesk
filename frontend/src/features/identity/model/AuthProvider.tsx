"use client";

import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useSyncExternalStore,
} from "react";

import * as identityApi from "@/features/identity/api/identity-api";
import { purgeEvidenceDrafts } from "@/features/tasks/model/evidence-draft";
import {
  clearSession,
  getSessionState,
  setSessionState,
  subscribeSession,
  type Account,
} from "@/features/identity/model/session-store";
import {
  clearMemoryAccessToken,
  setAuthenticationFailureHandler,
  setMemoryAccessToken,
} from "@/shared/transport/authenticated-fetch";

type AuthContextValue = {
  state: ReturnType<typeof getSessionState>;
  login(username: string, password: string): Promise<void>;
  logout(): Promise<void>;
  changePassword(currentPassword: string, newPassword: string): Promise<void>;
  hasCapability(capability: string): boolean;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);
let bootstrapFlight: Promise<Account> | undefined;

function failureCode(error: unknown): string | undefined {
  if (typeof error !== "object" || error === null) return undefined;
  const candidate = error as { errorCode?: unknown; error_code?: unknown };
  const code = candidate.errorCode ?? candidate.error_code;
  return typeof code === "string" ? code : undefined;
}

function asAccount(value: Awaited<ReturnType<typeof identityApi.getMe>>): Account {
  return value as Account;
}

function bootstrapAccount(): Promise<Account> {
  if (bootstrapFlight) return bootstrapFlight;
  const promise = identityApi
    .refresh()
    .then((session) => {
      setMemoryAccessToken(session.access);
      return identityApi.getMe();
    })
    .then(asAccount)
    .finally(() => {
      if (bootstrapFlight === promise) bootstrapFlight = undefined;
    });
  bootstrapFlight = promise;
  return promise;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const state = useSyncExternalStore(subscribeSession, getSessionState, getSessionState);

  useEffect(() => {
    let current = true;
    void bootstrapAccount()
      .then((next) => {
        if (!current) return;
        setSessionState(
          next.must_change_password
            ? { kind: "forced_change", account: next }
            : { kind: "authenticated", account: next },
        );
      })
      .catch((error: unknown) => {
        if (!current) return;
        if (failureCode(error) === "ACCOUNT_INACTIVE") {
          purgeEvidenceDrafts();
          clearMemoryAccessToken();
          setSessionState({ kind: "inactive" });
        } else {
          clearSession();
        }
      });
    return () => {
      current = false;
    };
  }, []);

  useEffect(() => {
    setAuthenticationFailureHandler((code) => {
      if (code === "ACCOUNT_INACTIVE") {
        purgeEvidenceDrafts();
        setSessionState({ kind: "inactive" });
      }
      if (code === "PASSWORD_CHANGE_REQUIRED") setSessionState({ kind: "forced_change" });
      if (code === "INVALID_TOKEN") clearSession();
    });
    return () => setAuthenticationFailureHandler(undefined);
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    purgeEvidenceDrafts();
    const session = await identityApi.login({ username, password });
    setMemoryAccessToken(session.access);
    if (session.must_change_password) {
      setSessionState({ kind: "forced_change" });
      return;
    }
    setSessionState({ kind: "authenticated", account: asAccount(await identityApi.getMe()) });
  }, []);

  const logout = useCallback(async () => {
    try {
      await identityApi.logout();
    } finally {
      purgeEvidenceDrafts(state.kind === "authenticated" ? state.account.id : undefined);
      clearMemoryAccessToken();
      clearSession();
    }
  }, [state]);

  const changePassword = useCallback(async (currentPassword: string, newPassword: string) => {
    const session = await identityApi.changePassword(currentPassword, newPassword);
    setMemoryAccessToken(session.access);
    setSessionState({ kind: "authenticated", account: asAccount(await identityApi.getMe()) });
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      state,
      login,
      logout,
      changePassword,
      hasCapability: (capability) =>
        state.kind === "authenticated" && state.account.capabilities.includes(capability),
    }),
    [state, login, logout, changePassword],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error("AuthProvider is required");
  return value;
}
