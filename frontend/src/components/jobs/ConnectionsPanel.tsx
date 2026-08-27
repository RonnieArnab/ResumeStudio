import { useEffect, useState } from "react";
import { Alert, Badge, Button, Group, Stack, Text } from "@mantine/core";
import { IconBrandLinkedin, IconInfoCircle } from "@tabler/icons-react";
import { jobsApi } from "../../api/jobs";
import { notify } from "../../lib/notify";
import type { ConnectionStatus, Provider } from "../../types/jobs";

const LABELS: Record<string, string> = { linkedin: "LinkedIn", wellfound: "Wellfound" };

export default function ConnectionsPanel() {
  const [conns, setConns] = useState<ConnectionStatus[]>([]);
  const [pending, setPending] = useState<Provider | null>(null);
  const [busy, setBusy] = useState<Provider | null>(null);

  const refresh = () => jobsApi.listConnections().then(setConns).catch(() => {});

  useEffect(() => {
    refresh();
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

  return (
    <Stack gap="sm">
      <Alert variant="light" color="gray" icon={<IconInfoCircle size={15} />} p="xs">
        <Text size="xs">
          Log in once in a visible browser; the session is saved locally and reused to open applications. Nothing is
          auto-submitted. Requires running the app locally.
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
