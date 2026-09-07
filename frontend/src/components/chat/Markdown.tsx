/**
 * A small, safe Markdown renderer.
 *
 * Deliberately not `react-markdown` + `remark`: that is ~120 KB to render the
 * four constructs the chat prompt permits — paragraphs, `**bold**`, `` `code` ``
 * and `- ` bullets. Anything else the model emits is shown as plain text,
 * which is the correct outcome for a renderer whose input is generated.
 *
 * It never touches `dangerouslySetInnerHTML`, so there is no HTML-injection
 * surface at all — the output is React elements built from parsed text, and a
 * `<script>` in a model's answer renders as the literal characters.
 */

import type { ReactNode } from 'react';

const INLINE = /(\*\*[^*]+\*\*|`[^`]+`|\*[^*]+\*)/g;

function renderInline(text: string, keyPrefix: string): ReactNode[] {
  return text.split(INLINE).filter(Boolean).map((token, index) => {
    const key = `${keyPrefix}-${index}`;
    if (token.startsWith('**') && token.endsWith('**') && token.length > 4) {
      return <strong key={key}>{token.slice(2, -2)}</strong>;
    }
    if (token.startsWith('`') && token.endsWith('`') && token.length > 2) {
      return <code key={key}>{token.slice(1, -1)}</code>;
    }
    if (token.startsWith('*') && token.endsWith('*') && token.length > 2) {
      return <em key={key}>{token.slice(1, -1)}</em>;
    }
    return <span key={key}>{token}</span>;
  });
}

export function Markdown({ text }: { text: string }) {
  const lines = text.split('\n');
  const blocks: ReactNode[] = [];
  let paragraph: string[] = [];
  let bullets: string[] = [];

  const flushParagraph = () => {
    if (paragraph.length === 0) return;
    const key = `p-${blocks.length}`;
    blocks.push(<p key={key}>{renderInline(paragraph.join(' '), key)}</p>);
    paragraph = [];
  };

  const flushBullets = () => {
    if (bullets.length === 0) return;
    const key = `ul-${blocks.length}`;
    blocks.push(
      <ul key={key}>
        {bullets.map((item, index) => (
          <li key={`${key}-${index}`}>{renderInline(item, `${key}-${index}`)}</li>
        ))}
      </ul>,
    );
    bullets = [];
  };

  for (const line of lines) {
    const trimmed = line.trim();
    if (trimmed.startsWith('- ')) {
      flushParagraph();
      bullets.push(trimmed.slice(2));
    } else if (trimmed === '') {
      flushParagraph();
      flushBullets();
    } else {
      flushBullets();
      paragraph.push(trimmed);
    }
  }
  flushParagraph();
  flushBullets();

  return <div className="markdown">{blocks}</div>;
}
