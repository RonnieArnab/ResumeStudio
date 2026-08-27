import { useState } from "react";
import { Button, Stack, Text, TextInput } from "@mantine/core";
import { jobsApi } from "../../api/jobs";
import { useStore } from "../../state/store";
import { notify } from "../../lib/notify";

export default function PasteUrlCard() {
  const session = useStore((s) => s.session);
  const setApplyRun = useStore((s) => s.setApplyRun);
  const bumpTracker = useStore((s) => s.bumpTracker);
  const [url, setUrl] = useState("");
  const [busy, setBusy] = useState(false);

  const go = async () => {
    if (!url.trim()) return;
    setBusy(true);
    try {
      setApplyRun(await jobsApi.prepareApplyUrl(url.trim(), undefined, session?.session_id ?? null));
      setUrl("");
      bumpTracker();
    } catch (err) {
      notify.error(err instanceof Error ? err.message : "Could not open that URL");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Stack gap="xs">
      <TextInput
        placeholder="https://…/careers/apply/…"
        value={url}
        onChange={(e) => setUrl(e.currentTarget.value)}
        onKeyDown={(e) => e.key === "Enter" && go()}
      />
      <Button onClick={go} loading={busy} disabled={!url.trim()}>
        Open &amp; fill form
      </Button>
      <Text size="xs" c="dimmed">
        Paste any job application URL — the browser fills what it can and stops for your review.
      </Text>
    </Stack>
  );
}
