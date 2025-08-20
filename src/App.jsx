import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import InventoryList from "./pages/inventory/List";
import InventoryDetail from "./pages/inventory/Detail";
import InventoryMaintenance from "./pages/inventory/Maintenance";
import InventoryStatus from "./pages/inventory/Status";
import InventoryEdit from "./pages/inventory/Edit";
import InventoryHistory from "./pages/inventory/History";
import InventoryAdd from "./pages/inventory/Add";
import LicenseList from "./pages/licenses/List";
import LicenseAssign from "./pages/licenses/Assign";
import Accessories from "./pages/accessories/Accessories";
import Printers from "./pages/printers/Printers";
import Requests from "./pages/requests/List";
import RequestCreate from "./pages/requests/Create";
import RequestToInventory from "./pages/requests/ToInventory";
import Stock from "./pages/stock/List";
import StockIn from "./pages/stock/In";
import StockOut from "./pages/stock/Out";
import StockCount from "./pages/stock/Count";
import Trash from "./pages/trash/Trash";
import Profile from "./pages/profile/Profile";
import AdminHome from "./pages/admin/Home";
import AdminUsers from "./pages/admin/Users";
import AdminCatalogs from "./pages/admin/Catalogs";
import AdminIntegrations from "./pages/admin/Integrations";
import AdminSystem from "./pages/admin/System";
import Integrations from "./pages/integrations/Integrations";
import Logs from "./pages/logs/Logs";
import Logout from "./pages/logout/Logout";
import ProtectedLayout from "./components/ProtectedLayout";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/" element={<ProtectedLayout />}>
          <Route index element={<Dashboard />} />
          <Route path="inventory">
            <Route index element={<InventoryList />} />
            <Route path=":id" element={<InventoryDetail />} />
            <Route path=":id/maintenance" element={<InventoryMaintenance />} />
            <Route path=":id/status" element={<InventoryStatus />} />
            <Route path=":id/edit" element={<InventoryEdit />} />
            <Route path=":id/history" element={<InventoryHistory />} />
          </Route>
          <Route path="licenses">
            <Route index element={<LicenseList />} />
            <Route path=":id/assign" element={<LicenseAssign />} />
          </Route>
          <Route path="accessories" element={<Accessories />} />
          <Route path="printers" element={<Printers />} />
          <Route path="requests">
            <Route index element={<Requests />} />
            <Route path="new" element={<RequestCreate />} />
            <Route path=":id/to-inventory" element={<RequestToInventory />} />
          </Route>
          <Route path="stock">
            <Route index element={<Stock />} />
            <Route path="in" element={<StockIn />} />
            <Route path="out" element={<StockOut />} />
            <Route path="count" element={<StockCount />} />
          </Route>
          <Route path="trash" element={<Trash />} />
          <Route path="profile" element={<Profile />} />
          <Route path="admin">
            <Route index element={<AdminHome />} />
            <Route path="users" element={<AdminUsers />} />
            <Route path="catalog" element={<AdminCatalogs />} />
            <Route path="integrations" element={<AdminIntegrations />} />
            <Route path="system" element={<AdminSystem />} />
          </Route>
          <Route path="integrations" element={<Integrations />} />
          <Route path="logs" element={<Logs />} />
          <Route path="inventory/add" element={<InventoryAdd />} />
          <Route path="logout" element={<Logout />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
