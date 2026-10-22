import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import { ProfileProvider } from "./profileContext";
import { ToastProvider } from "./toastContext";
import "./index.css";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <BrowserRouter>
      <ProfileProvider>
        <ToastProvider>
          <App />
        </ToastProvider>
      </ProfileProvider>
    </BrowserRouter>
  </StrictMode>
);
