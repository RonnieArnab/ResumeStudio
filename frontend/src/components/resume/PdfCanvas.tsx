import { useEffect, useRef, useState } from "react";
import * as pdfjsLib from "pdfjs-dist";
import pdfjsWorker from "pdfjs-dist/build/pdf.worker.min.mjs?url";
import { Alert } from "@mantine/core";

pdfjsLib.GlobalWorkerOptions.workerSrc = pdfjsWorker;

interface PdfCanvasProps {
  url: string;
  scale?: number;
}

export default function PdfCanvas({ url, scale = 1.5 }: PdfCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function render() {
      setError(null);
      try {
        const pdf = await pdfjsLib.getDocument(url).promise;
        const page = await pdf.getPage(1);
        const viewport = page.getViewport({ scale });
        const canvas = canvasRef.current;
        if (!canvas || cancelled) return;
        const context = canvas.getContext("2d");
        if (!context) return;
        canvas.width = viewport.width;
        canvas.height = viewport.height;
        await page.render({ canvasContext: context, viewport }).promise;
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to render PDF");
      }
    }
    void render();
    return () => {
      cancelled = true;
    };
  }, [url, scale]);

  if (error) {
    return (
      <Alert color="red" variant="light" title="Preview failed">
        {error}
      </Alert>
    );
  }
  return <canvas ref={canvasRef} style={{ maxWidth: "100%", display: "block" }} />;
}
