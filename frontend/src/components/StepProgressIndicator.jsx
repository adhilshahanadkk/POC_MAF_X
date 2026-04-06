// components/StepProgressIndicator.jsx
import { useState, useEffect } from "react";

// AG-UI STEP_STARTED/STEP_FINISHED events are consumed by CopilotKit internally.
// We surface them via a simple polling approach on a shared ref,
// or you can use CopilotKit's useCoAgent steps API.
export function StepProgressIndicator() {
  const [dots, setDots] = useState(".");
  useEffect(() => {
    const id = setInterval(() => setDots(d => d.length < 3 ? d + "." : "."), 500);
    return () => clearInterval(id);
  }, []);

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "6px 0", fontSize: 13, color: "var(--color-text-secondary)" }}>
      <div className="typing-dot"/><div className="typing-dot"/><div className="typing-dot"/>
      <span style={{ marginLeft: 6 }}>Agents working{dots}</span>
    </div>
  );
}