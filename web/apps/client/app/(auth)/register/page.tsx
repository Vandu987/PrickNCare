"use client";

/**
 * Registration page — stub.
 * Backend does not yet expose a public /auth/register endpoint;
 * this page will be fleshed out once that API is available.
 */
export default function RegisterPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-md space-y-6 rounded-xl bg-white p-8 shadow-lg text-center">
        <h1 className="text-2xl font-bold text-gray-900">Create an account</h1>
        <p className="text-sm text-gray-500">
          Registration is currently available by invitation only. Please contact
          support if you need an account.
        </p>
        <a
          href="/login"
          className="inline-block rounded-md bg-teal-600 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-500"
        >
          Back to login
        </a>
      </div>
    </div>
  );
}
