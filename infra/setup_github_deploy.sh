#!/bin/bash
# One-off setup: lets GitHub Actions of davins90/bible-network deploy to Cloud Run without stored keys.
# - Workload Identity pool "github" + provider "github-oidc", accepting ONLY this repository
# - github-deploy: the account Actions impersonates (deploy rights in dani-lab-507314)
# - bible-network-run: the account the site runs as (no roles: a static site needs no Google Cloud access)
set -euo pipefail
P=dani-lab-507314
N=$(gcloud projects describe $P --format="value(projectNumber)")
REPO=davins90/bible-network
DEPLOY=github-deploy@$P.iam.gserviceaccount.com
RUN=bible-network-run@$P.iam.gserviceaccount.com

gcloud services enable iamcredentials.googleapis.com sts.googleapis.com --project $P
gcloud iam workload-identity-pools describe github --location=global --project $P >/dev/null 2>&1 \
  || gcloud iam workload-identity-pools create github --location=global --project $P --display-name="GitHub Actions"
gcloud iam workload-identity-pools providers describe github-oidc --location=global --workload-identity-pool=github --project $P >/dev/null 2>&1 \
  || gcloud iam workload-identity-pools providers create-oidc github-oidc --location=global --workload-identity-pool=github --project $P \
       --issuer-uri="https://token.actions.githubusercontent.com" \
       --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" \
       --attribute-condition="assertion.repository=='$REPO'"

gcloud iam service-accounts describe $DEPLOY --project $P >/dev/null 2>&1 \
  || gcloud iam service-accounts create github-deploy --project $P --display-name="GitHub deploy (bible-network)"
gcloud iam service-accounts describe $RUN --project $P >/dev/null 2>&1 \
  || gcloud iam service-accounts create bible-network-run --project $P --display-name="Bible Network runtime (no roles)"

# same roles as the workout tracker's deploy account
for r in run.admin cloudbuild.builds.editor artifactregistry.admin storage.admin iam.serviceAccountUser serviceusage.serviceUsageConsumer; do
  gcloud projects add-iam-policy-binding $P --member="serviceAccount:$DEPLOY" --role="roles/$r" --condition=None --quiet >/dev/null
  echo "ruolo $r -> github-deploy"
done
gcloud iam service-accounts add-iam-policy-binding $DEPLOY --project $P --role=roles/iam.workloadIdentityUser \
  --member="principalSet://iam.googleapis.com/projects/$N/locations/global/workloadIdentityPools/github/attribute.repository/$REPO" --quiet >/dev/null
echo "fatto: workload_identity_provider = projects/$N/locations/global/workloadIdentityPools/github/providers/github-oidc"
