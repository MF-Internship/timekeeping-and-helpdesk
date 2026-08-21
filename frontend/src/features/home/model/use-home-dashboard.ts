"use client";
import { useCallback, useEffect, useState } from "react";
export type HomeResource<T> = {
  data?: T;
  loading: boolean;
  error?: unknown;
  refresh(): Promise<void>;
};
export function useHomeResource<T>(enabled: boolean, load: () => Promise<T>): HomeResource<T> {
  const [data, setData] = useState<T>();
  const [loading, setLoading] = useState(enabled);
  const [error, setError] = useState<unknown>();
  const refresh = useCallback(async () => {
    if (!enabled) return;
    setLoading(true);
    try {
      setData(await load());
      setError(undefined);
    } catch (failure) {
      setError(failure);
    } finally {
      setLoading(false);
    }
  }, [enabled, load]);
  useEffect(() => {
    if (!enabled) return;
    queueMicrotask(() => void refresh());
  }, [enabled, refresh]);
  return { data, loading, error, refresh };
}
