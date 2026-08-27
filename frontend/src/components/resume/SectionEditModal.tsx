import { useState } from "react";
import { Button, Group, Modal, Stack, Text, Textarea } from "@mantine/core";
import { applyDiff, getStagedDiff, rejectDiff, streamSectionEdit } from "../../api/agentStream";
import { getResume } from "../../api/resume";
import { useStore } from "../../state/store";
import { notify } from "../../lib/notify";
import type { AgentEvent, StagedEditSummary } from "../../types/agent";
import ActivityTimeline from "./ActivityTimeline";
import DiffLinesView from "./DiffLinesView";

interface SectionEditModalProps {
  sessionId: string;
  sectionId: string | null;
  onClose: () => void;
}

export default function SectionEditModal({ sessionId, sectionId, onClose }: SectionEditModalProps) {
  const [instruction, setInstruction] = useState("");
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [running, setRunning] = useState(false);
  const [diff, setDiff] = useState<StagedEditSummary | null>(null);
  const [applying, setApplying] = useState(false);
  const setSession = useStore((s) => s.setSession);

  const reset = () => {
    setInstruction("");
    setEvents([]);
    setDiff(null);
    setRunning(false);
    setApplying(false);
  };

  const close = () => {
    reset();
    onClose();
  };

  async function run() {
    if (!instruction.trim() || running || !sectionId) return;
    setRunning(true);
    setEvents([]);
    setDiff(null);
    try {
      let proposed = false;
      await streamSectionEdit(sessionId, sectionId, instruction, (event) => {
        setEvents((prev) => [...prev, event]);
        if (event.type === "section_proposed") proposed = true;
        if (event.type === "error") notify.error(event.message);
      });
      if (proposed) setDiff(await getStagedDiff(sessionId, sectionId));
    } catch (err) {
      notify.error(err instanceof Error ? err.message : "Agent run failed");
    } finally {
      setRunning(false);
    }
  }

  async function accept() {
    if (!sectionId) return;
    setApplying(true);
    try {
      await applyDiff(sessionId, [sectionId]);
      setSession(await getResume(sessionId));
      notify.success("Section updated");
      close();
    } catch (err) {
      notify.error(err instanceof Error ? err.message : "Failed to apply edit");
    } finally {
      setApplying(false);
    }
  }

  async function reject() {
    if (!sectionId) return;
    setApplying(true);
    try {
      await rejectDiff(sessionId, [sectionId]);
      setDiff(null);
      setEvents([]);
    } catch (err) {
      notify.error(err instanceof Error ? err.message : "Failed to reject edit");
    } finally {
      setApplying(false);
    }
  }

  return (
    <Modal
      opened={sectionId !== null}
      onClose={close}
      title={sectionId ? `Edit "${sectionId}" section` : "Edit section"}
      size="lg"
      centered
    >
      <Stack gap="md">
        {!diff && (
          <>
            <Textarea
              label="What should change?"
              placeholder="e.g. make this bullet more quantified and lead with impact"
              autosize
              minRows={2}
              maxRows={5}
              value={instruction}
              disabled={running}
              onChange={(e) => setInstruction(e.currentTarget.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                  e.preventDefault();
                  void run();
                }
              }}
            />
            <Group justify="flex-end">
              <Button onClick={run} loading={running} disabled={!instruction.trim()}>
                Propose edit
              </Button>
            </Group>
          </>
        )}

        {events.length > 0 && <ActivityTimeline events={events} />}

        {diff && (
          <Stack gap="xs">
            <Text size="sm" c="dimmed">
              {diff.rationale}
            </Text>
            <DiffLinesView oldText={diff.old_latex} newText={diff.new_latex} />
            <Group justify="flex-end">
              <Button variant="default" color="red" onClick={reject} loading={applying}>
                Reject
              </Button>
              <Button onClick={accept} loading={applying}>
                Accept &amp; recompile
              </Button>
            </Group>
          </Stack>
        )}
      </Stack>
    </Modal>
  );
}
