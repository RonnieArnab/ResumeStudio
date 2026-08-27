import { useStore } from "../state/store";

export function useSectionSelection() {
  const selectedSectionId = useStore((state) => state.selectedSectionId);
  const selectSection = useStore((state) => state.selectSection);
  return { selectedSectionId, selectSection };
}
