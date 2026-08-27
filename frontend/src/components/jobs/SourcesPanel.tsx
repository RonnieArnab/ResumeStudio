import { useState } from "react";
import {
  ActionIcon,
  Autocomplete,
  Badge,
  Button,
  Group,
  Stack,
  Table,
  Tabs,
  Text,
  TextInput,
} from "@mantine/core";
import { IconBuildingSkyscraper, IconLink, IconSearch, IconTrash } from "@tabler/icons-react";
import { jobsApi } from "../../api/jobs";
import { useStore } from "../../state/store";
import { notify } from "../../lib/notify";
import type { RegistryEntry } from "../../types/jobs";

export default function SourcesPanel() {
  const sources = useStore((s) => s.sources);
  const setSources = useStore((s) => s.setSources);
  const [busy, setBusy] = useState(false);

  const [ref, setRef] = useState("");
  const [companyQuery, setCompanyQuery] = useState("");
  const [companyOptions, setCompanyOptions] = useState<RegistryEntry[]>([]);
  const [kw, setKw] = useState("");
  const [loc, setLoc] = useState("");

  const refresh = async () => setSources(await jobsApi.listSources());

  const guard = async (fn: () => Promise<unknown>) => {
    setBusy(true);
    try {
      await fn();
      await refresh();
    } catch (err) {
      notify.error(err instanceof Error ? err.message : "Could not add source");
    } finally {
      setBusy(false);
    }
  };

  const addBoard = () => ref.trim() && guard(() => jobsApi.addSource(ref.trim()).then(() => setRef("")));

  const onCompanySearch = async (value: string) => {
    setCompanyQuery(value);
    if (value.trim().length < 1) return setCompanyOptions([]);
    try {
      setCompanyOptions(await jobsApi.searchRegistry(value));
    } catch {
      setCompanyOptions([]);
    }
  };

  const addCompany = (name: string) => {
    const entry = companyOptions.find((e) => e.name === name);
    if (!entry) return;
    void guard(() => jobsApi.addSource(`${entry.provider}:${entry.slug}`, entry.name).then(() => setCompanyQuery("")));
  };

  const addSearch = () =>
    kw.trim() && guard(() => jobsApi.addSearchSource("linkedin", kw.trim(), loc.trim()).then(() => { setKw(""); setLoc(""); }));

  const remove = (id: string) => guard(() => jobsApi.removeSource(id));

  return (
    <Stack gap="sm">
      <Tabs defaultValue="company" variant="pills">
        <Tabs.List grow>
          <Tabs.Tab value="company" leftSection={<IconBuildingSkyscraper size={13} />}>
            Company
          </Tabs.Tab>
          <Tabs.Tab value="board" leftSection={<IconLink size={13} />}>
            Board URL
          </Tabs.Tab>
          <Tabs.Tab value="search" leftSection={<IconSearch size={13} />}>
            LinkedIn
          </Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="company" pt="xs">
          <Autocomplete
            placeholder="Search companies (Stripe, OpenAI, Ramp…)"
            value={companyQuery}
            data={companyOptions.map((e) => e.name)}
            onChange={onCompanySearch}
            onOptionSubmit={addCompany}
            disabled={busy}
          />
          <Text size="xs" c="dimmed" mt={4}>
            Curated Greenhouse / Lever / Ashby boards.
          </Text>
        </Tabs.Panel>

        <Tabs.Panel value="board" pt="xs">
          <Group gap="xs" wrap="nowrap">
            <TextInput
              style={{ flex: 1 }}
              placeholder="boards.greenhouse.io/stripe  or  lever:netflix"
              value={ref}
              onChange={(e) => setRef(e.currentTarget.value)}
              onKeyDown={(e) => e.key === "Enter" && addBoard()}
            />
            <Button onClick={addBoard} loading={busy}>
              Add
            </Button>
          </Group>
        </Tabs.Panel>

        <Tabs.Panel value="search" pt="xs">
          <Stack gap="xs">
            <TextInput placeholder="Keywords (e.g. backend engineer)" value={kw} onChange={(e) => setKw(e.currentTarget.value)} />
            <TextInput placeholder="Location (e.g. Remote, United States)" value={loc} onChange={(e) => setLoc(e.currentTarget.value)} />
            <Button onClick={addSearch} loading={busy}>
              Add LinkedIn search
            </Button>
            <Text size="xs" c="dimmed">
              Uses LinkedIn's public guest search — unofficial and rate-limited. Applying opens Easy Apply in your connected browser.
            </Text>
          </Stack>
        </Tabs.Panel>
      </Tabs>

      {sources.length > 0 && (
        <Table>
          <Table.Tbody>
            {sources.map((s) => (
              <Table.Tr key={s.id}>
                <Table.Td>
                  <Badge size="sm" variant="light" mr={6}>
                    {s.provider}
                  </Badge>
                  {s.kind === "search" ? s.label : s.slug}
                </Table.Td>
                <Table.Td width={40}>
                  <ActionIcon variant="subtle" color="red" onClick={() => remove(s.id)} aria-label="Remove source">
                    <IconTrash size={15} />
                  </ActionIcon>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}
    </Stack>
  );
}
