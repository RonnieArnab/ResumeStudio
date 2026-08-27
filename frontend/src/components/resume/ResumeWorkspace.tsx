import { Container, ScrollArea, Stack, Title, Text } from "@mantine/core";
import { useStore } from "../../state/store";
import SplitPane from "../layout/SplitPane";
import ChatPanel from "./ChatPanel";
import ResumeDropzone from "./ResumeDropzone";
import ResumePreview from "./ResumePreview";
import SectionEditModal from "./SectionEditModal";

export default function ResumeWorkspace() {
  const session = useStore((s) => s.session);
  const selectedSectionId = useStore((s) => s.selectedSectionId);
  const selectSection = useStore((s) => s.selectSection);

  if (!session) {
    return (
      <ScrollArea h="100%" type="auto">
        <Container size="sm" py={80}>
          <Stack gap="lg">
            <div>
              <Title order={2}>AI Resume Editor</Title>
              <Text c="dimmed" mt={4}>
                Upload a resume to start editing it section by section, or tailoring it to a job.
              </Text>
            </div>
            <ResumeDropzone />
          </Stack>
        </Container>
      </ScrollArea>
    );
  }

  return (
    <>
      <SplitPane
        storageKey="resume-workspace"
        defaultRatio={0.52}
        left={
          <div style={{ height: "100%", padding: "var(--mantine-spacing-md)" }}>
            <ResumePreview />
          </div>
        }
        right={
          <div style={{ height: "100%", padding: "var(--mantine-spacing-md)" }}>
            <ChatPanel sessionId={session.session_id} />
          </div>
        }
      />
      <SectionEditModal sessionId={session.session_id} sectionId={selectedSectionId} onClose={() => selectSection(null)} />
    </>
  );
}
