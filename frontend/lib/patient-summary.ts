import { Patient } from "@/lib/types";
import { compareClinicalDatesDescending } from "@/lib/date-time";

function pluralize(count: number, noun: string) {
  return `${count} ${noun}${count === 1 ? "" : "s"}`;
}

export function buildPatientNarrative(patient: Patient) {
  const conditions = patient.conditions
    .slice(0, 3)
    .map((condition) => condition.condition_name)
    .filter(Boolean)
    .join(", ");

  const medications = patient.medication_requests
    .slice(0, 2)
    .map((medication) => medication.medication_name)
    .filter(Boolean)
    .join(", ");

  const latestObservation = patient.observations
    .slice()
    .sort((left, right) => compareClinicalDatesDescending(left.effective_date, right.effective_date))[0];

  const lead = `${patient.full_name ?? "This patient"} is represented by a longitudinal chart with ${pluralize(patient.encounters.length, "encounter")}, ${pluralize(patient.conditions.length, "active condition")}, and ${pluralize(patient.observations.length, "observation")}.`;

  const clinicalPicture = conditions
    ? `The documented problem list is led by ${conditions}.`
    : "The chart currently lacks a populated problem list, which should be reviewed for completeness.";

  const treatmentPicture = medications
    ? `Current medication activity includes ${medications}.`
    : "No medication requests are currently linked to the patient record.";

  const latestSignal = latestObservation?.observation_name
    ? `The most recent captured observation is ${latestObservation.observation_name}${latestObservation.value ? ` at ${latestObservation.value}${latestObservation.unit ? ` ${latestObservation.unit}` : ""}` : ""}.`
    : "No recent observation signal is available to summarize.";

  return [lead, clinicalPicture, treatmentPicture, latestSignal];
}
