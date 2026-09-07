/**
 * Recording expenses, and reviewing what was recorded.
 *
 * The amount is entered in rupees and converted to integer paise by
 * `rupeesToPaise` — a string split, never a float multiply — because money that
 * drifts by a paise is money the analysis can no longer trust (constraint 2).
 * Everything shown in the list is a value the backend returned; the form sends,
 * the list reads, and neither computes.
 */

import { useCallback, useState } from 'react';
import { createExpense, deleteExpense, listExpenses } from '../api/endpoints';
import type { Category, ExpenseRead, PaymentMethod } from '../api/types';
import { Card } from '../components/Card';
import { Field, FormStatus, SelectInput, TextInput } from '../components/forms/Fields';
import { EmptyState, ErrorState, SkeletonCard } from '../components/StateViews';
import { useAsync } from '../hooks/useAsync';
import { useMutation } from '../hooks/useMutation';
import { CATEGORY_OPTIONS, PAYMENT_METHOD_OPTIONS, todayIso } from '../lib/enums';
import { formatCategory, formatDayLong, formatPaise } from '../lib/format';
import { MoneyParseError, rupeesToPaise } from '../lib/money';

export function Expenses() {
  const list = useAsync(useCallback((signal) => listExpenses({ limit: 50 }, signal), []), []);

  const [amount, setAmount] = useState('');
  const [category, setCategory] = useState<Category>('FOOD_DINING');
  const [method, setMethod] = useState<PaymentMethod>('UPI');
  const [date, setDate] = useState(todayIso());
  const [merchant, setMerchant] = useState('');
  const [notes, setNotes] = useState('');
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [confirmation, setConfirmation] = useState<string | null>(null);

  const create = useMutation(createExpense);
  const remove = useMutation(deleteExpense);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setFieldError(null);
    setConfirmation(null);

    if (!date) {
      setFieldError('Choose a date.');
      return;
    }

    let paise: number;
    try {
      paise = rupeesToPaise(amount);
    } catch (cause) {
      setFieldError(cause instanceof MoneyParseError ? cause.message : 'Enter a valid amount.');
      return;
    }
    if (paise <= 0) {
      setFieldError('Amount must be greater than zero.');
      return;
    }

    const created = await create.mutate({
      expense_date: date,
      amount_paise: paise,
      category,
      payment_method: method,
      merchant: merchant.trim() || null,
      notes: notes.trim() || null,
    });

    if (created) {
      setAmount('');
      setMerchant('');
      setNotes('');
      setConfirmation(`Recorded ${formatPaise(paise)} in ${formatCategory(category)}.`);
      list.refetch();
    }
  };

  const onDelete = async (expense: ExpenseRead) => {
    const done = await remove.mutate(expense.id);
    if (done !== null) {
      setConfirmation('Expense deleted.');
      list.refetch();
    }
  };

  const expenses = list.data ?? [];

  return (
    <div className="grid">
      <header className="topbar span-12">
        <div>
          <h1 className="topbar__title">Expenses</h1>
          <p className="topbar__subtitle">
            Record what you spent. Amounts are stored exactly, to the paise.
          </p>
        </div>
      </header>

      <div className="span-5">
        <Card title="Add expense">
          <form className="form" onSubmit={submit} noValidate>
            <Field
              label="Amount (₹)"
              hint="Rupees and paise, e.g. 450.00. Stored as exact paise."
              error={fieldError ?? undefined}
            >
              {(id, describedBy) => (
                <TextInput
                  id={id}
                  describedBy={describedBy}
                  value={amount}
                  onChange={setAmount}
                  inputMode="decimal"
                  placeholder="0.00"
                />
              )}
            </Field>

            <Field label="Category">
              {(id, describedBy) => (
                <SelectInput
                  id={id}
                  describedBy={describedBy}
                  value={category}
                  options={CATEGORY_OPTIONS}
                  onChange={setCategory}
                />
              )}
            </Field>

            <Field label="Payment method">
              {(id, describedBy) => (
                <SelectInput
                  id={id}
                  describedBy={describedBy}
                  value={method}
                  options={PAYMENT_METHOD_OPTIONS}
                  onChange={setMethod}
                />
              )}
            </Field>

            <Field label="Date">
              {(id, describedBy) => (
                <TextInput id={id} describedBy={describedBy} value={date} onChange={setDate} type="date" />
              )}
            </Field>

            <Field label="Merchant (optional)">
              {(id, describedBy) => (
                <TextInput
                  id={id}
                  describedBy={describedBy}
                  value={merchant}
                  onChange={setMerchant}
                  maxLength={200}
                  placeholder="e.g. Blue Tokai"
                />
              )}
            </Field>

            <Field label="Notes (optional)">
              {(id, describedBy) => (
                <TextInput id={id} describedBy={describedBy} value={notes} onChange={setNotes} />
              )}
            </Field>

            <div className="form__actions">
              <button type="submit" className="btn btn--primary" disabled={create.isSubmitting}>
                {create.isSubmitting ? 'Saving…' : 'Add expense'}
              </button>
              <FormStatus
                error={create.status === 'error' ? create.error?.message : null}
                success={confirmation}
              />
            </div>
          </form>
        </Card>
      </div>

      <div className="span-7">
        <Card title="Recent expenses" hint={expenses.length ? `${expenses.length} shown` : undefined}>
          {list.error ? (
            <ErrorState error={list.error} onRetry={list.refetch} />
          ) : list.isLoading ? (
            <SkeletonCard height={200} />
          ) : expenses.length === 0 ? (
            <EmptyState
              title="Record your first expense"
              detail="Nothing is recorded yet. Add one on the left and it will appear here, and feed the analysis."
            />
          ) : (
            <div className="table-scroll">
              <table className="data-table">
                <caption className="visually-hidden">Recent expenses</caption>
                <thead>
                  <tr>
                    <th scope="col">Date</th>
                    <th scope="col">Category</th>
                    <th scope="col">Merchant</th>
                    <th scope="col" className="numeric">
                      Amount
                    </th>
                    <th scope="col">
                      <span className="visually-hidden">Actions</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {expenses.map((expense) => (
                    <tr key={expense.id}>
                      <td>{formatDayLong(expense.expense_date)}</td>
                      <td>{formatCategory(expense.category)}</td>
                      <td>{expense.merchant ?? '—'}</td>
                      <td className="numeric">{formatPaise(expense.amount_paise)}</td>
                      <td>
                        <button
                          type="button"
                          className="btn btn--ghost btn--small"
                          onClick={() => onDelete(expense)}
                          disabled={remove.isSubmitting}
                          aria-label={`Delete expense ${formatPaise(expense.amount_paise)} on ${expense.expense_date}`}
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <p className="field__hint" style={{ marginTop: 10 }}>
            Transfers and income are recorded, but excluded from spending analysis — moving your own
            money is not consumption.
          </p>
        </Card>
      </div>
    </div>
  );
}
