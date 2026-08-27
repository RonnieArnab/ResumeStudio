import { useEffect } from "react";
import { Accordion, ScrollArea, Tabs } from "@mantine/core";
import { IconAdjustments, IconBriefcase, IconChecklist, IconLink, IconPlugConnected, IconUser } from "@tabler/icons-react";
import { jobsApi } from "../../api/jobs";
import { useStore } from "../../state/store";
import ApplyReviewModal from "./ApplyReviewModal";
import ConnectionsPanel from "./ConnectionsPanel";
import CrawlPanel from "./CrawlPanel";
import JobDetailDrawer from "./JobDetailDrawer";
import JobsTable from "./JobsTable";
import PasteUrlCard from "./PasteUrlCard";
import ProfilePanel from "./ProfilePanel";
import SourcesPanel from "./SourcesPanel";
import TrackerPanel from "./TrackerPanel";

const fill = { height: "100%", minHeight: 0, overflow: "hidden" } as const;

export default function JobsPage() {
  const jobs = useStore((s) => s.jobs);
  const setJobs = useStore((s) => s.setJobs);
  const setSources = useStore((s) => s.setSources);
  const selectJob = useStore((s) => s.selectJob);

  useEffect(() => {
    jobsApi.listSources().then(setSources).catch(() => {});
    jobsApi.listJobs().then(setJobs).catch(() => {});
  }, [setSources, setJobs]);

  return (
    <>
      <div style={{ display: "flex", ...fill }}>
        <aside
          style={{
            width: 360,
            flexShrink: 0,
            borderRight: "1px solid var(--mantine-color-default-border)",
            ...fill,
          }}
        >
          <ScrollArea h="100%" p="sm" type="auto">
            <Accordion multiple defaultValue={["sources", "crawl"]} variant="separated">
              <Accordion.Item value="sources">
                <Accordion.Control icon={<IconAdjustments size={16} />}>Sources</Accordion.Control>
                <Accordion.Panel>
                  <SourcesPanel />
                </Accordion.Panel>
              </Accordion.Item>
              <Accordion.Item value="crawl">
                <Accordion.Control icon={<IconBriefcase size={16} />}>Crawl</Accordion.Control>
                <Accordion.Panel>
                  <CrawlPanel />
                </Accordion.Panel>
              </Accordion.Item>
              <Accordion.Item value="paste">
                <Accordion.Control icon={<IconLink size={16} />}>Apply from a URL</Accordion.Control>
                <Accordion.Panel>
                  <PasteUrlCard />
                </Accordion.Panel>
              </Accordion.Item>
              <Accordion.Item value="connections">
                <Accordion.Control icon={<IconPlugConnected size={16} />}>Connections</Accordion.Control>
                <Accordion.Panel>
                  <ConnectionsPanel />
                </Accordion.Panel>
              </Accordion.Item>
            </Accordion>
          </ScrollArea>
        </aside>

        <div style={{ flex: 1, minWidth: 0, ...fill }}>
          <Tabs defaultValue="jobs" style={{ display: "flex", flexDirection: "column", ...fill }}>
            <Tabs.List>
              <Tabs.Tab value="jobs" leftSection={<IconBriefcase size={14} />}>
                Jobs ({jobs.length})
              </Tabs.Tab>
              <Tabs.Tab value="tracker" leftSection={<IconChecklist size={14} />}>
                Applied
              </Tabs.Tab>
              <Tabs.Tab value="profile" leftSection={<IconUser size={14} />}>
                Profile
              </Tabs.Tab>
            </Tabs.List>

            <Tabs.Panel value="jobs" style={{ flex: 1, minHeight: 0 }}>
              <ScrollArea h="100%" p="md" type="auto">
                <JobsTable jobs={jobs} onSelect={selectJob} />
              </ScrollArea>
            </Tabs.Panel>
            <Tabs.Panel value="tracker" style={{ flex: 1, minHeight: 0 }}>
              <ScrollArea h="100%" p="md" type="auto">
                <TrackerPanel />
              </ScrollArea>
            </Tabs.Panel>
            <Tabs.Panel value="profile" style={{ flex: 1, minHeight: 0 }}>
              <ScrollArea h="100%" p="md" type="auto">
                <ProfilePanel />
              </ScrollArea>
            </Tabs.Panel>
          </Tabs>
        </div>
      </div>

      <JobDetailDrawer />
      <ApplyReviewModal />
    </>
  );
}
