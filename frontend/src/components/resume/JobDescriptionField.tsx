import { useState } from "react";
import { Badge, Button, Group, Textarea } from "@mantine/core";
import { IconX } from "@tabler/icons-react";
import { useStore } from "../../state/store";

export default function JobDescriptionField() {
  const jobDescription = useStore((s) => s.jobDescription);
  const setJobDescription = useStore((s) => s.setJobDescription);
  const [draft, setDraft] = useState("");
  const [open, setOpen] = useState(false);

  if (jobDescription && !open) {
    return (
      <Group gap="xs">
        <Badge
          variant="light"
          rightSection={
            <IconX
              size={12}
              style={{ cursor: "pointer" }}
              onClick={() => {
                setJobDescription(null);
                setDraft("");
              }}
            />
          }
        >
          JD attached · {(jobDescription.length / 1024).toFixed(1)} kb
        </Badge>
        <Button size="compact-xs" variant="subtle" onClick={() => setOpen(true)}>
          edit
        </Button>
      </Group>
    );
  }

  return (
    <Textarea
      label="Job description (optional)"
      description="Paste a JD to tailor edits toward it"
      placeholder="Paste the job description…"
      autosize
      minRows={2}
      maxRows={6}
      value={draft || jobDescription || ""}
      onChange={(e) => setDraft(e.currentTarget.value)}
      onBlur={() => {
        const v = (draft || jobDescription || "").trim();
        setJobDescription(v || null);
        setOpen(false);
      }}
    />
  );
}
