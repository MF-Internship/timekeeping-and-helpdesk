import type { EmployeeNavigationItem } from "./employee-navigation";
import { BottomNavigation } from "./BottomNavigation";
import { NavigationRail } from "./NavigationRail";

export function PrimaryNavigation(props: {
  items: readonly EmployeeNavigationItem[];
  pathname: string;
}) {
  if (props.items.length === 0) return null;
  return (
    <>
      <BottomNavigation {...props} />
      <NavigationRail {...props} />
    </>
  );
}
