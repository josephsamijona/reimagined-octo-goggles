// JHBridge - Notifications Panel Component
import { useState } from "react";
import { 
  Bell, 
  Check, 
  AlertTriangle, 
  CheckCircle, 
  Mail, 
  MapPin,
  Clock,
  X
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

// Mock notifications data
const MOCK_NOTIFICATIONS = [
  { 
    id: 1, 
    type: "alert", 
    title: "ASG-1045 needs interpreter", 
    message: "Unassigned mission starting in 24 hours",
    time: "2 hours ago",
    read: false,
    module: "dispatch",
    itemId: "ASG-1045"
  },
  { 
    id: 2, 
    type: "email", 
    title: "3 new emails classified", 
    message: "AI Agent processed incoming emails",
    time: "45 minutes ago",
    read: false,
    module: "ai-agent"
  },
  { 
    id: 3, 
    type: "success", 
    title: "INV-0034 payment received", 
    message: "Cambridge Health Alliance paid $450",
    time: "Yesterday",
    read: true,
    module: "finance"
  },
  { 
    id: 4, 
    type: "warning", 
    title: "2 onboardings stalled", 
    message: "No progress in more than 3 days",
    time: "2 days ago",
    read: true,
    module: "hiring"
  },
  { 
    id: 5, 
    type: "info", 
    title: "Mission completed", 
    message: "ASG-1046 marked as completed by Maria Santos",
    time: "3 days ago",
    read: true,
    module: "dispatch",
    itemId: "ASG-1046"
  },
];

export const NotificationsPanel = ({ isOpen, onClose, onNavigate }) => {
  const [notifications, setNotifications] = useState(MOCK_NOTIFICATIONS);

  const unreadCount = notifications.filter(n => !n.read).length;

  const handleMarkAsRead = (id) => {
    setNotifications(prev => 
      prev.map(n => n.id === id ? { ...n, read: true } : n)
    );
  };

  const handleMarkAllAsRead = () => {
    setNotifications(prev => prev.map(n => ({ ...n, read: true })));
  };

  const handleNotificationClick = (notification) => {
    handleMarkAsRead(notification.id);
    if (onNavigate) {
      onNavigate(notification.module, { selected: notification.itemId });
    }
    onClose();
  };

  const getIcon = (type) => {
    switch (type) {
      case "alert": return <AlertTriangle className="w-4 h-4 text-danger" />;
      case "success": return <CheckCircle className="w-4 h-4 text-success" />;
      case "warning": return <AlertTriangle className="w-4 h-4 text-warning" />;
      case "email": return <Mail className="w-4 h-4 text-info" />;
      case "info": return <MapPin className="w-4 h-4 text-navy dark:text-gold" />;
      default: return <Bell className="w-4 h-4" />;
    }
  };

  if (!isOpen) return null;

  return (
    <div 
      className="absolute top-full right-0 mt-2 w-80 bg-card border border-border rounded-lg shadow-lg z-50 animate-in fade-in slide-in-from-top-2 duration-200"
      data-testid="notifications-panel"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-sm">Notifications</span>
          {unreadCount > 0 && (
            <span className="px-1.5 py-0.5 text-[10px] font-semibold bg-danger text-white rounded">
              {unreadCount}
            </span>
          )}
        </div>
        <div className="flex items-center gap-1">
          {unreadCount > 0 && (
            <Button
              variant="ghost"
              size="sm"
              className="h-7 text-xs"
              onClick={handleMarkAllAsRead}
              data-testid="mark-all-read"
            >
              <Check className="w-3 h-3 mr-1" />
              Mark all
            </Button>
          )}
          <button
            onClick={onClose}
            className="p-1 rounded hover:bg-muted transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Notifications List */}
      <div className="max-h-96 overflow-y-auto">
        {/* Unread */}
        {notifications.filter(n => !n.read).length > 0 && (
          <div>
            <div className="px-4 py-2 text-[10px] font-semibold text-muted-foreground uppercase tracking-wider bg-muted/30">
              New
            </div>
            {notifications.filter(n => !n.read).map(notification => (
              <button
                key={notification.id}
                onClick={() => handleNotificationClick(notification)}
                className="w-full px-4 py-3 flex items-start gap-3 hover:bg-muted/50 transition-colors border-l-2 border-l-primary text-left"
                data-testid={`notification-${notification.id}`}
              >
                <div className="mt-0.5">{getIcon(notification.type)}</div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium truncate">{notification.title}</div>
                  <div className="text-xs text-muted-foreground truncate">{notification.message}</div>
                  <div className="text-[10px] text-muted-foreground mt-1 flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {notification.time}
                  </div>
                </div>
              </button>
            ))}
          </div>
        )}

        {/* Read */}
        {notifications.filter(n => n.read).length > 0 && (
          <div>
            <div className="px-4 py-2 text-[10px] font-semibold text-muted-foreground uppercase tracking-wider bg-muted/30">
              Earlier
            </div>
            {notifications.filter(n => n.read).map(notification => (
              <button
                key={notification.id}
                onClick={() => handleNotificationClick(notification)}
                className="w-full px-4 py-3 flex items-start gap-3 hover:bg-muted/50 transition-colors text-left opacity-70"
                data-testid={`notification-${notification.id}`}
              >
                <div className="mt-0.5">{getIcon(notification.type)}</div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium truncate">{notification.title}</div>
                  <div className="text-xs text-muted-foreground truncate">{notification.message}</div>
                  <div className="text-[10px] text-muted-foreground mt-1 flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {notification.time}
                  </div>
                </div>
              </button>
            ))}
          </div>
        )}

        {/* Empty State */}
        {notifications.length === 0 && (
          <div className="py-8 text-center text-sm text-muted-foreground">
            <Bell className="w-8 h-8 mx-auto mb-2 opacity-50" />
            No notifications
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="px-4 py-2 border-t border-border bg-muted/30">
        <Button
          variant="ghost"
          size="sm"
          className="w-full text-xs justify-center"
          onClick={() => {
            onNavigate("settings");
            onClose();
          }}
        >
          Notification Settings
        </Button>
      </div>
    </div>
  );
};

export default NotificationsPanel;
