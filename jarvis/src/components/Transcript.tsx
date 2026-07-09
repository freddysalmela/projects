import { useEffect, useRef } from 'react';
import type { Message } from '../types';
import './Transcript.css';

interface TranscriptProps {
  messages: Message[];
  interimTranscript: string;
}

export function Transcript({ messages, interimTranscript }: TranscriptProps) {
  const endRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, interimTranscript]);

  return (
    <div className="transcript">
      <div className="transcript-header">COMM LOG</div>
      <div className="transcript-body">
        {messages.length === 0 && !interimTranscript && (
          <div className="transcript-empty">Awaiting input, sir.</div>
        )}
        {messages.map((message, i) => (
          <div key={i} className={`transcript-line transcript-line--${message.role}`}>
            <span className="transcript-speaker">
              {message.role === 'user' ? 'YOU' : 'JARVIS'}
            </span>
            <span className="transcript-text">{message.content}</span>
          </div>
        ))}
        {interimTranscript && (
          <div className="transcript-line transcript-line--user transcript-line--interim">
            <span className="transcript-speaker">YOU</span>
            <span className="transcript-text">{interimTranscript}</span>
          </div>
        )}
        <div ref={endRef} />
      </div>
    </div>
  );
}
