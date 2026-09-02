import { useEffect, useState } from "react";
import {
  Accordion,
  Badge,
  Button,
  Card,
  Center,
  Divider,
  Group,
  List,
  Progress,
  RingProgress,
  ScrollArea,
  SimpleGrid,
  Stack,
  Text,
  Textarea,
  ThemeIcon,
} from "@mantine/core";
import {
  IconAlertTriangle,
  IconCheck,
  IconMinus,
  IconRefresh,
  IconSparkles,
  IconX,
} from "@tabler/icons-react";
import { createMatchReport, getMatchReport } from "../../api/resume";
import { useStore } from "../../state/store";
import { notify } from "../../lib/notify";
import type { MatchReport, RequirementStatus } from "../../types/resume";

function tone(score: number): string {
  if (score >= 70) return "teal";
  if (score >= 45) return "yellow";
  return "red";
}

const REQ_ICON: Record<RequirementStatus, { color: string; icon: React.ReactNode }> = {
  met: { color: "teal", icon: <IconCheck size={12} /> },
  partial: { color: "yellow", icon: <IconMinus size={12} /> },
  missing: { color: "red", icon: <IconX size={12} /> },
};

function KeywordChips({ items, color }: { items: string[]; color: string }) {
  const [expanded, setExpanded] = useState(false);
  if (items.length === 0) return null;
  const shown = expanded ? items : items.slice(0, 12);
  return (
    <Group gap={4}>
      {shown.map((k) => (
        <Badge key={k} variant="light" color={color} size="sm" style={{ textTransform: "none" }}>
          {k}
        </Badge>
      ))}
      {items.length > 12 && (
        <Badge
          variant="outline"
          color="gray"
          size="sm"
          style={{ cursor: "pointer", textTransform: "none" }}
          onClick={() => setExpanded((v) => !v)}
        >
          {expanded ? "show less" : `+${items.length - 12} more`}
        </Badge>
      )}
    </Group>
  );
}

interface Props {
  sessionId: string;
}

export default function MatchReportPanel({ sessionId }: Props) {
  const jobDescription = useStore((s) => s.jobDescription);
  const setJobDescription = useStore((s) => s.setJobDescription);
  const report = useStore((s) => s.matchReport);
  const setReport = useStore((s) => s.setMatchReport);
  const selectSection = useStore((s) => s.selectSection);
  const setPendingInstruction = useStore((s) => s.setPendingSectionInstruction);

  const [loading, setLoading] = useState(false);
  const [draft, setDraft] = useState("");
  const jd = jobDescription ?? "";

  // load the cached report for this session (also clears a stale one on a new upload)
  useEffect(() => {
    getMatchReport(sessionId)
      .then((r) => setReport(r ?? null))
      .catch(() => {});
  }, [sessionId, setReport]);

  const run = async (text: string) => {
    const body = text.trim();
    if (body.length < 40) {
      notify.error("Paste the full job description first");
      return;
    }
    setLoading(true);
    try {
      setJobDescription(body);
      const r = await createMatchReport(sessionId, body);
      setReport(r);
    } catch (err) {
      notify.error(err instanceof Error ? err.message : "Could not rate the resume");
    } finally {
      setLoading(false);
    }
  };

  const tailor = (section: string, title: string, detail: string) => {
    if (!section) return;
    const goal = [title.replace(/\.\s*$/, ""), detail.replace(/\.\s*$/, "")].filter(Boolean).join(". ");
    setPendingInstruction(`Tailor this section toward the job description — ${goal}.`);
    selectSection(section);
  };

  // ---- no JD yet ----------------------------------------------------------
  if (!jd && !report) {
    return (
      <Stack gap="sm" p="sm">
        <Text size="sm" c="dimmed">
          Paste a job description and get a scored breakdown of how well your resume matches it.
        </Text>
        <Textarea
          placeholder="Paste the full job description…"
          autosize
          minRows={6}
          maxRows={16}
          value={draft}
          onChange={(e) => setDraft(e.currentTarget.value)}
        />
        <Button leftSection={<IconSparkles size={15} />} loading={loading} onClick={() => run(draft)}>
          Rate my resume
        </Button>
      </Stack>
    );
  }

  return (
    <ScrollArea h="100%" type="auto">
      <Stack gap="md" p="sm">
        <Group justify="space-between" align="flex-start" wrap="nowrap">
          <Textarea
            style={{ flex: 1 }}
            size="xs"
            autosize
            minRows={1}
            maxRows={4}
            value={draft || jd}
            onChange={(e) => setDraft(e.currentTarget.value)}
            placeholder="Job description…"
          />
          <Button
            size="xs"
            variant="light"
            leftSection={report ? <IconRefresh size={14} /> : <IconSparkles size={14} />}
            loading={loading}
            onClick={() => run(draft || jd)}
          >
            {report ? "Re-run" : "Rate"}
          </Button>
        </Group>

        {report && <Report report={report} onTailor={tailor} />}
      </Stack>
    </ScrollArea>
  );
}

function Report({
  report,
  onTailor,
}: {
  report: MatchReport;
  onTailor: (section: string, title: string, detail: string) => void;
}) {
  const kw = report.keywords;
  const metCount = report.requirements.filter((r) => r.status === "met").length;

  return (
    <Stack gap="lg">
      {/* headline */}
      <Group align="center" wrap="nowrap" gap="md">
        <RingProgress
          size={92}
          thickness={9}
          roundCaps
          sections={[{ value: report.overall_score, color: tone(report.overall_score) }]}
          label={
            <Center>
              <Stack gap={0} align="center">
                <Text fw={800} size="lg">
                  {report.overall_score}
                </Text>
                <Text size="9px" c="dimmed">
                  / 100
                </Text>
              </Stack>
            </Center>
          }
        />
        <Stack gap={2} style={{ flex: 1 }}>
          <Group gap={6}>
            <Badge color={tone(report.overall_score)} variant="filled" tt="capitalize">
              {report.verdict} match
            </Badge>
            {report.jd_title && (
              <Text size="xs" c="dimmed">
                {report.jd_title}
              </Text>
            )}
          </Group>
          <Text size="sm" fw={600}>
            {report.headline}
          </Text>
        </Stack>
      </Group>

      {report.summary && (
        <Text size="sm" c="dimmed">
          {report.summary}
        </Text>
      )}

      {/* dimension metrics */}
      <Stack gap="xs">
        <Text size="xs" fw={700} tt="uppercase" c="dimmed">
          Breakdown
        </Text>
        {report.dimensions.map((d) => (
          <div key={d.key}>
            <Group justify="space-between" mb={2}>
              <Text size="sm">{d.label}</Text>
              <Text size="sm" fw={700} c={tone(d.score)}>
                {d.score}
              </Text>
            </Group>
            <Progress value={d.score} color={tone(d.score)} size="sm" radius="xl" />
            {d.note && (
              <Text size="xs" c="dimmed" mt={2}>
                {d.note}
              </Text>
            )}
          </div>
        ))}
      </Stack>

      {/* keywords */}
      <Stack gap="xs">
        <Group justify="space-between">
          <Text size="xs" fw={700} tt="uppercase" c="dimmed">
            Keyword coverage
          </Text>
          <Text size="sm" fw={700} c={tone(kw.coverage)}>
            {kw.coverage}%
          </Text>
        </Group>
        <Progress value={kw.coverage} color={tone(kw.coverage)} size="sm" radius="xl" />
        {kw.matched.length > 0 && (
          <div>
            <Text size="xs" c="teal" fw={600} mb={3}>
              In your resume
            </Text>
            <KeywordChips items={kw.matched} color="teal" />
          </div>
        )}
        {kw.partial.length > 0 && (
          <div>
            <Text size="xs" c="yellow.7" fw={600} mb={3}>
              Weakly covered
            </Text>
            <KeywordChips items={kw.partial} color="yellow" />
          </div>
        )}
        {kw.missing.length > 0 && (
          <div>
            <Text size="xs" c="red" fw={600} mb={3}>
              Missing
            </Text>
            <KeywordChips items={kw.missing} color="red" />
          </div>
        )}
      </Stack>

      {/* requirements */}
      {report.requirements.length > 0 && (
        <Stack gap="xs">
          <Text size="xs" fw={700} tt="uppercase" c="dimmed">
            Requirements — {metCount}/{report.requirements.length} met
          </Text>
          <Stack gap={6}>
            {report.requirements.map((r, i) => (
              <Group key={i} gap={8} wrap="nowrap" align="flex-start">
                <ThemeIcon size={18} radius="xl" color={REQ_ICON[r.status].color} variant="light" mt={1}>
                  {REQ_ICON[r.status].icon}
                </ThemeIcon>
                <div style={{ flex: 1 }}>
                  <Text size="sm">{r.requirement}</Text>
                  {r.evidence && (
                    <Text size="xs" c="dimmed">
                      {r.evidence}
                    </Text>
                  )}
                </div>
              </Group>
            ))}
          </Stack>
        </Stack>
      )}

      {/* strengths / gaps */}
      {(report.strengths.length > 0 || report.gaps.length > 0) && (
        <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="sm">
          {report.strengths.length > 0 && (
            <Card withBorder radius="md" padding="sm">
              <Group gap={6} mb={4}>
                <IconCheck size={14} color="var(--mantine-color-teal-6)" />
                <Text size="sm" fw={600}>
                  Strengths
                </Text>
              </Group>
              <List size="xs" spacing={4}>
                {report.strengths.map((s, i) => (
                  <List.Item key={i}>{s}</List.Item>
                ))}
              </List>
            </Card>
          )}
          {report.gaps.length > 0 && (
            <Card withBorder radius="md" padding="sm">
              <Group gap={6} mb={4}>
                <IconAlertTriangle size={14} color="var(--mantine-color-red-6)" />
                <Text size="sm" fw={600}>
                  Gaps
                </Text>
              </Group>
              <List size="xs" spacing={4}>
                {report.gaps.map((s, i) => (
                  <List.Item key={i}>{s}</List.Item>
                ))}
              </List>
            </Card>
          )}
        </SimpleGrid>
      )}

      {/* suggestions */}
      {report.suggestions.length > 0 && (
        <Stack gap="xs">
          <Text size="xs" fw={700} tt="uppercase" c="dimmed">
            Suggested edits
          </Text>
          <Accordion variant="separated" radius="md">
            {report.suggestions.map((s, i) => (
              <Accordion.Item key={i} value={String(i)}>
                <Accordion.Control>
                  <Group gap={8} wrap="nowrap">
                    <Badge
                      size="xs"
                      color={s.priority === "high" ? "red" : s.priority === "medium" ? "yellow" : "gray"}
                    >
                      {s.priority}
                    </Badge>
                    <Text size="sm">{s.title}</Text>
                  </Group>
                </Accordion.Control>
                <Accordion.Panel>
                  <Stack gap="xs">
                    {s.detail && (
                      <Text size="sm" c="dimmed">
                        {s.detail}
                      </Text>
                    )}
                    {s.section && (
                      <Button
                        size="compact-xs"
                        variant="light"
                        leftSection={<IconSparkles size={12} />}
                        onClick={() => onTailor(s.section, s.title, s.detail)}
                      >
                        Tailor the “{s.section}” section
                      </Button>
                    )}
                  </Stack>
                </Accordion.Panel>
              </Accordion.Item>
            ))}
          </Accordion>
        </Stack>
      )}

      <Divider />
      <Text size="10px" c="dimmed">
        Generated {new Date(report.generated_at).toLocaleString()}
      </Text>
    </Stack>
  );
}
