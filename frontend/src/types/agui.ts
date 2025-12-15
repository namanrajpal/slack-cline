/**
 * AG-UI event types for CopilotKit integration.
 * 
 * These types match the backend AG-UI schema.
 * CopilotKit handles these events internally.
 */

export type AGUIEventType =
  | 'runStarted'
  | 'runFinished'
  | 'runError'
  | 'stepStarted'
  | 'stepFinished'
  | 'textMessageStart'
  | 'textMessageContent'
  | 'textMessageEnd'
  | 'toolCallStart'
  | 'toolCallArgs'
  | 'toolCallEnd';

/**
 * CopilotKit shared state for project context.
 * 
 * Future: Add project selector that sets this state,
 * which backend can read to skip LLM classification.
 */
export interface CopilotSharedState {
  selectedProjectId?: string;
  selectedProjectName?: string;
}
