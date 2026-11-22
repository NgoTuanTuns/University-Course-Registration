import { useEffect, useState } from "react";
import { Clock, Lock, CheckCircle2, ClipboardList } from "lucide-react";
import type { RegistrationPhaseInfo } from "../api/registrationPhase";

function formatCountdown(endsAtIso: string | null, nowMs: number): string {
  if (!endsAtIso) return "";
  const target = new Date(endsAtIso).getTime();
  if (Number.isNaN(target)) return "";
  const diff = target - nowMs;
  if (diff <= 0) return "Đã đến mốc kết thúc đợt";
  const totalMinutes = Math.floor(diff / 60000);
  const days = Math.floor(totalMinutes / (60 * 24));
  const hours = Math.floor((totalMinutes % (60 * 24)) / 60);
  const minutes = totalMinutes % 60;
  if (days > 0) return `Còn ${days} ngày ${hours} giờ`;
  if (hours > 0) return `Còn ${hours} giờ ${minutes} phút`;
  return `Còn ${minutes} phút`;
}

export function PhaseBanner({
  phase,
}: {
  phase: RegistrationPhaseInfo | null;
}) {
  const [nowMs, setNowMs] = useState(() => Date.now());

  useEffect(() => {
    if (!phase?.phaseEndsAt) return;
    const id = window.setInterval(() => setNowMs(Date.now()), 30000);
    return () => window.clearInterval(id);
  }, [phase?.phaseEndsAt]);

  if (!phase) return null;

  const countdown = formatCountdown(phase.phaseEndsAt, nowMs);
  const toneClass =
    phase.phase === "ENROLLMENT_OPEN"
      ? "is-open"
      : phase.phase === "STUDY_PLAN_OPEN"
        ? "is-plan"
        : phase.phase === "CLASS_OPENING_REVIEW"
          ? "is-review"
          : "is-locked";

  const Icon =
    phase.phase === "ENROLLMENT_OPEN"
      ? CheckCircle2
      : phase.phase === "STUDY_PLAN_OPEN"
        ? ClipboardList
        : phase.phase === "CLASS_OPENING_REVIEW"
          ? Clock
          : Lock;

  return (
    <div className={`phase-banner ${toneClass}`} role="status">
      <div className="phase-banner-left">
        <span className="phase-badge">
          <Icon size={14} />
          {phase.phaseLabel}
        </span>
        <span className="phase-text">
          {phase.note || phase.phaseDescription}
        </span>
      </div>
      {countdown && (
        <span className="phase-countdown">
          <Clock size={13} />
          {countdown}
        </span>
      )}
    </div>
  );
}
