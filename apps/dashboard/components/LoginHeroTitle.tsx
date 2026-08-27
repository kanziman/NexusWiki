"use client";

import { useEffect, useState } from "react";

export function LoginHeroTitle() {
  const [documentVisible, setDocumentVisible] = useState(true);
  const [reducedMotion, setReducedMotion] = useState(false);

  useEffect(() => {
    const syncVisibility = () => setDocumentVisible(!document.hidden);
    syncVisibility();
    document.addEventListener("visibilitychange", syncVisibility);

    if (typeof window.matchMedia !== "function") {
      return () =>
        document.removeEventListener("visibilitychange", syncVisibility);
    }

    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    const syncReducedMotion = () => setReducedMotion(media.matches);
    syncReducedMotion();
    media.addEventListener("change", syncReducedMotion);

    return () => {
      document.removeEventListener("visibilitychange", syncVisibility);
      media.removeEventListener("change", syncReducedMotion);
    };
  }, []);

  return (
    <h1 id="login-visual-title">
      팀의 지식을,
      <br />
      <span
        className={`login-visual-underlined${
          documentVisible && !reducedMotion ? " is-animating" : " is-complete"
        }`}
      >
        답으로 연결하다.
      </span>
    </h1>
  );
}
