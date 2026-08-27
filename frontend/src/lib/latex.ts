/**
 * Minimal LaTeX → readable-text/structure helpers for the resume editor.
 *
 * The app's resume LaTeX is simple and predictable (see backend/latex_templates):
 * sections are wrapped in `% [SECTION:id] … % [/SECTION:id]` markers, each holds
 * `\section{Title}` + a list of `\resumeItem{…}` bullets (and sometimes
 * `\resumeSubheading{a}{b}{c}{d}` entries). We only need to parse that subset.
 */

export interface InlineToken {
  text: string;
  bold?: boolean;
  italic?: boolean;
  href?: string;
}

export interface ResumeEntry {
  kind: "entry";
  title: InlineToken[];
  titleRight: InlineToken[];
  subtitle: InlineToken[];
  subtitleRight: InlineToken[];
}

export interface ResumeBullet {
  kind: "bullet";
  content: InlineToken[];
}

export type SectionBlock = ResumeEntry | ResumeBullet;

export interface ParsedSection {
  id: string;
  title: string;
  blocks: SectionBlock[];
}

export interface ParsedHeader {
  name: string;
  contact: string[];
}

const SECTION_RE = /% \[SECTION:([\w-]+)\]\n([\s\S]*?)\n% \[\/SECTION:\1\]/g;

const ESCAPES: Record<string, string> = {
  "&": "&",
  "%": "%",
  $: "$",
  "#": "#",
  _: "_",
  "{": "{",
  "}": "}",
  " ": " ",
};

/** Read a `{ … }` group starting at s[i] === '{'. Returns [content, indexAfter]. */
function readGroup(s: string, i: number): [string, number] {
  if (s[i] !== "{") return ["", i];
  let depth = 0;
  let j = i;
  for (; j < s.length; j++) {
    const c = s[j];
    if (c === "\\") {
      j++;
      continue;
    }
    if (c === "{") depth++;
    else if (c === "}") {
      depth--;
      if (depth === 0) return [s.slice(i + 1, j), j + 1];
    }
  }
  return [s.slice(i + 1), s.length];
}

/** Tokenize inline LaTeX into styled runs. */
export function tokenizeInline(input: string): InlineToken[] {
  const out: InlineToken[] = [];
  const push = (text: string, style: Partial<InlineToken> = {}) => {
    if (!text) return;
    const last = out[out.length - 1];
    if (last && !last.href && !style.href && !!last.bold === !!style.bold && !!last.italic === !!style.italic) {
      last.text += text;
    } else {
      out.push({ text, ...style });
    }
  };

  let buf = "";
  let i = 0;
  const flush = () => {
    if (buf) push(buf);
    buf = "";
  };

  while (i < input.length) {
    const c = input[i];

    if (c === "~") {
      buf += " ";
      i++;
      continue;
    }
    if (c === "{" || c === "}") {
      i++;
      continue;
    }
    if (c === "-" && input[i + 1] === "-") {
      const isEm = input[i + 2] === "-";
      buf += isEm ? "—" : "–";
      i += isEm ? 3 : 2;
      continue;
    }
    if (c !== "\\") {
      buf += c;
      i++;
      continue;
    }

    // c === '\\'
    const next = input[i + 1];
    if (next === "\\") {
      // line break — treat as a space in inline context
      buf += " ";
      i += 2;
      continue;
    }
    if (next && ESCAPES[next] !== undefined) {
      buf += ESCAPES[next];
      i += 2;
      continue;
    }

    const cmdMatch = /^\\([a-zA-Z]+)\*?\s*/.exec(input.slice(i));
    if (!cmdMatch) {
      i++;
      continue;
    }
    const cmd = cmdMatch[1];
    let j = i + cmdMatch[0].length;

    if ((cmd === "textbf" || cmd === "textit" || cmd === "emph" || cmd === "underline" || cmd === "textrm") && input[j] === "{") {
      const [inner, after] = readGroup(input, j);
      flush();
      const style = cmd === "textbf" ? { bold: true } : { italic: true };
      for (const tk of tokenizeInline(inner)) {
        push(tk.text, { bold: tk.bold || style.bold, italic: tk.italic || style.italic, href: tk.href });
      }
      i = after;
      continue;
    }

    if (cmd === "href" && input[j] === "{") {
      const [url, afterUrl] = readGroup(input, j);
      let k = afterUrl;
      let label = url;
      if (input[k] === "{") {
        const [lbl, afterLbl] = readGroup(input, k);
        label = lbl;
        k = afterLbl;
      }
      flush();
      push(tokenizeInline(label).map((t) => t.text).join("") || url, { href: url });
      i = k;
      continue;
    }

    // known no-arg spacing commands
    if (cmd === "vspace" || cmd === "hspace") {
      if (input[j] === "{") {
        const [, after] = readGroup(input, j);
        j = after;
      }
      i = j;
      continue;
    }

    // unknown command: drop the command, keep any following group's content
    if (input[j] === "{") {
      const [inner, after] = readGroup(input, j);
      buf += inner.replace(/\\[a-zA-Z]+\*?/g, "").replace(/[{}]/g, "");
      i = after;
      continue;
    }
    i = j;
  }
  flush();
  return out.map((t) => ({ ...t, text: t.text.replace(/\s+/g, " ") })).filter((t) => t.text.length > 0);
}

export function inlineToPlainText(tokens: InlineToken[]): string {
  return tokens
    .map((t) => t.text)
    .join("")
    .replace(/\s+/g, " ")
    .trim();
}

export function latexToPlainText(latex: string): string {
  return inlineToPlainText(tokenizeInline(latex));
}

export function parseResumeSections(latex: string): { id: string; body: string }[] {
  const out: { id: string; body: string }[] = [];
  for (const m of latex.matchAll(SECTION_RE)) {
    out.push({ id: m[1], body: m[2].trim() });
  }
  return out;
}

const _EMAIL = /[\w.+-]+@[\w-]+\.[\w.-]+/;

export function parseHeader(body: string): ParsedHeader {
  const nameMatch = /\\name\s*\{/.exec(body);
  const contactMatch = /\\contact\s*\{/.exec(body);
  let name = nameMatch ? latexToPlainText(readGroup(body, nameMatch.index + nameMatch[0].length - 1)[0]) : "";
  const contactRaw = contactMatch ? readGroup(body, contactMatch.index + contactMatch[0].length - 1)[0] : "";

  const extra: string[] = [];
  // PDF extraction often glues the contact line onto \name{} — pull it back out.
  const em = _EMAIL.exec(name);
  if (em) {
    extra.push(em[0]);
    name = name.slice(0, em.index).replace(/\b(e-?mail|contact|phone|mobile)\s*:?\s*$/i, "").trim();
  }
  name = name.replace(/\s*[|·]\s*/g, " ").replace(/\s{2,}/g, " ").replace(/[:|]\s*$/, "").trim();
  // keep at most the first 4 words as the name
  if (name.split(" ").length > 5) name = name.split(" ").slice(0, 4).join(" ");

  const contact = [
    ...extra,
    ...latexToPlainText(contactRaw)
      .split(/\s*[|·]\s*/)
      .map((s) => s.replace(/\b(mobile|phone|email|portfolio|github|linkedin)\s*:?\s*/i, (m) => m).trim())
      .filter(Boolean),
  ];
  // de-dupe
  return { name, contact: [...new Set(contact)] };
}

const TITLE_RE = /\\(?:section|sectionheading)\s*\{/;
const RESUME_ITEM_RE = /\\resumeItem\s*\{/g;
const SUBHEADING_RE = /\\resumeSubheading\s*\{/g;

export function parseSection(id: string, body: string): ParsedSection {
  const tm = TITLE_RE.exec(body);
  const title = tm ? readGroup(body, tm.index + tm[0].length - 1)[0].trim() : id;

  const blocks: SectionBlock[] = [];

  // Subheading entries (title/date/subtitle/location)
  for (const m of body.matchAll(SUBHEADING_RE)) {
    let k = m.index! + m[0].length - 1;
    const groups: string[] = [];
    for (let g = 0; g < 4 && body[k] === "{"; g++) {
      const [inner, after] = readGroup(body, k);
      groups.push(inner);
      k = after;
      while (/\s/.test(body[k])) k++;
    }
    blocks.push({
      kind: "entry",
      title: tokenizeInline(groups[0] ?? ""),
      titleRight: tokenizeInline(groups[1] ?? ""),
      subtitle: tokenizeInline(groups[2] ?? ""),
      subtitleRight: tokenizeInline(groups[3] ?? ""),
    });
  }

  // Bullets
  for (const m of body.matchAll(RESUME_ITEM_RE)) {
    const [inner] = readGroup(body, m.index! + m[0].length - 1);
    const tokens = tokenizeInline(inner);
    // strip leading bullet glyphs left over from PDF extraction ("• • • …")
    if (tokens[0]) tokens[0].text = tokens[0].text.replace(/^[\s•‣·▪◦*-]+/, "");
    if (inlineToPlainText(tokens)) blocks.push({ kind: "bullet", content: tokens });
  }

  return { id, title, blocks };
}

/** Flatten a raw section body to readable lines — used for human-readable diffs. */
export function sectionBodyToLines(body: string): string[] {
  const parsed = parseSection("", body);
  const lines: string[] = [];
  for (const b of parsed.blocks) {
    if (b.kind === "entry") {
      const l = [inlineToPlainText(b.title), inlineToPlainText(b.titleRight)].filter(Boolean).join(" — ");
      const s = [inlineToPlainText(b.subtitle), inlineToPlainText(b.subtitleRight)].filter(Boolean).join(" — ");
      if (l) lines.push(l);
      if (s) lines.push(s);
    } else {
      lines.push(inlineToPlainText(b.content));
    }
  }
  return lines;
}
