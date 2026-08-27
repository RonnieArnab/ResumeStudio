import { Paper, ScrollArea, Stack, Text } from "@mantine/core";
import { useStore } from "../../state/store";
import PdfCanvas from "./PdfCanvas";
import SectionCanvas from "./SectionCanvas";

export default function ResumePreview() {
  const session = useStore((s) => s.session);
  if (!session) return null;

  return (
    <Paper withBorder radius="md" h="100%" style={{ display: "flex", flexDirection: "column", overflow: "hidden" }}>
      <Text fw={600} size="sm" p="sm" c="dimmed">
        Preview · click a section to edit it
      </Text>
      <ScrollArea style={{ flex: 1 }} p="md" bg="var(--mantine-color-body)">
        {session.section_fragments.length === 0 ? (
          <Text c="dimmed" size="sm">
            No compiled preview for this resume yet.
          </Text>
        ) : (
          <Stack gap="xs" align="center">
            {session.section_fragments.map((fragment) => (
              <SectionCanvas key={fragment.id} sectionId={fragment.id}>
                <PdfCanvas url={fragment.pdf_url} />
              </SectionCanvas>
            ))}
          </Stack>
        )}
      </ScrollArea>
    </Paper>
  );
}
