import { BrowserRouter, Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import SearchPage from "./pages/Search";
import ServicePage from "./pages/Service";
import PartnerPage from "./pages/Partner";
import Dashboard from "./pages/admin/Dashboard";
import Queue from "./pages/admin/Queue";
import Upload from "./pages/admin/Upload";

export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<SearchPage />} />
          <Route path="/service/:id" element={<ServicePage />} />
          <Route path="/partner/:id" element={<PartnerPage />} />
          <Route path="/admin" element={<Dashboard />} />
          <Route path="/admin/queue" element={<Queue />} />
          <Route path="/admin/upload" element={<Upload />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}
