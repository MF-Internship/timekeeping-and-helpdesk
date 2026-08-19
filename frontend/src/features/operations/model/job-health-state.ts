import { useCallback, useEffect, useState } from "react";

import { getJobHealth, type JobHealth } from "../api/job-health-api";

const REFRESH_MS = 60_000;

export function useJobHealth() {
  const [data, setData] = useState<JobHealth>();
  const [error, setError] = useState<unknown>();
  const [refreshing, setRefreshing] = useState(false);
  const refresh = useCallback(async () => {
    setRefreshing(true);
    try {
      setData(await getJobHealth());
      setError(undefined);
    } catch (nextError) {
      setError(nextError);
    } finally {
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    queueMicrotask(() => void refresh());
    const interval = window.setInterval(() => {
      if (document.visibilityState === "visible") void refresh();
    }, REFRESH_MS);
    return () => window.clearInterval(interval);
  }, [refresh]);

  return { data, error, refreshing, refresh };
}
