/**
 * Light/dark selection.
 *
 * Three states, not two: `system` follows the OS, and an explicit choice
 * stamps `data-theme` on the root so the CSS toggle scope wins over the media
 * query in both directions.
 */

import { useCallback, useEffect, useState } from 'react';

export type ThemeChoice = 'system' | 'light' | 'dark';

const STORAGE_KEY = 'afi.theme';

function readStored(): ThemeChoice {
  if (typeof localStorage === 'undefined') return 'system';
  const stored = localStorage.getItem(STORAGE_KEY);
  return stored === 'light' || stored === 'dark' ? stored : 'system';
}

export function useTheme(): [ThemeChoice, (choice: ThemeChoice) => void] {
  const [choice, setChoice] = useState<ThemeChoice>(readStored);

  useEffect(() => {
    const root = document.documentElement;
    if (choice === 'system') {
      root.removeAttribute('data-theme');
      localStorage.removeItem(STORAGE_KEY);
    } else {
      root.setAttribute('data-theme', choice);
      localStorage.setItem(STORAGE_KEY, choice);
    }
  }, [choice]);

  return [choice, useCallback((next: ThemeChoice) => setChoice(next), [])];
}
