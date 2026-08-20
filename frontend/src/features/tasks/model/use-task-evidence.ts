"use client";

import { useEffect, useState } from "react";

import {
  clearEvidenceDraft,
  loadEvidenceDraft,
  saveEvidenceDraft,
  type DraftLoadResult,
  type DraftSaveResult,
} from "./evidence-draft";

export function useTaskEvidenceDraft(accountId: number, taskId: number) {
  const [loaded] = useState<DraftLoadResult>(() => loadEvidenceDraft(accountId, taskId));
  const [files, setFiles] = useState<File[]>(loaded.kind === "ready" ? loaded.files : []);
  const [note, setNote] = useState(loaded.kind === "ready" ? loaded.note : "");
  const [persistence, setPersistence] = useState<DraftSaveResult | DraftLoadResult>(loaded);

  useEffect(() => {
    let current = true;
    void saveEvidenceDraft(accountId, taskId, files, note).then((result) => {
      if (current) setPersistence(result);
    });
    return () => { current = false; };
  }, [accountId, taskId, files, note]);

  function discard() {
    clearEvidenceDraft(accountId, taskId);
    setFiles([]);
    setNote("");
    setPersistence({ kind: "empty" });
  }

  return { files, setFiles, note, setNote, persistence, discard };
}
