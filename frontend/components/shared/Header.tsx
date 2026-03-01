"use client";

import { AlertBell } from "./AlertBell";

interface HeaderProps {
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
}

export function Header({ title, subtitle, actions }: HeaderProps) {
  return (
    <div className="flex items-center justify-between h-14 px-6 border-b border-border bg-card/50 backdrop-blur-sm shrink-0">
      <div>
        <h1 className="text-base font-semibold">{title}</h1>
        {subtitle && (
          <p className="text-xs text-muted-foreground">{subtitle}</p>
        )}
      </div>
      <div className="flex items-center gap-3">
        {actions}
        <AlertBell />
      </div>
    </div>
  );
}
