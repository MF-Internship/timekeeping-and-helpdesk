import { AsyncState } from "@/shared/ui/async-state";
import { PageIntro } from "@/shared/ui/typography";

export default function Page() {
  return (
    <section>
      <PageIntro title="Tổng quan hệ thống" description="Ứng dụng đã sẵn sàng để tích hợp các mô-đun được phê duyệt." />
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
    </section>
  );
}
