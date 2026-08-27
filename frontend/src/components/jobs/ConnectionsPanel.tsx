import { useEffect, useState } from "react";
import { ActionIcon, Alert, Badge, Button, Code, CopyButton, Divider, Group, Stack, Text, Tooltip } from "@mantine/core";
import { IconBrandLinkedin, IconCheck, IconCopy, IconInfoCircle, IconRefresh } from "@tabler/icons-react";
import { jobsApi } from "../../api/jobs";
import { notify } from "../../lib/notify";
import type { CdpStatus, ConnectionStatus, Provider } from "../../types/jobs";

const LABELS: Record<string, string> = { linkedin: "LinkedIn", wellfound: "Wellfound" };

export default function ConnectionsPanel() {
  const [conns, setConns] = useState<ConnectionStatus[]>([]);
  const [cdp, setCdp] = useState<CdpStatus | null>(null);
  const [pending, setPending] = useState<Provider | null>(null);
  const [busy, setBusy] = useState<Provider | null>(null);
  const [checking, setChecking] = useState(false);

  const refresh = () => jobsApi.listConnections().then(setConns).catch(() => {});
  const refreshCdp = () => {
    setChecking(true);
    jobsApi
      .cdpStatus()
      .then(setCdp)
      .catch(() => {})
      .finally(() => setChecking(false));
  };

  useEffect(() => {
    refresh();
    refreshCdp();
  }, []);

  const start = async (p: Provider) => {
    setBusy(p);
    try {
      await jobsApi.connectStart(p);
      setPending(p);
      notify.info("A browser window opened — log in there, then click 'I've logged in'.");
    } catch (err) {
      notify.error(err instanceof Error ? err.message : "Could not open a browser (local run only)");
    } finally {
      setBusy(null);
    }
  };

  const finish = async (p: Provider) => {
    setBusy(p);
    try {
      await jobsApi.connectFinish(p);
      setPending(null);
      notify.success(`${LABELS[p]} connected`);
      refresh();
    } catch (err) {
      notify.error(err instanceof Error ? err.message : "Finish failed");
    } finally {
      setBusy(null);
    }
  };

  const disconnect = async (p: Provider) => {
    await jobsApi.connectDelete(p).catch(() => {});
    refresh();
  };

  const openLogin = async (p: string) => {
    try {
      await jobsApi.openLoginTab(p);
      notify.info(`Opened ${LABELS[p] ?? p} sign-in in a new tab of your Chrome — finish it there.`);
    } catch (err) {
      notify.error(err instanceof Error ? err.message : "Could not open a tab");
    }
  };

  return (
    <Stack gap="md">
      {/* --- Preferred: attach to the user's own running Chrome over CDP --- */}
      <Stack gap="xs">
        <Group justify="space-between">
          <Text size="sm" fw={600}>
            Use your own Chrome
          </Text>
          <Group gap={6}>
            {cdp?.available ? (
              <Badge size="sm" color="teal" variant="light" leftSection={<IconCheck size={11} />}>
                detected on :{cdp.port}
              </Badge>
            ) : (
              <Badge size="sm" color="gray" variant="light">
                not detected
              </Badge>
            )}
            <Tooltip label="Re-check">
              <ActionIcon size="sm" variant="subtle" loading={checking} onClick={refreshCdp}>
                <IconRefresh size={14} />
              </ActionIcon>
            </Tooltip>
          </Group>
        </Group>

        <Text size="xs" c="dimmed">
          Quit all Chrome windows, then run this once. Apply flows then run in your real Chrome — you watch and take over
          in a normal tab.
        </Text>

        <Group gap={4} wrap="nowrap" align="flex-start">
          <Code block style={{ flex: 1, fontSize: 11, whiteSpace: "pre-wrap", wordBreak: "break-all" }}>
            {cdp?.launch_command ?? "…"}
          </Code>
          {cdp?.launch_command && (
            <CopyButton value={cdp.launch_command}>
              {({ copied, copy }) => (
                <Tooltip label={copied ? "Copied" : "Copy"}>
                  <ActionIcon variant="light" onClick={copy}>
                    {copied ? <IconCheck size={14} /> : <IconCopy size={14} />}
                  </ActionIcon>
                </Tooltip>
              )}
            </CopyButton>
          )}
        </Group>

        {cdp?.available ? (
          <>
            <Text size="xs" c="dimmed">
              Attached to {cdp.browser}. Sign in once in that window — open the pages in a new tab:
            </Text>
            <Group gap={6}>
              <Button size="compact-xs" variant="light" onClick={() => openLogin("google")}>
                Google
              </Button>
              <Button size="compact-xs" variant="light" onClick={() => openLogin("linkedin")}>
                LinkedIn
              </Button>
              <Button size="compact-xs" variant="light" onClick={() => openLogin("wellfound")}>
                Wellfound
              </Button>
            </Group>
            <Text size="xs" c="dimmed">
              Once you're signed into Google, LinkedIn/Wellfound "Continue with Google" is one click and the session sticks.
            </Text>
          </>
        ) : (
          <Text size="xs" c="dimmed">
            Not detected yet — run the command above, then hit re-check.
          </Text>
        )}
      </Stack>

      <Divider label="or save a login session" labelPosition="center" />

      <Alert variant="light" color="gray" icon={<IconInfoCircle size={15} />} p="xs">
        <Text size="xs">
          If you don't want to run Chrome yourself: log in once in a browser we open, and the session is saved locally and
          reused. Nothing is auto-submitted. Local runs only.
        </Text>
      </Alert>

      {conns.map((c) => (
        <Group key={c.provider} justify="space-between" wrap="nowrap">
          <Group gap={6}>
            <IconBrandLinkedin size={16} />
            <Text size="sm">{LABELS[c.provider] ?? c.provider}</Text>
            {c.connected ? (
              <Badge size="xs" color="teal" variant="light">
                connected
              </Badge>
            ) : cdp?.available ? (
              <Badge size="xs" color="teal" variant="light">
                via your Chrome
              </Badge>
            ) : (
              <Badge size="xs" color="gray" variant="light">
                not connected
              </Badge>
            )}
          </Group>
          <Group gap="xs">
            {pending === c.provider ? (
              <Button size="compact-xs" loading={busy === c.provider} onClick={() => finish(c.provider)}>
                I've logged in
              </Button>
            ) : (
              <Button size="compact-xs" variant="light" loading={busy === c.provider} onClick={() => start(c.provider)}>
                {c.connected ? "Reconnect" : "Connect"}
              </Button>
            )}
            {c.connected && (
              <Button size="compact-xs" variant="subtle" color="red" onClick={() => disconnect(c.provider)}>
                Disconnect
              </Button>
            )}
          </Group>
        </Group>
      ))}
    </Stack>
  );
}
