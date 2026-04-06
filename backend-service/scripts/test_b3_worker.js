const { PrismaClient } = require('@prisma/client');
const prisma = new PrismaClient();
const path = require('path');

async function main() {
  console.log('--- B3 Worker Integration Test Setup ---');

  // 1. Get the paid plan
  const paidPlan = await prisma.plan.findUnique({
    where: { name: 'paid' }
  });

  if (!paidPlan) {
    console.error('Paid plan not found. Please run scripts/seed.js first.');
    return;
  }

  // 2. Create a test user
  const user = await prisma.user.upsert({
    where: { email: 'worker_test@example.com' },
    update: { planId: paidPlan.id },
    create: {
      email: 'worker_test@example.com',
      passwordHash: 'hashed_pw', // Normally bcrypt
      planId: paidPlan.id
    }
  });

  console.log(`User created: ${user.email} (Plan: ${paidPlan.name})`);

  // 3. Create a queued job with our test file
  const testFilePath = path.join('storage', 'test_b3.png');
  
  const job = await prisma.job.create({
    data: {
      userId: user.id,
      status: 'queued',
      originalFile: testFilePath,
      fileSize: 2889 // size of test_pid.png
    }
  });

  console.log(`Job Created: ID=${job.id}, Status=${job.status}, File=${job.originalFile}`);
  console.log('-----------------------------------------');
  console.log('NOW RUN: npm run worker');
  console.log('Keep this terminal open to see logs.');
}

main()
  .catch(e => console.error(e))
  .finally(() => prisma.$disconnect());
