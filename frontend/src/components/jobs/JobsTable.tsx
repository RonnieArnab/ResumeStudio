import { useMemo, useState } from "react";
import { Badge, Group, RingProgress, ScrollArea, Table, Text, TextInput, Center } from "@mantine/core";
import { IconSearch } from "@tabler/icons-react";
import type { RankedJob } from "../../types/jobs";
import { scoreColor } from "./scoreColor";

interface JobsTableProps {
  jobs: RankedJob[];
  onSelect: (jobId: string) => void;
}

type SortKey = "score" | "title" | "company";

export default function JobsTable({ jobs, onSelect }: JobsTableProps) {
  const [q, setQ] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("score");
  const [asc, setAsc] = useState(false);

  const rows = useMemo(() => {
    const filtered = jobs.filter((r) => {
      if (!q.trim()) return true;
      const hay = `${r.job.title} ${r.job.company} ${r.job.location}`.toLowerCase();
      return hay.includes(q.toLowerCase());
    });
    const sorted = [...filtered].sort((a, b) => {
      let cmp = 0;
      if (sortKey === "score") cmp = (a.match?.score ?? -1) - (b.match?.score ?? -1);
      else if (sortKey === "title") cmp = a.job.title.localeCompare(b.job.title);
      else cmp = a.job.company.localeCompare(b.job.company);
      return asc ? cmp : -cmp;
    });
    return sorted;
  }, [jobs, q, sortKey, asc]);

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) setAsc((v) => !v);
    else {
      setSortKey(key);
      setAsc(key !== "score");
    }
  };

  const Th = ({ k, label }: { k: SortKey; label: string }) => (
    <Table.Th style={{ cursor: "pointer" }} onClick={() => toggleSort(k)}>
      {label}
      {sortKey === k ? (asc ? " ↑" : " ↓") : ""}
    </Table.Th>
  );

  return (
    <>
      <TextInput
        leftSection={<IconSearch size={14} />}
        placeholder="Filter jobs…"
        value={q}
        onChange={(e) => setQ(e.currentTarget.value)}
        mb="sm"
      />
      <ScrollArea>
        <Table highlightOnHover stickyHeader miw={640}>
          <Table.Thead>
            <Table.Tr>
              <Th k="score" label="Match" />
              <Th k="title" label="Role" />
              <Th k="company" label="Company" />
              <Table.Th>Location</Table.Th>
              <Table.Th>Source</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {rows.map((r) => (
              <Table.Tr key={r.job.id} style={{ cursor: "pointer" }} onClick={() => onSelect(r.job.id)}>
                <Table.Td>
                  {r.match ? (
                    <RingProgress
                      size={44}
                      thickness={4}
                      roundCaps
                      sections={[{ value: r.match.score, color: scoreColor(r.match.verdict, r.match.score) }]}
                      label={
                        <Center>
                          <Text size="xs" fw={700}>
                            {r.match.score}
                          </Text>
                        </Center>
                      }
                    />
                  ) : (
                    <Text c="dimmed" size="sm">
                      —
                    </Text>
                  )}
                </Table.Td>
                <Table.Td>
                  <Text size="sm" fw={500}>
                    {r.job.title}
                  </Text>
                  {r.match?.summary && (
                    <Text size="xs" c="dimmed" lineClamp={2}>
                      {r.match.summary}
                    </Text>
                  )}
                </Table.Td>
                <Table.Td>
                  <Text size="sm">{r.job.company}</Text>
                </Table.Td>
                <Table.Td>
                  <Text size="sm" c="dimmed">
                    {r.job.location || "—"}
                  </Text>
                </Table.Td>
                <Table.Td>
                  <Group gap={4}>
                    <Badge size="sm" variant="light">
                      {r.job.provider}
                    </Badge>
                    {r.job.remote && (
                      <Badge size="sm" variant="light" color="teal">
                        remote
                      </Badge>
                    )}
                  </Group>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </ScrollArea>
      {rows.length === 0 && (
        <Text c="dimmed" size="sm" ta="center" py="xl">
          No jobs. Add board sources and run a crawl.
        </Text>
      )}
    </>
  );
}
