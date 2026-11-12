"use client";

import { ToastContainer } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";

// Global toast surface with react-toastify
function ToastProvider() {
  return (
    <ToastContainer
      position="bottom-right"
      autoClose={4000}
      hideProgressBar={false}
      newestOnTop
      closeOnClick
      rtl={false}
      pauseOnFocusLoss
      draggable
      pauseOnHover
      theme="colored"
    />
  );
}

export { ToastProvider };
