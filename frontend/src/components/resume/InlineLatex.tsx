import { Anchor } from "@mantine/core";
import { tokenizeInline, type InlineToken } from "../../lib/latex";

export function InlineTokens({ tokens }: { tokens: InlineToken[] }) {
  return (
    <>
      {tokens.map((t, i) => {
        const style: React.CSSProperties = {
          fontWeight: t.bold ? 600 : undefined,
          fontStyle: t.italic ? "italic" : undefined,
        };
        if (t.href) {
          return (
            <Anchor key={i} href={t.href} target="_blank" rel="noreferrer" style={style} size="inherit">
              {t.text}
            </Anchor>
          );
        }
        return (
          <span key={i} style={style}>
            {t.text}
          </span>
        );
      })}
    </>
  );
}

export function InlineLatex({ latex }: { latex: string }) {
  return <InlineTokens tokens={tokenizeInline(latex)} />;
}
