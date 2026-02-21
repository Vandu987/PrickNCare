import { Button } from "@prickncare/ui";

export default function AdminDashboard() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24">
      <h1 className="text-4xl font-bold mb-4">PricknCare Admin Panel</h1>
      <p className="text-gray-600 mb-8">
        Blood Sample Collection Management System
      </p>
      <Button>Get Started</Button>
    </main>
  );
}
