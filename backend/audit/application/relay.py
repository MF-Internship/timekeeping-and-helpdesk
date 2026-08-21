from __future__ import annotations

from dataclasses import dataclass

from audit.domain.relay import RelayConfig, safe_transport_error
from audit.ports.relay import OutboxAlertSink, OutboxRelayRepository, OutboxTransport


@dataclass(frozen=True, slots=True)
class RelayResult:
    claimed: int
    published: int
    failed: int
    lost_claims: int


@dataclass(frozen=True, slots=True)
class OutboxRelayService:
    repository: OutboxRelayRepository
    transport: OutboxTransport
    alerts: OutboxAlertSink
    config: RelayConfig

    def run_once(self, worker_id: str) -> RelayResult:
        claimed = self.repository.claim_batch(worker_id=worker_id, config=self.config)
        published = 0
        failed = 0
        lost_claims = 0
        for message in claimed:
            try:
                self.transport.publish(message)
            except Exception as error:
                if self.repository.mark_failed(message, error, self.config):
                    failed += 1
                    if message.attempt_count >= self.config.max_attempts:
                        self.alerts.dead_letter(message, safe_transport_error(error))
                else:
                    lost_claims += 1
                continue
            if self.repository.mark_published(message):
                published += 1
            else:
                lost_claims += 1
        return RelayResult(len(claimed), published, failed, lost_claims)
