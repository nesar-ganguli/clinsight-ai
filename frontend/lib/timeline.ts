import { Patient } from "@/lib/types";

type TimelineItem = {
  id: string;
  label: string;
  type: string;
  date: string;
  detail: string;
  meta?: string;
};

export function buildTimeline(patient: Patient): TimelineItem[] {
  const items: TimelineItem[] = [
    ...patient.encounters.map((encounter) => ({
      id: `encounter-${encounter.id}`,
      label: encounter.encounter_type || "Encounter",
      type: "Encounter",
      date: encounter.period_start || "",
      detail: `Status: ${encounter.status || "unknown"}${encounter.encounter_class ? ` • Class: ${encounter.encounter_class}` : ""}`,
      meta: encounter.period_end ? `Ended ${encounter.period_end}` : undefined,
    })),
    ...patient.conditions.map((condition) => ({
      id: `condition-${condition.id}`,
      label: condition.condition_name || "Condition",
      type: "Condition",
      date: condition.onset_date || "",
      detail: `Clinical status: ${condition.clinical_status || "unspecified"}`,
      meta: condition.condition_code ? `Code ${condition.condition_code}` : undefined,
    })),
    ...patient.observations.map((observation) => ({
      id: `observation-${observation.id}`,
      label: observation.observation_name || "Observation",
      type: "Observation",
      date: observation.effective_date || "",
      detail: observation.value ? `${observation.value}${observation.unit ? ` ${observation.unit}` : ""}` : "Value missing",
      meta: observation.observation_code ? `Code ${observation.observation_code}` : undefined,
    })),
    ...patient.medication_requests.map((medication) => ({
      id: `medication-${medication.id}`,
      label: medication.medication_name || "Medication request",
      type: "Medication",
      date: medication.authored_on || "",
      detail: `Status: ${medication.status || "unknown"} • Intent: ${medication.intent || "unspecified"}`,
      meta: medication.medication_code ? `Code ${medication.medication_code}` : undefined,
    })),
    ...patient.allergies.map((allergy) => ({
      id: `allergy-${allergy.id}`,
      label: allergy.allergy_name || "Allergy",
      type: "Allergy",
      date: allergy.recorded_date || "",
      detail: `Criticality: ${allergy.criticality || "unspecified"} • Verification: ${allergy.verification_status || "unknown"}`,
      meta: allergy.allergy_code ? `Code ${allergy.allergy_code}` : undefined,
    })),
  ];

  return items.sort((left, right) => right.date.localeCompare(left.date));
}
