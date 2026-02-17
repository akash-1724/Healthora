import React from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Link, Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";

import Dashboard from "./Dashboard";
import Inventory from "./Inventory";
import Login from "./Login";
import Reorder from "./Reorder";
import Reports from "./Reports";
import Users from "./Users";
import { api } from "./api";

function Protected({ children }) {
  const token = localStorage.getItem("token");
  if (!token) return <Navigate to="/" replace />;
  return children;
}

function TopNav() {
  const location = useLocation();
  const navigate = useNavigate();
  const [username, setUsername] = React.useState(localStorage.getItem("username") || "User");

  React.useEffect(() => {
    api
      .me()
      .then((user) => {
        setUsername(user.username);
        localStorage.setItem("username", user.username);
      })
      .catch(() => {
        setUsername(localStorage.getItem("username") || "User");
      });
  }, [location.pathname]);

  function logout() {
    localStorage.removeItem("token");
    localStorage.removeItem("username");
    navigate("/");
  }

  const navLinkStyle = {
    color: "#d6e4ff",
    textDecoration: "none",
    padding: "8px 12px",
    borderRadius: 8,
    fontSize: 14,
  };

  return (
    <div
      style={{
        position: "sticky",
        top: 0,
        zIndex: 10,
        background: "#173f5f",
        color: "white",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "10px 18px",
        fontFamily: "Arial",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <Link to="/dashboard" style={{ color: "white", textDecoration: "none", fontWeight: 700 }}>
          HEALTHORA
        </Link>
        <Link to="/dashboard" style={{ ...navLinkStyle, background: "#20639b" }}>
          Home
        </Link>
      </div>

      <div style={{ display: "flex", gap: 8 }}>
        <Link to="/dashboard" style={{ ...navLinkStyle, background: location.pathname === "/dashboard" ? "#20639b" : "transparent" }}>
          Dashboard
        </Link>
        <Link to="/inventory" style={{ ...navLinkStyle, background: location.pathname === "/inventory" ? "#20639b" : "transparent" }}>
          Inventory
        </Link>
        <Link to="/reorder" style={{ ...navLinkStyle, background: location.pathname === "/reorder" ? "#20639b" : "transparent" }}>
          Reorder
        </Link>
        <Link to="/reports" style={{ ...navLinkStyle, background: location.pathname === "/reports" ? "#20639b" : "transparent" }}>
          Reports
        </Link>
        <Link to="/users" style={{ ...navLinkStyle, background: location.pathname === "/users" ? "#20639b" : "transparent" }}>
          Users
        </Link>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <span style={{ fontSize: 14 }}>Hi, {username}</span>
        <button
          onClick={logout}
          style={{ background: "#ef476f", border: "none", color: "white", padding: "8px 12px", borderRadius: 8, cursor: "pointer" }}
        >
          Logout
        </button>
      </div>
    </div>
  );
}

function ProtectedPage({ children }) {
  return (
    <Protected>
      <div style={{ minHeight: "100vh", background: "#f4f7fb" }}>
        <TopNav />
        <div style={{ padding: 18 }}>{children}</div>
      </div>
    </Protected>
  );
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Login />} />
        <Route
          path="/dashboard"
          element={
            <ProtectedPage>
              <Dashboard />
            </ProtectedPage>
          }
        />
        <Route
          path="/users"
          element={
            <ProtectedPage>
              <Users />
            </ProtectedPage>
          }
        />
        <Route
          path="/inventory"
          element={
            <ProtectedPage>
              <Inventory />
            </ProtectedPage>
          }
        />
        <Route
          path="/reorder"
          element={
            <ProtectedPage>
              <Reorder />
            </ProtectedPage>
          }
        />
        <Route
          path="/reports"
          element={
            <ProtectedPage>
              <Reports />
            </ProtectedPage>
          }
        />
        <Route
          path="*"
          element={<Navigate to={localStorage.getItem("token") ? "/dashboard" : "/"} replace />}
        />
      </Routes>
    </BrowserRouter>
  );
}

createRoot(document.getElementById("root")).render(<App />);
