"use client";

import { useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Activity, Bot, Database, Gauge, PanelLeft, ShieldAlert } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { cn } from '@/lib/utils';

const navItems = [
  { href: '/dashboard', label: 'Dashboard', icon: PanelLeft },
  { href: '/auth', label: 'Auth', icon: ShieldAlert },
  { href: '/architecture', label: 'Architecture', icon: Database },
  { href: '/incidents', label: 'Incidents', icon: Database },
  { href: '/logs', label: 'Logs', icon: Activity },
  { href: '/orchestrator', label: 'Orchestrator', icon: Bot },
  { href: '/dashboard#metrics', label: 'Metrics', icon: Gauge },
];

export function AppShell({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  const pathname = usePathname();

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const hash = window.location.hash;
    if (!hash) return;

    const target = document.querySelector(hash);
    if (target) {
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }, [pathname]);

  return (
    <main className="mx-auto min-h-screen max-w-7xl px-6 py-6 lg:px-10">
      <div className="grid gap-6 lg:grid-cols-[260px_1fr]">
        <aside className="rounded-[2rem] border border-white/10 bg-white/5 p-5 shadow-glow backdrop-blur">
          <div className="space-y-4">
            <Badge className="border-cyan-400/20 bg-cyan-400/10 text-cyan-200">AegisOps AI</Badge>
            <div>
              <h2 className="text-2xl font-semibold text-white">{title}</h2>
              <p className="mt-2 text-sm leading-6 text-slate-300">{description}</p>
            </div>
            <Separator />
            <nav className="space-y-2">
              {navItems.map((item) => (
                <Button
                  key={item.href}
                  asChild
                  variant="ghost"
                  className={cn(
                    'w-full justify-start transition-colors',
                    pathname === item.href.split('#')[0] && 'bg-cyan-400/10 text-cyan-100 hover:bg-cyan-400/15',
                  )}
                >
                  <Link href={item.href}>
                    <item.icon className="h-4 w-4" />
                    {item.label}
                  </Link>
                </Button>
              ))}
            </nav>
          </div>
        </aside>
        <section>{children}</section>
      </div>
    </main>
  );
}
