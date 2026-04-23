const { PrismaClient } = require('@prisma/client');

const prisma = new PrismaClient();
const jobId = process.argv[2];

if (!jobId) {
  console.error('Usage: node scripts/check_job_status.js <jobId>');
  process.exit(1);
}

async function main() {
  const job = await prisma.job.findUnique({
    where: { id: jobId },
    include: { artifacts: true, user: { include: { plan: true } } },
  });

  if (!job) {
    console.error(`Job not found: ${jobId}`);
    process.exit(1);
  }

  console.log(JSON.stringify({
    id: job.id,
    status: job.status,
    error: job.error,
    processingTime: job.processingTime,
    userEmail: job.user.email,
    userPlan: job.user.plan.name,
    artifactsCount: job.artifacts.length,
    updatedAt: job.updatedAt,
  }, null, 2));
}

main()
  .catch((error) => {
    console.error('Failed to check job status:', error.message);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
