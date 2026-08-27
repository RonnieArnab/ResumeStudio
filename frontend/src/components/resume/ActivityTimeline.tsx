import { Timeline, Text, Code } from "@mantine/core";
import { IconCheck, IconAlertTriangle, IconTool, IconArrowRight, IconFlag } from "@tabler/icons-react";
import type { AgentEvent } from "../../types/agent";

function argsPreview(args: Record<string, unknown>): string {
  return Object.entries(args)
    .map(([k, v]) => `${k}=${typeof v === "string" ? (v.length > 40 ? `${v.slice(0, 40)}…` : v) : JSON.stringify(v)}`)
    .join(", ");
}

function resultPreview(result: unknown): string {
  const s = JSON.stringify(result) ?? String(result);
  return s.length > 120 ? `${s.slice(0, 120)}…` : s;
}

interface ActivityTimelineProps {
  events: AgentEvent[];
}

export default function ActivityTimeline({ events }: ActivityTimelineProps) {
  if (events.length === 0) return null;

  return (
    <Timeline active={events.length} bulletSize={20} lineWidth={2}>
      {events.map((event, i) => {
        switch (event.type) {
          case "tool_call":
            return (
              <Timeline.Item key={i} bullet={<IconTool size={12} />} title={event.name}>
                <Code fz="xs">{argsPreview(event.arguments)}</Code>
              </Timeline.Item>
            );
          case "tool_result":
            return (
              <Timeline.Item key={i} bullet={<IconArrowRight size={12} />} title="result">
                <Text size="xs" c="dimmed">
                  {resultPreview(event.result)}
                </Text>
              </Timeline.Item>
            );
          case "section_proposed":
            return (
              <Timeline.Item key={i} bullet={<IconCheck size={12} />} color="teal" title={`staged ${event.section_id}`} />
            );
          case "validation_error":
            return (
              <Timeline.Item key={i} bullet={<IconAlertTriangle size={12} />} color="red" title="validation error">
                <Text size="xs" c="red">
                  {event.errors.join("; ")}
                </Text>
              </Timeline.Item>
            );
          case "error":
            return (
              <Timeline.Item key={i} bullet={<IconAlertTriangle size={12} />} color="red" title="error">
                <Text size="xs" c="red">
                  {event.message}
                </Text>
              </Timeline.Item>
            );
          case "done":
            return <Timeline.Item key={i} bullet={<IconFlag size={12} />} color="gray" title="done" />;
        }
      })}
    </Timeline>
  );
}
