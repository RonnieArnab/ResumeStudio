import { useState } from "react";
import { Button, Card, Group, Stack, Text } from "@mantine/core";
import { applyDiff, rejectDiff } from "../../api/agentStream";
import { notify } from "../../lib/notify";
import type { StagedEditSummary } from "../../types/agent";
import DiffLinesView from "./DiffLinesView";

interface DiffReviewProps {
  sessionId: string;
  diffs: StagedEditSummary[];
  onChanged: () => void;
}

export default function DiffReview({ sessionId, diffs, onChanged }: DiffReviewProps) {
  const [busy, setBusy] = useState(false);

  if (diffs.length === 0) return null;

  const act = async (fn: () => Promise<unknown>, verb: string) => {
    setBusy(true);
    try {
      await fn();
      onChanged();
    } catch (err) {
      notify.error(err instanceof Error ? err.message : `Failed to ${verb}`);
    } finally {
      setBusy(false);
    }
  };

  const allIds = diffs.map((d) => d.section_id);

  return (
    <Card withBorder radius="md" padding="sm">
      <Group justify="space-between" mb="xs">
        <Text fw={600} size="sm">
          {diffs.length} staged change{diffs.length === 1 ? "" : "s"}
        </Text>
        <Group gap="xs">
          <Button size="xs" variant="light" color="red" disabled={busy} onClick={() => act(() => rejectDiff(sessionId, allIds), "reject")}>
            Reject all
          </Button>
          <Button size="xs" disabled={busy} onClick={() => act(() => applyDiff(sessionId, allIds), "apply")}>
            Accept all
          </Button>
        </Group>
      </Group>

      <Stack gap="sm">
        {diffs.map((diff) => (
          <Card key={diff.section_id} withBorder radius="sm" padding="xs" bg="var(--mantine-color-body)">
            <Text size="xs" fw={600} c="dimmed" mb={4}>
              {diff.section_id}
            </Text>
            <DiffLinesView oldText={diff.old_latex} newText={diff.new_latex} />
            <Text size="xs" c="dimmed" mt={4}>
              {diff.rationale}
            </Text>
            <Group gap="xs" mt="xs">
              <Button size="compact-xs" variant="light" color="red" disabled={busy} onClick={() => act(() => rejectDiff(sessionId, [diff.section_id]), "reject")}>
                Reject
              </Button>
              <Button size="compact-xs" variant="light" disabled={busy} onClick={() => act(() => applyDiff(sessionId, [diff.section_id]), "apply")}>
                Accept
              </Button>
            </Group>
          </Card>
        ))}
      </Stack>
    </Card>
  );
}
