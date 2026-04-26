#!/usr/bin/env bash
set -euo pipefail

if ! command -v oci >/dev/null 2>&1; then
  echo "error: OCI CLI is required. Install and configure \`oci\` before running this script." >&2
  exit 2
fi

: "${COMPARTMENT_ID:?Set COMPARTMENT_ID to the OCI compartment OCID.}"
: "${SUBNET_ID:?Set SUBNET_ID to the target public subnet OCID.}"
: "${SSH_PUBLIC_KEY_FILE:?Set SSH_PUBLIC_KEY_FILE to your public SSH key path.}"

DISPLAY_NAME="${DISPLAY_NAME:-probate-bot}"
SHAPE="${SHAPE:-VM.Standard.A1.Flex}"
OCPUS="${OCPUS:-1}"
MEMORY_GBS="${MEMORY_GBS:-6}"
BOOT_VOLUME_GBS="${BOOT_VOLUME_GBS:-50}"
POLL_SECONDS="${POLL_SECONDS:-600}"
ASSIGN_PUBLIC_IP="${ASSIGN_PUBLIC_IP:-true}"
IMAGE_COMPARTMENT_ID="${IMAGE_COMPARTMENT_ID:-${COMPARTMENT_ID}}"
IMAGE_DISPLAY_NAME_FILTER="${IMAGE_DISPLAY_NAME_FILTER:-Canonical Ubuntu 24.04}"

if [[ "${SHAPE}" != "VM.Standard.A1.Flex" ]]; then
  echo "error: This project is provisioned only for VM.Standard.A1.Flex. E2.1.Micro is intentionally not used." >&2
  exit 2
fi

if [[ ! -f "${SSH_PUBLIC_KEY_FILE}" ]]; then
  echo "error: SSH public key file not found: ${SSH_PUBLIC_KEY_FILE}" >&2
  exit 2
fi

resolve_image_id() {
  if [[ -n "${IMAGE_ID:-}" ]]; then
    echo "${IMAGE_ID}"
    return 0
  fi

  echo "Resolving Ubuntu image automatically from compartment ${IMAGE_COMPARTMENT_ID}..." >&2

  local resolved_image_id
  resolved_image_id="$(
    oci compute image list \
      --compartment-id "${IMAGE_COMPARTMENT_ID}" \
      --all \
      --operating-system Ubuntu \
      --shape "${SHAPE}" \
      --query "sort_by(data[?contains(\"display-name\", '${IMAGE_DISPLAY_NAME_FILTER}') && \"lifecycle-state\" == 'AVAILABLE'], &\"time-created\")[-1].id" \
      --raw-output 2>/dev/null || true
  )"

  if [[ -n "${resolved_image_id}" && "${resolved_image_id}" != "null" ]]; then
    echo "${resolved_image_id}"
    return 0
  fi

  resolved_image_id="$(
    oci compute image list \
      --compartment-id "${IMAGE_COMPARTMENT_ID}" \
      --all \
      --query "sort_by(data[?contains(\"display-name\", '${IMAGE_DISPLAY_NAME_FILTER}') && \"lifecycle-state\" == 'AVAILABLE'], &\"time-created\")[-1].id" \
      --raw-output 2>/dev/null || true
  )"

  if [[ -n "${resolved_image_id}" && "${resolved_image_id}" != "null" ]]; then
    echo "${resolved_image_id}"
    return 0
  fi

  echo "error: Unable to resolve an Ubuntu image automatically." >&2
  echo "Set IMAGE_ID explicitly, or adjust IMAGE_COMPARTMENT_ID / IMAGE_DISPLAY_NAME_FILTER." >&2
  exit 1
}

IMAGE_ID="$(resolve_image_id)"
echo "Using image ${IMAGE_ID}"

echo "Listing availability domains for ${COMPARTMENT_ID}..."
availability_domains=()
while IFS= read -r availability_domain; do
  if [[ -n "${availability_domain}" ]]; then
    availability_domains+=("${availability_domain}")
  fi
done < <(
  oci iam availability-domain list \
    --compartment-id "${COMPARTMENT_ID}" \
    --all \
    --query 'data[].name' \
    --raw-output
)

if [[ ${#availability_domains[@]} -eq 0 ]]; then
  echo "error: No availability domains were returned by OCI." >&2
  exit 1
fi

echo "Found ${#availability_domains[@]} availability domain(s): ${availability_domains[*]}"
echo "Polling every ${POLL_SECONDS}s until VM.Standard.A1.Flex capacity becomes available."

attempt=0
while true; do
  attempt=$((attempt + 1))
  echo
  echo "Provisioning pass ${attempt}..."

  for availability_domain in "${availability_domains[@]}"; do
    echo "Trying ${availability_domain}..."

    stdout_file="$(mktemp)"
    stderr_file="$(mktemp)"

    set +e
    oci compute instance launch \
      --availability-domain "${availability_domain}" \
      --compartment-id "${COMPARTMENT_ID}" \
      --subnet-id "${SUBNET_ID}" \
      --display-name "${DISPLAY_NAME}" \
      --shape "${SHAPE}" \
      --shape-config "{\"ocpus\": ${OCPUS}, \"memoryInGBs\": ${MEMORY_GBS}}" \
      --image-id "${IMAGE_ID}" \
      --boot-volume-size-in-gbs "${BOOT_VOLUME_GBS}" \
      --ssh-authorized-keys-file "${SSH_PUBLIC_KEY_FILE}" \
      --assign-public-ip "${ASSIGN_PUBLIC_IP}" \
      --wait-for-state RUNNING \
      --wait-interval-seconds 30 \
      --query 'data.id' \
      --raw-output \
      >"${stdout_file}" 2>"${stderr_file}"
    status=$?
    set -e

    if [[ ${status} -eq 0 ]]; then
      instance_id="$(tr -d '\r' < "${stdout_file}")"
      rm -f "${stdout_file}" "${stderr_file}"
      echo "Instance created successfully in ${availability_domain}: ${instance_id}"
      echo "Next step: use the OCI console or \`oci compute instance list-vnics --instance-id ${instance_id}\` to get the public IP."
      exit 0
    fi

    error_text="$(cat "${stderr_file}")"
    rm -f "${stdout_file}" "${stderr_file}"

    if grep -qiE 'out of (host )?capacity' <<<"${error_text}"; then
      echo "Capacity unavailable in ${availability_domain}. Continuing to the next AD."
      continue
    fi

    echo "error: Launch failed for a non-capacity reason in ${availability_domain}." >&2
    echo "${error_text}" >&2
    exit ${status}
  done

  echo "No A1.Flex capacity available in any AD. Sleeping ${POLL_SECONDS}s before retry."
  sleep "${POLL_SECONDS}"
done
