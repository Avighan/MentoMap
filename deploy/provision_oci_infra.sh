#!/usr/bin/env bash
# Provisions the VCN + subnet + security rules + compute instance for
# MentoMap on Oracle Cloud "Always Free". Run this in OCI Cloud Shell
# (console top-right ">_" icon) — it's already authenticated as you, the
# `oci` CLI is preinstalled, and nothing here needs a shared credential.
#
# Usage: paste this whole file into Cloud Shell, or:
#   curl -fsSL https://raw.githubusercontent.com/Avighan/MentoMap/main/deploy/provision_oci_infra.sh -o provision.sh
#   chmod +x provision.sh && ./provision.sh
#
# Safe-ish to re-run: it checks for an existing VCN/instance by display
# name before creating a new one, but isn't fully idempotent for every
# resource — read the echoed output as it goes.
set -euo pipefail

DISPLAY_PREFIX="mentomap"
VCN_CIDR="10.0.0.0/16"
SUBNET_CIDR="10.0.0.0/24"
SHAPE_PRIMARY="VM.Standard.A1.Flex"   # Ampere, 4 OCPU/24GB free tier
SHAPE_FALLBACK="VM.Standard.E2.1.Micro"  # AMD, if A1 capacity is unavailable
OCPUS=4
MEMORY_GB=24

echo "==> Reading tenancy/region from Cloud Shell's pre-authenticated config"
TENANCY_ID="$(oci iam availability-domain list --query 'data[0]."compartment-id"' --raw-output)"
COMPARTMENT_ID="$TENANCY_ID"   # using the root compartment; fine for a single test box
REGION="$(oci iam region-subscription list --query 'data[0]."region-name"' --raw-output)"
AD="$(oci iam availability-domain list --query 'data[0].name' --raw-output)"
echo "    tenancy=$COMPARTMENT_ID region=$REGION AD=$AD"

echo "==> [1/6] VCN"
VCN_ID="$(oci network vcn list --compartment-id "$COMPARTMENT_ID" \
  --display-name "${DISPLAY_PREFIX}-vcn" --query 'data[0].id' --raw-output 2>/dev/null || true)"
if [ -z "$VCN_ID" ] || [ "$VCN_ID" = "null" ]; then
  VCN_ID="$(oci network vcn create --compartment-id "$COMPARTMENT_ID" \
    --cidr-block "$VCN_CIDR" --display-name "${DISPLAY_PREFIX}-vcn" \
    --dns-label "mentomap" --query 'data.id' --raw-output)"
  echo "    created VCN $VCN_ID"
else
  echo "    reusing existing VCN $VCN_ID"
fi

echo "==> [2/6] Internet Gateway"
IGW_ID="$(oci network internet-gateway list --compartment-id "$COMPARTMENT_ID" --vcn-id "$VCN_ID" \
  --query 'data[0].id' --raw-output 2>/dev/null || true)"
if [ -z "$IGW_ID" ] || [ "$IGW_ID" = "null" ]; then
  IGW_ID="$(oci network internet-gateway create --compartment-id "$COMPARTMENT_ID" --vcn-id "$VCN_ID" \
    --is-enabled true --display-name "${DISPLAY_PREFIX}-igw" --query 'data.id' --raw-output)"
  echo "    created IGW $IGW_ID"
else
  echo "    reusing existing IGW $IGW_ID"
fi

echo "==> [3/6] Route table: default route -> Internet Gateway"
RT_ID="$(oci network route-table list --compartment-id "$COMPARTMENT_ID" --vcn-id "$VCN_ID" \
  --query 'data[0].id' --raw-output)"
oci network route-table update --rt-id "$RT_ID" --force \
  --route-rules "[{\"destination\":\"0.0.0.0/0\",\"destinationType\":\"CIDR_BLOCK\",\"networkEntityId\":\"$IGW_ID\"}]" \
  > /dev/null
echo "    default route table $RT_ID now points 0.0.0.0/0 -> IGW"

echo "==> [4/6] Security list: allow inbound SSH (22) and HTTP (80)"
SL_ID="$(oci network security-list list --compartment-id "$COMPARTMENT_ID" --vcn-id "$VCN_ID" \
  --query 'data[0].id' --raw-output)"
oci network security-list update --security-list-id "$SL_ID" --force \
  --ingress-security-rules '[
    {"protocol":"6","source":"0.0.0.0/0","isStateless":false,
     "tcpOptions":{"destinationPortRange":{"min":22,"max":22}}},
    {"protocol":"6","source":"0.0.0.0/0","isStateless":false,
     "tcpOptions":{"destinationPortRange":{"min":80,"max":80}}},
    {"protocol":"6","source":"0.0.0.0/0","isStateless":false,
     "tcpOptions":{"destinationPortRange":{"min":443,"max":443}}}
  ]' \
  --egress-security-rules '[{"protocol":"all","destination":"0.0.0.0/0","isStateless":false}]' \
  > /dev/null
echo "    security list $SL_ID allows 22, 80, 443 inbound"

echo "==> [5/6] Subnet"
SUBNET_ID="$(oci network subnet list --compartment-id "$COMPARTMENT_ID" --vcn-id "$VCN_ID" \
  --query 'data[0].id' --raw-output 2>/dev/null || true)"
if [ -z "$SUBNET_ID" ] || [ "$SUBNET_ID" = "null" ]; then
  SUBNET_ID="$(oci network subnet create --compartment-id "$COMPARTMENT_ID" --vcn-id "$VCN_ID" \
    --cidr-block "$SUBNET_CIDR" --display-name "${DISPLAY_PREFIX}-subnet" \
    --route-table-id "$RT_ID" --security-list-ids "[\"$SL_ID\"]" \
    --dns-label "public" --query 'data.id' --raw-output)"
  echo "    created subnet $SUBNET_ID"
else
  echo "    reusing existing subnet $SUBNET_ID"
fi

echo "==> [6/6] Launching the compute instance"
if [ ! -f ~/.ssh/id_rsa.pub ]; then
  echo "    no SSH key found in Cloud Shell home — generating one"
  ssh-keygen -t rsa -b 4096 -N "" -f ~/.ssh/id_rsa
fi

IMAGE_ID="$(oci compute image list --compartment-id "$COMPARTMENT_ID" \
  --operating-system "Canonical Ubuntu" --operating-system-version "22.04" \
  --shape "$SHAPE_PRIMARY" --sort-by TIMECREATED --sort-order DESC \
  --query 'data[0].id' --raw-output)"

launch_instance() {
  local shape="$1"
  local extra_args=()
  if [ "$shape" = "$SHAPE_PRIMARY" ]; then
    extra_args=(--shape-config "{\"ocpus\": $OCPUS, \"memoryInGBs\": $MEMORY_GB}")
  fi
  oci compute instance launch \
    --compartment-id "$COMPARTMENT_ID" \
    --availability-domain "$AD" \
    --shape "$shape" \
    "${extra_args[@]}" \
    --image-id "$IMAGE_ID" \
    --subnet-id "$SUBNET_ID" \
    --assign-public-ip true \
    --ssh-authorized-keys-file ~/.ssh/id_rsa.pub \
    --display-name "${DISPLAY_PREFIX}-vm" \
    --wait-for-state RUNNING \
    --query 'data.id' --raw-output
}

echo "    trying $SHAPE_PRIMARY (Ampere, free 4 OCPU/24GB)..."
INSTANCE_ID="$(launch_instance "$SHAPE_PRIMARY" 2>/dev/null || true)"
if [ -z "$INSTANCE_ID" ]; then
  echo "    $SHAPE_PRIMARY unavailable in this AD (common — Ampere free capacity is popular)."
  echo "    falling back to $SHAPE_FALLBACK (AMD, smaller but still free)..."
  INSTANCE_ID="$(launch_instance "$SHAPE_FALLBACK")"
fi

PUBLIC_IP="$(oci compute instance list-vnics --instance-id "$INSTANCE_ID" \
  --query 'data[0]."public-ip"' --raw-output)"

echo ""
echo "================================================================"
echo " Instance is running."
echo " Public IP: $PUBLIC_IP"
echo ""
echo " SSH in (private key is in THIS Cloud Shell session at ~/.ssh/id_rsa"
echo " — download it via Cloud Shell's menu > Download File if you want"
echo " to SSH from your own machine instead of Cloud Shell):"
echo ""
echo "   ssh -i ~/.ssh/id_rsa ubuntu@$PUBLIC_IP"
echo ""
echo " Then run the app deployment script:"
echo "   curl -fsSL https://raw.githubusercontent.com/Avighan/MentoMap/main/deploy/setup_oracle_vm.sh -o setup.sh"
echo "   chmod +x setup.sh && ./setup.sh"
echo "================================================================"
