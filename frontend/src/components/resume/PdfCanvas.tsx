import { useEffect, useRef, useState } from "react";
import * as pdfjsLib from "pdfjs-dist";
import pdfjsWorker from "pdfjs-dist/build/pdf.worker.min.mjs?url";
import { Alert } from "@mantine/core";

pdfjsLib.GlobalWorkerOptions.workerSrc = pdfjsWorker;

interface PdfCanvasProps {
  url: string;
  scale?: number;
  /** render every page (default: first page only) */
  allPages?: boolean;
}

export default function PdfCanvas({ url, scale = 1.5, allPages = false }: PdfCanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function render() {
      setError(null);
      try {
        const pdf = await pdfjsLib.getDocument(url).promise;
        const container = containerRef.current;
        if (!container || cancelled) return;
        container.innerHTML = "";
        const total = allPages ? pdf.numPages : 1;
        for (let p = 1; p <= total; p++) {
          const page = await pdf.getPage(p);
          const viewport = page.getViewport({ scale });
          const canvas = document.createElement("canvas");
          canvas.style.maxWidth = "100%";
          canvas.style.display = "block";
          canvas.style.marginBottom = "12px";
          canvas.style.boxShadow = "0 1px 4px rgba(0,0,0,0.15)";
          canvas.width = viewport.width;
          canvas.height = viewport.height;
          const ctx = canvas.getContext("2d");
          if (!ctx || cancelled) return;
          container.appendChild(canvas);
          await page.render({ canvasContext: ctx, viewport }).promise;
        }
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to render PDF");
      }
    }
    void render();
    return () => {
      cancelled = true;
    };
  }, [url, scale, allPages]);

  if (error) {
    return (
      <Alert color="red" variant="light" title="Preview failed">
        {error}
      </Alert>
    );
  }
  return <div ref={containerRef} />;
}
