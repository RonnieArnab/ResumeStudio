import { Badge, Group, Paper, Tabs } from "@mantine/core";
import { IconMessageCircle, IconTargetArrow } from "@tabler/icons-react";
import { useStore } from "../../state/store";
import ChatPanel from "./ChatPanel";
import MatchReportPanel from "./MatchReportPanel";

const fill = { flex: 1, minHeight: 0, display: "flex", flexDirection: "column" } as const;

export default function RightPane({ sessionId }: { sessionId: string }) {
  const report = useStore((s) => s.matchReport);

  return (
    <Paper withBorder radius="md" h="100%" style={{ display: "flex", flexDirection: "column", overflow: "hidden" }}>
      <Tabs defaultValue="assistant" keepMounted style={{ display: "flex", flexDirection: "column", height: "100%" }}>
        <Tabs.List>
          <Tabs.Tab value="assistant" leftSection={<IconMessageCircle size={14} />}>
            Assistant
          </Tabs.Tab>
          <Tabs.Tab value="match" leftSection={<IconTargetArrow size={14} />}>
            <Group gap={6}>
              JD Match
              {report && (
                <Badge
                  size="xs"
                  circle
                  color={report.overall_score >= 70 ? "teal" : report.overall_score >= 45 ? "yellow" : "red"}
                >
                  {report.overall_score}
                </Badge>
              )}
            </Group>
          </Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="assistant" style={fill}>
          <ChatPanel sessionId={sessionId} />
        </Tabs.Panel>
        <Tabs.Panel value="match" style={fill}>
          <MatchReportPanel sessionId={sessionId} />
        </Tabs.Panel>
      </Tabs>
    </Paper>
  );
}
