import { describe, expect, it } from 'vitest';
import {
  formatCategory,
  formatDayLong,
  formatHabit,
  formatMonth,
  formatPaise,
  formatPaiseCompact,
  formatRatio,
  pluralise,
} from './format';

describe('money formatting', () => {
  it('renders integer paise as rupees', () => {
    expect(formatPaise(412050)).toBe('₹4,120.50');
  });

  it('keeps sub-rupee amounts exact', () => {
    expect(formatPaise(5)).toBe('₹0.05');
  });

  it('handles zero', () => {
    expect(formatPaise(0)).toBe('₹0.00');
  });

  it('groups large amounts in the Indian system', () => {
    // 10,00,000 paise is ₹10,000 — the lakh grouping matters for the market.
    expect(formatPaise(1_000_000)).toBe('₹10,000.00');
  });

  it('drops paise in the compact form used for axis ticks', () => {
    expect(formatPaiseCompact(412050)).toBe('₹4,121');
  });
});

describe('ratio formatting', () => {
  it('renders a backend ratio as a percentage', () => {
    expect(formatRatio(0.4939)).toBe('49.4%');
  });

  it('respects the requested precision', () => {
    expect(formatRatio(0.4939, 2)).toBe('49.39%');
    expect(formatRatio(0.6, 0)).toBe('60%');
  });
});

describe('label formatting', () => {
  it('gives categories readable names', () => {
    expect(formatCategory('FOOD_DINING')).toBe('Food & dining');
  });

  it('falls back gracefully for an unknown category', () => {
    // A category added to the backend enum must not crash the dashboard.
    expect(formatCategory('CRYPTO_MINING')).toBe('crypto mining');
  });

  it('gives habits readable names', () => {
    expect(formatHabit('sleep_minutes')).toBe('Sleep');
    expect(formatHabit('home_cooked_meals')).toBe('Home-cooked meals');
  });

  it('formats a month key', () => {
    expect(formatMonth('2026-07')).toBe('July 2026');
  });

  it('formats an ISO date', () => {
    expect(formatDayLong('2026-07-28')).toContain('2026');
  });

  it('returns an unparseable date unchanged rather than showing Invalid Date', () => {
    expect(formatDayLong('not-a-date')).toBe('not-a-date');
  });
});

describe('pluralise', () => {
  it('uses the singular for one', () => {
    expect(pluralise(1, 'day')).toBe('1 day');
  });

  it('uses the plural otherwise', () => {
    expect(pluralise(0, 'day')).toBe('0 days');
    expect(pluralise(7, 'day')).toBe('7 days');
  });
});
