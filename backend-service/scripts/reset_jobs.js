const { PrismaClient } = require('@prisma/client');
const prisma = new PrismaClient();

async function main() {
  const result = await prisma.job.updateMany({
    where: { status: 'failed' },
    data: { status: 'queued', error: null }
  });
  console.log(`Reset ${result.count} failed jobs to queued.`);
}

main().finally(() => prisma.$disconnect());
