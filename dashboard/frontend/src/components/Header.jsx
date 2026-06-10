import { useState, useEffect } from "react";

export default function Header() {
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <header className="header">
      <div className="header-brand">
        <div className="header-logo">α</div>
        <div>
          <div className="header-title">Auto_Plus_Ops</div>
          <div className="header-subtitle">ML Pipeline Health Agent</div>
        </div>
      </div>
      <div className="header-clock">
        <span className="header-live-dot" />
        {time.toLocaleString("en-US", {
          weekday: "short",
          month: "short",
          day: "numeric",
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
          hour12: false,
        })}
      </div>
    </header>
  );
}
