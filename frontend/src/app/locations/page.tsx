import { IdentityRouteBoundary } from "@/features/identity/model/IdentityRouteBoundary";
import { LocationDirectory } from "@/features/locations/ui/LocationDirectory";

export default function LocationsPage() {
  return (
    <main>
      <h1>Địa điểm</h1>
      <IdentityRouteBoundary route="locations">
        <LocationDirectory />
      </IdentityRouteBoundary>
    </main>
  );
}
