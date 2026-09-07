import { describe, expect, it } from 'vitest';
import { MoneyParseError, rupeesToPaise } from './money';

describe('rupeesToPaise', () => {
  it('converts whole rupees to paise', () => {
    expect(rupeesToPaise('450')).toBe(45_000);
  });

  it('converts rupees and paise without floating-point drift', () => {
    // 19.99 * 100 in float is 1998.9999999999998; the string split avoids it.
    expect(rupeesToPaise('19.99')).toBe(1999);
    expect(rupeesToPaise('450.50')).toBe(45_050);
    expect(rupeesToPaise('450.5')).toBe(45_050);
    expect(rupeesToPaise('0.05')).toBe(5);
  });

  it('strips rupee signs, commas and spaces', () => {
    expect(rupeesToPaise('₹1,299.99')).toBe(129_999);
  });

  it('rejects a blank amount', () => {
    expect(() => rupeesToPaise('')).toThrow(MoneyParseError);
  });

  it('rejects more than two decimal places', () => {
    expect(() => rupeesToPaise('10.999')).toThrow(MoneyParseError);
  });

  it('rejects non-numeric input', () => {
    expect(() => rupeesToPaise('abc')).toThrow(MoneyParseError);
  });
});
