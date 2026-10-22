import { createContext, useContext, useEffect, useState } from "react";

// Profile context: stores the acting profile (household or collector) in
// React state and localStorage so a demo survives page refreshes.
const ProfileContext = createContext(null);

export function ProfileProvider({ children }) {
  const [profile, setProfile] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem("rpx_profile"));
    } catch {
      return null;
    }
  });

  useEffect(() => {
    if (profile) localStorage.setItem("rpx_profile", JSON.stringify(profile));
    else localStorage.removeItem("rpx_profile");
  }, [profile]);

  return (
    <ProfileContext.Provider value={{ profile, setProfile }}>
      {children}
    </ProfileContext.Provider>
  );
}

export function useProfile() {
  return useContext(ProfileContext);
}
