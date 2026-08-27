import { useState } from "react";
import { Group, Loader, Stack, Text, rem } from "@mantine/core";
import { Dropzone, MIME_TYPES } from "@mantine/dropzone";
import { IconFileText, IconUpload, IconX } from "@tabler/icons-react";
import { uploadResume } from "../../api/resume";
import { ApiError } from "../../api/client";
import { useStore } from "../../state/store";
import { notify } from "../../lib/notify";

const DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document";

export default function ResumeDropzone() {
  const setSession = useStore((s) => s.setSession);
  const [uploading, setUploading] = useState(false);

  async function handle(file: File) {
    setUploading(true);
    try {
      setSession(await uploadResume(file));
      notify.success("Resume parsed");
    } catch (err) {
      notify.error(err instanceof ApiError ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  return (
    <Dropzone
      onDrop={(files) => files[0] && handle(files[0])}
      onReject={() => notify.error("Only PDF or DOCX files are supported")}
      maxSize={15 * 1024 ** 2}
      accept={[MIME_TYPES.pdf, DOCX]}
      loading={uploading}
      maxFiles={1}
    >
      <Group justify="center" gap="xl" mih={200} style={{ pointerEvents: "none" }}>
        <Dropzone.Accept>
          <IconUpload style={{ width: rem(48), height: rem(48) }} stroke={1.5} />
        </Dropzone.Accept>
        <Dropzone.Reject>
          <IconX style={{ width: rem(48), height: rem(48) }} stroke={1.5} />
        </Dropzone.Reject>
        <Dropzone.Idle>
          {uploading ? <Loader /> : <IconFileText style={{ width: rem(48), height: rem(48) }} stroke={1.5} />}
        </Dropzone.Idle>
        <Stack gap={4}>
          <Text size="lg" inline>
            {uploading ? "Parsing your resume…" : "Drop your resume here or click to browse"}
          </Text>
          <Text size="sm" c="dimmed" inline>
            PDF or DOCX, up to 15 MB
          </Text>
        </Stack>
      </Group>
    </Dropzone>
  );
}
