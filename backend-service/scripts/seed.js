const { PrismaClient } = require('@prisma/client');
const prisma = new PrismaClient();

async function main() {
  console.log('Seeding plans...');
  
  const freePlan = await prisma.plan.upsert({
    where: { name: 'free' },
    update: {},
    create: {
      name: 'free',
      maxDaily: 5,
      maxMonthly: 150,
    },
  });

  const paidPlan = await prisma.plan.upsert({
    where: { name: 'paid' },
    update: {},
    create: {
      name: 'paid',
      maxDaily: 100, // Very high daily limit for paid users
      maxMonthly: 1000,
    },
  });

  console.log({ freePlan, paidPlan });
  console.log('Seeding completed.');
}

main()
  .catch((e) => {
    console.error(e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
