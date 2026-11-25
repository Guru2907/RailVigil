import { useEffect, useState } from "react";
import { getHealth } from "../api/health.js";

const POLL_MS = 15000;

// Real backend health and round-trip time, polled every 15 s.
// online: null while the first check is running, then true or false.
export function useHealth() {
  const [state, setState] = useState({ online: null, ms: null });
  useEffect(() => {
    let cancelled = false;
    const check = () => {
      const t0 = performance.now();
      getHealth()
        .then(() => !cancelled && setState({ online: true, ms: Math.round(performance.now() - t0) }))
        .catch(() => !cancelled && setState({ online: false, ms: null }));
    };
    check();
    const timer = setInterval(check, POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, []);
  return state;
}
