"use client";
import Link from "next/link";
import { KeyRound, LogOut, Mail, Phone, UserRound } from "lucide-react";
import { useAuth } from "@/features/identity/model/AuthProvider";
import { roleLabel } from "@/shared/formatters/identity";
import { Button } from "@/shared/ui/button";
import { Card } from "@/shared/ui/card";
import { ThemeToggle } from "@/shared/ui/theme";
import { PageHeader, SectionHeader } from "@/shared/ui/typography";
export function AccountPanel() {
  const auth = useAuth();
  if (auth.state.kind !== "authenticated") return null;
  const account = auth.state.account;
  return (
    <section>
      <PageHeader
        title="Tài khoản"
        description="Thông tin hồ sơ, giao diện và các thao tác bảo mật của bạn."
      />
      <div className="account-layout">
        <Card>
          <SectionHeader title="Hồ sơ" />
          <dl className="account-details">
            <div>
              <dt>
                <UserRound />
                Họ tên
              </dt>
              <dd>{account.full_name || "Chưa cập nhật"}</dd>
            </div>
            <div>
              <dt>Tên đăng nhập</dt>
              <dd>{account.username}</dd>
            </div>
            <div>
              <dt>
                <Mail />
                Email
              </dt>
              <dd>{account.email || "Chưa cập nhật"}</dd>
            </div>
            <div>
              <dt>
                <Phone />
                Điện thoại
              </dt>
              <dd>{account.phone || "Chưa cập nhật"}</dd>
            </div>
            <div>
              <dt>Vai trò</dt>
              <dd>{roleLabel(account.role)}</dd>
            </div>
          </dl>
        </Card>
        <Card>
          <SectionHeader
            title="Tùy chọn"
            description="Lựa chọn giao diện chỉ được lưu trên thiết bị này."
          />
          <ThemeToggle compact={false} />
        </Card>
        <Card>
          <SectionHeader title="Bảo mật và phiên" />
          <div className="actions">
            <Link className="button-link" href="/change-password">
              <KeyRound />
              Đổi mật khẩu
            </Link>
            <Button variant="destructive" onClick={() => void auth.logout()}>
              <LogOut />
              Đăng xuất
            </Button>
          </div>
        </Card>
      </div>
    </section>
  );
}
