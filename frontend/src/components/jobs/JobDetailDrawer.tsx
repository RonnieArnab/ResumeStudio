import { useEffect, useState } from "react";
import { Anchor, Badge, Button, CopyButton, Drawer, Group, List, Paper, ScrollArea, Stack, Text, ThemeIcon, Title } from "@mantine/core";
import { IconCheck, IconCopy, IconExternalLink, IconX } from "@tabler/icons-react";
import { jobsApi } from "../../api/jobs";
import { useStore } from "../../state/store";
import { notify } from "../../lib/notify";
import type { ApplicantProfile, RankedJob } from "../../types/jobs";
import { scoreColor } from "./scoreColor";

function ProfileCheatSheet() {
  const [p, setP] = useState<ApplicantProfile | null>(null);
  useEffect(() => {
    jobsApi.getProfile().then(setP).catch(() => {});
  }, []);
  if (!p) return null;
  const rows: [string, string][] = [
    ["Name", p.full_name],
    ["Email", p.email],
    ["Phone", p.phone],
    ["Location", p.location],
    ["LinkedIn", p.linkedin_url],
    ["GitHub", p.github_url],
  ].filter(([, v]) => v) as [string, string][];
  return (
    <Paper withBorder radius="sm" p="xs">
      <Stack gap={4}>
        {rows.map(([k, v]) => (
          <Group key={k} gap={6} wrap="nowrap" justify="space-between">
            <Text size="xs" c="dimmed" w={64}>
              {k}
            </Text>
            <Text size="xs" style={{ flex: 1 }} truncate>
              {v}
            </Text>
            <CopyButton value={v}>
              {({ copied, copy }) => (
                <Button size="compact-xs" variant="subtle" onClick={copy} leftSection={copied ? <IconCheck size={11} /> : <IconCopy size={11} />}>
                  {copied ? "" : "copy"}
                </Button>
              )}
            </CopyButton>
          </Group>
        ))}
      </Stack>
    </Paper>
  );
}

export default function JobDetailDrawer() {
  const jobId = useStore((s) => s.selectedJobId);
  const selectJob = useStore((s) => s.selectJob);
  const session = useStore((s) => s.session);
  const setApplyRun = useStore((s) => s.setApplyRun);
  const bumpTracker = useStore((s) => s.bumpTracker);

  const [row, setRow] = useState<RankedJob | null>(null);
  const [preparing, setPreparing] = useState(false);

  useEffect(() => {
    if (!jobId) return; // keep the last content visible while the drawer animates closed
    setRow(null);
    jobsApi.getJob(jobId).then(setRow).catch(() => notify.error("Could not load job"));
  }, [jobId]);

  const externalProvider = row?.job.provider === "linkedin" || row?.job.provider === "wellfound";

  const prepare = async () => {
    if (!jobId) return;
    setPreparing(true);
    try {
      if (externalProvider) {
        // Open the posting in a new tab of the user's own browser — they're
        // already signed in there, so they just click Easy Apply.
        const { url } = await jobsApi.openExternal(jobId);
        window.open(url || row?.job.url, "_blank", "noopener");
        bumpTracker();
        selectJob(null);
        return;
      }
      const apply = await jobsApi.prepareApply(jobId, session?.session_id ?? null);
      setApplyRun(apply);
      bumpTracker();
      selectJob(null);
    } catch (err) {
      notify.error(err instanceof Error ? err.message : "Could not open the application");
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
            <Button
              onClick={prepare}
              loading={preparing}
              rightSection={externalProvider ? <IconExternalLink size={14} /> : undefined}
            >
              {externalProvider ? `Apply on ${row.job.provider === "linkedin" ? "LinkedIn" : "Wellfound"}` : "Prepare application"}
            </Button>
            {!externalProvider && (
              <Anchor href={row.job.url || row.job.apply_url} target="_blank" rel="noreferrer">
                <Group gap={4}>
                  Open posting <IconExternalLink size={14} />
                </Group>
              </Anchor>
            )}
          </Group>

          <Text size="xs" c="dimmed">
            {externalProvider
              ? "Opens the posting in a new tab of this browser — you're already signed in, so just click Easy Apply there. Your details from the profile:"
              : "Prepare opens the form in a browser, fills every field it can, and stops for your review. Nothing is submitted until you confirm."}
          </Text>

          {externalProvider && <ProfileCheatSheet />}

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
