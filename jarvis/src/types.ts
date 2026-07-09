export type AssistantState = 'idle' | 'listening' | 'thinking' | 'speaking' | 'error';

export interface Message {
  role: 'user' | 'assistant';
  content: string;
}

export interface Settings {
  anthropicApiKey: string;
  elevenLabsApiKey: string;
  elevenLabsVoiceId: string;
  model: string;
  useVoiceOutput: boolean;
}
