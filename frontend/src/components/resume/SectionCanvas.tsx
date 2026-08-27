import type { ReactNode } from "react";
import { useSectionSelection } from "../../hooks/useSectionSelection";
import classes from "./SectionCanvas.module.css";

interface SectionCanvasProps {
  sectionId: string;
  children: ReactNode;
}

export default function SectionCanvas({ sectionId, children }: SectionCanvasProps) {
  const { selectedSectionId, selectSection } = useSectionSelection();
  const isSelected = selectedSectionId === sectionId;

  return (
    <div
      role="button"
      tabIndex={0}
      aria-pressed={isSelected}
      aria-label={`Edit section: ${sectionId}`}
      data-selected={isSelected}
      className={classes.wrap}
      onClick={() => selectSection(isSelected ? null : sectionId)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          selectSection(isSelected ? null : sectionId);
        }
      }}
    >
      <span className={classes.tag}>{sectionId}</span>
      {children}
    </div>
  );
}
