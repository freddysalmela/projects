import { useEffect, useState } from 'react';
import './StatusBar.css';

export function StatusBar() {
  const [now, setNow] = useState(new Date());

  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  const time = now.toLocaleTimeString([], { hour12: false });
  const date = now.toLocaleDateString([], { weekday: 'long', month: 'long', day: 'numeric' });

  return (
    <div className="status-bar">
      <div className="status-bar-block">
        <span className="status-bar-label">DATE</span>
        <span className="status-bar-value">{date}</span>
      </div>
      <div className="status-bar-block status-bar-block--time">
        <span className="status-bar-value status-bar-value--time">{time}</span>
      </div>
      <div className="status-bar-block status-bar-block--right">
        <span className="status-bar-label">SYSTEM</span>
        <span className="status-bar-value">J.A.R.V.I.S ONLINE</span>
      </div>
    </div>
  );
}
