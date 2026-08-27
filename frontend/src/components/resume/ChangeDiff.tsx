import { useState } from "react";
import { Box, Code, Group, Stack, Switch, Text } from "@mantine/core";
import { IconArrowRight } from "@tabler/icons-react";
import { diffLines } from "../../utils/diffLines";
import { sectionBodyToLines } from "../../lib/latex";

interface ChangeDiffProps {
  oldLatex: string;
  newLatex: string;
}

export default function ChangeDiff({ oldLatex, newLatex }: ChangeDiffProps) {
  const [showLatex, setShowLatex] = useState(false);

  const oldLines = sectionBodyToLines(oldLatex);
  const newLines = sectionBodyToLines(newLatex);
  const lines = showLatex ? diffLines(oldLatex, newLatex) : diffLines(oldLines.join("\n"), newLines.join("\n"));

  // group consecutive remove(s)+add(s) into a single "changed" block
  type Row = { kind: "same"; text: string } | { kind: "removed"; texts: string[] } | { kind: "added"; texts: string[] } | { kind: "changed"; before: string[]; after: string[] };
  const rows: Row[] = [];
  for (let i = 0; i < lines.length; ) {
    const l = lines[i];
    if (l.type === "context") {
      rows.push({ kind: "same", text: l.text });
      i++;
      continue;
    }
    const removed: string[] = [];
    const added: string[] = [];
    while (i < lines.length && lines[i].type === "removed") removed.push(lines[i++].text);
    while (i < lines.length && lines[i].type === "added") added.push(lines[i++].text);
    if (removed.length && added.length) rows.push({ kind: "changed", before: removed, after: added });
    else if (removed.length) rows.push({ kind: "removed", texts: removed });
    else if (added.length) rows.push({ kind: "added", texts: added });
  }

  return (
    <Stack gap={6}>
      <Group justify="flex-end">
        <Switch size="xs" label="Show LaTeX" checked={showLatex} onChange={(e) => setShowLatex(e.currentTarget.checked)} />
      </Group>

      {showLatex ? (
        <Code block style={{ fontSize: 11.5, lineHeight: 1.55 }}>
          {lines.map((l, i) => (
            <Box
              key={i}
              style={{
                background:
                  l.type === "added"
                    ? "var(--mantine-color-teal-light)"
                    : l.type === "removed"
                      ? "var(--mantine-color-red-light)"
                      : "transparent",
                whiteSpace: "pre-wrap",
                wordBreak: "break-word",
              }}
            >
              {l.type === "added" ? "+ " : l.type === "removed" ? "- " : "  "}
              {l.text || " "}
            </Box>
          ))}
        </Code>
      ) : rows.every((r) => r.kind === "same") ? (
        <Text size="sm" c="dimmed">
          Formatting-only change (no visible text difference).
        </Text>
      ) : (
        <Stack gap={5}>
          {rows.map((r, i) => {
            if (r.kind === "same") {
              return (
                <Text key={i} size="sm" c="dimmed" style={{ paddingLeft: 10 }}>
                  {r.text}
                </Text>
              );
            }
            if (r.kind === "removed") {
              return r.texts.map((t, j) => <Line key={`${i}-${j}`} kind="removed" text={t} />);
            }
            if (r.kind === "added") {
              return r.texts.map((t, j) => <Line key={`${i}-${j}`} kind="added" text={t} />);
            }
            return (
              <Box key={i} style={{ border: "1px solid var(--mantine-color-default-border)", borderRadius: 6, padding: 6 }}>
                {r.before.map((t, j) => (
                  <Line key={`b${j}`} kind="removed" text={t} />
                ))}
                <Group gap={4} my={3} c="dimmed">
                  <IconArrowRight size={12} />
                  <Text size="10px" tt="uppercase" fw={600} style={{ letterSpacing: 0.5 }}>
                    becomes
                  </Text>
                </Group>
                {r.after.map((t, j) => (
                  <Line key={`a${j}`} kind="added" text={t} />
                ))}
              </Box>
            );
          })}
        </Stack>
      )}
    </Stack>
  );
}

function Line({ kind, text }: { kind: "added" | "removed"; text: string }) {
  const isAdd = kind === "added";
  return (
    <Text
      size="sm"
      style={{
        background: isAdd ? "var(--mantine-color-teal-light)" : "var(--mantine-color-red-light)",
        borderLeft: `3px solid ${isAdd ? "var(--mantine-color-teal-6)" : "var(--mantine-color-red-6)"}`,
        padding: "3px 8px",
        borderRadius: 4,
        whiteSpace: "pre-wrap",
        wordBreak: "break-word",
        textDecoration: isAdd ? undefined : "line-through",
        opacity: isAdd ? 1 : 0.7,
        marginBottom: 2,
      }}
    >
      {text || " "}
    </Text>
  );
}
