import { useEffect, useState } from "react";

import { api } from "../api/endpoints.js";

// The free hosting plan puts the API to sleep when nobody is using it, and the
// first request then takes up to a minute. Explain that, so visitors don't think the site is broken.
export default function ServerWakeNotice({ delayMs = 2500 }) {
  const [state, setState] = useState("checking"); // checking | slow | down | ok

  useEffect(() => {
    // Only show the notice if the server hasn't answered after a short wait.
    let done = false;
    const timer = setTimeout(() => !done && setState("slow"), delayMs);

    const ping = async (attempt = 0) => {
      try {
        await api.health();
        done = true;
        setState("ok");
      } catch {
        // While the server boots, requests can fail outright. Keep trying for about a minute.
        if (attempt < 12) setTimeout(() => ping(attempt + 1), 5000);
        else setState("down");
      }
    };
    ping();
    return () => clearTimeout(timer);
  }, [delayMs]);

  // Server is slow: show a spinner and explain why.
  if (state === "slow") {
    return (
      <div className="notice" role="status">
        <span className="spinner" aria-hidden="true" />
        Waking up the server… This demo runs on free hosting that sleeps when idle, so the first load can take up to a
        minute.
      </div>
    );
  }
  // Server never answered: show an error.
  if (state === "down") {
    return (
      <div className="notice notice-error" role="alert">
        The server isn't responding right now. Please try again in a minute.
      </div>
    );
  }
  // Server is up: show nothing.
  return null;
}
