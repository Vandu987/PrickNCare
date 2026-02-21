import { Button } from "@prickncare/ui";

export default function ClientDashboard() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24">
      <h1 className="text-4xl font-bold mb-4">PricknCare Client Portal</h1>
      <p className="text-gray-600 mb-8">
        Order and manage blood sample collections
      </p>
      <Button>Place Order</Button>
    </main>
  );
}
