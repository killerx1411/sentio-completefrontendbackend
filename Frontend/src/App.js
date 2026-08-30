import {
  createBrowserRouter,
  createRoutesFromElements,
  RouterProvider,
  Route,
  Navigate,
} from "react-router-dom";
import { SessionProvider } from "./context/SessionContext";
import { ADMIN_ROLES, CONSOLE_ROLES, MOBILE_ADMIN_ROLES, ROLES } from "./constants/roles";
import ProtectedRoute from "./components/ProtectedRoute";
import HomePage from "./HomePage";
import SignupPage from "./SignupPage";
import ResetPasswordPage from "./ResetPasswordPage";
import BehaviourAnalyst from "./BehaviourAnalyst";
import PrincipleDashboard from "./PrincipleDashboard";
import SchoolCounsellorDashboard from "./SchoolCounsellorDashboard";
import TeacherDashboard from "./TeacherDashboard";
import AdminLayout from "./admin/AdminLayout";
import AdminHome from "./admin/AdminHome";
import AdminDashboard from "./admin/AdminDashboard";
import UserManagement from "./admin/UserManagement";
import UserDetails from "./admin/UserDetails";
import AuditLogsPage from "./admin/AuditLogsPage";
import { MobileAdminProvider } from "./mobile/MobileAdminContext";
import MobileSectionGate from "./mobile/MobileSectionGate";
import MobileDashboard from "./mobile/pages/MobileDashboard";
import MobileExperts from "./mobile/pages/MobileExperts";
import MobileExpertDetail from "./mobile/pages/MobileExpertDetail";
import MobileUsers from "./mobile/pages/MobileUsers";
import MobileUserDetail from "./mobile/pages/MobileUserDetail";
import MobileRisk from "./mobile/pages/MobileRisk";
import MobileContent from "./mobile/pages/MobileContent";
import MobileExercises from "./mobile/pages/MobileExercises";
import MobileSessions from "./mobile/pages/MobileSessions";
import MobilePayments from "./mobile/pages/MobilePayments";
import MobileSubscriptions from "./mobile/pages/MobileSubscriptions";
import MobileAdmins from "./mobile/pages/MobileAdmins";
import MobileAudit from "./mobile/pages/MobileAudit";
import MobileSettings from "./mobile/pages/MobileSettings";
import MobileHealth from "./mobile/pages/MobileHealth";

// Data router (not <BrowserRouter>): useBlocker in UserDetails requires one.
const router = createBrowserRouter(
  createRoutesFromElements(
    <Route>
      <Route path="/" element={<HomePage />} />
      <Route path="/signup" element={<SignupPage />} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />

      <Route
        path="/BehaviourAnalyst"
        element={
          <ProtectedRoute allowedRoles={[ROLES.BEHAVIOUR_SCIENTIST]}>
            <BehaviourAnalyst />
          </ProtectedRoute>
        }
      />
      <Route
        path="/PrincipleDashboard"
        element={
          <ProtectedRoute allowedRoles={["Principal"]}>
            <PrincipleDashboard />
          </ProtectedRoute>
        }
      />
      <Route
        path="/SchoolCounsellorDashboard"
        element={
          <ProtectedRoute allowedRoles={[ROLES.PSYCHOLOGIST]}>
            <SchoolCounsellorDashboard />
          </ProtectedRoute>
        }
      />
      <Route
        path="/TeacherDashboard"
        element={
          <ProtectedRoute allowedRoles={[ROLES.CLASS_TEACHER]}>
            <TeacherDashboard />
          </ProtectedRoute>
        }
      />

      {/* One administrative console, two administrations. The shell admits both
          role families; each page below is gated on its own family, so a Mobile
          Admin never reaches a B2B page and a B2B admin never reaches a Mobile
          one. Their tokens are bound to different applications, so the backends
          would refuse the crossover regardless. */}
      <Route
        path="/admin"
        element={
          <ProtectedRoute allowedRoles={CONSOLE_ROLES}>
            <MobileAdminProvider>
              <AdminLayout />
            </MobileAdminProvider>
          </ProtectedRoute>
        }
      >
        <Route
          index
          element={
            <ProtectedRoute allowedRoles={ADMIN_ROLES}>
              <AdminHome />
            </ProtectedRoute>
          }
        />
        <Route
          path="pending"
          element={
            <ProtectedRoute allowedRoles={[ROLES.SUPER_ADMIN]}>
              <AdminDashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="users"
          element={
            <ProtectedRoute allowedRoles={ADMIN_ROLES}>
              <UserManagement />
            </ProtectedRoute>
          }
        />
        <Route
          path="users/:id"
          element={
            <ProtectedRoute allowedRoles={ADMIN_ROLES}>
              <UserDetails />
            </ProtectedRoute>
          }
        />
        <Route
          path="audit-logs"
          element={
            <ProtectedRoute allowedRoles={ADMIN_ROLES}>
              <AuditLogsPage />
            </ProtectedRoute>
          }
        />

        {/* Mobile administration. Backed entirely by the Mobile backend's
            /api/admin API — no direct database access from this frontend. */}
        <Route
          path="mobile"
          element={
            <ProtectedRoute allowedRoles={MOBILE_ADMIN_ROLES}>
              <MobileSectionGate />
            </ProtectedRoute>
          }
        >
          <Route index element={<MobileDashboard />} />
          <Route path="experts" element={<MobileExperts />} />
          <Route path="experts/:userId" element={<MobileExpertDetail />} />
          <Route path="users" element={<MobileUsers />} />
          <Route path="users/:userId" element={<MobileUserDetail />} />
          <Route path="risk" element={<MobileRisk />} />
          <Route path="content" element={<MobileContent />} />
          <Route path="exercises" element={<MobileExercises />} />
          <Route path="sessions" element={<MobileSessions />} />
          <Route path="payments" element={<MobilePayments />} />
          <Route path="subscriptions" element={<MobileSubscriptions />} />
          <Route path="admins" element={<MobileAdmins />} />
          <Route path="audit" element={<MobileAudit />} />
          <Route path="settings" element={<MobileSettings />} />
          <Route path="health" element={<MobileHealth />} />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Route>
  )
);

export default function App() {
  return (
    <SessionProvider>
      <RouterProvider router={router} />
    </SessionProvider>
  );
}
