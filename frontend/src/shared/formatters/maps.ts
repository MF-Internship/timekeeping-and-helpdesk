export function googleMapsSearchUrl(latitude: string, longitude: string) {
  const coordinates = encodeURIComponent(`${latitude},${longitude}`);
  return `https://www.google.com/maps/search/?api=1&query=${coordinates}`;
}
