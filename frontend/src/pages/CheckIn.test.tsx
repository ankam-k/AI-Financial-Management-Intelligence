/**
 * The check-in form's three-state contract: an explicit "No" is a recorded
 * `false`; "Unknown" is omitted entirely and never coerced into a `false`.
 */

import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it } from 'vitest';
import { CheckIn } from './CheckIn';
import type { CheckInRead } from '../api/types';
import { todayIso } from '../lib/enums';
import { stubServer } from '../test/server';

beforeEach(() => localStorage.clear());

function createBody(server: ReturnType<typeof stubServer>) {
  return server.requests.find((r) => r.method === 'POST' && r.url.includes('/api/check-ins'))?.body;
}

function patchBody(server: ReturnType<typeof stubServer>) {
  return server.requests.find((r) => r.method === 'PATCH' && r.url.includes('/api/check-ins'))?.body;
}

/** A recorded check-in for *today*, so the page opens in edit mode over it. */
function existingToday(): CheckInRead {
  return {
    log_date: todayIso(),
    sleep_hours: 7, // a stored numeric
    exercise: true, // a stored TRUE
    home_cooked_meals: 2,
    stress_level: 4,
    alcohol: false, // a stored FALSE (recorded negative)
    work_mode: null, // a genuine UNKNOWN
    created_at: '',
    updated_at: '',
  };
}

async function ready() {
  await waitFor(() => expect(screen.getByText('Log a day')).toBeInTheDocument());
}

async function editReady() {
  await waitFor(() =>
    expect(screen.getByRole('button', { name: 'Update check-in' })).toBeEnabled(),
  );
}

function pressed(groupName: string | RegExp, optionName: string) {
  return within(screen.getByRole('group', { name: groupName })).getByRole('button', {
    name: optionName,
  });
}

describe('three-state habits', () => {
  it('sends an explicit No as false, and omits an Unknown field entirely', async () => {
    const server = stubServer({ checkIns: [] });
    render(<CheckIn />);
    await ready();

    // Exercise → No (a recorded negative). Alcohol is left Unknown (untouched).
    await userEvent.click(
      within(screen.getByRole('group', { name: 'Exercise' })).getByRole('button', { name: 'No' }),
    );
    await userEvent.click(screen.getByRole('button', { name: 'Save check-in' }));

    await waitFor(() => expect(createBody(server)).toBeTruthy());
    const body = createBody(server)!;
    expect(body.exercise).toBe(false);
    // Unknown is not sent — never turned into a false.
    expect('alcohol' in body).toBe(false);
    expect('stress_level' in body).toBe(false);
    expect('work_mode' in body).toBe(false);
  });

  it('sends a recorded "None" of zero home-cooked meals', async () => {
    const server = stubServer({ checkIns: [] });
    render(<CheckIn />);
    await ready();

    await userEvent.click(
      within(screen.getByRole('group', { name: 'Home-cooked meals' })).getByRole('button', {
        name: '0',
      }),
    );
    await userEvent.click(screen.getByRole('button', { name: 'Save check-in' }));

    await waitFor(() => expect(createBody(server)).toBeTruthy());
    expect(createBody(server)!.home_cooked_meals).toBe(0);
  });

  it('refuses to submit an all-Unknown check-in', async () => {
    const server = stubServer({ checkIns: [] });
    render(<CheckIn />);
    await ready();

    await userEvent.click(screen.getByRole('button', { name: 'Save check-in' }));

    expect(screen.getByText(/Log at least one habit/)).toBeInTheDocument();
    expect(createBody(server)).toBeUndefined();
  });

  it('explains that Unknown is not No', async () => {
    stubServer({ checkIns: [] });
    render(<CheckIn />);
    await ready();

    expect(screen.getByText(/Unknown is not No/)).toBeInTheDocument();
  });
});

describe('editing an existing check-in — never silently wipes (regression)', () => {
  it('populates every stored value on load: TRUE, FALSE, UNKNOWN, sleep, stress', async () => {
    stubServer({ checkIns: [existingToday()] });
    render(<CheckIn />);
    await editReady();

    expect(pressed('Exercise', 'Yes')).toHaveAttribute('aria-pressed', 'true'); // TRUE
    expect(pressed('Alcohol', 'No')).toHaveAttribute('aria-pressed', 'true'); // FALSE
    expect(pressed('Home-cooked meals', '2')).toHaveAttribute('aria-pressed', 'true');
    expect(pressed(/Stress level/, '4')).toHaveAttribute('aria-pressed', 'true');
    expect(pressed('Work mode', 'Unknown')).toHaveAttribute('aria-pressed', 'true'); // UNKNOWN
    expect(screen.getByLabelText('Sleep (hours)')).toHaveValue('7');
  });

  it('⭐ pressing Update immediately after load sends the STORED values, not nulls', async () => {
    // This is the exact bug: before the fix the form was blank on load, so an
    // immediate Update PATCHed every habit to null and erased the day.
    const server = stubServer({ checkIns: [existingToday()] });
    render(<CheckIn />);
    await editReady();

    await userEvent.click(screen.getByRole('button', { name: 'Update check-in' }));

    await waitFor(() => expect(patchBody(server)).toBeTruthy());
    expect(patchBody(server)).toMatchObject({
      exercise: true,
      alcohol: false,
      home_cooked_meals: 2,
      stress_level: 4,
      sleep_hours: 7,
      work_mode: null,
    });
  });

  it('changing one field leaves every other stored value unchanged', async () => {
    const server = stubServer({ checkIns: [existingToday()] });
    render(<CheckIn />);
    await editReady();

    await userEvent.click(pressed('Exercise', 'No')); // TRUE → FALSE
    await userEvent.click(screen.getByRole('button', { name: 'Update check-in' }));

    await waitFor(() => expect(patchBody(server)).toBeTruthy());
    const body = patchBody(server)!;
    expect(body.exercise).toBe(false); // the one change
    expect(body.alcohol).toBe(false); // untouched
    expect(body.home_cooked_meals).toBe(2);
    expect(body.stress_level).toBe(4);
    expect(body.sleep_hours).toBe(7);
  });

  it('can still intentionally record a field as Unknown', async () => {
    const server = stubServer({ checkIns: [existingToday()] });
    render(<CheckIn />);
    await editReady();

    // Exercise was TRUE; the user deliberately sets it back to Unknown.
    await userEvent.click(pressed('Exercise', 'Unknown'));
    await userEvent.click(screen.getByRole('button', { name: 'Update check-in' }));

    await waitFor(() => expect(patchBody(server)).toBeTruthy());
    const body = patchBody(server)!;
    expect(body.exercise).toBeNull(); // Unknown → null on an edit (API semantics)
    expect(body.alcohol).toBe(false); // other values intact
  });
});

describe('recent check-ins list is capped', () => {
  it('renders at most 50 rows and reports the true total', async () => {
    const many: CheckInRead[] = Array.from({ length: 60 }, (_, i) => ({
      // Unique, non-today dates spread across three months.
      log_date: `2026-0${1 + Math.floor(i / 28)}-${String((i % 28) + 1).padStart(2, '0')}`,
      sleep_hours: 7,
      exercise: true,
      home_cooked_meals: null,
      stress_level: null,
      alcohol: null,
      work_mode: null,
      created_at: '',
      updated_at: '',
    }));
    stubServer({ checkIns: many });
    render(<CheckIn />);
    await ready();

    await waitFor(() => expect(screen.getByText('50 of 60')).toBeInTheDocument());
    expect(screen.getAllByRole('button', { name: /Delete check-in for/ })).toHaveLength(50);
  });
});
