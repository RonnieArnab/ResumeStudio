import { useState } from "react";
import { ActionIcon, Badge, Box, Button, Group, Paper, Stack, Text } from "@mantine/core";
import { IconBulb, IconCheck, IconX } from "@tabler/icons-react";
import { applyDiff, rejectDiff } from "../../api/agentStream";
import { notify } from "../../lib/notify";
import type { StagedEditSummary } from "../../types/agent";
import ChangeDiff from "./ChangeDiff";

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
    <Paper
      radius="md"
      p="sm"
      style={{
        border: "1px solid var(--mantine-color-yellow-6)",
        background: "color-mix(in srgb, var(--mantine-color-yellow-6) 7%, var(--mantine-color-body))",
      }}
    >
      <Group justify="space-between" mb="sm">
        <Group gap={8}>
          <Badge color="yellow" variant="filled" radius="sm">
            {diffs.length}
          </Badge>
          <Text fw={650} size="sm">
            proposed change{diffs.length === 1 ? "" : "s"} — review below
          </Text>
        </Group>
        <Group gap={6}>
          <Button
            size="xs"
            variant="default"
            leftSection={<IconX size={13} />}
            disabled={busy}
            onClick={() => act(() => rejectDiff(sessionId, allIds), "reject")}
          >
            Reject all
          </Button>
          <Button
            size="xs"
            color="teal"
            leftSection={<IconCheck size={13} />}
            disabled={busy}
            onClick={() => act(() => applyDiff(sessionId, allIds), "apply")}
          >
            Accept all
          </Button>
        </Group>
      </Group>

      <Stack gap="sm">
        {diffs.map((diff) => (
          <Paper key={diff.section_id} radius="sm" p="sm" bg="var(--mantine-color-body)" withBorder>
            <Group justify="space-between" mb={6}>
              <Badge variant="light" radius="sm" tt="capitalize">
                {diff.section_id}
              </Badge>
              <Group gap={4}>
                <ActionIcon
                  variant="light"
                  color="red"
                  size="sm"
                  disabled={busy}
                  onClick={() => act(() => rejectDiff(sessionId, [diff.section_id]), "reject")}
                  aria-label="Reject"
                >
                  <IconX size={14} />
                </ActionIcon>
                <ActionIcon
                  variant="light"
                  color="teal"
                  size="sm"
                  disabled={busy}
                  onClick={() => act(() => applyDiff(sessionId, [diff.section_id]), "apply")}
                  aria-label="Accept"
                >
                  <IconCheck size={14} />
                </ActionIcon>
              </Group>
            </Group>

            <ChangeDiff oldLatex={diff.old_latex} newLatex={diff.new_latex} />

            {diff.rationale && (
              <Group
                gap={6}
                wrap="nowrap"
                mt={8}
                align="flex-start"
                style={{
                  background: "var(--mantine-color-default-hover)",
                  borderRadius: 6,
                  padding: "6px 8px",
                }}
              >
                <Box pt={2}>
                  <IconBulb size={13} />
                </Box>
                <Text size="xs" c="dimmed">
                  {diff.rationale}
                </Text>
              </Group>
            )}
          </Paper>
        ))}
      </Stack>
    </Paper>
  );
}
