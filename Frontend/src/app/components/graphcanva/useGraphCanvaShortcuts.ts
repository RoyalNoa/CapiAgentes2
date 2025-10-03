"use client";

import { useEffect } from "react";
import { useReactFlow } from "@xyflow/react";

export const useGraphCanvaShortcuts = (onRun: () => void) => {
  const instance = useReactFlow();

  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "f") {
        event.preventDefault();
        instance.fitView({ padding: 0.2 });
      }
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "r") {
        event.preventDefault();
        onRun();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [instance, onRun]);
};
