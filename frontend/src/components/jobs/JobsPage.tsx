import { useEffect } from "react";
import { Accordion, Grid, ScrollArea, Tabs } from "@mantine/core";
import { IconAdjustments, IconBriefcase, IconLink, IconPlugConnected, IconUser } from "@tabler/icons-react";
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
      <Grid gutter={0} h="100%" style={{ overflow: "hidden" }}>
        <Grid.Col span={{ base: 12, md: 3.5 }} h="100%" style={{ borderRight: "1px solid var(--mantine-color-default-border)", overflow: "hidden" }}>
          <ScrollArea h="100%" p="sm">
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
        </Grid.Col>

        <Grid.Col span={{ base: 12, md: 8.5 }} h="100%" style={{ overflow: "hidden" }}>
          <Tabs defaultValue="jobs" h="100%" style={{ display: "flex", flexDirection: "column" }}>
            <Tabs.List>
              <Tabs.Tab value="jobs" leftSection={<IconBriefcase size={14} />}>
                Jobs ({jobs.length})
              </Tabs.Tab>
              <Tabs.Tab value="profile" leftSection={<IconUser size={14} />}>
                Profile
              </Tabs.Tab>
            </Tabs.List>
            <Tabs.Panel value="jobs" style={{ flex: 1, overflow: "hidden" }}>
              <ScrollArea h="100%" p="md">
                <JobsTable jobs={jobs} onSelect={selectJob} />
              </ScrollArea>
            </Tabs.Panel>
            <Tabs.Panel value="profile" style={{ flex: 1, overflow: "hidden" }}>
              <ScrollArea h="100%" p="md">
                <ProfilePanel />
              </ScrollArea>
            </Tabs.Panel>
          </Tabs>
        </Grid.Col>
      </Grid>

      <JobDetailDrawer />
      <ApplyReviewModal />
    </>
  );
}
