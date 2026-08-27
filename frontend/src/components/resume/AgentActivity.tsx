import { useState } from "react";
import { Box, Collapse, Group, Loader, Text, UnstyledButton } from "@mantine/core";
import { IconChevronRight, IconListDetails } from "@tabler/icons-react";
import type { AgentEvent } from "../../types/agent";
import ActivityTimeline from "./ActivityTimeline";

interface AgentActivityProps {
  events: AgentEvent[];
  running?: boolean;
}

function summarize(events: AgentEvent[]): string {
  const tools = events.filter((e) => e.type === "tool_call").map((e) => (e as { name: string }).name);
  const unique = [...new Set(tools)];
  if (unique.length === 0) return "thinking…";
  return unique.join(" · ");
}

/** Collapsed-by-default agent activity log. Users expand it to see which tools
 * ran and what they returned. */
export default function AgentActivity({ events, running }: AgentActivityProps) {
  const [open, setOpen] = useState(false);
  if (events.length === 0 && !running) return null;

  const toolCount = events.filter((e) => e.type === "tool_call").length;
  const lastCall = [...events].reverse().find((e) => e.type === "tool_call") as { name: string } | undefined;

  return (
    <Box
      style={{
        border: "1px solid var(--mantine-color-default-border)",
        borderRadius: "var(--mantine-radius-md)",
        overflow: "hidden",
      }}
    >
      <UnstyledButton
        onClick={() => setOpen((v) => !v)}
        style={{ display: "block", width: "100%", padding: "8px 10px" }}
      >
        <Group gap={8} wrap="nowrap">
          <IconChevronRight
            size={14}
            style={{ transform: open ? "rotate(90deg)" : "none", transition: "transform 120ms" }}
          />
          {running ? <Loader size={12} /> : <IconListDetails size={14} />}
          <Text size="xs" fw={600}>
            Agent activity
          </Text>
          <Text size="xs" c="dimmed" truncate style={{ flex: 1 }}>
            {running
              ? lastCall
                ? `running ${lastCall.name}…`
                : "working…"
              : `${toolCount} step${toolCount === 1 ? "" : "s"} · ${summarize(events)}`}
          </Text>
        </Group>
      </UnstyledButton>
      <Collapse in={open}>
        <Box p="sm" pt={4} style={{ borderTop: "1px solid var(--mantine-color-default-border)" }}>
          <ActivityTimeline events={events} />
        </Box>
      </Collapse>
    </Box>
  );
}
