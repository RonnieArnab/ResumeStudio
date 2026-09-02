import { useEffect, useRef, useState } from "react";
import { Alert, Button, Group, ScrollArea, Stack, Text, Textarea } from "@mantine/core";
import { IconAlertTriangle, IconDeviceFloppy, IconRotate2 } from "@tabler/icons-react";
import { updateResumeLatex } from "../../api/resume";
import { useStore } from "../../state/store";
import { notify } from "../../lib/notify";

/** Raw-LaTeX editor. Edits the whole document; "Save & compile" persists it
 * and recompiles server-side. The "Formatted" view renders straight from
 * `session.latex`, so it reflects a save immediately. */
export default function LatexEditor() {
  const session = useStore((s) => s.session);
  const setSession = useStore((s) => s.setSession);

  const [draft, setDraft] = useState(session?.latex ?? "");
  const [saving, setSaving] = useState(false);
  const [errors, setErrors] = useState<string[]>([]);
  const savedRef = useRef(session?.latex ?? "");

  // resync when the document changes underneath us (agent edit, add/remove
  // section) — but only when we have no unsaved work to lose.
  useEffect(() => {
    if (!session) return;
    if (draft === savedRef.current) setDraft(session.latex);
    savedRef.current = session.latex;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session?.latex]);

  if (!session) return null;
  const dirty = draft !== session.latex;

  const revert = () => {
    setDraft(session.latex);
    setErrors([]);
  };

  const save = async () => {
    setSaving(true);
    setErrors([]);
    try {
      const { compile_errors, ...saved } = await updateResumeLatex(session.session_id, draft);
      setSession(saved);
      savedRef.current = saved.latex;
      setDraft(saved.latex);
      if (compile_errors.length) {
        setErrors(compile_errors);
        notify.error("Saved, but the document didn't compile — the PDF download is paused until it's fixed");
      } else {
        notify.success("LaTeX saved and recompiled");
      }
    } catch (err) {
      setErrors([err instanceof Error ? err.message : "Could not save the LaTeX"]);
    } finally {
      setSaving(false);
    }
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Tab") {
      e.preventDefault();
      const el = e.currentTarget;
      const start = el.selectionStart;
      const end = el.selectionEnd;
      setDraft(draft.slice(0, start) + "  " + draft.slice(end));
      requestAnimationFrame(() => el.setSelectionRange(start + 2, start + 2));
    }
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey) && dirty && !saving) {
      e.preventDefault();
      void save();
    }
  };

  return (
    <Stack gap="xs" h="100%" style={{ minHeight: 0 }}>
      <Group justify="space-between">
        <Text size="xs" c={dirty ? "yellow.7" : "dimmed"}>
          {dirty ? "Unsaved changes — ⌘/Ctrl+Enter to save" : "Editing the raw LaTeX source"}
        </Text>
        <Group gap={6}>
          <Button
            size="xs"
            variant="default"
            leftSection={<IconRotate2 size={14} />}
            disabled={!dirty || saving}
            onClick={revert}
          >
            Revert
          </Button>
          <Button
            size="xs"
            leftSection={<IconDeviceFloppy size={14} />}
            loading={saving}
            disabled={!dirty}
            onClick={save}
          >
            Save &amp; compile
          </Button>
        </Group>
      </Group>

      {errors.length > 0 && (
        <Alert
          color="red"
          icon={<IconAlertTriangle size={15} />}
          title="LaTeX problem"
          withCloseButton
          onClose={() => setErrors([])}
          p="xs"
        >
          <ScrollArea.Autosize mah={140}>
            <Text size="xs" style={{ whiteSpace: "pre-wrap", fontFamily: "var(--mantine-font-family-monospace)" }}>
              {errors.join("\n")}
            </Text>
          </ScrollArea.Autosize>
        </Alert>
      )}

      <Textarea
        flex={1}
        value={draft}
        onChange={(e) => setDraft(e.currentTarget.value)}
        onKeyDown={onKeyDown}
        spellCheck={false}
        autosize={false}
        styles={{
          wrapper: { height: "100%" },
          input: {
            height: "100%",
            fontFamily: "var(--mantine-font-family-monospace)",
            fontSize: 12,
            lineHeight: 1.55,
            whiteSpace: "pre",
            overflowWrap: "normal",
          },
        }}
      />
    </Stack>
  );
}
