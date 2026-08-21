"use client";

import { type FormEvent, useCallback, useEffect, useState } from "react";

import { createHoliday, deleteHoliday, listHolidays } from "@/features/locations/api/location-api";
import { useAuth } from "@/features/identity/model/AuthProvider";
import { Button } from "@/shared/ui/button";
import { Input } from "@/shared/ui/form";
import styles from "./Administration.module.css";

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
    <section className={styles.surface}>
      <form className={styles.holidayForm} onSubmit={(event) => void submit(event)}>
        <label>
          Ngày <Input type="date" value={date} onChange={(event) => setDate(event.target.value)} />
        </label>
        <label>
          Tên <Input value={name} onChange={(event) => setName(event.target.value)} />
        </label>
        <Button variant="primary">Thêm ngày nghỉ</Button>
      </form>
      {error && (
        <p className={styles.notice} role="alert">
          {error}
        </p>
      )}
      {!items.length ? <p className={styles.empty}>Chưa có ngày nghỉ nào được cấu hình.</p> : null}
      <ul className={styles.recordList}>
        {items.map((item) => (
          <li className={styles.recordRow} key={item.id}>
            <span className={styles.recordIdentity}>
              <strong>{item.name}</strong>
              <span className={styles.meta}>{item.date}</span>
            </span>
            <Button
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
            </Button>
          </li>
        ))}
      </ul>
    </section>
  );
}
