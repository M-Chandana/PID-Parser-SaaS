const { PrismaClient } = require('@prisma/client');
const prisma = new PrismaClient();

async function main() {
  const job = await prisma.job.findUnique({
    where: { id: '33189d55-cd94-418b-a2c3-1a84926117d2' }
  });
  if (job) {
    console.log(`--- JOB STATUS: ${job.status} ---`);
  } else {
    console.log('--- JOB NOT FOUND ---');
  }
  prisma.$disconnect();
}

main();
