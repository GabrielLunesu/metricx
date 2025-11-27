import Link from 'next/link';

export default function FooterDashboard() {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="mt-12 pt-8 border-t border-slate-200">
      <div className="flex flex-col sm:flex-row justify-between items-center gap-4 text-sm text-slate-600">
        <div className="flex flex-wrap justify-center gap-4">
          <Link
            href="/privacy"
            className="hover:text-cyan-600 transition-colors"
            target="_blank"
          >
            Privacy
          </Link>
          <Link
            href="/terms"
            className="hover:text-cyan-600 transition-colors"
            target="_blank"
          >
            Terms
          </Link>
          <Link
            href="/settings"
            className="hover:text-cyan-600 transition-colors"
          >
            Delete My Data
          </Link>
        </div>
        <div>
          © {currentYear} metricx
        </div>
      </div>
    </footer>
  );
}

