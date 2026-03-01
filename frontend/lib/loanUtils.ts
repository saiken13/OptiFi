export function loan_amortization(
  balance: number,
  annualRate: number,
  monthlyPayment: number,
  extraPayment: number = 0
): Array<{ month: number; payment: number; principal: number; interest: number; balance: number }> {
  const monthlyRate = annualRate / 100 / 12;
  const schedule = [];
  let currentBalance = balance;
  let month = 0;

  while (currentBalance > 0 && month < 600) {
    month++;
    const interest = currentBalance * monthlyRate;
    const payment = Math.min(monthlyPayment + extraPayment, currentBalance + interest);
    const principal = payment - interest;
    currentBalance = Math.max(0, currentBalance - principal);
    schedule.push({
      month,
      payment: Math.round(payment * 100) / 100,
      principal: Math.round(principal * 100) / 100,
      interest: Math.round(interest * 100) / 100,
      balance: Math.round(currentBalance * 100) / 100,
    });
  }

  return schedule;
}
