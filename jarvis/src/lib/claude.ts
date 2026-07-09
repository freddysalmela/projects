import Anthropic from '@anthropic-ai/sdk';
import type { Message } from '../types';

const SYSTEM_PROMPT = `You are JARVIS, a personal AI assistant. Respond concisely and conversationally,
as your replies will be read aloud by a text-to-speech engine. Avoid markdown formatting,
bullet points, or code blocks in your responses — speak in plain, natural sentences. Keep
answers brief unless the user asks for detail. You may be witty and dry, but stay helpful
and to the point.`;

export async function askClaude(
  apiKey: string,
  model: string,
  history: Message[],
): Promise<string> {
  const client = new Anthropic({ apiKey, dangerouslyAllowBrowser: true });

  const response = await client.messages.create({
    model,
    max_tokens: 1024,
    system: SYSTEM_PROMPT,
    messages: history.map((m) => ({ role: m.role, content: m.content })),
  });

  const textBlock = response.content.find((block) => block.type === 'text');
  return textBlock && textBlock.type === 'text' ? textBlock.text : '';
}
