import { useEffect, useState } from "react";
import { ActionIcon, Badge, Button, Code, CopyButton, Group, Spoiler, Stack, Text } from "@mantine/core";
import { IconBrandLinkedin, IconCheck, IconCopy, IconExternalLink, IconRefresh } from "@tabler/icons-react";
import { jobsApi } from "../../api/jobs";
import type { CdpStatus } from "../../types/jobs";

const OPEN: Record<string, string> = {
  LinkedIn: "https://www.linkedin.com/jobs/",
  Wellfound: "https://wellfound.com/jobs",
};

export default function ConnectionsPanel() {
  const [cdp, setCdp] = useState<CdpStatus | null>(null);
  const [checking, setChecking] = useState(false);

  const refreshCdp = () => {
    setChecking(true);
    jobsApi.cdpStatus().then(setCdp).catch(() => {}).finally(() => setChecking(false));
  };
  useEffect(refreshCdp, []);

  return (
    <Stack gap="sm">
      <Text size="xs" c="dimmed">
        Applying to a LinkedIn or Wellfound job opens the posting in a <b>new tab of this browser</b> — you're already
        signed in, so just click Easy Apply there. Your profile details show up next to the job for copy-paste.
      </Text>

      <Group gap={6}>
        <IconBrandLinkedin size={15} />
        {Object.entries(OPEN).map(([label, url]) => (
          <Button
            key={label}
            size="compact-xs"
            variant="light"
            rightSection={<IconExternalLink size={12} />}
            onClick={() => window.open(url, "_blank", "noopener")}
          >
            {label}
          </Button>
        ))}
      </Group>

      <Spoiler maxHeight={0} showLabel="Advanced: drive a separate Chrome" hideLabel="Hide advanced" fz="xs">
        <Stack gap="xs" mt="xs">
          <Group justify="space-between">
            <Text size="xs" fw={600}>
              Attach to a debug Chrome (for the auto-fill walkthrough)
            </Text>
            <Group gap={4}>
              {cdp?.available ? (
                <Badge size="xs" color="teal" variant="light">
                  on :{cdp.port}
                </Badge>
              ) : (
                <Badge size="xs" color="gray" variant="light">
                  off
                </Badge>
              )}
              <ActionIcon size="sm" variant="subtle" loading={checking} onClick={refreshCdp}>
                <IconRefresh size={13} />
              </ActionIcon>
            </Group>
          </Group>
          <Text size="xs" c="dimmed">
            Only needed if you want the paste-a-URL flow to fill forms step-by-step in a visible window. Quit Chrome, run:
          </Text>
          <Group gap={4} wrap="nowrap" align="flex-start">
            <Code block style={{ flex: 1, fontSize: 10.5, whiteSpace: "pre-wrap", wordBreak: "break-all" }}>
              {cdp?.launch_command ?? "…"}
            </Code>
            {cdp?.launch_command && (
              <CopyButton value={cdp.launch_command}>
                {({ copied, copy }) => (
                  <ActionIcon variant="light" onClick={copy}>
                    {copied ? <IconCheck size={13} /> : <IconCopy size={13} />}
                  </ActionIcon>
                )}
              </CopyButton>
            )}
          </Group>
        </Stack>
      </Spoiler>
    </Stack>
  );
}
