import { useState } from "react";
import { Badge, Button, Group, Modal, Paper, Stack, Text, Textarea } from "@mantine/core";
import { IconBulb } from "@tabler/icons-react";
import { applyDiff, getStagedDiff, listStagedDiffs, rejectDiff, streamSectionEdit } from "../../api/agentStream";
import { getResume } from "../../api/resume";
import { useStore } from "../../state/store";
import { notify } from "../../lib/notify";
import type { AgentEvent, StagedEditSummary } from "../../types/agent";
import AgentActivity from "./AgentActivity";
import ChangeDiff from "./ChangeDiff";

interface SectionEditModalProps {
  sessionId: string;
  sectionId: string | null;
  onClose: () => void;
}

const SUGGESTIONS = [
  "Make the bullets more quantified and impact-first",
  "Tighten wording and remove filler",
  "Tailor this to the attached job description",
];

export default function SectionEditModal({ sessionId, sectionId, onClose }: SectionEditModalProps) {
  const [instruction, setInstruction] = useState("");
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [running, setRunning] = useState(false);
  const [diff, setDiff] = useState<StagedEditSummary | null>(null);
  const [applying, setApplying] = useState(false);
  const setSession = useStore((s) => s.setSession);
  const setStagedEdits = useStore((s) => s.setStagedEdits);

  const close = () => {
    setInstruction("");
    setEvents([]);
    setDiff(null);
    setRunning(false);
    setApplying(false);
    onClose();
  };

  const syncStaged = async () => setStagedEdits(await listStagedDiffs(sessionId).catch(() => []));

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
      if (proposed) {
        setDiff(await getStagedDiff(sessionId, sectionId));
        void syncStaged();
      }
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
      await syncStaged();
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
      await syncStaged();
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
      title={
        <Group gap={8}>
          <Text fw={600}>Edit section</Text>
          {sectionId && (
            <Badge variant="light" tt="capitalize">
              {sectionId}
            </Badge>
          )}
        </Group>
      }
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
              maxRows={6}
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
            <Group gap={6}>
              {SUGGESTIONS.map((s) => (
                <Badge
                  key={s}
                  variant="outline"
                  color="gray"
                  style={{ cursor: "pointer", textTransform: "none" }}
                  onClick={() => setInstruction(s)}
                >
                  {s}
                </Badge>
              ))}
            </Group>
            <Group justify="flex-end">
              <Button onClick={run} loading={running} disabled={!instruction.trim()}>
                Propose edit
              </Button>
            </Group>
          </>
        )}

        {(events.length > 0 || running) && <AgentActivity events={events} running={running} />}

        {diff && (
          <Stack gap="sm">
            <ChangeDiff oldLatex={diff.old_latex} newLatex={diff.new_latex} />
            {diff.rationale && (
              <Group
                gap={6}
                wrap="nowrap"
                align="flex-start"
                style={{ background: "var(--mantine-color-default-hover)", borderRadius: 6, padding: "6px 8px" }}
              >
                <IconBulb size={13} style={{ marginTop: 2 }} />
                <Text size="xs" c="dimmed">
                  {diff.rationale}
                </Text>
              </Group>
            )}
            <Group justify="flex-end">
              <Button variant="default" color="red" onClick={reject} loading={applying}>
                Reject
              </Button>
              <Button color="teal" onClick={accept} loading={applying}>
                Accept &amp; recompile
              </Button>
            </Group>
          </Stack>
        )}

        {!diff && !running && events.length > 0 && (
          <Paper withBorder p="xs" radius="sm">
            <Text size="xs" c="dimmed">
              The agent didn't propose a change. Try rephrasing your instruction.
            </Text>
          </Paper>
        )}
      </Stack>
    </Modal>
  );
}
