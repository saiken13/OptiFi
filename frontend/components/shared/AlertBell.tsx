"use client";

import { Bell } from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { alertsApi } from "@/lib/api";
import type { Alert } from "@/types";
import { formatDate } from "@/lib/utils";

export function AlertBell() {
  const [open, setOpen] = useState(false);
  const qc = useQueryClient();

  const { data: alerts = [] } = useQuery<Alert[]>({
    queryKey: ["alerts"],
    queryFn: () => alertsApi.list().then((r) => r.data),
    refetchInterval: 30000,
  });

  const unreadCount = alerts.filter((a) => !a.is_read).length;

  const markRead = useMutation({
    mutationFn: (ids: string[]) => alertsApi.markRead(ids),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["alerts"] }),
  });

  const handleOpen = () => {
    setOpen(!open);
    if (!open && unreadCount > 0) {
      const unreadIds = alerts.filter((a) => !a.is_read).map((a) => a.id);
      markRead.mutate(unreadIds);
    }
  };

  return (
    <div className="relative">
      <button
        onClick={handleOpen}
        className="relative p-1.5 rounded-md hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
      >
        <Bell className="h-4 w-4" />
        {unreadCount > 0 && (
          <span className="absolute -top-0.5 -right-0.5 bg-destructive text-destructive-foreground text-[10px] font-bold rounded-full w-4 h-4 flex items-center justify-center">
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <>
          <div
            className="fixed inset-0 z-10"
            onClick={() => setOpen(false)}
          />
          <div className="absolute right-0 top-full mt-2 w-80 bg-card border border-border rounded-xl shadow-xl z-20 overflow-hidden">
            <div className="px-4 py-3 border-b border-border">
              <h3 className="text-sm font-semibold">Notifications</h3>
            </div>
            <div className="max-h-80 overflow-y-auto">
              {alerts.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-8">
                  No notifications
                </p>
              ) : (
                alerts.map((alert) => (
                  <div
                    key={alert.id}
                    className={`px-4 py-3 border-b border-border/50 last:border-0 ${
                      !alert.is_read ? "bg-primary/5" : ""
                    }`}
                  >
                    <p className="text-sm font-medium">{alert.title}</p>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {alert.message}
                    </p>
                    <p className="text-[10px] text-muted-foreground/60 mt-1">
                      {formatDate(alert.created_at)}
                    </p>
                  </div>
                ))
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
