import type { NavigationItem } from "./navigation";
import { BottomNavigation } from "./BottomNavigation";
import { NavigationRail } from "./NavigationRail";

export function PrimaryNavigation(props: { items: readonly NavigationItem[]; pathname: string }) {
  if (props.items.length === 0) return null;
  return (
    <>
      <BottomNavigation {...props} />
      <NavigationRail {...props} />
    </>
  );
}
