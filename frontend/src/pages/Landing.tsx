/**
 * The public landing page.
 *
 * Shown before there is a session. It is pure marketing — no data, no backend
 * calls — and its two calls to action hand control back to `App`, which swaps in
 * the auth screen on the right tab. The copy keeps the product's evidence-first
 * promise: an account starts empty, and the app describes only what you record.
 */

function Check() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2.75}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <polyline points="20 6 9 17 4 12" />
    </svg>
  );
}

const LOOP = [
  { n: '1', title: 'Record', body: 'Log expenses, a ten-second daily check-in, and the life events around them.' },
  { n: '2', title: 'Build history', body: 'Your entries become a timeline — the only thing the analysis ever reads.' },
  { n: '3', title: 'Analyse', body: 'The engine tests patterns statistically and suppresses what does not clear the bar.' },
  { n: '4', title: 'Understand', body: 'Each validated finding arrives with the evidence behind it, in plain language.' },
];

const MODULES = [
  { title: 'Expenses', body: 'Every spend, categorised, in rupees down to the paise.' },
  { title: 'Check-in', body: 'Sleep, exercise, meals, stress and work mode — recorded, never assumed.' },
  { title: 'Life & Context', body: 'Travel, moves, exams and more, as context around your spending.' },
  { title: 'History', body: 'One chronological stream of everything you have entered.' },
  { title: 'Insights', body: 'Behavioural relationships, validated and evidence-backed.' },
  { title: 'Explore', body: 'Ask about your recorded history in plain language.' },
];

export function Landing({ onStart, onSignIn }: { onStart: () => void; onSignIn: () => void }) {
  return (
    <div className="landing">
      <nav className="landing__nav">
        <span className="landing__brand">Financial Intelligence</span>
        <a href="#how">How it works</a>
        <a href="#principles">Principles</a>
        <button type="button" className="link" onClick={onSignIn}>
          Sign in
        </button>
        <button type="button" className="btn btn--primary" onClick={onStart}>
          Start tracking
        </button>
      </nav>

      <header className="landing__hero">
        <h1>Understand your financial behaviour — with the evidence.</h1>
        <p>
          A private, explainable view of how you spend and live. It analyses only what you record,
          shows its working for every claim, and never guesses in the meantime.
        </p>
        <div className="landing__cta-row">
          <button type="button" className="btn btn--primary" onClick={onStart}>
            Start tracking
          </button>
          <button type="button" className="btn btn--ghost" onClick={onSignIn}>
            I already have an account
          </button>
        </div>
      </header>

      <section className="landing__section" id="how">
        <h2 className="landing__section-title">The loop</h2>
        <p className="landing__section-lead">
          Record what happens, and the app turns it into understanding — in that order, never before.
        </p>
        <div className="landing__grid">
          {LOOP.map((step) => (
            <div className="card elev-sm" key={step.n}>
              <div className="landing__step-num">{step.n}</div>
              <h3 className="card__title" style={{ fontSize: 17, color: 'var(--text-primary)' }}>
                {step.title}
              </h3>
              <p className="card__body">{step.body}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="landing__section" id="principles">
        <h2 className="landing__section-title">Principles</h2>
        <p className="landing__section-lead">
          The rules that keep it honest — the same ones that shaped the engine underneath.
        </p>
        <div className="landing__principles">
          <div className="card">
            <div className="landing__check">
              <Check />
              <span>Your account starts empty. No demo dashboard, no sample figures dressed up as yours.</span>
            </div>
            <div className="landing__check">
              <Check />
              <span>Every claim shows its evidence — the records, the comparison and the test behind it.</span>
            </div>
            <div className="landing__check">
              <Check />
              <span>Associations are labelled as associations, never causation and never a prediction.</span>
            </div>
          </div>
          <div className="card">
            <div className="landing__check">
              <Check />
              <span>Nothing is computed on the page; the analysis engine produces every number.</span>
            </div>
            <div className="landing__check">
              <Check />
              <span>When there isn’t enough history yet, it says so plainly instead of inventing a pattern.</span>
            </div>
            <div className="landing__check">
              <Check />
              <span>Your data is yours — scoped to your account and separate from everyone else’s.</span>
            </div>
          </div>
        </div>
      </section>

      <section className="landing__section">
        <h2 className="landing__section-title">Six modules, one history</h2>
        <p className="landing__section-lead">
          Each one adds to the same timeline the analysis reads from.
        </p>
        <div className="landing__grid">
          {MODULES.map((module) => (
            <div className="card elev-sm" key={module.title}>
              <h3 className="card__title" style={{ fontSize: 16, color: 'var(--text-primary)' }}>
                {module.title}
              </h3>
              <p className="card__body">{module.body}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="landing__section" style={{ textAlign: 'center' }}>
        <h2 className="landing__section-title">Your history starts here.</h2>
        <p className="landing__section-lead">It begins empty. What you record is what it reads.</p>
        <div className="landing__cta-row">
          <button type="button" className="btn btn--primary" onClick={onStart}>
            Create your account
          </button>
        </div>
      </section>

      <footer className="landing__footer">
        Financial Intelligence · An explainable, evidence-first view of your money and habits.
      </footer>
    </div>
  );
}
