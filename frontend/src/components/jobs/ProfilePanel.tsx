import { useEffect, useState } from "react";
import { Button, Card, FileButton, Group, Progress, Select, SimpleGrid, Stack, Text, Textarea, TextInput, Title } from "@mantine/core";
import { jobsApi } from "../../api/jobs";
import { useStore } from "../../state/store";
import { notify } from "../../lib/notify";
import type { ApplicantProfile } from "../../types/jobs";

const FIELDS: { key: keyof ApplicantProfile; label: string }[] = [
  { key: "full_name", label: "Full name" },
  { key: "email", label: "Email" },
  { key: "phone", label: "Phone" },
  { key: "location", label: "Location (city, country)" },
  { key: "linkedin_url", label: "LinkedIn URL" },
  { key: "github_url", label: "GitHub URL" },
  { key: "portfolio_url", label: "Portfolio / website" },
  { key: "years_experience", label: "Years of experience" },
  { key: "pronouns", label: "Pronouns" },
  { key: "work_authorization", label: "Work authorization statement" },
];

const COMPLETENESS_KEYS: (keyof ApplicantProfile)[] = [
  "full_name", "email", "phone", "location", "linkedin_url", "work_authorization", "resume_pdf_path",
];

export default function ProfilePanel() {
  const session = useStore((s) => s.session);
  const [profile, setProfile] = useState<ApplicantProfile | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    jobsApi.getProfile().then(setProfile).catch(() => notify.error("Could not load profile"));
  }, []);

  if (!profile) return <Text c="dimmed">Loading profile…</Text>;

  const set = (key: keyof ApplicantProfile, value: unknown) => setProfile({ ...profile, [key]: value });

  const filled = COMPLETENESS_KEYS.filter((k) => Boolean(profile[k])).length;
  const pct = Math.round((filled / COMPLETENESS_KEYS.length) * 100);

  const save = async () => {
    setSaving(true);
    try {
      setProfile(await jobsApi.saveProfile(profile));
      notify.success("Profile saved");
    } catch (err) {
      notify.error(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const useSessionResume = async () => {
    if (!session) return;
    try {
      setProfile(await jobsApi.setResumeFromSession(session.session_id));
      notify.success("Resume attached from current session");
    } catch (err) {
      notify.error(err instanceof Error ? err.message : "Failed");
    }
  };

  const upload = async (file: File | null) => {
    if (!file) return;
    try {
      setProfile(await jobsApi.uploadResume(file));
      notify.success("Resume uploaded");
    } catch (err) {
      notify.error(err instanceof Error ? err.message : "Upload failed");
    }
  };

  return (
    <Stack gap="lg" maw={720}>
      <div>
        <Title order={4}>Applicant profile</Title>
        <Text size="sm" c="dimmed">
          Used to auto-fill application forms. Stored on the backend only.
        </Text>
      </div>

      <Card withBorder padding="sm" radius="md">
        <Group justify="space-between" mb={4}>
          <Text size="sm" fw={500}>
            Profile completeness
          </Text>
          <Text size="sm" c="dimmed">
            {pct}%
          </Text>
        </Group>
        <Progress value={pct} color={pct === 100 ? "teal" : "indigo"} />
      </Card>

      <SimpleGrid cols={{ base: 1, sm: 2 }}>
        {FIELDS.map((f) => (
          <TextInput
            key={f.key}
            label={f.label}
            value={(profile[f.key] as string) ?? ""}
            onChange={(e) => set(f.key, e.currentTarget.value)}
          />
        ))}
      </SimpleGrid>

      <Select
        label="Requires visa sponsorship?"
        data={[
          { value: "", label: "Unspecified" },
          { value: "no", label: "No" },
          { value: "yes", label: "Yes" },
        ]}
        value={profile.requires_sponsorship === null ? "" : profile.requires_sponsorship ? "yes" : "no"}
        onChange={(v) => set("requires_sponsorship", v === "" || v === null ? null : v === "yes")}
        maw={280}
      />

      <Textarea
        label='Default answer for "why this company" / cover-letter questions'
        autosize
        minRows={3}
        value={profile.cover_letter_blurb}
        onChange={(e) => set("cover_letter_blurb", e.currentTarget.value)}
      />

      <Card withBorder padding="sm" radius="md">
        <Text size="sm" fw={500} mb={4}>
          Resume PDF
        </Text>
        <Text size="xs" c="dimmed" mb="xs">
          {profile.resume_pdf_path ? `Attached: ${profile.resume_source_label ?? profile.resume_pdf_path}` : "None attached"}
        </Text>
        <Group gap="xs">
          {session && (
            <Button size="xs" variant="light" onClick={useSessionResume}>
              Use current resume session
            </Button>
          )}
          <FileButton onChange={upload} accept="application/pdf">
            {(props) => (
              <Button size="xs" variant="light" {...props}>
                Upload PDF
              </Button>
            )}
          </FileButton>
        </Group>
      </Card>

      <Group>
        <Button onClick={save} loading={saving}>
          Save profile
        </Button>
      </Group>
    </Stack>
  );
}
