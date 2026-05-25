export default function LoadingSpinner({ className = "h-4 w-4" }: { className?: string }) {
  return <span className={`spinner ${className}`} aria-hidden="true" />;
}
