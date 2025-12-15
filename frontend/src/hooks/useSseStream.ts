/**
 * Robust SSE stream parser with buffered frame handling.
 *
 * Handles partial frames that can occur when TCP chunks split SSE events
 * across multiple reads.
 *
 * SSE Format:
 * - Each frame is delimited by `\n\n` (double newline)
 * - Each frame can have multiple `data:` lines (content is concatenated)
 * - Empty lines between frames are ignored
 */

import { useCallback, useRef } from 'react';

export interface SseEvent {
  type: string;
  [key: string]: unknown;
}

export interface UseSseStreamResult {
  /**
   * Stream SSE events from a Response object.
   * Calls onEvent for each parsed event.
   */
  stream: (response: Response, onEvent: (event: SseEvent) => void) => Promise<void>;
  /**
   * Cancel the current stream.
   */
  cancel: () => void;
}

/**
 * Parse a single SSE frame (text between \n\n delimiters) into an event object.
 * Handles multi-line `data:` fields by concatenating their values.
 */
function parseFrame(frame: string): SseEvent | null {
  const lines = frame.split('\n');
  const dataLines: string[] = [];
  let eventType = 'message';

  for (const line of lines) {
    if (line.startsWith('data:')) {
      // Remove 'data:' prefix and optional leading space
      const content = line.slice(5).trimStart();
      dataLines.push(content);
    } else if (line.startsWith('event:')) {
      eventType = line.slice(6).trim();
    }
    // Ignore id:, retry:, and comment lines for now
  }

  if (dataLines.length === 0) {
    return null;
  }

  // Join all data lines (SSE spec says newlines between data: lines should be preserved)
  const data = dataLines.join('\n');

  try {
    const parsed = JSON.parse(data);
    // If the parsed object doesn't have a type, add the event type
    if (typeof parsed === 'object' && parsed !== null && !parsed.type) {
      parsed.type = eventType;
    }
    return parsed as SseEvent;
  } catch {
    // If JSON parsing fails, return raw data
    console.warn('Failed to parse SSE data as JSON:', data);
    return { type: eventType, data };
  }
}

export function useSseStream(): UseSseStreamResult {
  const abortControllerRef = useRef<AbortController | null>(null);

  const cancel = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
  }, []);

  const stream = useCallback(
    async (response: Response, onEvent: (event: SseEvent) => void) => {
      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('No response body');
      }

      console.log('[SSE] Starting stream...');

      // Create abort controller for this stream
      abortControllerRef.current = new AbortController();

      const decoder = new TextDecoder();
      let buffer = '';
      let chunkCount = 0;
      let eventCount = 0;

      try {
        while (true) {
          // Check if cancelled
          if (abortControllerRef.current?.signal.aborted) {
            console.log('[SSE] Stream aborted');
            break;
          }

          const { done, value } = await reader.read();

          if (done) {
            console.log(`[SSE] Stream done. Total chunks: ${chunkCount}, Total events: ${eventCount}`);
            // Process any remaining data in buffer
            if (buffer.trim()) {
              console.log('[SSE] Processing remaining buffer:', buffer.substring(0, 100));
              const event = parseFrame(buffer);
              if (event) {
                eventCount++;
                console.log('[SSE] Final event:', event.type);
                onEvent(event);
              }
            }
            break;
          }

          chunkCount++;
          // Append new chunk to buffer
          const chunk = decoder.decode(value, { stream: true });
          buffer += chunk;

          if (chunkCount <= 3 || chunkCount % 10 === 0) {
            console.log(`[SSE] Chunk ${chunkCount} received (${chunk.length} bytes)`);
          }

          // Process complete frames (delimited by \n\n)
          let frameEndIndex: number;
          while ((frameEndIndex = buffer.indexOf('\n\n')) !== -1) {
            const frame = buffer.slice(0, frameEndIndex);
            buffer = buffer.slice(frameEndIndex + 2); // Skip past \n\n

            if (frame.trim()) {
              const event = parseFrame(frame);
              if (event) {
                eventCount++;
                console.log(`[SSE] Event ${eventCount}:`, event.type, event);
                onEvent(event);
              }
            }
          }
        }
      } catch (err) {
        console.error('[SSE] Stream error:', err);
        throw err;
      } finally {
        console.log('[SSE] Stream cleanup');
        reader.releaseLock();
        abortControllerRef.current = null;
      }
    },
    []
  );

  return { stream, cancel };
}
