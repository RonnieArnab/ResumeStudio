import { useEffect, useRef, useState } from "react";
import { ActionIcon, Paper, ScrollArea, Stack, Text, Textarea } from "@mantine/core";
import { IconSend } from "@tabler/icons-react";
import { getChatHistory, streamChatMessage } from "../../api/chat";
import { listStagedDiffs } from "../../api/agentStream";
import { getResume } from "../../api/resume";
import { useStore } from "../../state/store";
import { notify } from "../../lib/notify";
import type { AgentEvent } from "../../types/agent";
import AgentActivity from "./AgentActivity";
import DiffReview from "./DiffReview";
import JobDescriptionField from "./JobDescriptionField";

interface ChatPanelProps {
  sessionId: string;
}

export default function ChatPanel({ sessionId }: ChatPanelProps) {
  const messages = useStore((s) => s.messages);
  const setMessages = useStore((s) => s.setMessages);
  const addMessage = useStore((s) => s.addMessage);
  const jobDescription = useStore((s) => s.jobDescription);
  const setSession = useStore((s) => s.setSession);
  const stagedEdits = useStore((s) => s.stagedEdits);
  const setStagedEdits = useStore((s) => s.setStagedEdits);

  const [text, setText] = useState("");
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [running, setRunning] = useState(false);
  const viewport = useRef<HTMLDivElement>(null);

  useEffect(() => {
    getChatHistory(sessionId).then(setMessages).catch(() => {});
    listStagedDiffs(sessionId).then(setStagedEdits).catch(() => {});
  }, [sessionId, setMessages, setStagedEdits]);

  useEffect(() => {
    viewport.current?.scrollTo({ top: viewport.current.scrollHeight, behavior: "smooth" });
  }, [messages, events]);

  async function refresh() {
    const [diffs, session] = await Promise.all([listStagedDiffs(sessionId), getResume(sessionId)]);
    setStagedEdits(diffs);
    setSession(session);
  }

  async function send() {
    if (!text.trim() || running) return;
    const userText = text.trim();
    setText("");
    addMessage({ role: "user", text: userText, created_at: new Date().toISOString() });
    setRunning(true);
    setEvents([]);
    try {
      let finalMessage = "";
      await streamChatMessage(sessionId, userText, jobDescription, (event) => {
        setEvents((prev) => [...prev, event]);
        if (event.type === "done") finalMessage = event.message;
        if (event.type === "error") notify.error(event.message);
      });
      addMessage({ role: "agent", text: finalMessage, created_at: new Date().toISOString() });
      setStagedEdits(await listStagedDiffs(sessionId));
    } catch (err) {
      notify.error(err instanceof Error ? err.message : "Agent run failed");
    } finally {
      setRunning(false);
    }
  }

  return (
    <Paper withBorder radius="md" h="100%" style={{ display: "flex", flexDirection: "column", overflow: "hidden" }}>
      <Stack gap="xs" p="sm">
        <JobDescriptionField />
      </Stack>

      <ScrollArea style={{ flex: 1 }} viewportRef={viewport} px="sm">
        <Stack gap="md" py="sm">
          {messages.length === 0 && (
            <Text c="dimmed" size="sm">
              Ask for changes, or attach a job description and ask to tailor the resume.
            </Text>
          )}
          {messages.map((m, i) => (
            <Paper
              key={i}
              withBorder
              radius="md"
              p="sm"
              bg={m.role === "user" ? "var(--mantine-color-indigo-light)" : "var(--mantine-color-body)"}
            >
              <Text size="xs" c="dimmed" mb={4}>
                {m.role === "user" ? "You" : "Agent"} · {new Date(m.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
              </Text>
              <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>
                {m.text}
              </Text>
            </Paper>
          ))}

          {(events.length > 0 || running) && <AgentActivity events={events} running={running} />}

          {stagedEdits.length > 0 && <DiffReview sessionId={sessionId} diffs={stagedEdits} onChanged={() => void refresh()} />}
        </Stack>
      </ScrollArea>

      <Stack gap={0} p="sm">
        <Textarea
          placeholder="Ask for changes…"
          autosize
          minRows={1}
          maxRows={5}
          value={text}
          disabled={running}
          onChange={(e) => setText(e.currentTarget.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void send();
            }
          }}
          rightSection={
            <ActionIcon variant="filled" aria-label="Send" loading={running} disabled={!text.trim()} onClick={send}>
              <IconSend size={16} />
            </ActionIcon>
          }
        />
      </Stack>
    </Paper>
  );
}
