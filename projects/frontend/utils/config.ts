// Define a type for the configuration object
interface Config {
  apiUrl: string;
}

// This function will validate and return the environment variables
export const getConfig = (): Config => {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL;
  if (!apiUrl) {
    throw new Error("NEXT_PUBLIC_API_URL is not set");
  }

  // Trim any trailing slash from the API URL
  const trimmedApiUrl = apiUrl.replace(/\/+$/, "");

  return {
    apiUrl: trimmedApiUrl,
  };
};
