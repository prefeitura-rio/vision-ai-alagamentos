"use client";

import React, { ComponentType, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/useAuthStore";

// Make sure this is the default export
const ProtectRoute = <P extends object>(Component: ComponentType<P>) => {
  const ProtectedComponent: React.FC<P> = (props) => {
    const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
    const router = useRouter();

    useEffect(() => {
      if (!isAuthenticated) {
        router.replace("/login");
      }
    }, [isAuthenticated, router]);

    if (!isAuthenticated) {
      // Show a loading spinner or return null to render nothing
      return <div>Loading...</div>;
    }

    // Spread the props to the component
    return <Component {...props} />;
  };

  // If the component has getInitialProps, we need to copy it to the ProtectedComponent
  if (Component.getInitialProps) {
    ProtectedComponent.getInitialProps = Component.getInitialProps;
  }

  return ProtectedComponent; // This should be the returned value of the ProtectRoute function
};

export default ProtectRoute; // Ensure it's a default export
