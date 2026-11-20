import React, { useState, useEffect, useCallback } from 'react';
import { AppLayout, UserRole } from './components/AppLayout';
import { LoginPage, SessionUser } from './pages/LoginPage';
import { StudentPortal } from './pages/StudentPortal';
import { FacultyPortal } from './pages/FacultyPortal';
import { AdminPortal } from './pages/AdminPortal';
import { ProjectorView } from './pages/ProjectorView';
import { ShieldAlert, ArrowLeft } from 'lucide-react';

export const App: React.FC = () => {
  // Current route pathname
  const [currentPath, setCurrentPath] = useState<string>(() => {
    if (typeof window !== 'undefined') {
      return window.location.pathname || '/';
    }
    return '/';
  });

  // Current session user (default student demo session, can log out or switch)
  const [user, setUser] = useState<SessionUser | null>(() => {
    // Check if demo user stored in localStorage/session
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('classync_session');
      if (stored) {
        try {
          return JSON.parse(stored);
        } catch {
          // ignore parsing error
        }
      }
    }
    // Default active session for initial exploration
    return {
      user_id: 'usr_student_01',
      email: 'rcastillo@student.pnm.edu.ph',
      student_id: '24-00123',
      full_name: 'Renmaur Castillo',
      role: 'STUDENT',
      requires_password_change: false,
    };
  });

  const [unauthorizedMessage, setUnauthorizedMessage] = useState<string | null>(null);

  // Sync with browser navigation (popstate)
  useEffect(() => {
    const handlePopState = () => {
      setCurrentPath(window.location.pathname || '/');
      setUnauthorizedMessage(null);
    };

    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  // Safe client-side navigation
  const navigate = useCallback((path: string) => {
    if (typeof window !== 'undefined') {
      window.history.pushState({}, '', path);
    }
    setCurrentPath(path);
    setUnauthorizedMessage(null);
  }, []);

  const handleLoginSuccess = (authenticatedUser: SessionUser) => {
    setUser(authenticatedUser);
    if (typeof window !== 'undefined') {
      localStorage.setItem('classync_session', JSON.stringify(authenticatedUser));
    }

    if (authenticatedUser.requires_password_change) {
      navigate('/setup-password');
      return;
    }

    switch (authenticatedUser.role) {
      case 'ADMIN':
        navigate('/admin');
        break;
      case 'FACULTY':
        navigate('/faculty');
        break;
      case 'STUDENT':
      default:
        navigate('/student');
        break;
    }
  };

  const handleSignOut = () => {
    setUser(null);
    if (typeof window !== 'undefined') {
      localStorage.removeItem('classync_session');
    }
    navigate('/login');
  };

  // Password Setup Complete callback
  const handlePasswordSetupComplete = (updatedUser: SessionUser) => {
    const freshUser = { ...updatedUser, requires_password_change: false };
    setUser(freshUser);
    if (typeof window !== 'undefined') {
      localStorage.setItem('classync_session', JSON.stringify(freshUser));
    }
    navigate('/student');
  };

  // 1. Standalone Chromeless Route: /projector/:roomCode (e.g. /projector/PRRC 301)
  if (currentPath.startsWith('/projector')) {
    const segments = currentPath.split('/');
    const roomCodeParam = segments[2] ? decodeURIComponent(segments[2]) : 'PRRC 301';

    return (
      <main className="min-h-screen bg-[var(--brand-midnight)] text-white relative">
        <div className="absolute top-4 left-4 z-50">
          <button
            onClick={() => {
              if (user?.role === 'FACULTY') {
                navigate('/faculty');
              } else if (user?.role === 'ADMIN') {
                navigate('/admin');
              } else {
                navigate('/student');
              }
            }}
            className="flex items-center gap-2 bg-white/10 hover:bg-white/20 text-white px-3 py-2 rounded-lg text-xs font-semibold backdrop-blur transition-colors"
            title="Exit Projector Mode"
          >
            <ArrowLeft size={16} />
            <span>Exit Projector Mode</span>
          </button>
        </div>
        <ProjectorView roomCode={roomCodeParam} />
      </main>
    );
  }

  // 2. Authentication Route: /login
  if (currentPath === '/login') {
    return <LoginPage initialMode="login" onLoginSuccess={handleLoginSuccess} />;
  }

  // 3. Password Setup Interceptor Route: /setup-password
  if (currentPath === '/setup-password') {
    return (
      <LoginPage
        initialMode="setup-password"
        onLoginSuccess={handlePasswordSetupComplete}
      />
    );
  }

  // Password Change Interceptor: If user requires password change, lock to setup mode
  if (user?.requires_password_change) {
    return (
      <LoginPage
        initialMode="setup-password"
        onLoginSuccess={handlePasswordSetupComplete}
      />
    );
  }

  // If unauthenticated, redirect to Login
  if (!user) {
    return <LoginPage initialMode="login" onLoginSuccess={handleLoginSuccess} />;
  }

  // 4. Role-based Route Protection and Guarding
  const renderProtectedContent = () => {
    // Admin Routes
    if (currentPath.startsWith('/admin')) {
      if (user.role !== 'ADMIN') {
        return (
          <div className="max-w-2xl mx-auto my-12 p-8 bg-white rounded-2xl border border-[var(--line)] shadow-sm text-center space-y-4">
            <div className="w-14 h-14 bg-rose-50 text-[var(--brand-rouge)] rounded-full flex items-center justify-center mx-auto">
              <ShieldAlert size={28} />
            </div>
            <h2 className="text-xl font-bold text-[var(--ink)]">Institutional Admin Access Restricted</h2>
            <p className="text-sm text-[var(--ink-soft)] leading-relaxed">
              This space requires Dean or Administrative Registrar credentials. Your account is logged in as{' '}
              <strong className="text-[var(--brand-rouge)]">{user.full_name} ({user.role})</strong>.
            </p>
            <div className="pt-2">
              <button
                onClick={() => navigate(user.role === 'FACULTY' ? '/faculty' : '/student')}
                className="tactile-button min-h-[48px] px-6 py-2.5 rounded-[10px] bg-[var(--brand-rouge)] text-white font-semibold text-sm hover:opacity-95"
              >
                Return to My Dashboard
              </button>
            </div>
          </div>
        );
      }
      return <AdminPortal />;
    }

    // Faculty Routes
    if (currentPath.startsWith('/faculty')) {
      if (user.role !== 'FACULTY' && user.role !== 'ADMIN') {
        return (
          <div className="max-w-2xl mx-auto my-12 p-8 bg-white rounded-2xl border border-[var(--line)] shadow-sm text-center space-y-4">
            <div className="w-14 h-14 bg-rose-50 text-[var(--brand-rouge)] rounded-full flex items-center justify-center mx-auto">
              <ShieldAlert size={28} />
            </div>
            <h2 className="text-xl font-bold text-[var(--ink)]">Faculty Teaching Portal Restricted</h2>
            <p className="text-sm text-[var(--ink-soft)] leading-relaxed">
              Faculty matrix schedules are accessible to full-time instructors and college administrators.
            </p>
            <div className="pt-2">
              <button
                onClick={() => navigate('/student')}
                className="tactile-button min-h-[48px] px-6 py-2.5 rounded-[10px] bg-[var(--brand-rouge)] text-white font-semibold text-sm hover:opacity-95"
              >
                Return to Student Portal
              </button>
            </div>
          </div>
        );
      }
      return (
        <FacultyPortal
          onLaunchProjector={(roomCode) => navigate(`/projector/${encodeURIComponent(roomCode)}`)}
        />
      );
    }

    // Student Routes (or default '/')
    return <StudentPortal />;
  };

  return (
    <AppLayout
      activePath={currentPath}
      onNavigate={navigate}
      userRole={user.role}
      userName={user.full_name}
      studentIdOrEmail={user.student_id || user.email}
      onSignOut={handleSignOut}
    >
      {renderProtectedContent()}
    </AppLayout>
  );
};

export default App;
