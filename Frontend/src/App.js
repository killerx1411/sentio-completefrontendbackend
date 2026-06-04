import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { SessionProvider } from "./context/SessionContext";
import ProtectedRoute from "./components/ProtectedRoute";
import HomePage from "./HomePage";
import SignupPage from "./SignupPage";
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

export default function App() {
  return (
    <SessionProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/signup" element={<SignupPage />} />

          <Route
            path="/BehaviourAnalyst"
            element={
              <ProtectedRoute allowedRoles={["Behaviour Analyst"]}>
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
              <ProtectedRoute allowedRoles={["Counsellor"]}>
                <SchoolCounsellorDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/TeacherDashboard"
            element={
              <ProtectedRoute allowedRoles={["Teacher"]}>
                <TeacherDashboard />
              </ProtectedRoute>
            }
          />

          <Route
            path="/admin"
            element={
              <ProtectedRoute
                allowedRoles={["Super Admin", "Secondary Admin", "Normal Admin"]}
              >
                <AdminLayout />
              </ProtectedRoute>
            }
          >
            <Route index element={<AdminHome />} />
            <Route
              path="pending"
              element={
                <ProtectedRoute allowedRoles={["Super Admin"]}>
                  <AdminDashboard />
                </ProtectedRoute>
              }
            />
            <Route path="users" element={<UserManagement />} />
            <Route path="users/:id" element={<UserDetails />} />
            <Route path="audit-logs" element={<AuditLogsPage />} />
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </SessionProvider>
  );
}
