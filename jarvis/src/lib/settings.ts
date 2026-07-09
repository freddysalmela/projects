import type { Settings } from '../types';

const STORAGE_KEY = 'jarvis.settings.v1';

export const DEFAULT_SETTINGS: Settings = {
  anthropicApiKey: '',
  elevenLabsApiKey: '',
  elevenLabsVoiceId: 'pNInz6obpgDQGcFmaJgB', // "Adam" - a default ElevenLabs premade voice
  model: 'claude-sonnet-5',
  useVoiceOutput: true,
};

export function loadSettings(): Settings {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT_SETTINGS;
    return { ...DEFAULT_SETTINGS, ...JSON.parse(raw) };
  } catch {
    return DEFAULT_SETTINGS;
  }
}

export function saveSettings(settings: Settings): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
}
