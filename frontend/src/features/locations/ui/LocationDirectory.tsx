"use client";

import { type FormEvent, useEffect, useState } from "react";

import { listLocations, updateLocation } from "@/features/locations/api/location-api";
import { useAuth } from "@/features/identity/model/AuthProvider";
import {
  isLocationConflict,
  type LocationDraft,
  locationDraft,
  type LocationRecord,
  pendingLocationUpdate,
  warningText,
} from "@/features/locations/model/location-editor";

type Filters = {
  kind: "" | "BUSINESS_CENTER" | "SHOP";
  parent: string;
  active: "" | "true" | "false";
};

function queryFor(filters: Filters) {
  return {
    ...(filters.kind ? { kind: filters.kind } : {}),
    ...(filters.parent ? { parent: Number(filters.parent) } : {}),
    ...(filters.active ? { is_active: filters.active === "true" } : {}),
  };
}

function LocationFilters({
  value,
  onChange,
}: {
  value: Filters;
  onChange: (value: Filters) => void;
}) {
  return (
    <div className="filter-grid">
      <label>
        Loại địa điểm
        <select
          value={value.kind}
          onChange={(event) => onChange({ ...value, kind: event.target.value as Filters["kind"] })}
        >
          <option value="">Tất cả</option>
          <option value="BUSINESS_CENTER">Trung tâm kinh doanh</option>
          <option value="SHOP">Cửa hàng</option>
        </select>
      </label>
      <label>
        Mã cha
        <input
          type="number"
          min="1"
          value={value.parent}
          onChange={(event) => onChange({ ...value, parent: event.target.value })}
        />
      </label>
      <label>
        Trạng thái
        <select
          value={value.active}
          onChange={(event) =>
            onChange({ ...value, active: event.target.value as Filters["active"] })
          }
        >
          <option value="">Tất cả</option>
          <option value="true">Đang hoạt động</option>
          <option value="false">Ngừng hoạt động</option>
        </select>
      </label>
    </div>
  );
}

function LocationList({
  items,
  canManage,
  onEdit,
}: {
  items: LocationRecord[];
  canManage: boolean;
  onEdit: (item: LocationRecord) => void;
}) {
  return (
    <ul className="record-list">
      {items.map((item) => (
        <li key={item.id}>
          <div>
            <strong>
              {item.code} — {item.name}
            </strong>
            <br />
            {item.kind} · cha {item.parent_code ?? "—"} ·{" "}
            {item.is_active ? "đang hoạt động" : "ngừng hoạt động"}
            <br />
            {item.address}
            <br />
            {item.latitude}, {item.longitude} · bán kính {item.radius_m} m · phiên bản{" "}
            {item.version}
          </div>
          {canManage && (
            <button aria-label={`Chỉnh sửa ${item.code}`} onClick={() => onEdit(item)}>
              Chỉnh sửa
            </button>
          )}
        </li>
      ))}
    </ul>
  );
}

type EditProps = {
  draft: LocationDraft;
  busy: boolean;
  onChange: (draft: LocationDraft) => void;
  onCancel: () => void;
  onSubmit: (event: FormEvent) => void;
};

function LocationEditForm({ draft, busy, onChange, onCancel, onSubmit }: EditProps) {
  const text = (
    field: "name" | "address" | "latitude" | "longitude" | "radius_m" | "reason",
    value: string,
  ) => onChange({ ...draft, [field]: value });
  return (
    <form className="editor-card" onSubmit={onSubmit}>
      <h2>Chỉnh sửa {draft.code}</h2>
      <p>Phiên bản máy chủ: {draft.version}</p>
      <div className="form-grid">
        <label>
          Tên địa điểm
          <input
            required
            value={draft.name}
            onChange={(event) => text("name", event.target.value)}
          />
        </label>
        <label>
          Địa chỉ
          <input
            required
            value={draft.address}
            onChange={(event) => text("address", event.target.value)}
          />
        </label>
        <label>
          Vĩ độ
          <input
            required
            inputMode="decimal"
            value={draft.latitude}
            onChange={(event) => text("latitude", event.target.value)}
          />
        </label>
        <label>
          Kinh độ
          <input
            required
            inputMode="decimal"
            value={draft.longitude}
            onChange={(event) => text("longitude", event.target.value)}
          />
        </label>
        <label>
          Bán kính (m)
          <input
            required
            inputMode="decimal"
            value={draft.radius_m}
            onChange={(event) => text("radius_m", event.target.value)}
          />
        </label>
        <label className="checkbox">
          <input
            type="checkbox"
            checked={draft.is_active}
            onChange={(event) => onChange({ ...draft, is_active: event.target.checked })}
          />
          Đang hoạt động
        </label>
      </div>
      <label>
        Lý do thay đổi
        <textarea
          maxLength={500}
          value={draft.reason}
          onChange={(event) => text("reason", event.target.value)}
        />
      </label>
      <div className="actions">
        <button disabled={busy}>Lưu địa điểm</button>
        <button type="button" disabled={busy} onClick={onCancel}>
          Hủy
        </button>
      </div>
    </form>
  );
}

export function LocationDirectory() {
  const canManage = useAuth().hasCapability("location.manage");
  const [items, setItems] = useState<LocationRecord[]>([]);
  const [filters, setFilters] = useState<Filters>({ kind: "", parent: "", active: "" });
  const [draft, setDraft] = useState<LocationDraft>();
  const [notice, setNotice] = useState<{ text: string; alert?: boolean }>();
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    let active = true;
    void listLocations(queryFor(filters))
      .then((values) => active && setItems(values))
      .catch(() => active && setNotice({ text: "Không thể tải danh sách địa điểm.", alert: true }));
    return () => {
      active = false;
    };
  }, [filters]);
  async function submit(event: FormEvent) {
    event.preventDefault();
    const change = pendingLocationUpdate(draft, items);
    if (!change) {
      setNotice({ text: "Không có thay đổi để lưu." });
      return;
    }
    setBusy(true);
    setNotice(undefined);
    try {
      const result = await updateLocation(change.draft.id, change.body);
      setItems((current) =>
        current.map((item) => (item.id === result.location.id ? result.location : item)),
      );
      setDraft(locationDraft(result.location));
      setNotice({
        text: result.warnings.length
          ? `Đã lưu; cảnh báo: ${warningText(result.warnings)}`
          : "Đã lưu địa điểm.",
      });
    } catch (error) {
      if (isLocationConflict(error)) {
        const latest = await listLocations(queryFor(filters)).catch(() => items);
        setItems(latest);
        const item = latest.find((value) => value.id === change.draft.id);
        if (item) setDraft({ ...change.draft, version: item.version });
        setNotice({
          text: `Dữ liệu đã thay đổi; bản nháp và lý do được giữ lại ở phiên bản ${item?.version ?? "mới nhất"}. Hãy kiểm tra rồi lưu lại.`,
          alert: true,
        });
      } else setNotice({ text: "Không thể lưu địa điểm. Vui lòng kiểm tra dữ liệu.", alert: true });
    } finally {
      setBusy(false);
    }
  }
  return (
    <section>
      <LocationFilters value={filters} onChange={setFilters} />
      {notice && <p role={notice.alert ? "alert" : "status"}>{notice.text}</p>}
      {draft && (
        <LocationEditForm
          draft={draft}
          busy={busy}
          onChange={setDraft}
          onCancel={() => setDraft(undefined)}
          onSubmit={(event) => void submit(event)}
        />
      )}
      <LocationList
        items={items}
        canManage={canManage}
        onEdit={(item) => {
          setDraft(locationDraft(item));
          setNotice(undefined);
        }}
      />
    </section>
  );
}
