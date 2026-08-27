import { useMemo, useState } from "react";
import { ActionIcon, Badge, Button, Group, Text, TextInput, Tooltip } from "@mantine/core";
import { IconPencil, IconPlus, IconTrash } from "@tabler/icons-react";
import { modals } from "@mantine/modals";
import { useStore } from "../../state/store";
import { parseHeader, parseResumeSections, parseSection } from "../../lib/latex";
import { InlineTokens } from "./InlineLatex";
import classes from "./ResumeDocument.module.css";

interface ResumeDocumentProps {
  latex: string;
  pendingSectionIds?: Set<string>;
  onSelectSection: (id: string) => void;
  onAddSection?: (title: string) => Promise<void> | void;
  onDeleteSection?: (id: string) => Promise<void> | void;
}

export default function ResumeDocument({
  latex,
  pendingSectionIds,
  onSelectSection,
  onAddSection,
  onDeleteSection,
}: ResumeDocumentProps) {
  const [adding, setAdding] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [busy, setBusy] = useState(false);

  const submitNew = async () => {
    if (!newTitle.trim() || !onAddSection) return;
    setBusy(true);
    try {
      await onAddSection(newTitle.trim());
      setNewTitle("");
      setAdding(false);
    } finally {
      setBusy(false);
    }
  };

  const confirmDelete = (id: string) =>
    modals.openConfirmModal({
      title: `Remove the "${id}" section?`,
      children: <Text size="sm">This deletes the section and recompiles the resume.</Text>,
      labels: { confirm: "Remove", cancel: "Keep" },
      confirmProps: { color: "red" },
      onConfirm: () => onDeleteSection?.(id),
    });

  const selectedSectionId = useStore((s) => s.selectedSectionId);
  const sections = useMemo(() => parseResumeSections(latex), [latex]);

  const headerRaw = sections.find((s) => s.id === "header");
  const header = headerRaw ? parseHeader(headerRaw.body) : null;
  const body = sections.filter((s) => s.id !== "header");

  return (
    <div className={classes.doc}>
      {header && (
        <div className={classes.header}>
          <div className={classes.name}>{header.name || "Your Name"}</div>
          {header.contact.length > 0 && (
            <div className={classes.contact}>{header.contact.join("  ·  ")}</div>
          )}
        </div>
      )}

      {body.map(({ id, body }) => {
        const parsed = parseSection(id, body);
        const pending = pendingSectionIds?.has(id);
        return (
          <div
            key={id}
            className={classes.section}
            role="button"
            tabIndex={0}
            data-pending={pending || undefined}
            data-selected={selectedSectionId === id || undefined}
            onClick={() => onSelectSection(id)}
            onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && (e.preventDefault(), onSelectSection(id))}
          >
            <span className={classes.editHint}>
              <IconPencil size={12} /> edit
              {onDeleteSection && (
                <Tooltip label="Remove section">
                  <ActionIcon
                    size="xs"
                    variant="subtle"
                    color="red"
                    onClick={(e) => {
                      e.stopPropagation();
                      confirmDelete(id);
                    }}
                  >
                    <IconTrash size={11} />
                  </ActionIcon>
                </Tooltip>
              )}
            </span>
            <div className={classes.sectionTitle}>
              {parsed.title}
              {pending && (
                <Badge size="xs" color="yellow" variant="light">
                  pending change
                </Badge>
              )}
            </div>

            {parsed.blocks.length === 0 ? (
              <Text size="sm" c="dimmed">
                (empty)
              </Text>
            ) : (
              <>
                {parsed.blocks
                  .filter((b) => b.kind === "entry")
                  .map((b, i) =>
                    b.kind === "entry" ? (
                      <div key={`e${i}`} className={classes.entry}>
                        <div className={classes.entryRow}>
                          <span>
                            <InlineTokens tokens={b.title} />
                          </span>
                          <span>
                            <InlineTokens tokens={b.titleRight} />
                          </span>
                        </div>
                        {(b.subtitle.length > 0 || b.subtitleRight.length > 0) && (
                          <div className={classes.entryRow}>
                            <span>
                              <InlineTokens tokens={b.subtitle} />
                            </span>
                            <span>
                              <InlineTokens tokens={b.subtitleRight} />
                            </span>
                          </div>
                        )}
                      </div>
                    ) : null,
                  )}

                {parsed.blocks.some((b) => b.kind === "bullet") && (
                  <ul className={classes.bullets}>
                    {parsed.blocks
                      .filter((b) => b.kind === "bullet")
                      .map((b, i) =>
                        b.kind === "bullet" ? (
                          <li key={`b${i}`}>
                            <InlineTokens tokens={b.content} />
                          </li>
                        ) : null,
                      )}
                  </ul>
                )}
              </>
            )}
          </div>
        );
      })}

      {onAddSection && (
        <div style={{ padding: "12px", textAlign: "center" }}>
          {adding ? (
            <Group gap={6} justify="center" wrap="nowrap">
              <TextInput
                size="xs"
                placeholder="Section name (e.g. Certifications)"
                value={newTitle}
                autoFocus
                onChange={(e) => setNewTitle(e.currentTarget.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") submitNew();
                  if (e.key === "Escape") setAdding(false);
                }}
                style={{ maxWidth: 260 }}
              />
              <Button size="xs" loading={busy} onClick={submitNew}>
                Add
              </Button>
              <Button size="xs" variant="subtle" onClick={() => setAdding(false)}>
                Cancel
              </Button>
            </Group>
          ) : (
            <Button size="xs" variant="light" leftSection={<IconPlus size={13} />} onClick={() => setAdding(true)}>
              Add section
            </Button>
          )}
        </div>
      )}
    </div>
  );
}
