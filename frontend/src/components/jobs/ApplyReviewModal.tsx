import { useMemo, useState } from "react";
import {
  Alert,
  Badge,
  Button,
  Checkbox,
  Group,
  Image,
  Modal,
  ScrollArea,
  Select,
  Stack,
  Table,
  Tabs,
  Text,
  Textarea,
  TextInput,
} from "@mantine/core";
import { IconAlertTriangle, IconCircleCheck } from "@tabler/icons-react";
import { jobsApi } from "../../api/jobs";
import { useStore } from "../../state/store";
import { notify } from "../../lib/notify";
import type { FormField } from "../../types/jobs";

const SOURCE_COLOR: Record<string, string> = {
  profile: "teal",
  generated: "yellow",
  default: "blue",
  user: "grape",
  empty: "gray",
};

export default function ApplyReviewModal() {
  const run = useStore((s) => s.applyRun);
  const setApplyRun = useStore((s) => s.setApplyRun);
  const bumpTracker = useStore((s) => s.bumpTracker);
  const [edits, setEdits] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [confirming, setConfirming] = useState(false);

  const dirty = useMemo(() => Object.keys(edits).length > 0, [edits]);
  const opened = run !== null;

  const close = async () => {
    // For manual_only (LinkedIn/Wellfound) runs, leave the user's browser window open.
    if (run && run.status !== "submitted" && !run.manual_only) {
      await jobsApi.cancelApply(run.run_id).catch(() => {});
    }
    setApplyRun(null);
    setEdits({});
    setConfirming(false);
  };

  if (!run) return <Modal opened={false} onClose={() => {}} title="" children={null} />;

  const valueOf = (f: FormField) => (f.selector in edits ? edits[f.selector] : f.value);
  const submitted = run.status === "submitted";
  const canSubmit = run.status === "ready_for_review" && !run.captcha_detected && !run.manual_only && !dirty;

  const applyEdits = async () => {
    setBusy(true);
    try {
      setApplyRun(await jobsApi.editFields(run.run_id, edits));
      setEdits({});
    } catch (err) {
      notify.error(err instanceof Error ? err.message : "Update failed");
    } finally {
      setBusy(false);
    }
  };

  const submit = async () => {
    setBusy(true);
    try {
      setApplyRun(await jobsApi.submitApply(run.run_id));
      setConfirming(false);
      bumpTracker();
      notify.success("Application submitted");
    } catch (err) {
      notify.error(err instanceof Error ? err.message : "Submit failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal opened={opened} onClose={close} title={`Review · ${run.job_title} · ${run.company}`} size="90%" centered>
      <Stack gap="md">
        <Group gap="xs">
          <Badge variant="light">{run.status}</Badge>
        </Group>

        {run.manual_only && (
          <Alert color="blue" icon={<IconAlertTriangle size={16} />} title="Finish in the open Chrome window">
            A visible Google Chrome window is open and has been driven through{" "}
            {run.steps.length > 1 ? `${run.steps.length} steps` : "the first page"} of this application. Review the
            captures below, then complete and submit it in that window yourself.
          </Alert>
        )}

        {run.captcha_detected && !run.manual_only && (
          <Alert color="yellow" icon={<IconAlertTriangle size={16} />} title="CAPTCHA present">
            This form has a bot check and can't be auto-submitted — open the posting and finish it yourself.
          </Alert>
        )}

        {run.notes.length > 0 && (
          <Alert color="gray" variant="light">
            <Stack gap={2}>
              {run.notes.map((n, i) => (
                <Text key={i} size="xs">
                  · {n}
                </Text>
              ))}
            </Stack>
          </Alert>
        )}

        {submitted && (
          <Alert color="teal" icon={<IconCircleCheck size={16} />} title="Submitted">
            {run.confirmation_text}
          </Alert>
        )}

        {run.steps.length > 1 ? (
          <Stack gap="xs">
            <Text size="sm" fw={600}>
              Walkthrough — {run.steps.length} steps captured
            </Text>
            <Tabs defaultValue="0" keepMounted={false}>
              <Tabs.List>
                {run.steps.map((s) => (
                  <Tabs.Tab key={s.index} value={String(s.index)}>
                    {s.index + 1}. {s.title}
                  </Tabs.Tab>
                ))}
              </Tabs.List>
              {run.steps.map((s) => (
                <Tabs.Panel key={s.index} value={String(s.index)} pt="xs">
                  {s.note && (
                    <Text size="xs" c="dimmed" mb={6}>
                      {s.note}
                    </Text>
                  )}
                  <ScrollArea.Autosize mah={460} type="auto" style={{ border: "1px solid var(--mantine-color-default-border)", borderRadius: 8 }}>
                    <Image src={s.screenshot_url} alt={s.title} />
                  </ScrollArea.Autosize>
                </Tabs.Panel>
              ))}
            </Tabs>
          </Stack>
        ) : (
          <ScrollArea.Autosize mah={360} type="auto" style={{ border: "1px solid var(--mantine-color-default-border)", borderRadius: 8 }}>
            <Image src={run.screenshot_url} alt="Filled application form" />
          </ScrollArea.Autosize>
        )}

        {!submitted && (
          <>
            <ScrollArea.Autosize mah={320}>
              <Table stickyHeader withRowBorders>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Field</Table.Th>
                    <Table.Th>Value</Table.Th>
                    <Table.Th>From</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {run.fields.map((f) => (
                    <Table.Tr key={f.selector}>
                      <Table.Td>
                        <Text size="xs">
                          {f.label}
                          {f.required ? " *" : ""}
                        </Text>
                      </Table.Td>
                      <Table.Td>
                        {f.kind === "select" || f.kind === "radio" ? (
                          <Select
                            size="xs"
                            data={f.options.map((o) => ({ value: o, label: o }))}
                            value={valueOf(f) || null}
                            onChange={(v) => setEdits({ ...edits, [f.selector]: v ?? "" })}
                            clearable
                            searchable
                          />
                        ) : f.kind === "checkbox" ? (
                          <Checkbox
                            size="xs"
                            checked={["true", "yes", "1", "on"].includes(valueOf(f).toLowerCase())}
                            onChange={(e) => setEdits({ ...edits, [f.selector]: e.currentTarget.checked ? "true" : "false" })}
                          />
                        ) : f.kind === "file" ? (
                          <Text size="xs" c="dimmed">
                            {f.value || "(no file)"}
                          </Text>
                        ) : f.kind === "textarea" ? (
                          <Textarea size="xs" autosize minRows={1} maxRows={4} value={valueOf(f)} onChange={(e) => setEdits({ ...edits, [f.selector]: e.currentTarget.value })} />
                        ) : (
                          <TextInput size="xs" value={valueOf(f)} onChange={(e) => setEdits({ ...edits, [f.selector]: e.currentTarget.value })} />
                        )}
                      </Table.Td>
                      <Table.Td>
                        <Badge size="xs" variant="light" color={SOURCE_COLOR[f.source] ?? "gray"}>
                          {f.source}
                        </Badge>
                      </Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </ScrollArea.Autosize>

            <Group justify="space-between">
              <Button variant="default" onClick={close}>
                Cancel
              </Button>
              <Group gap="xs">
                <Button variant="light" onClick={applyEdits} disabled={!dirty} loading={busy}>
                  Apply edits to form
                </Button>
                {!confirming ? (
                  <Button color="teal" disabled={!canSubmit} loading={busy} onClick={() => setConfirming(true)}>
                    Submit application
                  </Button>
                ) : (
                  <Group gap="xs">
                    <Text size="xs" c="dimmed">
                      Submit for real?
                    </Text>
                    <Button color="teal" loading={busy} onClick={submit}>
                      Yes, submit
                    </Button>
                    <Button variant="subtle" onClick={() => setConfirming(false)}>
                      No
                    </Button>
                  </Group>
                )}
              </Group>
            </Group>
            {dirty && (
              <Text size="xs" c="dimmed">
                Apply your edits to the form before submitting.
              </Text>
            )}
          </>
        )}

        {submitted && (
          <Group justify="flex-end">
            <Button onClick={close}>Close</Button>
          </Group>
        )}
      </Stack>
    </Modal>
  );
}
