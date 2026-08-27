import type { ReactNode } from "react";
import {
  ActionIcon,
  AppShell,
  Group,
  SegmentedControl,
  Text,
  Tooltip,
  useComputedColorScheme,
  useMantineColorScheme,
} from "@mantine/core";
import { IconBriefcase, IconFileText, IconMoon, IconSun } from "@tabler/icons-react";
import { useStore } from "../../state/store";
import type { AppView } from "../../state/viewSlice";

function ColorSchemeToggle() {
  const { setColorScheme } = useMantineColorScheme();
  const computed = useComputedColorScheme("light", { getInitialValueInEffect: true });
  const next = computed === "dark" ? "light" : "dark";
  return (
    <Tooltip label={`Switch to ${next} mode`}>
      <ActionIcon variant="default" size="lg" aria-label="Toggle color scheme" onClick={() => setColorScheme(next)}>
        {computed === "dark" ? <IconSun size={18} /> : <IconMoon size={18} />}
      </ActionIcon>
    </Tooltip>
  );
}

interface AppLayoutProps {
  meta?: ReactNode;
  children: ReactNode;
}

export default function AppLayout({ meta, children }: AppLayoutProps) {
  const view = useStore((s) => s.view);
  const setView = useStore((s) => s.setView);

  return (
    <AppShell header={{ height: 56 }} padding={0}>
      <AppShell.Header>
        <Group h="100%" px="md" justify="space-between" wrap="nowrap">
          <Group gap="sm" wrap="nowrap">
            <Text fw={700} size="lg" style={{ letterSpacing: "-0.02em" }}>
              Resume Studio
            </Text>
            <SegmentedControl
              size="xs"
              value={view}
              onChange={(v) => setView(v as AppView)}
              data={[
                {
                  value: "resume",
                  label: (
                    <Group gap={6} wrap="nowrap">
                      <IconFileText size={14} /> Resume
                    </Group>
                  ),
                },
                {
                  value: "jobs",
                  label: (
                    <Group gap={6} wrap="nowrap">
                      <IconBriefcase size={14} /> Jobs
                    </Group>
                  ),
                },
              ]}
            />
          </Group>
          <Group gap="sm" wrap="nowrap">
            {meta && (
              <Text size="xs" c="dimmed">
                {meta}
              </Text>
            )}
            <ColorSchemeToggle />
          </Group>
        </Group>
      </AppShell.Header>
      {/* height:100dvh + AppShell's own 56px header padding-top => content box is
          exactly the viewport minus the header. Views scroll internally. */}
      <AppShell.Main h="100dvh" style={{ overflow: "hidden" }}>
        {children}
      </AppShell.Main>
    </AppShell>
  );
}
