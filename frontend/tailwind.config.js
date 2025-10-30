/** @type {import('tailwindcss').Config} */
module.exports = {
    content: [
      "./index.html",
      "./src/**/*.{js,jsx,ts,tsx}",
    ],
  theme: {
    extend: {
      colors: {
        almaBlue: "#0055B7", // deep blue
        almaLightBlue: "#9BD1F9",
        almaGray: "#F9FAFB",
      },
    },
  },
  plugins: [],
};
