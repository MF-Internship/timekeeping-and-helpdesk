"use client";

import { useCallback, useEffect, useRef, useState, type MutableRefObject } from "react";

export type FreshPosition = {
  latitude: string;
  longitude: string;
  accuracy_m: string;
  captured_at: string;
};

function watchFreshPosition(
  watch: MutableRefObject<number | undefined>,
  stop: () => void,
): Promise<FreshPosition> {
  return new Promise((resolve, reject) => {
    watch.current = navigator.geolocation.watchPosition(
      (position) => {
        stop();
        resolve({
          latitude: String(position.coords.latitude),
          longitude: String(position.coords.longitude),
          accuracy_m: String(position.coords.accuracy),
          captured_at: new Date(position.timestamp).toISOString(),
        });
      },
      (error) => {
        stop();
        reject(error);
      },
      { enableHighAccuracy: true, maximumAge: 0, timeout: 15000 },
    );
  });
}

export function useForegroundPosition() {
  const [loading, setLoading] = useState(false);
  const watch = useRef<number | undefined>(undefined);

  const stop = useCallback(() => {
    if (watch.current !== undefined) navigator.geolocation.clearWatch(watch.current);
    watch.current = undefined;
    setLoading(false);
  }, []);

  useEffect(() => {
    const visibility = () => document.hidden && stop();
    document.addEventListener("visibilitychange", visibility);
    return () => {
      document.removeEventListener("visibilitychange", visibility);
      stop();
    };
  }, [stop]);

  const acquire = useCallback(async (): Promise<FreshPosition> => {
    stop();
    setLoading(true);
    return await watchFreshPosition(watch, stop);
  }, [stop]);

  return { acquire, loading, cancel: stop };
}
