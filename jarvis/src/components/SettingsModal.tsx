import { useState } from 'react';
import type { Settings } from '../types';
import './SettingsModal.css';

interface SettingsModalProps {
  settings: Settings;
  onSave: (settings: Settings) => void;
  onClose: () => void;
}

export function SettingsModal({ settings, onSave, onClose }: SettingsModalProps) {
  const [draft, setDraft] = useState<Settings>(settings);

  return (
    <div className="settings-overlay" onClick={onClose}>
      <div className="settings-panel" onClick={(e) => e.stopPropagation()}>
        <div className="settings-header">SYSTEM CONFIGURATION</div>

        <label className="settings-field">
          <span>Anthropic API key</span>
          <input
            type="password"
            value={draft.anthropicApiKey}
            onChange={(e) => setDraft({ ...draft, anthropicApiKey: e.target.value })}
            placeholder="sk-ant-..."
            autoComplete="off"
          />
        </label>

        <label className="settings-field">
          <span>Claude model</span>
          <input
            type="text"
            value={draft.model}
            onChange={(e) => setDraft({ ...draft, model: e.target.value })}
          />
        </label>

        <label className="settings-field settings-checkbox">
          <input
            type="checkbox"
            checked={draft.useVoiceOutput}
            onChange={(e) => setDraft({ ...draft, useVoiceOutput: e.target.checked })}
          />
          <span>Enable voice output</span>
        </label>

        <label className="settings-field">
          <span>ElevenLabs API key</span>
          <input
            type="password"
            value={draft.elevenLabsApiKey}
            onChange={(e) => setDraft({ ...draft, elevenLabsApiKey: e.target.value })}
            placeholder="Leave blank to use browser voice"
            autoComplete="off"
          />
        </label>

        <label className="settings-field">
          <span>ElevenLabs voice ID</span>
          <input
            type="text"
            value={draft.elevenLabsVoiceId}
            onChange={(e) => setDraft({ ...draft, elevenLabsVoiceId: e.target.value })}
          />
        </label>

        <p className="settings-note">
          Keys are stored only in this browser's local storage. They are never sent anywhere
          except directly to Anthropic / ElevenLabs from your machine.
        </p>

        <div className="settings-actions">
          <button className="hud-button" onClick={onClose}>CANCEL</button>
          <button
            className="hud-button hud-button--primary"
            onClick={() => {
              onSave(draft);
              onClose();
            }}
          >
            SAVE
          </button>
        </div>
      </div>
    </div>
  );
}
