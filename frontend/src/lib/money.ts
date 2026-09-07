/**
 * Parsing a rupee string into integer paise — the inbound direction that
 * `format.ts` never covers.
 *
 * The one rule that matters: **no floating point.** `parseFloat('19.99') * 100`
 * is `1998.9999999999998`, and a `Math.round` over it is a coin-flip on the
 * boundary. So the string is split on the decimal point and each side is parsed
 * as an integer, then combined as integer paise. `₹` signs, spaces and grouping
 * commas are stripped first; everything else is a validation error.
 */

export class MoneyParseError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'MoneyParseError';
  }
}

/**
 * `"450"` → `45000`, `"450.5"` → `45050`, `"₹1,299.99"` → `129999`.
 *
 * Throws `MoneyParseError` for anything that is not a non-negative amount with
 * at most two decimal places. The caller surfaces the message inline.
 */
export function rupeesToPaise(input: string): number {
  const cleaned = input.replace(/[₹,\s]/g, '');
  if (cleaned === '' || cleaned === '.') {
    throw new MoneyParseError('Enter an amount.');
  }
  if (!/^\d*(\.\d*)?$/.test(cleaned)) {
    throw new MoneyParseError('Enter a plain number, e.g. 450.00.');
  }

  const [whole, frac = ''] = cleaned.split('.');
  if (frac.length > 2) {
    throw new MoneyParseError('Rupees have at most two decimal places.');
  }

  // Pad the fractional part to exactly two digits, then parse each side as an
  // integer. `"5"` → paise `50`, `"05"` → `5`, `""` → `0`.
  const fracPaise = Number.parseInt(((frac ?? '') + '00').slice(0, 2), 10);
  const wholePaise = (whole ? Number.parseInt(whole, 10) : 0) * 100;
  const paise = wholePaise + fracPaise;

  if (!Number.isSafeInteger(paise)) {
    throw new MoneyParseError('That amount is too large.');
  }
  return paise;
}
