import { useEffect, useState } from "react";
import { Button, Code, NumberInput, ScrollArea, Select, Stack, Switch, Text, Textarea, TextInput } from "@mantine/core";
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
    case "filtered":
      return `  ${e.slug}: dropped ${e.dropped_old} older than the window`;
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

const RECENCY = [
  { value: "0", label: "Any time" },
  { value: "1", label: "Past 24 hours" },
  { value: "3", label: "Past 3 days" },
  { value: "7", label: "Past week" },
  { value: "30", label: "Past month" },
];

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
  const [postedWithin, setPostedWithin] = useState("7");
  const [years, setYears] = useState<number | string>("");

  // prefill target experience from the saved profile
  useEffect(() => {
    jobsApi
      .getProfile()
      .then((p) => {
        const n = parseInt(String(p.years_experience || "").replace(/[^\d]/g, ""), 10);
        if (!Number.isNaN(n)) setYears(n);
      })
      .catch(() => {});
  }, []);

  const filters = () => ({
    min_score: Number(minScore) || 0,
    location_contains: location || undefined,
    remote_only: remoteOnly,
    posted_within_days: Number(postedWithin) || null,
    target_years_experience: years === "" ? null : Number(years),
  });

  const run = async () => {
    if (sources.length === 0) return;
    setCrawling(true);
    setCrawlLog([]);
    try {
      await jobsApi.crawl(
        {
          resume_session_id: session?.session_id ?? null,
          resume_text: session ? null : resumeText || null,
          ...filters(),
        },
        (e) => appendCrawlLog(describe(e)),
      );
      setJobs(await jobsApi.listJobs(filters()));
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

      <Select label="Posted" size="xs" data={RECENCY} value={postedWithin} onChange={(v) => setPostedWithin(v || "0")} />
      <NumberInput
        label="Target experience (years)"
        description="Ranks roles near your level higher"
        size="xs"
        min={0}
        max={40}
        value={years}
        onChange={setYears}
        placeholder="from your resume"
      />
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
