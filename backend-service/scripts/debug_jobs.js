const { PrismaClient } = require('@prisma/client');
const prisma = new PrismaClient();

async function main() {
  const jobs = await prisma.job.findMany({
    include: { user: { include: { plan: true } } }
  });
  console.log('--- ALL JOBS IN DATABASE ---');
  jobs.forEach(j => {
    console.log(`[ID: ${j.id}] Status: ${j.status} | User: ${j.user.email} | Plan: ${j.user.plan.name}`);
  });
}

main().finally(() => prisma.$disconnect());
