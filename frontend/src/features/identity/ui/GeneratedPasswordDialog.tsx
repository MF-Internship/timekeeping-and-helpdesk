"use client";

import { forwardRef, useEffect, useImperativeHandle, useState } from "react";

import { subscribeSession } from "@/features/identity/model/session-store";

export type GeneratedPasswordDialogHandle = { show(value: string): void; clear(): void };

export const GeneratedPasswordDialog = forwardRef<GeneratedPasswordDialogHandle>(
  function GeneratedPasswordDialog(_, ref) {
    const [value, setValue] = useState<string>();
    useImperativeHandle(ref, () => ({ show: setValue, clear: () => setValue(undefined) }), []);
    useEffect(() => () => setValue(undefined), []);
    useEffect(() => subscribeSession(() => setValue(undefined)), []);
    if (!value) return null;
    return (
      <div role="dialog" aria-modal="true" aria-label="Mật khẩu được tạo">
        <p>Mật khẩu chỉ hiển thị lần này.</p>
        <output>{value}</output>
        <button type="button" onClick={() => setValue(undefined)}>
          Đã lưu, đóng
        </button>
      </div>
    );
  },
);
