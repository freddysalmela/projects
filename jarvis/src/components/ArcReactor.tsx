import type { AssistantState } from '../types';
import './ArcReactor.css';

interface ArcReactorProps {
  state: AssistantState;
}

const STATE_LABEL: Record<AssistantState, string> = {
  idle: 'STANDING BY',
  listening: 'LISTENING',
  thinking: 'PROCESSING',
  speaking: 'RESPONDING',
  error: 'ERROR',
};

export function ArcReactor({ state }: ArcReactorProps) {
  return (
    <div className={`arc-reactor arc-reactor--${state}`}>
      <div className="arc-ring arc-ring--outer" />
      <div className="arc-ring arc-ring--mid" />
      <div className="arc-ring arc-ring--tick" />
      <svg className="arc-spokes" viewBox="0 0 200 200">
        {Array.from({ length: 12 }).map((_, i) => (
          <line
            key={i}
            x1="100"
            y1="14"
            x2="100"
            y2="30"
            transform={`rotate(${i * 30} 100 100)`}
          />
        ))}
      </svg>
      <div className="arc-core">
        <div className="arc-core-inner" />
      </div>
      <div className="arc-label">{STATE_LABEL[state]}</div>
    </div>
  );
}
