/**
 * The rendered width of an element, for charts that draw at real pixel sizes.
 *
 * The alternative — a fixed `viewBox` scaled with CSS — scales the *text* too,
 * so axis labels shrink to unreadable on a phone and bloat on a wide monitor.
 * Measuring costs one observer and keeps typography at a fixed size whatever
 * the chart's width.
 *
 * Falls back to `fallback` where `ResizeObserver` is absent (jsdom), so tests
 * render a real chart rather than a zero-width one.
 */

import { useEffect, useRef, useState } from 'react';

export function useElementWidth<T extends HTMLElement>(
  fallback = 640,
): [React.RefObject<T>, number] {
  const ref = useRef<T>(null);
  const [width, setWidth] = useState(fallback);

  useEffect(() => {
    const node = ref.current;
    if (!node) return;

    if (typeof ResizeObserver === 'undefined') {
      const measured = node.getBoundingClientRect().width;
      if (measured > 0) setWidth(measured);
      return;
    }

    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (!entry) return;
      const measured = entry.contentRect.width;
      if (measured > 0) setWidth(measured);
    });

    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  return [ref, width];
}
