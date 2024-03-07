"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation"; // Correct import path for 'useRouter'
import { useAuthStore } from "../store/useAuthStore";

const SideMenu = () => {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const logout = useAuthStore((state) => state.logout);
  const router = useRouter();

  const handleLogout = () => {
    logout();
    router.push("/");
  };

  return (
    <div>
      {/* Toggle Button */}
      <button
        className={`fixed top-4 left-4 z-30 flex items-center px-3 py-2 text-white bg-blue-600 rounded-md focus:outline-none ${
          isMenuOpen ? "left-64" : ""
        }`}
        onClick={() => setIsMenuOpen(!isMenuOpen)}
      >
        {/* Hamburger Icon */}
        <div className="space-y-1">
          <span className="block w-8 h-0.5 bg-white"></span>
          <span className="block w-8 h-0.5 bg-white"></span>
          <span className="block w-8 h-0.5 bg-white"></span>
        </div>
      </button>

      {/* Side Menu */}
      <div
        className={`fixed top-0 left-0 z-20 w-64 h-full bg-white shadow-md transform ${
          isMenuOpen ? "translate-x-0" : "-translate-x-full"
        } transition-transform duration-300 ease-in-out`}
      >
        {/* Menu Links */}
        <nav className="flex flex-col p-4">
          <Link
            className="mb-4 p-2 text-indigo-700 rounded hover:bg-indigo-50"
            href="/"
          >
            Início
          </Link>
          <Link
            className="mb-4 p-2 text-indigo-700 rounded hover:bg-indigo-50"
            href="/classify"
          >
            Classificador de labels
          </Link>
          {isAuthenticated ? (
            <button
              onClick={handleLogout}
              className="mt-auto p-2 text-indigo-700 rounded hover:bg-indigo-50"
            >
              Logout
            </button>
          ) : (
            <Link
              className="mt-auto p-2 text-indigo-700 rounded hover:bg-indigo-50"
              href="/login"
            >
              Login
            </Link>
          )}
        </nav>
      </div>

      {/* Overlay */}
      {isMenuOpen && (
        <div
          className="fixed inset-0 z-10 bg-black bg-opacity-25"
          onClick={() => setIsMenuOpen(false)}
        ></div>
      )}
    </div>
  );
};

export default SideMenu;
