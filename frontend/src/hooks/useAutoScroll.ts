/**
 * Controlled auto-scroll hook for chat interfaces.
 *
 * Features:
 * - Auto-scrolls only when the user is near the bottom
 * - Preserves scroll position when user scrolls up
 * - Provides "scroll to bottom" affordance when not at bottom
 * - Handles both new messages and streaming content updates
 */

import { useRef, useState, useCallback, useEffect } from 'react';

export interface UseAutoScrollOptions {
  /**
   * Distance from bottom (in pixels) to consider "at bottom".
   * Default: 100px
   */
  thresholdPx?: number;
  /**
   * Whether to enable auto-scroll. Default: true
   */
  enabled?: boolean;
}

export interface UseAutoScrollResult {
  /**
   * Ref to attach to the scroll container element.
   */
  containerRef: React.RefObject<HTMLDivElement | null>;
  /**
   * Ref to attach to a sentinel element at the end of the content.
   */
  endRef: React.RefObject<HTMLDivElement | null>;
  /**
   * Whether the scroll position is currently near the bottom.
   */
  isAtBottom: boolean;
  /**
   * Manually scroll to bottom.
   */
  scrollToBottom: (behavior?: ScrollBehavior) => void;
  /**
   * Event handler to attach to the scroll container's onScroll event.
   */
  onScroll: () => void;
  /**
   * Reset user scroll override (call after sending a message).
   */
  resetUserScroll: () => void;
}

export function useAutoScroll(options: UseAutoScrollOptions = {}): UseAutoScrollResult {
  const { thresholdPx = 100, enabled = true } = options;

  const containerRef = useRef<HTMLDivElement>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const [isAtBottom, setIsAtBottom] = useState(true);
  const userScrolledRef = useRef(false);

  /**
   * Check if the container is scrolled near the bottom.
   */
  const checkIsAtBottom = useCallback(() => {
    const container = containerRef.current;
    if (!container) return true;

    const { scrollHeight, scrollTop, clientHeight } = container;
    const distanceFromBottom = scrollHeight - scrollTop - clientHeight;
    return distanceFromBottom <= thresholdPx;
  }, [thresholdPx]);

  /**
   * Scroll to the bottom of the container.
   */
  const scrollToBottom = useCallback((behavior: ScrollBehavior = 'smooth') => {
    if (endRef.current) {
      endRef.current.scrollIntoView({ behavior });
    } else if (containerRef.current) {
      const container = containerRef.current;
      container.scrollTo({
        top: container.scrollHeight,
        behavior,
      });
    }
    userScrolledRef.current = false;
    setIsAtBottom(true);
  }, []);

  /**
   * Handle scroll events from the container.
   */
  const onScroll = useCallback(() => {
    const atBottom = checkIsAtBottom();
    setIsAtBottom(atBottom);

    // If user scrolled away from bottom, mark as user-scrolled
    if (!atBottom) {
      userScrolledRef.current = true;
    }
  }, [checkIsAtBottom]);

  /**
   * Reset the user scroll flag (call when sending a new message).
   */
  const resetUserScroll = useCallback(() => {
    userScrolledRef.current = false;
  }, []);

  /**
   * Auto-scroll when enabled and at bottom (not user-scrolled).
   * This effect runs on mount and whenever container content changes.
   */
  useEffect(() => {
    if (!enabled) return;

    // Only auto-scroll if we were at bottom and user hasn't scrolled
    if (isAtBottom && !userScrolledRef.current) {
      // Use requestAnimationFrame to ensure content is rendered
      requestAnimationFrame(() => {
        scrollToBottom('instant');
      });
    }
  }, [enabled, isAtBottom, scrollToBottom]);

  return {
    containerRef,
    endRef,
    isAtBottom,
    scrollToBottom,
    onScroll,
    resetUserScroll,
  };
}
