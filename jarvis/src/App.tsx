import { useCallback, useEffect, useRef, useState } from 'react';
import { ArcReactor } from './components/ArcReactor';
import { Transcript } from './components/Transcript';
import { SettingsModal } from './components/SettingsModal';
import { StatusBar } from './components/StatusBar';
import { useSpeechRecognition } from './hooks/useSpeechRecognition';
import { askClaude } from './lib/claude';
import { speakWithBrowser, speakWithElevenLabs } from './lib/tts';
import { loadSettings, saveSettings } from './lib/settings';
import type { AssistantState, Message, Settings } from './types';
import './App.css';

function App() {
  const [settings, setSettings] = useState<Settings>(() => loadSettings());
  const [showSettings, setShowSettings] = useState(false);
  const [state, setState] = useState<AssistantState>('idle');
  const [messages, setMessages] = useState<Message[]>([]);
  const [errorText, setErrorText] = useState('');
  const messagesRef = useRef<Message[]>([]);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const handleSaveSettings = (next: Settings) => {
    setSettings(next);
    saveSettings(next);
  };

  const handleFinalTranscript = useCallback(
    async (transcript: string) => {
      if (!settings.anthropicApiKey) {
        setErrorText('Add your Anthropic API key in settings first.');
        setState('error');
        setTimeout(() => setState('idle'), 2500);
        return;
      }

      const userMessage: Message = { role: 'user', content: transcript };
      const nextHistory = [...messagesRef.current, userMessage];
      messagesRef.current = nextHistory;
      setMessages(nextHistory);
      setState('thinking');

      try {
        const reply = await askClaude(settings.anthropicApiKey, settings.model, nextHistory);
        const assistantMessage: Message = { role: 'assistant', content: reply };
        messagesRef.current = [...nextHistory, assistantMessage];
        setMessages(messagesRef.current);

        if (settings.useVoiceOutput) {
          setState('speaking');
          if (settings.elevenLabsApiKey) {
            const audio = await speakWithElevenLabs(
              settings.elevenLabsApiKey,
              settings.elevenLabsVoiceId,
              reply,
            );
            audioRef.current = audio;
            audio.onended = () => setState('idle');
            audio.onerror = () => setState('idle');
            await audio.play();
          } else {
            speakWithBrowser(reply);
            setState('idle');
          }
        } else {
          setState('idle');
        }
      } catch (err) {
        console.error(err);
        setErrorText(err instanceof Error ? err.message : 'Something went wrong.');
        setState('error');
        setTimeout(() => setState('idle'), 3000);
      }
    },
    [settings],
  );

  const { isListening, interimTranscript, isSupported, startListening, stopListening } =
    useSpeechRecognition({ onFinalResult: handleFinalTranscript });

  useEffect(() => {
    if (!isListening && state === 'listening') {
      setState('idle');
    }
  }, [isListening, state]);

  const handleTalkPress = () => {
    if (state === 'thinking' || state === 'speaking' || isListening) return;
    setState('listening');
    startListening();
  };

  const handleTalkRelease = () => {
    if (isListening) {
      stopListening();
    }
  };

  return (
    <div className="app-shell">
      <div className="hud-corner hud-corner--tl" />
      <div className="hud-corner hud-corner--tr" />
      <div className="hud-corner hud-corner--bl" />
      <div className="hud-corner hud-corner--br" />

      <StatusBar />

      <button className="settings-toggle" onClick={() => setShowSettings(true)}>
        CONFIG
      </button>

      <main className="app-main">
        <ArcReactor state={state} />

        {state === 'error' && <div className="error-banner">{errorText}</div>}

        <button
          className={`talk-button ${isListening ? 'talk-button--active' : ''}`}
          onMouseDown={handleTalkPress}
          onMouseUp={handleTalkRelease}
          onTouchStart={handleTalkPress}
          onTouchEnd={handleTalkRelease}
          disabled={!isSupported || state === 'thinking' || state === 'speaking'}
        >
          {isSupported ? (isListening ? 'RELEASE TO SEND' : 'HOLD TO TALK') : 'MIC NOT SUPPORTED'}
        </button>

        <Transcript messages={messages} interimTranscript={interimTranscript} />
      </main>

      {showSettings && (
        <SettingsModal
          settings={settings}
          onSave={handleSaveSettings}
          onClose={() => setShowSettings(false)}
        />
      )}
    </div>
  );
}

export default App;
