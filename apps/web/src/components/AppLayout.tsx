import React from 'react';
import { BrandLogo } from './common/BrandLogo';
import {
  Calendar,
  Home,
  Monitor,
  User,
  LogOut,
  Layers,
  Sparkles,
  ShieldCheck,
  Tv,
  AlertTriangle,
  Menu,
  X,
} from 'lucide-react';

export type UserRole = 'STUDENT' | 'FACULTY' | 'ADMIN';

export interface AppLayoutProps {
  children: React.ReactNode;
  activePath: string;
  onNavigate: (path: string) => void;
  userRole?: UserRole;
  userName?: string;
  studentIdOrEmail?: string;
  isOffline?: boolean;
  onSignOut?: () => void;
}

export const AppLayout: React.FC<AppLayoutProps> = ({
  children,
  activePath,
  onNavigate,
  userRole = 'STUDENT',
  userName = 'Renmaur Castillo',
  studentIdOrEmail = '24-00123',
  isOffline = false,
  onSignOut,
}) => {
  const [mobileMenuOpen, setMobileMenuOpen] = React.useState(false);

  const getNavLinks = () => {
    switch (userRole) {
      case 'ADMIN':
        return [
          { path: '/admin', label: 'Overview', icon: Home },
          { path: '/admin/rooms', label: 'Spatial Directory', icon: Layers },
          { path: '/admin/solver', label: 'CP-SAT Solver', icon: Sparkles },
          { path: '/admin/audit', label: 'Conflict Auditor', icon: ShieldCheck },
        ];
      case 'FACULTY':
        return [
          { path: '/faculty', label: 'My Teaching Matrix', icon: Calendar },
          { path: '/faculty/swaps', label: 'Room Swap Requests', icon: Layers },
          { path: '/projector/PRRC 301', label: 'Projector Mode', icon: Tv },
          { path: '/faculty/profile', label: 'Faculty Profile', icon: User },
        ];
      case 'STUDENT':
      default:
        return [
          { path: '/student', label: 'Today', icon: Home },
          { path: '/student/timetable', label: 'Schedule', icon: Calendar },
          { path: '/student/comlab', label: 'COMLAB Vacancy', icon: Monitor },
          { path: '/student/profile', label: 'Profile', icon: User },
        ];
    }
  };

  const navLinks = getNavLinks();

  return (
    <div className="min-h-screen bg-[var(--canvas)] flex flex-col">
      {/* 1. Offline Banner Notification (Decision Log D-12) */}
      {isOffline && (
        <div className="bg-[var(--warning-soft)] border-b border-[var(--warning-border)] text-[var(--warning)] px-4 py-2 text-xs sm:text-sm font-medium flex items-center justify-center gap-2 sticky top-0 z-50">
          <AlertTriangle size={15} />
          <span>🟢 Offline Mode • Showing your saved schedule. Reconnecting to campus Wi-Fi...</span>
        </div>
      )}

      {/* 2. Top Utility Bar (64px) */}
      <header className="h-16 bg-white border-b border-[var(--line)] px-4 sm:px-6 flex items-center justify-between sticky top-0 z-40">
        <div className="flex items-center gap-3">
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="lg:hidden min-h-[48px] min-w-[48px] flex items-center justify-center text-[var(--ink)]"
            aria-label="Toggle Navigation"
          >
            {mobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
          </button>
          <div className="cursor-pointer" onClick={() => onNavigate(navLinks[0].path)}>
            <BrandLogo variant="horizontal" className="h-7 w-auto" />
          </div>
        </div>

        <div className="flex items-center gap-4">
          <div className="hidden sm:flex items-center gap-2 px-2.5 py-1 rounded-full bg-[var(--surface-strong)] text-xs font-medium text-[var(--ink-soft)]">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span>Campus Network Active</span>
          </div>

          <div className="flex items-center gap-2">
            <div className="text-right hidden sm:block">
              <div className="text-sm font-bold text-[var(--ink)] leading-tight">{userName}</div>
              <div className="text-xs text-[var(--ink-soft)]">{studentIdOrEmail} • {userRole}</div>
            </div>
            <div className="w-10 h-10 rounded-full bg-[var(--brand-rouge)] text-white font-bold flex items-center justify-center text-sm shadow-sm">
              {userName.charAt(0)}
            </div>
            {onSignOut && (
              <button
                onClick={onSignOut}
                className="tactile-button min-h-[48px] min-w-[48px] flex items-center justify-center text-[var(--ink-soft)] hover:text-[var(--danger)] transition-colors"
                title="Sign Out"
                aria-label="Sign Out"
              >
                <LogOut size={18} />
              </button>
            )}
          </div>
        </div>
      </header>

      {/* 3. Main Workspace with Desktop Sidebar Rail */}
      <div className="flex-1 flex overflow-hidden">
        {/* Desktop Sidebar Rail (256px) */}
        <aside className="hidden lg:flex w-64 bg-white border-r border-[var(--line)] flex-col justify-between p-4 flex-shrink-0">
          <div className="space-y-1">
            <div className="px-3 py-2 text-xs font-semibold text-[var(--ink-soft)] uppercase tracking-wider">
              {userRole} Navigation
            </div>
            {navLinks.map((link) => {
              const Icon = link.icon;
              const isActive = activePath === link.path;
              return (
                <button
                  key={link.path}
                  onClick={() => onNavigate(link.path)}
                  className={`tactile-button w-full min-h-[48px] px-3.5 py-2.5 rounded-[10px] text-sm font-semibold flex items-center gap-3 transition-colors ${
                    isActive
                      ? 'bg-[var(--brand-rose)] text-[var(--brand-rouge)]'
                      : 'text-[var(--ink)] hover:bg-[var(--surface-strong)]'
                  }`}
                >
                  <Icon size={18} className={isActive ? 'text-[var(--brand-rouge)]' : 'text-[var(--ink-soft)]'} />
                  <span>{link.label}</span>
                </button>
              );
            })}
          </div>

          {/* Sidebar Footer */}
          <div className="p-3 bg-[var(--surface-strong)] rounded-[12px] text-xs text-[var(--ink-soft)]">
            <div className="font-semibold text-[var(--ink)]">Colegio de Montalban</div>
            <div>Pamantasan ng Montalban</div>
            <div className="text-[10px] mt-1 text-[var(--ink-soft)]">ClassSync v2 • Academic Year 2026–2027</div>
          </div>
        </aside>

        {/* Mobile Navigation Drawer Overlay */}
        {mobileMenuOpen && (
          <div className="fixed inset-0 z-50 lg:hidden flex">
            <div
              className="fixed inset-0 bg-black/40 backdrop-blur-sm"
              onClick={() => setMobileMenuOpen(false)}
            />
            <div className="relative w-72 max-w-[80%] bg-white h-full shadow-2xl p-5 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between pb-4 border-b border-[var(--line)]">
                  <BrandLogo variant="horizontal" className="h-6 w-auto" />
                  <button
                    onClick={() => setMobileMenuOpen(false)}
                    className="min-h-[48px] min-w-[48px] flex items-center justify-center"
                    aria-label="Close menu"
                  >
                    <X size={20} />
                  </button>
                </div>
                <div className="mt-4 space-y-1">
                  {navLinks.map((link) => {
                    const Icon = link.icon;
                    const isActive = activePath === link.path;
                    return (
                      <button
                        key={link.path}
                        onClick={() => {
                          onNavigate(link.path);
                          setMobileMenuOpen(false);
                        }}
                        className={`tactile-button w-full min-h-[48px] px-4 py-3 rounded-[10px] text-sm font-semibold flex items-center gap-3 ${
                          isActive
                            ? 'bg-[var(--brand-rose)] text-[var(--brand-rouge)]'
                            : 'text-[var(--ink)] hover:bg-[var(--surface-strong)]'
                        }`}
                      >
                        <Icon size={18} className={isActive ? 'text-[var(--brand-rouge)]' : 'text-[var(--ink-soft)]'} />
                        <span>{link.label}</span>
                      </button>
                    );
                  })}
                </div>
              </div>

              {onSignOut && (
                <button
                  onClick={() => {
                    setMobileMenuOpen(false);
                    onSignOut();
                  }}
                  className="tactile-button min-h-[48px] w-full px-4 py-3 rounded-[10px] text-sm font-semibold text-[var(--danger)] hover:bg-[var(--danger-soft)] flex items-center gap-2"
                >
                  <LogOut size={18} />
                  <span>Sign Out</span>
                </button>
              )}
            </div>
          </div>
        )}

        {/* Main Content Area */}
        <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto w-full pb-24 lg:pb-8">
          {children}
        </main>
      </div>

      {/* 4. Mobile Bottom Navigation Bar (72px) per Fitts's Law */}
      <nav className="lg:hidden h-[72px] bg-white border-t border-[var(--line)] fixed bottom-0 left-0 right-0 z-40 px-3 flex items-center justify-around shadow-lg">
        {navLinks.map((link) => {
          const Icon = link.icon;
          const isActive = activePath === link.path;
          return (
            <button
              key={link.path}
              onClick={() => onNavigate(link.path)}
              className="min-h-[48px] min-w-[48px] flex flex-col items-center justify-center gap-1 flex-1 text-center"
              aria-label={link.label}
            >
              <Icon
                size={20}
                className={isActive ? 'text-[var(--brand-rouge)]' : 'text-[var(--ink-soft)]'}
              />
              <span
                className={`text-[10px] font-semibold leading-tight ${
                  isActive ? 'text-[var(--brand-rouge)]' : 'text-[var(--ink-soft)]'
                }`}
              >
                {link.label}
              </span>
            </button>
          );
        })}
      </nav>
    </div>
  );
};
