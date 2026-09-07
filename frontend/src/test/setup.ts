import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach, vi } from 'vitest';

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

// jsdom has no layout engine, so charts that measure their container would
// render at zero width. The hook falls back to a default when ResizeObserver
// is absent; this stub keeps that path deterministic rather than
// environment-dependent.
// jsdom implements no scrolling, so `scrollIntoView` is simply absent. The
// chat auto-scroll is real behaviour in a browser; here it is a no-op.
if (typeof Element.prototype.scrollIntoView !== 'function') {
  Element.prototype.scrollIntoView = function scrollIntoView() {};
}

if (typeof globalThis.ResizeObserver === 'undefined') {
  globalThis.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  } as unknown as typeof ResizeObserver;
}
