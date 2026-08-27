import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { ActionIcon, Tooltip } from "@mantine/core";
import { IconLayoutSidebarLeftCollapse, IconLayoutSidebarRightCollapse } from "@tabler/icons-react";
import classes from "./SplitPane.module.css";

type Collapsed = "none" | "left" | "right";

interface SplitPaneProps {
  left: ReactNode;
  right: ReactNode;
  storageKey: string;
  /** initial left-pane fraction 0..1 */
  defaultRatio?: number;
  /** min px for each pane while dragging */
  minPx?: number;
}

export default function SplitPane({ left, right, storageKey, defaultRatio = 0.5, minPx = 260 }: SplitPaneProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [ratio, setRatio] = useState<number>(() => {
    try {
      const v = Number(localStorage.getItem(`split:${storageKey}`));
      return v > 0.05 && v < 0.95 ? v : defaultRatio;
    } catch {
      return defaultRatio;
    }
  });
  const [collapsed, setCollapsed] = useState<Collapsed>(() => {
    try {
      return (localStorage.getItem(`split:${storageKey}:collapsed`) as Collapsed) || "none";
    } catch {
      return "none";
    }
  });
  const [dragging, setDragging] = useState(false);

  useEffect(() => {
    try {
      localStorage.setItem(`split:${storageKey}`, String(ratio));
    } catch {
      /* ignore */
    }
  }, [ratio, storageKey]);

  useEffect(() => {
    try {
      localStorage.setItem(`split:${storageKey}:collapsed`, collapsed);
    } catch {
      /* ignore */
    }
  }, [collapsed, storageKey]);

  const onPointerMove = useCallback(
    (e: PointerEvent) => {
      const el = containerRef.current;
      if (!el) return;
      const rect = el.getBoundingClientRect();
      const raw = (e.clientX - rect.left) / rect.width;
      const minR = minPx / rect.width;
      setRatio(Math.min(1 - minR, Math.max(minR, raw)));
    },
    [minPx],
  );

  const stopDrag = useCallback(() => {
    setDragging(false);
    window.removeEventListener("pointermove", onPointerMove);
    window.removeEventListener("pointerup", stopDrag);
    document.body.style.userSelect = "";
    document.body.style.cursor = "";
  }, [onPointerMove]);

  const startDrag = () => {
    setDragging(true);
    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerup", stopDrag);
    document.body.style.userSelect = "none";
    document.body.style.cursor = "col-resize";
  };

  useEffect(() => stopDrag, [stopDrag]);

  const leftPct = collapsed === "left" ? 0 : collapsed === "right" ? 100 : ratio * 100;

  return (
    <div ref={containerRef} className={classes.root} data-dragging={dragging || undefined}>
      <div className={classes.pane} style={{ width: `${leftPct}%`, display: collapsed === "left" ? "none" : undefined }}>
        {left}
        {collapsed === "right" && (
          <Tooltip label="Show editor">
            <ActionIcon className={classes.restoreRight} variant="default" onClick={() => setCollapsed("none")}>
              <IconLayoutSidebarRightCollapse size={16} />
            </ActionIcon>
          </Tooltip>
        )}
      </div>

      {collapsed === "none" && (
        <div className={classes.divider} onPointerDown={startDrag} role="separator" aria-orientation="vertical">
          <div className={classes.handle} />
          <div className={classes.collapseBtns}>
            <Tooltip label="Collapse left" position="right">
              <ActionIcon size="xs" variant="subtle" onPointerDown={(e) => e.stopPropagation()} onClick={() => setCollapsed("left")}>
                <IconLayoutSidebarLeftCollapse size={13} />
              </ActionIcon>
            </Tooltip>
            <Tooltip label="Collapse right" position="right">
              <ActionIcon size="xs" variant="subtle" onPointerDown={(e) => e.stopPropagation()} onClick={() => setCollapsed("right")}>
                <IconLayoutSidebarRightCollapse size={13} />
              </ActionIcon>
            </Tooltip>
          </div>
        </div>
      )}

      <div className={classes.pane} style={{ width: `${100 - leftPct}%`, display: collapsed === "right" ? "none" : undefined }}>
        {right}
        {collapsed === "left" && (
          <Tooltip label="Show preview">
            <ActionIcon className={classes.restoreLeft} variant="default" onClick={() => setCollapsed("none")}>
              <IconLayoutSidebarLeftCollapse size={16} />
            </ActionIcon>
          </Tooltip>
        )}
      </div>
    </div>
  );
}
