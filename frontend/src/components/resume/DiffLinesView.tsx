import { Box, Code } from "@mantine/core";
import { diffLines } from "../../utils/diffLines";

interface DiffLinesViewProps {
  oldText: string;
  newText: string;
}

const COLORS: Record<string, string> = {
  added: "var(--mantine-color-teal-light)",
  removed: "var(--mantine-color-red-light)",
  context: "transparent",
};

export default function DiffLinesView({ oldText, newText }: DiffLinesViewProps) {
  const lines = diffLines(oldText, newText);
  return (
    <Code block style={{ fontSize: 12, lineHeight: 1.55 }}>
      {lines.map((line, i) => (
        <Box
          key={i}
          style={{
            background: COLORS[line.type],
            whiteSpace: "pre-wrap",
            wordBreak: "break-word",
          }}
        >
          {line.type === "added" ? "+ " : line.type === "removed" ? "- " : "  "}
          {line.text || " "}
        </Box>
      ))}
    </Code>
  );
}
