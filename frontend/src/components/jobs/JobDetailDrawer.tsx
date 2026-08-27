import { useEffect, useState } from "react";
import { Anchor, Badge, Button, Drawer, Group, List, ScrollArea, Stack, Text, ThemeIcon, Title } from "@mantine/core";
import { IconCheck, IconExternalLink, IconX } from "@tabler/icons-react";
import { jobsApi } from "../../api/jobs";
import { useStore } from "../../state/store";
import { notify } from "../../lib/notify";
import type { RankedJob } from "../../types/jobs";
import { scoreColor } from "./scoreColor";

export default function JobDetailDrawer() {
  const jobId = useStore((s) => s.selectedJobId);
  const selectJob = useStore((s) => s.selectJob);
  const session = useStore((s) => s.session);
  const setApplyRun = useStore((s) => s.setApplyRun);
  const bumpTracker = useStore((s) => s.bumpTracker);

  const [row, setRow] = useState<RankedJob | null>(null);
  const [preparing, setPreparing] = useState(false);

  useEffect(() => {
    if (!jobId) {
      setRow(null);
      return;
    }
    setRow(null);
    jobsApi.getJob(jobId).then(setRow).catch(() => notify.error("Could not load job"));
  }, [jobId]);

  const prepare = async () => {
    if (!jobId) return;
    setPreparing(true);
    try {
      const apply = await jobsApi.prepareApply(jobId, session?.session_id ?? null);
      setApplyRun(apply);
      bumpTracker();
      selectJob(null);
    } catch (err) {
      notify.error(err instanceof Error ? err.message : "Prepare failed");
    } finally {
      setPreparing(false);
    }
  };

  return (
    <Drawer
      opened={jobId !== null}
      onClose={() => selectJob(null)}
      position="right"
      size="xl"
      title={row ? row.job.title : "Loading…"}
    >
      {row && (
        <Stack gap="md">
          <Group gap="xs">
            <Text c="dimmed">{row.job.company}</Text>
            <Text c="dimmed">·</Text>
            <Text c="dimmed">{row.job.location || "location n/a"}</Text>
            <Badge variant="light">{row.job.provider}</Badge>
            {row.job.remote && (
              <Badge variant="light" color="teal">
                remote
              </Badge>
            )}
          </Group>

          {row.match && (
            <Stack gap="xs">
              <Group gap="xs">
                <Badge size="lg" color={scoreColor(row.match.verdict, row.match.score)}>
                  {row.match.score} / 100
                </Badge>
                <Text size="sm" c="dimmed">
                  {row.match.verdict}
                </Text>
              </Group>
              {row.match.summary && <Text size="sm">{row.match.summary}</Text>}
              <List spacing={2} size="sm" center>
                {row.match.matched_requirements.map((m) => (
                  <List.Item key={m} icon={<ThemeIcon color="teal" size={18} radius="xl"><IconCheck size={12} /></ThemeIcon>}>
                    {m}
                  </List.Item>
                ))}
                {row.match.missing_requirements.map((m) => (
                  <List.Item key={m} icon={<ThemeIcon color="yellow" size={18} radius="xl"><IconX size={12} /></ThemeIcon>}>
                    {m}
                  </List.Item>
                ))}
              </List>
            </Stack>
          )}

          <Group>
            <Button onClick={prepare} loading={preparing}>
              Prepare application
            </Button>
            <Anchor href={row.job.url || row.job.apply_url} target="_blank" rel="noreferrer">
              <Group gap={4}>
                Open posting <IconExternalLink size={14} />
              </Group>
            </Anchor>
          </Group>

          <Text size="xs" c="dimmed">
            Prepare opens the form in a headless browser, fills every field it can, and stops for your review. Nothing is
            submitted until you confirm.
          </Text>

          <div>
            <Title order={5} mb={4}>
              Job description
            </Title>
            <ScrollArea.Autosize mah={360} style={{ border: "1px solid var(--mantine-color-default-border)", borderRadius: 8, padding: 12 }}>
              <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>
                {row.job.description_text}
              </Text>
            </ScrollArea.Autosize>
          </div>
        </Stack>
      )}
    </Drawer>
  );
}
