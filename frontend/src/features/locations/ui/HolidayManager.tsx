"use client";

import { type FormEvent, useCallback, useEffect, useState } from "react";

import { createHoliday, deleteHoliday, listHolidays } from "@/features/locations/api/location-api";
import { useAuth } from "@/features/identity/model/AuthProvider";

type Holiday = Awaited<ReturnType<typeof listHolidays>>[number];

export function HolidayManager() {
  const auth = useAuth();
  const canManage = auth.hasCapability("holiday.manage");
  const [items, setItems] = useState<Holiday[]>([]);
  const [date, setDate] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const load = useCallback(async () => setItems(await listHolidays()), []);
  useEffect(() => {
    let active = true;
    if (!canManage) return;
    void listHolidays()
      .then((values) => {
        if (active) setItems(values);
      })
      .catch(() => {
        if (active) setError("Không thể tải danh sách ngày nghỉ.");
      });
    return () => {
      active = false;
    };
  }, [canManage]);
  if (!canManage) return <p>Bạn không có quyền quản lý ngày nghỉ.</p>;
  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      await createHoliday({ date, name });
      setDate("");
      setName("");
      await load();
    } catch {
      setError("Ngày nghỉ không hợp lệ hoặc đã tồn tại.");
    }
  }
  return (
    <section>
      <form onSubmit={(event) => void submit(event)}>
        <label>
          Ngày <input type="date" value={date} onChange={(event) => setDate(event.target.value)} />
        </label>
        <label>
          Tên <input value={name} onChange={(event) => setName(event.target.value)} />
        </label>
        <button>Thêm ngày nghỉ</button>
      </form>
      {error && <p role="alert">{error}</p>}
      <ul>
        {items.map((item) => (
          <li key={item.id}>
            {item.date} — {item.name}{" "}
            <button
              onClick={() => {
                if (!window.confirm("Xác nhận xóa ngày nghỉ?")) return;
                void deleteHoliday(item.id)
                  .then(load)
                  .catch(async () => {
                    setError("Ngày nghỉ không còn tồn tại; danh sách đã được làm mới.");
                    await load();
                  });
              }}
            >
              Xóa
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
