import { AsyncState } from "@/shared/ui/async-state";

export default function Page() {
  return (
    <main>
      <h1>Nền tảng API</h1>
      <p>Ứng dụng đã sẵn sàng để tích hợp các mô-đun được phê duyệt.</p>
      <AsyncState state={{ kind: "loading" }} />
      <AsyncState state={{ kind: "empty" }} />
      <AsyncState
        state={{
          kind: "canonical",
          message: "Yêu cầu không thể được xử lý.",
          details: {},
          requestId: "00000000-0000-4000-8000-000000000000",
        }}
      />
      <AsyncState state={{ kind: "unexpected_response" }} />
      <AsyncState state={{ kind: "network" }} />
    </main>
  );
}
