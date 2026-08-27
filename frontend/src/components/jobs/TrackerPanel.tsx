import { useEffect, useState } from "react";
import {
  ActionIcon,
  Anchor,
  Badge,
  Button,
  Group,
  Modal,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { IconExternalLink, IconPlus, IconTrash } from "@tabler/icons-react";
import { jobsApi } from "../../api/jobs";
import { useStore } from "../../state/store";
import { notify } from "../../lib/notify";
import { TRACKER_STATUSES, type Application, type TrackerStatus } from "../../types/jobs";

const STATUS_COLOR: Record<TrackerStatus, string> = {
  interested: "gray",
  preparing: "blue",
  applied: "indigo",
  interviewing: "yellow",
  offer: "teal",
  rejected: "red",
  withdrawn: "gray",
};

function fmt(iso: string) {
  return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

export default function TrackerPanel() {
  const [apps, setApps] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [adding, setAdding] = useState(false);
  const [draft, setDraft] = useState({ company: "", title: "", url: "", status: "applied" as TrackerStatus });
  const trackerVersion = useStore((s) => s.trackerVersion);

  const refresh = () =>
    jobsApi
      .listApplications()
      .then(setApps)
      .catch(() => notify.error("Could not load the tracker"))
      .finally(() => setLoading(false));

  useEffect(() => {
    refresh();
  }, [trackerVersion]);

  const patch = async (id: string, body: Parameters<typeof jobsApi.updateApplication>[1]) => {
    const updated = await jobsApi.updateApplication(id, body).catch(() => null);
    if (updated) setApps((prev) => prev.map((a) => (a.id === id ? updated : a)));
  };

  const remove = async (id: string) => {
    await jobsApi.deleteApplication(id).catch(() => {});
    setApps((prev) => prev.filter((a) => a.id !== id));
  };

  const add = async () => {
    if (!draft.company && !draft.title) return;
    try {
      const created = await jobsApi.addApplication(draft);
      setApps((prev) => [created, ...prev]);
      setDraft({ company: "", title: "", url: "", status: "applied" });
      setAdding(false);
    } catch (err) {
      notify.error(err instanceof Error ? err.message : "Could not add");
    }
  };

  const counts = TRACKER_STATUSES.map((s) => ({ s, n: apps.filter((a) => a.status === s).length })).filter((c) => c.n > 0);

  return (
    <Stack gap="md">
      <Group justify="space-between">
        <div>
          <Title order={4}>Applied jobs</Title>
          <Group gap={6} mt={4}>
            {counts.length === 0 ? (
              <Text size="xs" c="dimmed">
                Nothing tracked yet — preparing or submitting an application adds it here automatically.
              </Text>
            ) : (
              counts.map((c) => (
                <Badge key={c.s} size="sm" variant="light" color={STATUS_COLOR[c.s]}>
                  {c.s} {c.n}
                </Badge>
              ))
            )}
          </Group>
        </div>
        <Button size="xs" variant="light" leftSection={<IconPlus size={14} />} onClick={() => setAdding(true)}>
          Add manually
        </Button>
      </Group>

      {!loading && apps.length > 0 && (
        <Table.ScrollContainer minWidth={620}>
          <Table verticalSpacing="sm">
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Role</Table.Th>
                <Table.Th>Company</Table.Th>
                <Table.Th>Status</Table.Th>
                <Table.Th>Updated</Table.Th>
                <Table.Th>Notes</Table.Th>
                <Table.Th />
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {apps.map((a) => (
                <Table.Tr key={a.id}>
                  <Table.Td>
                    <Group gap={6} wrap="nowrap">
                      <Text size="sm">{a.title || "—"}</Text>
                      {a.url && (
                        <Anchor href={a.url} target="_blank" rel="noreferrer">
                          <IconExternalLink size={13} />
                        </Anchor>
                      )}
                    </Group>
                  </Table.Td>
                  <Table.Td>
                    <Text size="sm">{a.company || "—"}</Text>
                  </Table.Td>
                  <Table.Td>
                    <Select
                      size="xs"
                      w={130}
                      data={TRACKER_STATUSES.map((s) => ({ value: s, label: s }))}
                      value={a.status}
                      onChange={(v) => v && patch(a.id, { status: v as TrackerStatus })}
                      comboboxProps={{ withinPortal: true }}
                    />
                  </Table.Td>
                  <Table.Td>
                    <Text size="xs" c="dimmed">
                      {fmt(a.updated_at)}
                    </Text>
                  </Table.Td>
                  <Table.Td>
                    <TextInput
                      size="xs"
                      placeholder="notes…"
                      defaultValue={a.notes}
                      onBlur={(e) => e.currentTarget.value !== a.notes && patch(a.id, { notes: e.currentTarget.value })}
                    />
                  </Table.Td>
                  <Table.Td>
                    <ActionIcon variant="subtle" color="red" onClick={() => remove(a.id)} aria-label="Remove">
                      <IconTrash size={14} />
                    </ActionIcon>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      )}

      <Modal opened={adding} onClose={() => setAdding(false)} title="Add an application" centered>
        <Stack>
          <TextInput label="Company" value={draft.company} onChange={(e) => setDraft({ ...draft, company: e.currentTarget.value })} />
          <TextInput label="Role" value={draft.title} onChange={(e) => setDraft({ ...draft, title: e.currentTarget.value })} />
          <TextInput label="URL" value={draft.url} onChange={(e) => setDraft({ ...draft, url: e.currentTarget.value })} />
          <Select
            label="Status"
            data={TRACKER_STATUSES.map((s) => ({ value: s, label: s }))}
            value={draft.status}
            onChange={(v) => v && setDraft({ ...draft, status: v as TrackerStatus })}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setAdding(false)}>
              Cancel
            </Button>
            <Button onClick={add}>Add</Button>
          </Group>
        </Stack>
      </Modal>
    </Stack>
  );
}
