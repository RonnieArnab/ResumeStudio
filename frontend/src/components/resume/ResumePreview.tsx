import { useMemo, useState } from "react";
import { ActionIcon, Box, Paper, ScrollArea, SegmentedControl, Group, Text, Tooltip } from "@mantine/core";
import { IconDownload } from "@tabler/icons-react";
import { useStore } from "../../state/store";
import { addResumeSection, deleteResumeSection } from "../../api/resume";
import { notify } from "../../lib/notify";
import LatexEditor from "./LatexEditor";
import ResumeDocument from "./ResumeDocument";

export default function ResumePreview() {
  const session = useStore((s) => s.session);
  const setSession = useStore((s) => s.setSession);
  const stagedEdits = useStore((s) => s.stagedEdits);
  const selectSection = useStore((s) => s.selectSection);
  const [mode, setMode] = useState<"formatted" | "latex">("formatted");

  const pendingIds = useMemo(() => new Set(stagedEdits.map((e) => e.section_id)), [stagedEdits]);
  if (!session) return null;

  const addSection = async (title: string) => {
    try {
      setSession(await addResumeSection(session.session_id, title));
      notify.success(`Added "${title}" — click it to have the agent fill it in`);
    } catch (err) {
      notify.error(err instanceof Error ? err.message : "Could not add section");
    }
  };

  const removeSection = async (id: string) => {
    try {
      setSession(await deleteResumeSection(session.session_id, id));
      notify.success("Section removed");
    } catch (err) {
      notify.error(err instanceof Error ? err.message : "Could not remove section");
    }
  };

  return (
    <Paper withBorder radius="md" h="100%" style={{ display: "flex", flexDirection: "column", overflow: "hidden" }}>
      <Group justify="space-between" p="xs" style={{ borderBottom: "1px solid var(--mantine-color-default-border)" }}>
        <Text fw={600} size="xs" c="dimmed">
          {mode === "formatted" ? "Click a section to edit it with the agent" : "Edit the LaTeX, then save to recompile"}
        </Text>
        <Group gap={6}>
          <SegmentedControl
            size="xs"
            value={mode}
            onChange={(v) => setMode(v as typeof mode)}
            data={[
              { label: "Formatted", value: "formatted" },
              { label: "LaTeX", value: "latex" },
            ]}
          />
          {session.pdf_url && (
            <Tooltip label="Download PDF">
              <ActionIcon variant="default" component="a" href={session.pdf_url} download>
                <IconDownload size={15} />
              </ActionIcon>
            </Tooltip>
          )}
        </Group>
      </Group>

      {mode === "formatted" ? (
        <ScrollArea style={{ flex: 1 }} p="md" bg="var(--mantine-color-body)" type="auto">
          <ResumeDocument
            latex={session.latex}
            pendingSectionIds={pendingIds}
            onSelectSection={selectSection}
            onAddSection={addSection}
            onDeleteSection={removeSection}
          />
        </ScrollArea>
      ) : (
        <Box p="md" style={{ flex: 1, minHeight: 0, display: "flex" }}>
          <LatexEditor />
        </Box>
      )}
    </Paper>
  );
}
