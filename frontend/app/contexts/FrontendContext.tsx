"use client";

import React, { createContext, useContext, useState, ReactNode } from "react";

interface FrontendContextProps {
  isGlobalLoading: boolean;
  setGlobalLoading: (isLoading: boolean) => void;
}

const FrontendContext = createContext<FrontendContextProps | undefined>(undefined);

export const FrontendProvider = ({ children }: { children: ReactNode }) => {
  const [isGlobalLoading, setGlobalLoading] = useState(true);

  return (
    <FrontendContext.Provider value={{ isGlobalLoading, setGlobalLoading }}>
      {children}
    </FrontendContext.Provider>
  );
};

export const useFrontendContext = () => {
  const context = useContext(FrontendContext);
  if (!context) {
    throw new Error("useFrontendContext must be used within a FrontendProvider");
  }
  return context;
};
