const ROLE_LABELS: Record<string, string> = {
  MANAGER: "Quản lý",
  LEADER: "Trưởng nhóm",
  HELPDESK: "Nhân viên Helpdesk",
};

export function roleLabel(role: string) {
  return ROLE_LABELS[role] ?? role;
}
