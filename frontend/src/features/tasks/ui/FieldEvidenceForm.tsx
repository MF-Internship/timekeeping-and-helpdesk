"use client";

import { type FormEvent, useState } from "react";
import { Camera, LocateFixed } from "lucide-react";

import { Button } from "@/shared/ui/button";
import { ActionGroup } from "@/shared/ui/action-group";
import { Input, Select, Textarea } from "@/shared/ui/form";
import type { ApiFailure } from "@/shared/errors/api-error";
import * as taskApi from "../api/task-api";
import { clearEvidenceDraft } from "../model/evidence-draft";
import { useTaskEvidenceDraft } from "../model/use-task-evidence";
import styles from "./TaskManagement.module.css";

const ACCEPTED = new Set(["image/jpeg", "image/png", "image/webp"]);
const MAX_FILES = 5;
const BYTES_PER_MIB = 1024 * 1024;
const MAX_BYTES = 5 * BYTES_PER_MIB;
const HEX_RADIX = 16;
const HEX_WIDTH = 2;
type Candidate = { id: number; code: string; name: string };

async function checksum(file: File) {
  const bytes = await crypto.subtle.digest("SHA-256", await new Response(file).arrayBuffer());
  return [...new Uint8Array(bytes)].map((value) => value.toString(HEX_RADIX).padStart(HEX_WIDTH, "0")).join("");
}

function currentPosition(): Promise<GeolocationPosition> {
  return new Promise((resolve, reject) => navigator.geolocation.getCurrentPosition(resolve, reject, {
    enableHighAccuracy: true, maximumAge: 0, timeout: 15_000,
  }));
}

export function FieldEvidenceForm(props: {
  accountId?: number;
  taskId: number;
  taskTitle: string;
  busy: boolean;
  onComplete(body: taskApi.TaskFieldCompletionInput, key: string): Promise<void>;
}) {
  const [error, setError] = useState<string>();
  const [stage, setStage] = useState<string>();
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [selectedLocationId, setSelectedLocationId] = useState<number>();
  const accountId = props.accountId ?? 0;
  const draft = useTaskEvidenceDraft(accountId, props.taskId);
  const { files, setFiles, note, setNote } = draft;
  const [uploadIds, setUploadIds] = useState<string[]>([]);
  const [idempotencyKey, setIdempotencyKey] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const validationError = validateFiles(files, uploadIds);
    if (validationError) return setError(validationError);
    setError(undefined);
    try {
      await performSubmission({
        props, files, note, uploadIds, idempotencyKey,
        selectedLocationId, setStage, setUploadIds, setIdempotencyKey,
      });
      setStage(undefined);
      clearEvidenceDraft(accountId, props.taskId);
      setFiles([]); setNote(""); setUploadIds([]); setIdempotencyKey("");
    } catch (reason) {
      setStage(undefined);
      handleFailure(reason, setCandidates, setError);
    }
  }
  return <form className={styles.evidenceForm} onSubmit={submit} aria-label={`Nộp minh chứng ${props.taskTitle}`}>
    <div className={styles.formHeading}><Camera size={20} aria-hidden="true" /><div><strong>Minh chứng hoàn thành</strong><p>1–5 ảnh, mỗi ảnh tối đa 5 MB. GPS mới được lấy khi bạn gửi.</p></div></div>
    <label>Ảnh minh chứng
      <Input type="file" accept="image/jpeg,image/png,image/webp" multiple required={!uploadIds.length} onChange={(event) => {
        const selected = Array.from(event.target.files ?? []).slice(0, MAX_FILES);
        setFiles(selected);
        void prepareEvidenceFiles(selected).then(setFiles).catch(() => setError("Không thể xử lý ảnh đã chọn."));
        setUploadIds([]); setIdempotencyKey(""); setCandidates([]); setSelectedLocationId(undefined);
      }} />
    </label>
    <DraftNotice persistence={draft.persistence} files={files} />
    <SelectedFiles files={files} />
    <label>Ghi chú hoàn thành <Textarea name="completion_note" value={note} onChange={(event) => setNote(event.target.value)} placeholder="Mô tả ngắn kết quả đã thực hiện" /></label>
    <LocationChoice candidates={candidates} selected={selectedLocationId} onSelect={setSelectedLocationId} />
    <SubmissionFeedback stage={stage} error={error} />
    <ActionGroup>
      <Button type="submit" variant="primary" loading={props.busy || Boolean(stage)}>Nộp minh chứng & hoàn thành</Button>
      <Button type="button" variant="quiet" onClick={draft.discard}>Bỏ bản nháp</Button>
    </ActionGroup>
  </form>;
}

function DraftNotice({ persistence, files }: {
  persistence: ReturnType<typeof useTaskEvidenceDraft>["persistence"];
  files: File[];
}) {
  if (persistence.kind === "ready") return <p role="status">Đã khôi phục {files.length} ảnh và ghi chú từ bản nháp của task này.</p>;
  if (persistence.kind === "quota") return <p role="alert">Bộ nhớ trình duyệt đã đầy; bản nháp chưa được lưu.</p>;
  if (persistence.kind === "unavailable") return <p role="alert">Không thể dùng bộ nhớ trình duyệt; bản nháp chưa được lưu.</p>;
  if (persistence.kind === "evicted") return <p role="alert">Bản nháp cục bộ đã bị trình duyệt xóa.</p>;
  return null;
}

function SelectedFiles({ files }: { files: File[] }) {
  if (!files.length) return null;
  return <ul className={styles.fileList}>{files.map((file) => (
    <li key={`${file.name}-${file.lastModified}`}>
      {file.name} · {(file.size / BYTES_PER_MIB).toFixed(1)} MB
    </li>
  ))}</ul>;
}

function LocationChoice(props: {
  candidates: Candidate[];
  selected?: number;
  onSelect(value: number): void;
}) {
  if (!props.candidates.length) return null;
  return <label>Địa điểm thực tế
    <Select required value={props.selected ?? ""} onChange={(event) => props.onSelect(Number(event.target.value))}>
      <option value="">Chọn địa điểm</option>
      {props.candidates.map((item) => <option key={item.id} value={item.id}>{item.code} — {item.name}</option>)}
    </Select>
  </label>;
}

function SubmissionFeedback({ stage, error }: { stage?: string; error?: string }) {
  return <>
    {stage && <p role="status"><LocateFixed size={16} aria-hidden="true" /> {stage}</p>}
    {error && <p role="alert">{error}</p>}
  </>;
}

type Submission = {
  props: Parameters<typeof FieldEvidenceForm>[0];
  files: readonly File[];
  note: string;
  uploadIds: string[];
  idempotencyKey: string;
  selectedLocationId?: number;
  setStage(value?: string): void;
  setUploadIds(value: string[]): void;
  setIdempotencyKey(value: string): void;
};

async function performSubmission(input: Submission) {
  let ids = input.uploadIds;
  if (ids.length < input.files.length) {
    input.setStage("Đang tải ảnh minh chứng…");
    ids = await uploadFiles(input.props.taskId, input.files, input.uploadIds, input.setUploadIds);
  }
  input.setStage("Đang lấy vị trí GPS mới…");
  const position = await currentPosition();
  const note = input.note.trim();
  const key = input.idempotencyKey || crypto.randomUUID();
  input.setIdempotencyKey(key);
  await input.props.onComplete(completionBody(ids, position, note, input.selectedLocationId), key);
}

function handleFailure(
  reason: unknown,
  setCandidates: (value: Candidate[]) => void,
  setError: (value: string) => void,
) {
  const choices = locationCandidates(reason);
  if (choices.length) {
    setCandidates(choices);
    setError("Vị trí nằm trong nhiều khu vực. Hãy chọn địa điểm thực tế rồi gửi lại.");
    return;
  }
  const gpsFailure = reason instanceof DOMException
    || (typeof reason === "object" && reason !== null && "code" in reason);
  setError(gpsFailure
    ? "Không lấy được GPS mới. Hãy cấp quyền vị trí, ra khu vực thoáng rồi thử lại."
    : reason instanceof Error ? reason.message : "Không thể nộp minh chứng.");
}

function validateFiles(files: readonly File[], uploadIds: readonly string[]) {
  if ((!files.length && !uploadIds.length) || files.length > MAX_FILES) return "Chọn từ 1 đến 5 ảnh minh chứng.";
  if (files.some((file) => !ACCEPTED.has(file.type) || file.size > MAX_BYTES)) {
    return "Mỗi ảnh phải là JPEG, PNG hoặc WebP và không quá 5 MB.";
  }
}

async function prepareEvidenceFiles(files: File[]) {
  return Promise.all(files.map(compressImage));
}

async function compressImage(file: File): Promise<File> {
  if (typeof createImageBitmap !== "function") return file;
  const bitmap = await createImageBitmap(file);
  const scale = Math.min(1, 1920 / Math.max(bitmap.width, bitmap.height));
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(bitmap.width * scale);
  canvas.height = Math.round(bitmap.height * scale);
  canvas.getContext("2d")?.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
  bitmap.close();
  const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.82));
  return blob && blob.size <= MAX_BYTES
    ? new File([blob], file.name.replace(/\.[^.]+$/, ".jpg"), { type: "image/jpeg", lastModified: file.lastModified })
    : file;
}

function completionBody(uploadIds: string[], position: GeolocationPosition, note: string, selected?: number): taskApi.TaskFieldCompletionInput {
  return {
    upload_ids: uploadIds, latitude: String(position.coords.latitude),
    longitude: String(position.coords.longitude), accuracy_m: String(position.coords.accuracy),
    captured_at: new Date().toISOString(), completion_note: note || null,
    selected_location_id: selected ?? null,
  };
}

function locationCandidates(reason: unknown): Candidate[] {
  const failure = reason as Partial<ApiFailure> & { details?: Record<string, unknown> };
  if (failure.kind !== "canonical" || failure.errorCode !== "LOCATION_CHOICE_REQUIRED") return [];
  const values = failure.details?.candidates;
  if (!Array.isArray(values)) return [];
  return values.filter((item): item is Candidate =>
    typeof item === "object" && item !== null && typeof (item as Candidate).id === "number"
    && typeof (item as Candidate).code === "string" && typeof (item as Candidate).name === "string"
  );
}

async function uploadFiles(
  taskId: number,
  files: readonly File[],
  completed: readonly string[],
  onProgress: (value: string[]) => void,
) {
  const uploadIds = [...completed];
  for (const file of files.slice(completed.length)) {
    const intent = await taskApi.createEvidenceUpload(taskId, {
      checksum_sha256: await checksum(file), mime: file.type as taskApi.EvidenceUploadInput["mime"], size_bytes: file.size,
    });
    await taskApi.uploadEvidenceFile(intent, file);
    uploadIds.push(intent.upload_id);
    onProgress([...uploadIds]);
  }
  return uploadIds;
}
