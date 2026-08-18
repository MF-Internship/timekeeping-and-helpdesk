"use client";

import { type FormEvent, useEffect, useState } from "react";

import { getConfig, updateConfig } from "@/features/locations/api/location-api";
import { useAuth } from "@/features/identity/model/AuthProvider";
import {
  changedConfig,
  type ConfigDraft,
  configDraft,
  type ConfigValue,
  validationDetails,
} from "@/features/locations/model/config-editor";
import { warningText } from "@/features/locations/model/location-editor";

const WEEKDAYS = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"];
const METERS = [
  ["default_radius_m", "Bán kính mặc định (m)"],
  ["max_radius_m", "Bán kính tối đa (m)"],
  ["max_attendance_accuracy_m", "Độ chính xác chấm công tối đa (m)"],
  ["task_gps_good_accuracy_m", "Ngưỡng GPS Task tốt (m)"],
  ["task_gps_low_accuracy_m", "Ngưỡng GPS Task thấp (m)"],
] as const;
const GRACES = [
  ["late_grace_minutes", "Cho phép đi muộn (phút)"],
  ["early_checkout_grace_minutes", "Cho phép về sớm (phút)"],
  ["late_checkout_grace_minutes", "Cho phép checkout muộn (phút)"],
] as const;

function ConfigSummary({ config }: { config: ConfigValue }) {
  const days = config.working_weekdays.map((day) => WEEKDAYS[day]).join(", ");
  return (
    <div className="summary-card">
      <p>Múi giờ: {config.timezone}</p>
      <p>Ngày làm việc: {days}</p>
      <p>
        Bán kính mặc định/tối đa: {config.default_radius_m}/{config.max_radius_m} m
      </p>
      <p>
        Ca làm: {config.shift_start}–{config.shift_end}
      </p>
      <p>Độ chính xác chấm công: {config.max_attendance_accuracy_m} m</p>
      <p>
        Ngưỡng GPS Task tốt/thấp: {config.task_gps_good_accuracy_m}/{config.task_gps_low_accuracy_m}{" "}
        m
      </p>
      <p>
        Đi muộn/về sớm/checkout muộn: {config.late_grace_minutes}/
        {config.early_checkout_grace_minutes}/{config.late_checkout_grace_minutes} phút
      </p>
    </div>
  );
}

type FormProps = {
  draft: ConfigDraft;
  errors: Record<string, string>;
  busy: boolean;
  onChange: (draft: ConfigDraft) => void;
  onSubmit: (event: FormEvent) => void;
  onReset: () => void;
};

type FieldsProps = {
  draft: ConfigDraft;
  errors: Record<string, string>;
  onText: (field: keyof ConfigDraft, value: string) => void;
};

function MeterFields({ draft, errors, onText }: FieldsProps) {
  return METERS.map(([field, label]) => (
    <label key={field}>
      {label}
      <input
        required
        aria-label={label}
        type="number"
        min="0.001"
        step="0.001"
        value={draft[field]}
        onChange={(event) => onText(field, event.target.value)}
      />
      {errors[field] && <small role="alert">{errors[field]}</small>}
    </label>
  ));
}

function ShiftFields({ draft, errors, onText }: FieldsProps) {
  return (["shift_start", "shift_end"] as const).map((field) => {
    const label = field === "shift_start" ? "Bắt đầu ca" : "Kết thúc ca";
    return (
      <label key={field}>
        {label}
        <input
          required
          aria-label={label}
          type="time"
          step="1"
          value={draft[field]}
          onChange={(event) => onText(field, event.target.value)}
        />
        {errors[field] && <small role="alert">{errors[field]}</small>}
      </label>
    );
  });
}

function GraceFields({ draft, errors, onText }: FieldsProps) {
  return GRACES.map(([field, label]) => (
    <label key={field}>
      {label}
      <input
        required
        aria-label={label}
        type="number"
        min="0"
        step="1"
        value={draft[field]}
        onChange={(event) => onText(field, event.target.value)}
      />
      {errors[field] && <small role="alert">{errors[field]}</small>}
    </label>
  ));
}

function ConfigForm({ draft, errors, busy, onChange, onSubmit, onReset }: FormProps) {
  const text = (field: keyof ConfigDraft, value: string) => onChange({ ...draft, [field]: value });
  const toggleDay = (day: number) =>
    onChange({
      ...draft,
      working_weekdays: draft.working_weekdays.includes(day)
        ? draft.working_weekdays.filter((value) => value !== day)
        : [...draft.working_weekdays, day].sort(),
    });
  return (
    <form className="editor-card" onSubmit={onSubmit}>
      <h2>Chỉnh sửa cấu hình</h2>
      <fieldset>
        <legend>Ngày làm việc</legend>
        <div className="weekday-grid">
          {WEEKDAYS.map((label, day) => (
            <label className="checkbox" key={label}>
              <input
                type="checkbox"
                checked={draft.working_weekdays.includes(day)}
                onChange={() => toggleDay(day)}
              />
              {label}
            </label>
          ))}
        </div>
        {errors.working_weekdays && <small role="alert">{errors.working_weekdays}</small>}
      </fieldset>
      <div className="form-grid">
        <MeterFields draft={draft} errors={errors} onText={text} />
        <ShiftFields draft={draft} errors={errors} onText={text} />
        <GraceFields draft={draft} errors={errors} onText={text} />
      </div>
      {errors.non_field_errors && <p role="alert">{errors.non_field_errors}</p>}
      <div className="actions">
        <button disabled={busy}>Lưu cấu hình</button>
        <button type="button" disabled={busy} onClick={onReset}>
          Hoàn tác
        </button>
      </div>
    </form>
  );
}

type ContentProps = FormProps & {
  config: ConfigValue;
  canManage: boolean;
  notice?: { text: string; alert?: boolean };
};

function ConfigContent(props: ContentProps) {
  return (
    <section>
      <ConfigSummary config={props.config} />
      {props.notice && <p role={props.notice.alert ? "alert" : "status"}>{props.notice.text}</p>}
      {props.canManage && <ConfigForm {...props} />}
    </section>
  );
}

export function ConfigEditor() {
  const canManage = useAuth().hasCapability("config.manage_attendance");
  const [config, setConfig] = useState<ConfigValue>();
  const [draft, setDraft] = useState<ConfigDraft>();
  const [notice, setNotice] = useState<{ text: string; alert?: boolean }>();
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    let active = true;
    void getConfig()
      .then((value) => {
        if (active) {
          setConfig(value);
          setDraft(configDraft(value));
        }
      })
      .catch(() => active && setNotice({ text: "Không thể tải cấu hình.", alert: true }));
    return () => {
      active = false;
    };
  }, []);
  if (!config || !draft)
    return <p role={notice?.alert ? "alert" : "status"}>{notice?.text ?? "Đang tải cấu hình…"}</p>;
  const currentConfig = config;
  const currentDraft = draft;
  async function submit(event: FormEvent) {
    event.preventDefault();
    const changes = changedConfig(currentConfig, currentDraft);
    if (!Object.keys(changes).length) {
      setNotice({ text: "Không có thay đổi để lưu." });
      return;
    }
    setBusy(true);
    setErrors({});
    setNotice(undefined);
    try {
      const result = await updateConfig(changes);
      setConfig(result.config);
      setDraft(configDraft(result.config));
      setNotice({
        text: result.warnings.length
          ? `Đã lưu; cảnh báo: ${warningText(result.warnings)}`
          : "Đã lưu cấu hình.",
      });
    } catch (error) {
      setErrors(validationDetails(error));
      setNotice({
        text: "Không thể lưu cấu hình. Vui lòng kiểm tra các trường được báo lỗi.",
        alert: true,
      });
    } finally {
      setBusy(false);
    }
  }
  return (
    <ConfigContent
      config={currentConfig}
      draft={currentDraft}
      errors={errors}
      busy={busy}
      canManage={canManage}
      notice={notice}
      onChange={setDraft}
      onSubmit={(event) => void submit(event)}
      onReset={() => {
        setDraft(configDraft(currentConfig));
        setErrors({});
        setNotice(undefined);
      }}
    />
  );
}
