import { useState } from "react";
import { Button, Code, NumberInput, ScrollArea, Stack, Switch, Text, Textarea, TextInput } from "@mantine/core";
import { jobsApi } from "../../api/jobs";
import { useStore } from "../../state/store";
import { notify } from "../../lib/notify";
import type { CrawlEvent } from "../../types/jobs";

function describe(e: CrawlEvent): string {
  switch (e.type) {
    case "board_started":
      return `→ ${e.label}…`;
    case "jobs_found":
      return `  ${e.slug}: ${e.count} postings`;
    case "board_error":
      return `  ✗ ${e.slug}: ${e.error}`;
    case "job_scored":
      if (e.skipped) return `  · ${e.title} — skipped`;
      if (e.capped) return `  · ${e.title} — not scored (cap)`;
      return `  ${e.score}  ${e.title}`;
    case "done":
      return `✓ ${e.jobs} postings, ${e.scored} scored${e.message ? ` — ${e.message}` : ""}`;
  }
}

export default function CrawlPanel() {
  const session = useStore((s) => s.session);
  const sources = useStore((s) => s.sources);
  const setJobs = useStore((s) => s.setJobs);
  const crawling = useStore((s) => s.crawling);
  const setCrawling = useStore((s) => s.setCrawling);
  const crawlLog = useStore((s) => s.crawlLog);
  const setCrawlLog = useStore((s) => s.setCrawlLog);
  const appendCrawlLog = useStore((s) => s.appendCrawlLog);

  const [resumeText, setResumeText] = useState("");
  const [minScore, setMinScore] = useState<number | string>(0);
  const [location, setLocation] = useState("");
  const [remoteOnly, setRemoteOnly] = useState(false);

  const run = async () => {
    if (sources.length === 0) return;
    setCrawling(true);
    setCrawlLog([]);
    try {
      await jobsApi.crawl(
        {
          resume_session_id: session?.session_id ?? null,
          resume_text: session ? null : resumeText || null,
          min_score: Number(minScore) || 0,
          location_contains: location || undefined,
          remote_only: remoteOnly,
        },
        (e) => appendCrawlLog(describe(e)),
      );
      setJobs(await jobsApi.listJobs({ min_score: Number(minScore) || 0, location_contains: location || undefined, remote_only: remoteOnly }));
      notify.success("Crawl complete");
    } catch (err) {
      notify.error(err instanceof Error ? err.message : "Crawl failed");
    } finally {
      setCrawling(false);
    }
  };

  return (
    <Stack gap="xs">
      {session ? (
        <Text size="xs" c="dimmed">
          Matching against resume session {session.session_id.slice(0, 8)}.
        </Text>
      ) : (
        <Textarea
          placeholder="No resume session open — paste your experience/resume text to enable matching (optional)."
          autosize
          minRows={2}
          maxRows={5}
          value={resumeText}
          onChange={(e) => setResumeText(e.currentTarget.value)}
        />
      )}

      <NumberInput label="Min score" min={0} max={100} value={minScore} onChange={setMinScore} size="xs" />
      <TextInput label="Location contains" value={location} onChange={(e) => setLocation(e.currentTarget.value)} size="xs" />
      <Switch label="Remote only" checked={remoteOnly} onChange={(e) => setRemoteOnly(e.currentTarget.checked)} size="xs" />

      <Button onClick={run} loading={crawling} disabled={sources.length === 0}>
        Run crawl
      </Button>

      {crawlLog.length > 0 && (
        <ScrollArea h={160}>
          <Code block fz={11}>
            {crawlLog.join("\n")}
          </Code>
        </ScrollArea>
      )}
    </Stack>
  );
}
