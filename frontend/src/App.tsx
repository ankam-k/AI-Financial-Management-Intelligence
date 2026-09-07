/**
 * Shell, navigation, and the session gate.
 *
 * The app has four top-level states, decided by the auth context: while the
 * session is resolving it shows a quiet placeholder; with no session it shows
 * the public Landing page (from which the visitor moves to sign in / sign up);
 * signed in but not yet onboarded it shows onboarding; and signed in and
 * onboarded it shows the app itself.
 *
 * The signed-in app uses the "Organic" shell: a fixed sidebar on desktop, and a
 * top bar + bottom tab bar (with a centre add-a-record sheet) on mobile. The
 * window and narration-source controls scope only the views that read an
 * analysis window (Overview, Insights, Explore), so they are shown there and
 * hidden elsewhere. Evidence is a drill-down reached from an insight, not a nav
 * destination.
 *
 * AI availability is fetched once here and handed down: the model is optional,
 * so its absence is surfaced as a calm banner on the analysis views rather than
 * as an error (constraint 7).
 */

import { useCallback, useEffect, useState } from 'react';
import { getLLMStatus } from './api/endpoints';
import type { Insight } from './api/types';
import { resolveAiAvailability } from './components/AiStatusBanner';
import { useAsync } from './hooks/useAsync';
import { useAuth } from './hooks/useAuth';
import { useTheme, type ThemeChoice } from './hooks/useTheme';
import { Auth } from './pages/Auth';
import { CheckIn } from './pages/CheckIn';
import { Chat } from './pages/Chat';
import { Dashboard } from './pages/Dashboard';
import { Evidence } from './pages/Evidence';
import { Expenses } from './pages/Expenses';
import { History } from './pages/History';
import { Insights } from './pages/Insights';
import { Landing } from './pages/Landing';
import { LifeEvents } from './pages/LifeEvents';
import { Onboarding } from './pages/Onboarding';
import { Settings } from './pages/Settings';

type View =
  | 'overview'
  | 'expenses'
  | 'checkin'
  | 'events'
  | 'history'
  | 'insights'
  | 'explore'
  | 'settings'
  | 'evidence';

/** SVG path bodies for the nav icons — static markup, no user data. */
const ICONS: Record<string, string> = {
  overview: '<path d="M4 11 12 4l8 7"/><path d="M6 10v9a1 1 0 0 0 1 1h3v-6h4v6h3a1 1 0 0 0 1-1v-9"/>',
  expenses: '<rect x="3" y="7" width="18" height="12" rx="3"/><path d="M3 10h18"/><circle cx="16.5" cy="14.5" r="1"/>',
  checkin: '<rect x="4" y="5" width="16" height="15" rx="3"/><path d="M4 10h16"/><path d="M8 3v4"/><path d="M16 3v4"/><polyline points="9 14 11 16 15 12"/>',
  events: '<path d="M12 21s-7-6.1-7-11a7 7 0 0 1 14 0c0 4.9-7 11-7 11z"/><circle cx="12" cy="10" r="2.5"/>',
  history: '<circle cx="12" cy="12" r="8.5"/><path d="M12 8v4l3 2"/>',
  insights: '<path d="M11.017 2.814a1 1 0 0 1 1.966 0l1.051 5.558a2 2 0 0 0 1.594 1.594l5.558 1.051a1 1 0 0 1 0 1.966l-5.558 1.051a2 2 0 0 0-1.594 1.594l-1.051 5.558a1 1 0 0 1-1.966 0l-1.051-5.558a2 2 0 0 0-1.594-1.594l-5.558-1.051a1 1 0 0 1 0-1.966l5.558-1.051a2 2 0 0 0 1.594-1.594z"/>',
  explore: '<path d="M4 12a8 8 0 1 1 3.2 6.4L4 20l1.2-3.4A7.96 7.96 0 0 1 4 12z"/>',
  settings: '<circle cx="12" cy="12" r="3"/><path d="M12 3v2M12 19v2M4.2 4.2l1.4 1.4M18.4 18.4l1.4 1.4M3 12h2M19 12h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4"/>',
  logout: '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>',
  plus: '<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>',
  theme: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M5 5l1.5 1.5M17.5 17.5 19 19M19 5l-1.5 1.5M6.5 17.5 5 19"/>',
};

function Icon({ name, size = 18 }: { name: keyof typeof ICONS | string; size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      dangerouslySetInnerHTML={{ __html: ICONS[name] ?? '' }}
    />
  );
}

const NAV: { view: View; label: string; icon: string }[] = [
  { view: 'overview', label: 'Overview', icon: 'overview' },
  { view: 'expenses', label: 'Expenses', icon: 'expenses' },
  { view: 'checkin', label: 'Check-in', icon: 'checkin' },
  { view: 'events', label: 'Life & Context', icon: 'events' },
  { view: 'history', label: 'History', icon: 'history' },
  { view: 'insights', label: 'Insights', icon: 'insights' },
  { view: 'explore', label: 'Explore', icon: 'explore' },
];

/** Bottom-bar destinations on mobile; the rest are reached via the add sheet. */
const MOBILE_TABS: { view: View; label: string; icon: string }[] = [
  { view: 'overview', label: 'Overview', icon: 'overview' },
  { view: 'insights', label: 'Insights', icon: 'insights' },
  { view: 'history', label: 'History', icon: 'history' },
  { view: 'explore', label: 'Explore', icon: 'explore' },
];

/** Views that scope to the analysis window and narration source. */
const WINDOWED: ReadonlySet<View> = new Set<View>(['overview', 'insights', 'explore']);

const WINDOWS = [
  { days: 30, label: '30 days' },
  { days: 90, label: '90 days' },
  { days: 180, label: '6 months' },
];

const THEMES: { value: ThemeChoice; label: string }[] = [
  { value: 'system', label: 'Auto' },
  { value: 'light', label: 'Light' },
  { value: 'dark', label: 'Dark' },
];

/**
 * Whether the viewport is at or below the mobile breakpoint. Guards the absence
 * of `matchMedia` (jsdom) by defaulting to the desktop layout, so only one nav
 * is ever in the tree.
 */
function useIsMobile(): boolean {
  const query = '(max-width: 860px)';
  const [isMobile, setIsMobile] = useState(
    () => typeof window !== 'undefined' && !!window.matchMedia && window.matchMedia(query).matches,
  );
  useEffect(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return;
    const mql = window.matchMedia(query);
    const onChange = () => setIsMobile(mql.matches);
    onChange();
    mql.addEventListener('change', onChange);
    return () => mql.removeEventListener('change', onChange);
  }, []);
  return isMobile;
}

export default function App() {
  const { status, needsOnboarding } = useAuth();
  const [anonView, setAnonView] = useState<'landing' | 'auth'>('landing');
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login');

  if (status === 'loading') {
    return (
      <main id="main" className="app-loading" role="status" aria-live="polite">
        <p>Loading…</p>
      </main>
    );
  }

  if (status === 'anon') {
    if (anonView === 'auth') {
      return <Auth initialMode={authMode} onBack={() => setAnonView('landing')} />;
    }
    return (
      <Landing
        onStart={() => {
          setAuthMode('register');
          setAnonView('auth');
        }}
        onSignIn={() => {
          setAuthMode('login');
          setAnonView('auth');
        }}
      />
    );
  }

  if (needsOnboarding) {
    return <Onboarding />;
  }

  return <AppShell />;
}

function AppShell() {
  const { user, logout } = useAuth();
  const isMobile = useIsMobile();
  const [view, setView] = useState<View>('overview');
  const [days, setDays] = useState(90);
  const [generate, setGenerate] = useState(false);
  const [theme, setTheme] = useTheme();
  const [addSheetOpen, setAddSheetOpen] = useState(false);
  const [evidenceInsight, setEvidenceInsight] = useState<Insight | null>(null);

  const llm = useAsync(useCallback((signal) => getLLMStatus(signal), []), []);
  const availability = resolveAiAvailability(llm.data, llm.data?.provider ?? '');

  const go = useCallback((next: View) => {
    setView(next);
    setAddSheetOpen(false);
  }, []);

  const openEvidence = useCallback((insight: Insight) => {
    setEvidenceInsight(insight);
    setView('evidence');
  }, []);

  const cycleTheme = () => {
    const order: ThemeChoice[] = ['system', 'light', 'dark'];
    const next = order[(order.indexOf(theme) + 1) % order.length] ?? 'system';
    setTheme(next);
  };

  const showWindowControls = WINDOWED.has(view);

  const themeControl = (
    <div className="control-group" role="group" aria-label="Colour theme">
      {THEMES.map((option) => (
        <button
          key={option.value}
          type="button"
          aria-pressed={theme === option.value}
          onClick={() => setTheme(option.value)}
        >
          {option.label}
        </button>
      ))}
    </div>
  );

  return (
    <>
      <a className="skip-link" href="#main">
        Skip to content
      </a>

      <div className="app-shell">
        {/* ── Desktop sidebar ─────────────────────────────────────────── */}
        {!isMobile ? (
        <aside className="sidebar" aria-label="Primary">
          <div className="sidebar__brand">Financial Intelligence</div>
          {user?.is_demo ? (
            <span className="account__badge" style={{ margin: '0 10px 12px', alignSelf: 'flex-start' }}>
              Demo
            </span>
          ) : null}
          <nav aria-label="Sections" style={{ display: 'grid', gap: 2 }}>
            {NAV.map((item) => (
              <button
                key={item.view}
                type="button"
                className="sidebar__link"
                aria-current={view === item.view ? 'page' : undefined}
                onClick={() => go(item.view)}
              >
                <Icon name={item.icon} />
                {item.label}
              </button>
            ))}
          </nav>
          <div className="sidebar__spacer" />
          <div className="sidebar__footer">
            {themeControl}
            <button
              type="button"
              className="sidebar__link"
              aria-current={view === 'settings' ? 'page' : undefined}
              onClick={() => go('settings')}
            >
              <Icon name="settings" />
              Settings
            </button>
            <button type="button" className="sidebar__link" onClick={() => logout()}>
              <Icon name="logout" />
              Sign out
            </button>
          </div>
        </aside>
        ) : null}

        {/* ── Mobile top bar ──────────────────────────────────────────── */}
        {isMobile ? (
        <div className="mobile-topbar">
          <span className="mobile-topbar__brand">Financial Intelligence</span>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <button
              type="button"
              className="mobile-tab"
              onClick={cycleTheme}
              aria-label={`Theme: ${theme}. Tap to change.`}
            >
              <Icon name="theme" size={21} />
            </button>
            <button
              type="button"
              className="mobile-tab"
              aria-label="Settings"
              aria-current={view === 'settings' ? 'page' : undefined}
              onClick={() => go('settings')}
            >
              <Icon name="settings" size={21} />
            </button>
          </div>
        </div>
        ) : null}

        <main className="app-main" id="main">
          <div className="app-main__inner">
            {user?.is_demo ? (
              <p className="demo-banner" role="status">
                You’re exploring a sample profile. <strong>Sign out</strong> to create your own
                account — it starts empty and is entirely separate from this demo.
              </p>
            ) : null}

            {showWindowControls ? (
              <div className="controls">
                <div className="control-group" role="group" aria-label="Analysis window">
                  {WINDOWS.map((option) => (
                    <button
                      key={option.days}
                      type="button"
                      aria-pressed={days === option.days}
                      onClick={() => setDays(option.days)}
                    >
                      {option.label}
                    </button>
                  ))}
                </div>

                <div className="control-group" role="group" aria-label="Narration source">
                  <button type="button" aria-pressed={!generate} onClick={() => setGenerate(false)}>
                    Template
                  </button>
                  <button
                    type="button"
                    aria-pressed={generate}
                    onClick={() => setGenerate(true)}
                    title="Ask the local model to write these. Slower — roughly 18s per insight."
                  >
                    AI-written
                  </button>
                </div>
              </div>
            ) : null}

            {view === 'overview' ? (
              <Dashboard
                days={days}
                generate={generate}
                availability={availability}
                onOpenInsights={() => go('insights')}
              />
            ) : view === 'insights' ? (
              <Insights
                days={days}
                generate={generate}
                availability={availability}
                onOpenEvidence={openEvidence}
              />
            ) : view === 'expenses' ? (
              <Expenses />
            ) : view === 'checkin' ? (
              <CheckIn />
            ) : view === 'events' ? (
              <LifeEvents />
            ) : view === 'history' ? (
              <History />
            ) : view === 'explore' ? (
              <Chat days={days} generate={generate} />
            ) : view === 'evidence' ? (
              <Evidence insight={evidenceInsight} onBack={() => go('insights')} />
            ) : (
              <Settings />
            )}
          </div>
        </main>

        {/* ── Mobile bottom tab bar + add-a-record FAB ────────────────── */}
        {isMobile ? (
        <nav className="mobile-tabbar" aria-label="Sections">
          {MOBILE_TABS.slice(0, 2).map((item) => (
            <button
              key={item.view}
              type="button"
              className="mobile-tab"
              aria-current={view === item.view ? 'page' : undefined}
              onClick={() => go(item.view)}
            >
              <Icon name={item.icon} size={21} />
              {item.label}
            </button>
          ))}
          <button
            type="button"
            className="fab"
            aria-label="Add a record"
            onClick={() => setAddSheetOpen(true)}
          >
            <Icon name="plus" size={24} />
          </button>
          {MOBILE_TABS.slice(2).map((item) => (
            <button
              key={item.view}
              type="button"
              className="mobile-tab"
              aria-current={view === item.view ? 'page' : undefined}
              onClick={() => go(item.view)}
            >
              <Icon name={item.icon} size={21} />
              {item.label}
            </button>
          ))}
        </nav>
        ) : null}
      </div>

      {isMobile && addSheetOpen ? (
        <div
          className="add-sheet__backdrop"
          role="presentation"
          onClick={() => setAddSheetOpen(false)}
        >
          <div
            className="add-sheet"
            role="dialog"
            aria-label="Add a record"
            onClick={(event) => event.stopPropagation()}
          >
            <p className="add-sheet__title">Add a record</p>
            <button type="button" className="add-sheet__item" onClick={() => go('expenses')}>
              <Icon name="expenses" size={16} />
              Add expense
            </button>
            <button type="button" className="add-sheet__item" onClick={() => go('checkin')}>
              <Icon name="checkin" size={16} />
              Daily check-in
            </button>
            <button type="button" className="add-sheet__item" onClick={() => go('events')}>
              <Icon name="events" size={16} />
              Add life &amp; context
            </button>
            <button
              type="button"
              className="btn btn--ghost"
              style={{ marginTop: 4 }}
              onClick={() => setAddSheetOpen(false)}
            >
              Cancel
            </button>
          </div>
        </div>
      ) : null}
    </>
  );
}
