/**
 * Life events — context around spending, never a cause of it.
 *
 * The language here is deliberately neutral (constraint 5): an event is
 * something to annotate so the analysis can describe spending around it
 * separately, not an explanation the UI asserts. The form validates what the
 * backend validates — a title, and an end date no earlier than the start — and
 * surfaces the backend's own message for anything else.
 */

import { useCallback, useState } from 'react';
import { createLifeEvent, deleteLifeEvent, listLifeEvents } from '../api/endpoints';
import type { EventType, LifeEventRead } from '../api/types';
import { Card } from '../components/Card';
import { Field, FormStatus, SelectInput, TextInput } from '../components/forms/Fields';
import { EmptyState, ErrorState, SkeletonCard } from '../components/StateViews';
import { useAsync } from '../hooks/useAsync';
import { useMutation } from '../hooks/useMutation';
import { EVENT_TYPE_OPTIONS, todayIso } from '../lib/enums';
import { formatDayLong, formatEventType } from '../lib/format';

function eventRange(event: LifeEventRead): string {
  if (!event.end_date || event.end_date === event.start_date) return formatDayLong(event.start_date);
  return `${formatDayLong(event.start_date)} – ${formatDayLong(event.end_date)}`;
}

export function LifeEvents() {
  const list = useAsync(useCallback((signal) => listLifeEvents(signal), []), []);

  const [type, setType] = useState<EventType>('TRAVEL');
  const [title, setTitle] = useState('');
  const [startDate, setStartDate] = useState(todayIso());
  const [endDate, setEndDate] = useState('');
  const [notes, setNotes] = useState('');
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [confirmation, setConfirmation] = useState<string | null>(null);

  const create = useMutation(createLifeEvent);
  const remove = useMutation(deleteLifeEvent);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setFieldError(null);
    setConfirmation(null);

    if (!title.trim()) {
      setFieldError('Give the event a title.');
      return;
    }
    if (!startDate) {
      setFieldError('Choose a start date.');
      return;
    }
    if (endDate && endDate < startDate) {
      setFieldError('The end date cannot be before the start date.');
      return;
    }

    const created = await create.mutate({
      event_type: type,
      title: title.trim(),
      start_date: startDate,
      end_date: endDate || null,
      notes: notes.trim() || null,
    });

    if (created) {
      setTitle('');
      setEndDate('');
      setNotes('');
      setConfirmation('Event annotated.');
      list.refetch();
    }
  };

  const onDelete = async (event: LifeEventRead) => {
    const done = await remove.mutate(event.id);
    if (done !== null) {
      setConfirmation('Event deleted.');
      list.refetch();
    }
  };

  const events = list.data ?? [];

  return (
    <div className="grid">
      <header className="topbar span-12">
        <div>
          <h1 className="topbar__title">Life events</h1>
          <p className="topbar__subtitle">
            Annotate travel, illness or a move. This is context for the analysis — an event is never
            described as causing your spending.
          </p>
        </div>
      </header>

      <div className="span-5">
        <Card title="Annotate an event">
          <form className="form" onSubmit={submit} noValidate>
            <Field label="Type">
              {(id, describedBy) => (
                <SelectInput
                  id={id}
                  describedBy={describedBy}
                  value={type}
                  options={EVENT_TYPE_OPTIONS}
                  onChange={setType}
                />
              )}
            </Field>

            <Field label="Title" error={fieldError ?? undefined}>
              {(id, describedBy) => (
                <TextInput
                  id={id}
                  describedBy={describedBy}
                  value={title}
                  onChange={setTitle}
                  maxLength={200}
                  placeholder="e.g. Goa trip"
                />
              )}
            </Field>

            <Field label="Start date">
              {(id, describedBy) => (
                <TextInput id={id} describedBy={describedBy} value={startDate} onChange={setStartDate} type="date" />
              )}
            </Field>

            <Field label="End date (optional)" hint="Leave blank for a single-day event.">
              {(id, describedBy) => (
                <TextInput
                  id={id}
                  describedBy={describedBy}
                  value={endDate}
                  onChange={setEndDate}
                  type="date"
                  min={startDate}
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
                {create.isSubmitting ? 'Saving…' : 'Annotate event'}
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
        <Card title="Timeline" hint={events.length ? `${events.length} events` : undefined}>
          {list.error ? (
            <ErrorState error={list.error} onRetry={list.refetch} />
          ) : list.isLoading ? (
            <SkeletonCard height={160} />
          ) : events.length === 0 ? (
            <EmptyState
              title="No events annotated yet"
              detail="Annotating travel, illness or a relocation lets the analysis report spending around them separately, instead of leaving you to guess what a spike was."
            />
          ) : (
            <ul className="timeline">
              {events.map((event) => (
                <li className="timeline__item" key={event.id}>
                  <span className="timeline__marker" aria-hidden="true" />
                  <div className="timeline__head">
                    <span className="timeline__title">{event.title}</span>
                    <button
                      type="button"
                      className="btn btn--ghost btn--small"
                      onClick={() => onDelete(event)}
                      disabled={remove.isSubmitting}
                      aria-label={`Delete ${event.title}`}
                    >
                      Delete
                    </button>
                  </div>
                  <p className="timeline__meta">
                    {formatEventType(event.event_type)} · {eventRange(event)}
                    {event.notes ? ` · ${event.notes}` : ''}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </div>
  );
}
