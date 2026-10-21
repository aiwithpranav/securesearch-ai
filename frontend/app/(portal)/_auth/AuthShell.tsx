import { DotsSphere } from "../../_components/DotsSphere";

// Frame for the sign-in pages: the dots sphere sits quietly behind the form card.
export function AuthShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="relative min-h-screen overflow-hidden">
      <DotsSphere strength={0.75} />
      <main id="main" className="relative z-10 mx-auto flex min-h-screen w-full max-w-md flex-col justify-center px-5 py-12">
        {children}
      </main>
    </div>
  );
}
